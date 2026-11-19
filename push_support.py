import base64, json, os, threading, time
from urllib.parse import urlsplit
from flask import request, jsonify, g
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from pywebpush import webpush, WebPushException

SCHEMA = """
CREATE TABLE IF NOT EXISTS push_settings(k TEXT PRIMARY KEY,v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS push_subscriptions(
 id INTEGER PRIMARY KEY,endpoint TEXT UNIQUE NOT NULL,subscription TEXT NOT NULL,
 user_id INTEGER NOT NULL,version INTEGER NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS push_jobs(
 id INTEGER PRIMARY KEY,subscription_id INTEGER NOT NULL,report_id INTEGER,
 attempts INTEGER NOT NULL DEFAULT 0,available REAL NOT NULL DEFAULT 0,
 created REAL NOT NULL DEFAULT (strftime('%s','now')));
CREATE INDEX IF NOT EXISTS push_jobs_available ON push_jobs(available);
CREATE TRIGGER IF NOT EXISTS push_new_report AFTER INSERT ON reports BEGIN
 INSERT INTO push_jobs(subscription_id,report_id)
 SELECT s.id,NEW.id FROM push_subscriptions s JOIN users u ON u.id=s.user_id
 WHERE u.active=1 AND u.version=s.version;
END;
"""

