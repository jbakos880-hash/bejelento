import base64, binascii, io, secrets, warnings
from pathlib import Path
from flask import request, jsonify, send_file
from PIL import Image, ImageOps, UnidentifiedImageError

def install(app, db, current, error, ROOT):
    store=Path(app.config['DATA_DIR'])/'photos';store.mkdir(exist_ok=True)
    app.config['MAX_CONTENT_LENGTH']=22*1024*1024
    with db() as c:c.execute('CREATE TABLE IF NOT EXISTS photos(id INTEGER PRIMARY KEY,report_id INTEGER NOT NULL,filename TEXT UNIQUE NOT NULL)')
    @app.post('/api/reports-with-photos')
    def report_photos():
        d=request.get_json();fields=['name','email','category','address','description'];limits=[100,200,100,300,5000]
        if any(not isinstance(d.get(k),str) or not d[k].strip() or len(d[k])>lim for k,lim in zip(fields,limits)):return error('Hiányzó vagy túl hosszú mező.')
        if '@' not in d['email'] or len(d['description'].strip())<10:return error('Ellenőrizze az e-mailt és a leírást.')
        if d['category'] not in ['Úthiba, kátyú','Közvilágítás','Illegális hulladék','Zöldterület, fa','Közterületi berendezés','Egyéb probléma']:return error('Hibás kategória.')
        photos=d.get('photos',[])
        if not isinstance(photos,list) or len(photos)>3:return error('Legfeljebb három kép tölthető fel.')
        lat=d.get('latitude');lon=d.get('longitude')
        import math
        if (lat is None)!=(lon is None):return error('Mindkét koordinátát adja meg, vagy törölje mindkettőt.')
        if lat is not None:
            if type(lat) not in (float,int) or type(lon) not in (float,int) or not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:return error('Hibás koordináták.')
        processed=[]
        for item in photos:
            if not isinstance(item,str) or len(item)>6990510:return error('Túl nagy vagy hibás kép.')
            try:
                raw=base64.b64decode(item,validate=True)
                if not raw or len(raw)>5*1024*1024:return error('Képenként legfeljebb 5 MB tölthető fel.')
                with warnings.catch_warnings():
                    warnings.simplefilter('error',Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(raw)) as im:
                        if im.format not in ('JPEG','PNG','WEBP'):return error('Csak JPG, PNG és WebP képek engedélyezettek.')
                        if im.width*im.height>20000000 or im.width>16000 or im.height>16000:return error('Túl nagy képfelbontás. Legfeljebb 20 megapixel engedélyezett.')
                        im.load();fixed=ImageOps.exif_transpose(im);fixed.thumbnail((2400,2400))
                        rgb=Image.new('RGB',fixed.size,'white')
                        if 'A' in fixed.getbands():rgb.paste(fixed.convert('RGB'),mask=fixed.getchannel('A'))
                        else:rgb.paste(fixed.convert('RGB'))
                        output=io.BytesIO();rgb.save(output,format='JPEG',quality=88);processed.append(output.getvalue())
            except (ValueError,binascii.Error,UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):return error('Az egyik kép sérült vagy nem támogatott.')
        written=[]
        try:
            with db() as c:
                r=c.execute('INSERT INTO reports(name,email,category,address,description) VALUES(?,?,?,?,?)',[d[k].strip() for k in fields]);rid=r.lastrowid
                c.execute('UPDATE reports SET latitude=?,longitude=? WHERE id=?',(lat,lon,rid))
                for content in processed:
                    name=secrets.token_hex(24)+'.jpg';path=store/name
                    path.write_bytes(content);written.append(path)
                    c.execute('INSERT INTO photos(report_id,filename) VALUES(?,?)',(rid,name))
        except Exception:
            for p in written:p.unlink(missing_ok=True)
            return error('Nem sikerült menteni a bejelentést és képeit.',500)
        return jsonify(id=rid,photo_count=len(processed)),201
    @app.get('/api/report-photos/<int:rid>')
    def list_photos(rid):
        if not current():return error('Belépés szükséges.',401)
        with db() as c:rows=c.execute('SELECT id FROM photos WHERE report_id=? ORDER BY id',(rid,)).fetchall()
        return jsonify([{'id':r['id'],'url':'/api/photo/'+str(r['id'])} for r in rows])
    @app.get('/api/photo/<int:pid>')
    def get_photo(pid):
        if not current():return error('Belépés szükséges.',401)
        with db() as c:r=c.execute('SELECT filename FROM photos WHERE id=?',(pid,)).fetchone()
        if not r:return error('Nem található.',404)
        p=store/r['filename']
        if not p.is_file():return error('A képfájl nem található.',404)
        return send_file(p,mimetype='image/jpeg',download_name='bejelentes-kep.jpg',conditional=False)
