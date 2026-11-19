import os,json,time,threading,urllib.request,urllib.parse,urllib.error,math
from flask import request,jsonify,send_from_directory

def install(app,db,current,error,ROOT):
    lock=threading.Lock();last=[0.0]
    with db() as c:
        cols={r['name'] for r in c.execute('PRAGMA table_info(reports)')}
        if 'latitude' not in cols:c.execute('ALTER TABLE reports ADD COLUMN latitude REAL')
        if 'longitude' not in cols:c.execute('ALTER TABLE reports ADD COLUMN longitude REAL')
        c.execute('CREATE TABLE IF NOT EXISTS address_cache(key TEXT PRIMARY KEY,result TEXT NOT NULL,created REAL NOT NULL)')
    @app.get('/map-form.js')
    def map_form_script():return send_from_directory(ROOT,'map-form.js')
    @app.get('/map-admin.js')
    def map_admin_script():return send_from_directory(ROOT,'map-admin.js')
    @app.get('/api/report-location/<int:rid>')
    def report_location(rid):
        if not current():return error('Belépés szükséges.',401)
        with db() as c:r=c.execute('SELECT latitude,longitude,address FROM reports WHERE id=?',(rid,)).fetchone()
        if not r:return error('Nem található.',404)
        return jsonify(dict(r))
    @app.post('/api/reverse-address')
    def reverse_address():
        d=request.get_json();lat=d.get('latitude');lon=d.get('longitude')
        if type(lat) not in (int,float) or type(lon) not in (int,float) or not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:return error('Hibás koordináták.')
        contact=os.environ.get('GEOCODING_CONTACT','').strip()
        if '@' not in contact or len(contact)>200:return error('A címkeresés nincs beállítva. A szerver indítása előtt állítsa be a GEOCODING_CONTACT változót. A címet addig kézzel adja meg.',503)
        key=f'{lat:.6f},{lon:.6f}'
        with db() as c:r=c.execute('SELECT result FROM address_cache WHERE key=? AND created>?',(key,time.time()-86400)).fetchone()
        if r:return jsonify(json.loads(r['result']))
        if not lock.acquire(blocking=False):return error('A címkereső foglalt. Várjon néhány másodpercet, majd próbálja újra.',429)
        try:
            delay=1.1-(time.monotonic()-last[0])
            if delay>0:time.sleep(delay)
            last[0]=time.monotonic()
            query=urllib.parse.urlencode({'format':'jsonv2','lat':f'{lat:.6f}','lon':f'{lon:.6f}','addressdetails':1,'zoom':18,'accept-language':'hu'})
            req=urllib.request.Request('https://nominatim.openstreetmap.org/reverse?'+query,headers={'User-Agent':'PolgardiBejelenteskezelo-LocalTest/1.0 (contact: '+contact+')','Accept':'application/json'})
            try:
                with urllib.request.urlopen(req,timeout=12) as response:raw=json.loads(response.read(150000))
            except (urllib.error.URLError,TimeoutError,ValueError,OSError):return error('A külső címkereső nem érhető el. Adja meg a címet kézzel.',502)
            a=raw.get('address',{});town=a.get('city') or a.get('town') or a.get('village') or a.get('municipality') or '';street=a.get('road') or a.get('pedestrian') or a.get('residential') or a.get('footway') or '';number=a.get('house_number','')
            address=', '.join(x for x in [town,' '.join(x for x in [street,number] if x)] if x)
            result={'address':address,'has_house_number':bool(number),'has_street':bool(street),'note':'Címjavaslat: ellenőrizze és szükség esetén javítsa.'}
            with db() as c:c.execute('INSERT OR REPLACE INTO address_cache(key,result,created) VALUES(?,?,?)',(key,json.dumps(result,ensure_ascii=False),time.time()))
            return jsonify(result)
        finally:lock.release()
