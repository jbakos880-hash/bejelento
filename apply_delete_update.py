from pathlib import Path
from datetime import datetime
import hashlib,ast,shutil,sqlite3,os
root=Path(__file__).resolve().parent
expected={'server.py': '8775a76e5727f45c774019065a9c9e1c695e72414afd09391efa295313b50a24', 'admin.html': 'd0b9067bdaf755133d513a1eb89d1c2ae1baa425748e814850d3430be2d7aa68', 'photo_support.py': '680560766ad99bbe4039a3aef4553a147bd54ad0aacabc4e1d76dc13db1e6800', 'map_support.py': 'dfaa4f5e488af250fcd84cf8fa1b4475885d1d3a0c45fd466a6dbf1227364393'}
for name,digest in expected.items():
    p=root/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise SystemExit('Eltero vagy hianyzo fajl: '+name+'. Nem tortent frissites.')
for n in ['delete_core.py','delete_support.py','delete-admin.js']:
    if not (root/n).is_file():raise SystemExit('Hianyzo csomagfajl: '+n)
for n in ['delete_core.py','delete_support.py']:ast.parse((root/n).read_text(encoding='utf-8'))
s=(root/'server.py').read_text(encoding='utf-8');a=(root/'admin.html').read_text(encoding='utf-8')
marker="if __name__=='__main__':"
if s.count(marker)!=1 or a.count('</body>')!=1:raise SystemExit('Nem vart fajlszerkezet.')
s=s.replace(marker,'from delete_support import install as install_delete\ninstall_delete(app, db, protected, error, ROOT)\n\n'+marker,1);a=a.replace('</body>','<script src="/delete-admin.js"></script></body>',1);ast.parse(s)
backup=root/('delete-update-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
for n in ['server.py','admin.html']:shutil.copy2(root/n,backup/n)
dbfile=root/'data'/'reports.sqlite3'
if dbfile.is_file():
    src=sqlite3.connect('file:'+dbfile.as_posix()+'?mode=ro',uri=True);dst=sqlite3.connect(backup/'reports.sqlite3')
    try:src.backup(dst)
    finally:dst.close();src.close()
try:
    for n,text in [('server.py',s),('admin.html',a)]:
        p=root/(n+'.delete-update.tmp');p.write_text(text,encoding='utf-8');os.replace(p,root/n)
except Exception:
    for n in ['server.py','admin.html']:shutil.copy2(backup/n,root/n)
    raise
print('Frissites kesz. Inditsa ujra: py server.py. Az elso inditas megorzi a bejelenteseket es atallitja az azonosito-kiosztast. Az admin PWA-ban Ctrl+R.')
