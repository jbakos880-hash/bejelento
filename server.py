import os, sqlite3, secrets, time
from pathlib import Path
from functools import wraps
from flask import Flask, request, session, jsonify, send_from_directory
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
ROOT=Path(__file__).resolve().parent
DATA_DIR=Path(os.environ.get('DATA_DIR', str(ROOT/'data'))).resolve()
DATA_DIR.mkdir(parents=True,exist_ok=True)
DB=DATA_DIR/'reports.sqlite3'
app=Flask(__name__,static_folder=None)
PUBLIC_ORIGIN=os.environ.get('PUBLIC_ORIGIN','http://localhost:8000').rstrip('/')
from urllib.parse import urlsplit
origin_parts=urlsplit(PUBLIC_ORIGIN)
if origin_parts.scheme not in ('http','https') or not origin_parts.netloc or origin_parts.path:
    raise RuntimeError('PUBLIC_ORIGIN: teljes eredet szükséges, útvonal nélkül.')
PRODUCTION=origin_parts.scheme=='https'
app.secret_key=os.environ.get('SECRET_KEY') or (None if PRODUCTION else secrets.token_hex(32))
if not app.secret_key or len(app.secret_key)<32:
    raise RuntimeError('Legalább 32 karakteres SECRET_KEY szükséges.')
app.config['DATA_DIR']=str(DATA_DIR)
app.config.update(MAX_CONTENT_LENGTH=30000,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',SESSION_COOKIE_SECURE=PRODUCTION,PERMANENT_SESSION_LIFETIME=3600)
ph=PasswordHasher();attempts={}
def db():
    c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def email_ok(v):return isinstance(v,str) and len(v)<=200 and '@' in v and '.' in v.rsplit('@',1)[-1] and not any(c.isspace() for c in v)
with db() as c:
    c.execute("CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,name TEXT,email TEXT,category TEXT,address TEXT,description TEXT,status TEXT DEFAULT 'Beérkezett',created TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,version INTEGER NOT NULL DEFAULT 1)")
    c.execute("CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,target INTEGER,created TEXT DEFAULT CURRENT_TIMESTAMP)")
    if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0:
        e=os.environ.get('ADMIN_EMAIL','').strip().lower();p=os.environ.get('ADMIN_PASSWORD','')
        if not email_ok(e) or len(p)<12:raise SystemExit('Elso inditas: allitsa be az ADMIN_EMAIL es legalabb 12 karakteres ADMIN_PASSWORD valtozot.')
        c.execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)',(e,ph.hash(p),'owner'))
def error(msg,status=400):return jsonify(error=msg),status
def current():
    with db() as c:u=c.execute('SELECT id,email,role,active,version FROM users WHERE id=?',(session.get('uid'),)).fetchone()
    if not u or not u['active'] or u['version']!=session.get('version'):return None
    return dict(u)
