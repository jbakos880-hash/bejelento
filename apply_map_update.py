from pathlib import Path
from datetime import datetime
import shutil,ast
root=Path(__file__).resolve().parent
names=['server.py','photo_support.py','integration.js','index.html','admin.html','map_support.py','map-form.js','map-admin.js']
for n in names:
    if not (root/n).is_file():raise SystemExit('Hianyzo fajl: '+n)
s=(root/'server.py').read_text(encoding='utf-8');photo=(root/'photo_support.py').read_text(encoding='utf-8');js=(root/'integration.js').read_text(encoding='utf-8');index=(root/'index.html').read_text(encoding='utf-8');admin=(root/'admin.html').read_text(encoding='utf-8')
if 'install_maps(app' in s:raise SystemExit('A terkepes frissites mar telepitve van.')
marker="if __name__=='__main__':"
if s.count(marker)!=1 or 'install_photos(app' not in s:raise SystemExit('Nem a vart fenykepes szervervaltozat.')
addition='from map_support import install as install_maps\ninstall_maps(app, db, current, error, ROOT)\n\n'
s=s.replace(marker,addition+marker,1)
needle="        processed=[]"
validation="        lat=d.get('latitude');lon=d.get('longitude')\n        import math\n        if (lat is None)!=(lon is None):return error('Mindkét koordinátát adja meg, vagy törölje mindkettőt.')\n        if lat is not None:\n            if type(lat) not in (float,int) or type(lon) not in (float,int) or not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:return error('Hibás koordináták.')\n"
if photo.count(needle)!=1:raise SystemExit('Nem a vart photo_support.py.')
photo=photo.replace(needle,validation+needle,1)
needle2='rid=r.lastrowid\n                for content in processed:'
replacement="rid=r.lastrowid\n                c.execute('UPDATE reports SET latitude=?,longitude=? WHERE id=?',(lat,lon,rid))\n                for content in processed:"
if photo.count(needle2)!=1:raise SystemExit('Nem talalhato a kepmentesi tranzakcio. Nem modositottunk semmit.')
photo=photo.replace(needle2,replacement,1)
needle3="data.photos=await Promise.all(files.map(encode));"
extra="const lat=f.querySelector('#latitude'),lon=f.querySelector('#longitude');data.latitude=lat&&lat.value!==''?Number(lat.value):null;data.longitude=lon&&lon.value!==''?Number(lon.value):null;"
if js.count(needle3)!=1:raise SystemExit('Nem a vart integration.js.')
js=js.replace(needle3,extra+needle3,1)
tag='<script src="map-form.js"></script>'
if '</body>' not in index or '</body>' not in admin:raise SystemExit('Hianyzo body zarotag.')
index=index.replace('</body>',tag+'</body>',1)
admin=admin.replace('</body>','<script src="/map-admin.js"></script></body>',1)
for code in (s,photo):ast.parse(code)
backup=root/('map-code-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
for n in ['server.py','photo_support.py','integration.js','index.html','admin.html']:shutil.copy2(root/n,backup/n)
for n,content in {'server.py':s,'photo_support.py':photo,'integration.js':js,'index.html':index,'admin.html':admin}.items():(root/n).write_text(content,encoding='utf-8')
print('Terkepes frissites kesz. Inditsa ujra a szervert: py server.py')