def install(app, db, current, error):
    with db() as c:
        c.executescript(SCHEMA)
        row=c.execute("SELECT v FROM push_settings WHERE k='private_key'").fetchone()
        if not row:
            key=ec.generate_private_key(ec.SECP256R1())
            der=key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
            c.execute("INSERT OR IGNORE INTO push_settings VALUES('private_key',?)",(base64.b64encode(der).decode(),))
    with db() as c:
        private=c.execute("SELECT v FROM push_settings WHERE k='private_key'").fetchone()['v']
    key=serialization.load_der_private_key(base64.b64decode(private),password=None)
    public=base64.urlsafe_b64encode(key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)).rstrip(b'=').decode()
    started=[False];start_lock=threading.Lock()

    def contact():
        value=os.environ.get('PUSH_CONTACT',os.environ.get('GEOCODING_CONTACT','')).strip()
        return 'mailto:'+value if '@' in value and not any(x.isspace() for x in value) else None

    def validate(sub):
        if not isinstance(sub,dict):return None
        endpoint=sub.get('endpoint');keys=sub.get('keys')
        if not isinstance(endpoint,str) or len(endpoint)>4096 or not isinstance(keys,dict):return None
        try:
            u=urlsplit(endpoint);host=u.hostname or ''
            allowed=host in ('fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com') or host.endswith('.push.apple.com')
            if u.scheme!='https' or not allowed or u.username or u.password or u.port not in (None,443) or u.fragment:return None
            for name,length in [('p256dh',65),('auth',16)]:
                v=keys.get(name)
                if not isinstance(v,str) or len(v)>150:return None
                raw=base64.b64decode(v+'='*(-len(v)%4),altchars=b'-_',validate=True)
                if len(raw)!=length:return None
            return {'endpoint':endpoint,'keys':{'p256dh':keys['p256dh'],'auth':keys['auth']}}
        except (ValueError,TypeError):return None

    @app.get('/api/push/config')
    def config():
        if not current():return error('Belépés szükséges.',401)
        if not contact():return error('Állítsa be a PUSH_CONTACT vagy GEOCODING_CONTACT e-mail-címet a Railwayen.',503)
        return jsonify(publicKey=public)

    @app.post('/api/push/subscribe')
    def subscribe():
        u=current()
        if not u:return error('Belépés szükséges.',401)
        if not contact():return error('Hiányzik a push kapcsolattartói e-mail.',503)
        sub=validate(request.get_json().get('subscription'))
        if not sub:return error('Nem támogatott vagy hibás pushfeliratkozás.')
        with db() as c:
            count=c.execute('SELECT COUNT(*) FROM push_subscriptions WHERE user_id=?',(u['id'],)).fetchone()[0]
            exists=c.execute('SELECT id FROM push_subscriptions WHERE endpoint=?',(sub['endpoint'],)).fetchone()
            if count>=20 and not exists:return error('Legfeljebb 20 eszköz regisztrálható adminonként.',429)
            c.execute('INSERT INTO push_subscriptions(endpoint,subscription,user_id,version,created) VALUES(?,?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET subscription=excluded.subscription,user_id=excluded.user_id,version=excluded.version,created=excluded.created',
                      (sub['endpoint'],json.dumps(sub),u['id'],u['version'],time.time()))
        return jsonify(ok=True)

    @app.post('/api/push/unsubscribe')
    def unsubscribe():
        u=current()
        if not u:return error('Belépés szükséges.',401)
        endpoint=request.get_json().get('endpoint')
        if not isinstance(endpoint,str):return error('Hibás végpont.')
        with db() as c:c.execute('DELETE FROM push_subscriptions WHERE endpoint=? AND user_id=?',(endpoint,u['id']))
        return jsonify(ok=True)

    @app.post('/api/push/test')
    def test():
        u=current()
        if not u:return error('Belépés szükséges.',401)
        endpoint=request.get_json().get('endpoint')
        if not isinstance(endpoint,str):return error('Hibás végpont.')
        with db() as c:
            row=c.execute('SELECT id FROM push_subscriptions WHERE endpoint=? AND user_id=? AND version=?',(endpoint,u['id'],u['version'])).fetchone()
            if not row:return error('Először kapcsolja be az értesítéseket.',409)
            recent=c.execute('SELECT 1 FROM push_jobs WHERE subscription_id=? AND report_id IS NULL AND created>?',(row['id'],time.time()-30)).fetchone()
            if recent:return error('Várjon fél percet a következő tesztig.',429)
            c.execute('INSERT INTO push_jobs(subscription_id) VALUES(?)',(row['id'],))
        return jsonify(ok=True)

    def worker():
        while True:
            job=None
            try:
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    c.execute('DELETE FROM push_jobs WHERE created<? OR attempts>=8',(time.time()-86400,))
                    c.execute('DELETE FROM push_jobs WHERE subscription_id NOT IN (SELECT s.id FROM push_subscriptions s JOIN users u ON u.id=s.user_id WHERE u.active=1 AND u.version=s.version)')
                    row=c.execute('SELECT j.*,s.subscription FROM push_jobs j JOIN push_subscriptions s ON s.id=j.subscription_id WHERE j.available<=? ORDER BY j.id LIMIT 1',(time.time(),)).fetchone()
                    if row:
                        job=dict(row)
                        c.execute('UPDATE push_jobs SET available=?,attempts=attempts+1 WHERE id=?',(time.time()+120,job['id']))
                if not job:
                    time.sleep(3);continue
                subject=contact()
                if not subject:raise RuntimeError('PUSH_CONTACT nincs beállítva')
                is_test=job['report_id'] is None
                payload={'title':'Polgárdi Admin','body':'Ez szerverről küldött tesztértesítés.' if is_test else 'Új lakossági bejelentés érkezett. Nyissa meg az admint a részletekhez.',
                         'tag':'polgardi-push-test' if is_test else 'polgardi-report-'+str(job['report_id'])}
                webpush(subscription_info=json.loads(job['subscription']),data=json.dumps(payload,ensure_ascii=False),vapid_private_key=private,vapid_claims={'sub':subject},ttl=3600,timeout=10)
                with db() as c:c.execute('DELETE FROM push_jobs WHERE id=?',(job['id'],))
            except Exception as exc:
                status=getattr(getattr(exc,'response',None),'status_code',None)
                app.logger.warning('Pushküldés nem sikerült: %s, HTTP=%s',type(exc).__name__,status)
                if job:
                    try:
                        with db() as c:
                            if status in (404,410):
                                c.execute('DELETE FROM push_subscriptions WHERE id=?',(job['subscription_id'],))
                                c.execute('DELETE FROM push_jobs WHERE subscription_id=?',(job['subscription_id'],))
                            else:c.execute('UPDATE push_jobs SET available=? WHERE id=?',(time.time()+min(3600,30*2**job['attempts']),job['id']))
                    except Exception:app.logger.exception('Push küldési sor hiba')
                time.sleep(3)

    @app.before_request
    def push_start():
        with start_lock:
            if not started[0]:
                threading.Thread(target=worker,name='push-sender',daemon=True).start();started[0]=True
        if request.path=='/api/logout' and request.method=='POST':
            u=current();g.push_logout_user=u['id'] if u else None

    @app.after_request
    def revoke_logout(response):
        uid=getattr(g,'push_logout_user',None)
        if uid and response.status_code<300:
            with db() as c:c.execute('DELETE FROM push_subscriptions WHERE user_id=?',(uid,))
        return response
