from pathlib import Path
from datetime import datetime
import ast,shutil
root=Path(__file__).resolve().parent
for n in ['server.py','index.html','admin.html','photo_support.py','integration.js','map_support_v2.py','map-form-v2.js','map-admin-v2.js']:
    if not (root/n).is_file():raise SystemExit('Hianyzo fajl: '+n)
s=(root/'server.py').read_text(encoding='utf-8');index=(root/'index.html').read_text(encoding='utf-8');admin=(root/'admin.html').read_text(encoding='utf-8')
if 'install_maps(app' not in s:raise SystemExit('A korabbi terkepes frissites szukseges.')
old="if request.path not in ('/api/login','/api/reports','/api/reports-with-photos'):"
new="if request.path not in ('/api/login','/api/reports','/api/reports-with-photos','/api/reverse-address'):"
if new not in s:
    if s.count(old)!=1:raise SystemExit('Nem a vart CSRF-feltetel. Nem modositottunk semmit.')
    s=s.replace(old,new,1)
if '</body>' not in index or '</body>' not in admin:raise SystemExit('Hianyzo body zarotag.')
# Keep exactly one map script, after the integration code.
for tag in ['<script src="map-form.js"></script>','<script src="/map-form.js"></script>']:index=index.replace(tag,'')
index=index.replace('</body>','<script src="/map-form.js"></script></body>',1)
for tag in ['<script src="map-admin.js"></script>','<script src="/map-admin.js"></script>']:admin=admin.replace(tag,'')
admin=admin.replace('</body>','<script src="/map-admin.js"></script></body>',1)
ast.parse(s);ast.parse((root/'map_support_v2.py').read_text(encoding='utf-8'))
backup=root/('address-map-code-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
for n in ['server.py','index.html','admin.html','map_support.py','map-form.js','map-admin.js']:
    if (root/n).exists():shutil.copy2(root/n,backup/n)
for n,v in {'server.py':s,'index.html':index,'admin.html':admin}.items():(root/n).write_text(v,encoding='utf-8')
for src,dest in [('map_support_v2.py','map_support.py'),('map-form-v2.js','map-form.js'),('map-admin-v2.js','map-admin.js')]:shutil.copy2(root/src,root/dest)
print('Frissites kesz. Allitsa be a GEOCODING_CONTACT valtozot, majd: py server.py')
