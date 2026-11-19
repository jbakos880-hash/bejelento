from pathlib import Path
from datetime import datetime
import shutil, ast
root=Path(__file__).resolve().parent
required=['server.py','admin.html','integration.js','photo_support.py','photos-admin.js']
for n in required:
    if not (root/n).is_file():raise SystemExit('Hianyzo fajl: '+n+'. Masolja a csomagot a projekt mappajaba.')
p=root/'server.py';s=p.read_text(encoding='utf-8');a=(root/'admin.html').read_text(encoding='utf-8')
marker="if __name__=='__main__':"
if marker not in s:raise SystemExit('Nem a vart server.py valtozat. Nem modositottunk semmit.')
if 'def current()' not in s or "@app.post('/api/user-active')" not in s:raise SystemExit('A tobbfelhasznalos Flask szerver szukseges.')
addition="from photo_support import install as install_photos\ninstall_photos(app, db, current, error, ROOT)\n@app.get('/photos-admin.js')\ndef photos_admin_js():\n    return send_from_directory(ROOT, 'photos-admin.js')\n\n"
updated=s if 'install_photos(app' in s else s.replace(marker,addition+marker,1)
ast.parse(updated)
tag='<script src="/photos-admin.js"></script>'
if tag not in a:
    if '</body>' not in a:raise SystemExit('Hianyzo body zarotag az admin.html fajlban.')
    a=a.replace('</body>',tag+'</body>',1)
backup=root/('photo-code-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
for n in ['server.py','admin.html','integration.js']:shutil.copy2(root/n,backup/n)
p.write_text(updated,encoding='utf-8');(root/'admin.html').write_text(a,encoding='utf-8')
shutil.copy2(root/'integration-photos.js',root/'integration.js')
print('Frissites kesz. Kodmentes: '+backup.name+'. Kovetkezo: py server.py')