def protected(owner=False):
    def deco(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            u=current()
            if not u:return error('Belépés szükséges.',401)
            if owner and u['role']!='owner':return error('Ehhez főadmin jogosultság szükséges.',403)
            return fn(u,*a,**kw)
        return wrapped
    return deco
@app.before_request
def guard():
    if request.host != origin_parts.netloc:return error('Tiltott kiszolgálónév.',403)
    if request.method=='POST':
        if request.path in ('/api/reports','/api/reports-with-photos') and os.environ.get('PUBLIC_SUBMISSIONS_ENABLED')!='true':
            return error('A bejelentések fogadása még nem indult el.',503)
        if request.headers.get('Origin') != PUBLIC_ORIGIN:return error('Tiltott eredet.',403)
        if not request.is_json or not isinstance(request.get_json(silent=True),dict):return error('JSON objektum szükséges.',415)
        if request.path not in ('/api/login','/api/reports','/api/reports-with-photos','/api/reverse-address'):
            expected=session.get('csrf');got=request.headers.get('X-CSRF-Token','')
            if not expected or not secrets.compare_digest(expected,got):return error('Lejárt vagy hibás kérés. Frissítse az oldalt.',403)
@app.after_request
def headers(r):
    r.headers['Cache-Control']='no-store';r.headers['X-Content-Type-Options']='nosniff';r.headers['X-Frame-Options']='DENY';r.headers['Referrer-Policy']='strict-origin-when-cross-origin';return r
@app.errorhandler(413)
def large(e):return error('Túl nagy kérés.',413)
@app.route('/')
def index():return send_from_directory(ROOT,'index.html')
@app.route('/admin')
def admin():return send_from_directory(ROOT,'admin.html')
@app.get('/adatkezeles')
def privacy():return send_from_directory(ROOT,'adatkezeles.html')
@app.route('/integration.js')
def integration():return send_from_directory(ROOT,'integration.js')
@app.route('/assets/polgardi-cimer.png')
def crest():return send_from_directory(ROOT/'assets','polgardi-cimer.png')
@app.post('/api/login')
def login():
    d=request.get_json();email=str(d.get('email','')).strip().lower();password=d.get('password','');now=time.time();ip=request.remote_addr
    keys=['ip:'+ip,'email:'+email];blocked=False
    for key in keys:
        attempts[key]=[t for t in attempts.get(key,[]) if t>now-300]
        blocked=blocked or len(attempts[key])>=10
    if blocked:return error('Túl sok próbálkozás. Várjon 5 percet.',429)
    with db() as c:u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    ok=False
    try:ok=ph.verify(u['password_hash'] if u else DUMMY_HASH,password) if isinstance(password,str) and len(password)<=1024 else False
    except (VerificationError,InvalidHashError):pass
    if not u or not u['active'] or not ok:
        for key in keys:attempts[key].append(now)
        return error('Hibás e-mail-cím vagy jelszó.',401)
    session.clear();session.permanent=True;session['uid']=u['id'];session['version']=u['version'];session['csrf']=secrets.token_urlsafe(32)
    with db() as c:c.execute('INSERT INTO audit(actor,action,target) VALUES(?,?,?)',(u['id'],'login',u['id']))
    return jsonify(ok=True)
@app.get('/api/me')
@protected()
def me(u):return jsonify(user=u,csrf=session['csrf'])
@app.post('/api/logout')
@protected()
def logout(u):session.clear();return jsonify(ok=True)
@app.route('/api/reports',methods=['GET','POST'])
def reports():
    if request.method=='GET':
        if not current():return error('Belépés szükséges.',401)
        with db() as c:return jsonify([dict(r) for r in c.execute('SELECT * FROM reports ORDER BY id DESC')])
    d=request.get_json();fields=['name','email','category','address','description'];limits=[100,200,100,300,5000]
    if any(not isinstance(d.get(k),str) or not d[k].strip() or len(d[k])>limit for k,limit in zip(fields,limits)):return error('Hiányzó vagy túl hosszú mező.')
    if not email_ok(d['email']) or len(d['description'].strip())<10:return error('Ellenőrizze az e-mailt és a leírást.')
    if d['category'] not in ['Úthiba, kátyú','Közvilágítás','Illegális hulladék','Zöldterület, fa','Közterületi berendezés','Egyéb probléma']:return error('Hibás kategória.')
    with db() as c:r=c.execute('INSERT INTO reports(name,email,category,address,description) VALUES(?,?,?,?,?)',[d[k].strip() for k in fields]);rid=r.lastrowid
    return jsonify(id=rid),201
@app.post('/api/status')
@protected()
def status(u):
    d=request.get_json()
    if type(d.get('id')) is not int or d.get('status') not in ['Beérkezett','Folyamatban','Megoldva','Elutasítva']:return error('Hibás adat.')
    with db() as c:
        r=c.execute('UPDATE reports SET status=? WHERE id=?',(d['status'],d['id']))
        if r.rowcount!=1:return error('Nem található.',404)
        c.execute('INSERT INTO audit(actor,action,target) VALUES(?,?,?)',(u['id'],'status:'+d['status'],d['id']))
    return jsonify(ok=True)
@app.get('/api/users')
@protected(owner=True)
def users(u):
    with db() as c:return jsonify([dict(r) for r in c.execute('SELECT id,email,role,active FROM users ORDER BY id')])
@app.post('/api/users')
@protected(owner=True)
def adduser(u):
    d=request.get_json();e=str(d.get('email','')).strip().lower();p=d.get('password','');role=d.get('role')
    if not email_ok(e) or not isinstance(p,str) or not 12<=len(p)<=1024 or role not in ('owner','staff'):return error('Érvényes e-mail, legalább 12 karakteres jelszó és szerepkör szükséges.')
    try:
        hashed=ph.hash(p)
        with db() as c:
            r=c.execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)',(e,hashed,role));c.execute('INSERT INTO audit(actor,action,target) VALUES(?,?,?)',(u['id'],'create-user',r.lastrowid))
    except sqlite3.IntegrityError:return error('Ez az e-mail-cím már szerepel.')
    return jsonify(ok=True),201
@app.post('/api/user-active')
@protected(owner=True)
def toggle(u):
    d=request.get_json()
    if type(d.get('id')) is not int or type(d.get('active')) is not bool:return error('Hibás kérés.')
    if d['id']==u['id']:return error('Saját fiókját itt nem tilthatja le.')
    with db() as c:
        r=c.execute('UPDATE users SET active=?,version=version+1 WHERE id=?',(int(d['active']),d['id']))
        if r.rowcount!=1:return error('Nem található.',404)
        c.execute('INSERT INTO audit(actor,action,target) VALUES(?,?,?)',(u['id'],'enable-user' if d['active'] else 'disable-user',d['id']))
    return jsonify(ok=True)
@app.post('/api/password')
@protected()
def password(u):
    d=request.get_json();old=d.get('old','');new=d.get('new','')
    if not isinstance(old,str) or not isinstance(new,str) or not 12<=len(new)<=1024:return error('Az új jelszó legalább 12 karakter legyen.')
    with db() as c:
        row=c.execute('SELECT password_hash FROM users WHERE id=?',(u['id'],)).fetchone()
        try:ph.verify(row['password_hash'],old)
        except (VerificationError,InvalidHashError):return error('Hibás jelenlegi jelszó.',401)
        c.execute('UPDATE users SET password_hash=?,version=version+1 WHERE id=?',(ph.hash(new),u['id']))
        c.execute('INSERT INTO audit(actor,action,target) VALUES(?,?,?)',(u['id'],'password-change',u['id']))
    session.clear();return jsonify(ok=True)
DUMMY_HASH=ph.hash(secrets.token_urlsafe(32))
from photo_support import install as install_photos
install_photos(app, db, current, error, ROOT)
@app.get('/photos-admin.js')
def photos_admin_js():
    return send_from_directory(ROOT, 'photos-admin.js')

from map_support import install as install_maps
install_maps(app, db, current, error, ROOT)

from pwa_support import install as install_pwa
install_pwa(app, ROOT)

from admin_pwa_support import install as install_admin_pwa
install_admin_pwa(app, db, current, error, ROOT)

from delete_support import install as install_delete
install_delete(app, db, protected, error, ROOT)

from public_support import install as install_public
install_public(app, db, protected, error, ROOT)

from admin_filter_support import install as install_admin_filters
install_admin_filters(app, ROOT)

if __name__=='__main__':
    print('Helyi felulet: http://localhost:8000 | Admin: http://localhost:8000/admin')
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT','8000')),debug=False)
