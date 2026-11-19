from pathlib import Path
from datetime import datetime
import hashlib,ast,sqlite3,shutil,os
root=Path(__file__).resolve().parent
expected={'server.py': '9c06b537f14a2f2c8051e8829b744737adb373e5bc97b2f133da46ad16ad3450', 'admin.html': 'a79e219739cca8f3a4c83be84f63d06f7ba44cf540d79b0bec0a8665fbcae66d', 'index.html': 'bc7d2fc5323003f096775fa2a3a2f5ff2521c6a8a829dfc6ef35c3baca3638ee'}
for name,digest in expected.items():
    p=root/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise SystemExit('Eltero vagy hianyzo fajl: '+name+'. Nem tortent frissites; ezt a csomagot a feltoltott valtozathoz keszitettuk.')
for name in ['public_core.py','public_support.py','public-reports.js','publication-admin.js','public_update/index.updated.html','public_update/admin.updated.html']:
    if not (root/name).is_file():raise SystemExit('Hianyzo csomagfajl: '+name)
for name in ['public_core.py','public_support.py']:ast.parse((root/name).read_text(encoding='utf-8'))
s=(root/'server.py').read_text(encoding='utf-8');marker="if __name__=='__main__':"
if s.count(marker)!=1:raise SystemExit('Nem vart szerver szerkezet.')
s=s.replace(marker,'from public_support import install as install_public\ninstall_public(app, db, protected, error, ROOT)\n\n'+marker,1);ast.parse(s)
contents={'server.py':s,'admin.html':(root/'public_update/admin.updated.html').read_text(encoding='utf-8'),'index.html':(root/'public_update/index.updated.html').read_text(encoding='utf-8')}
backup=root/('public-update-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
for name in expected:shutil.copy2(root/name,backup/name)
p=root/'data'/'reports.sqlite3'
if p.is_file():
    src=sqlite3.connect('file:'+p.as_posix()+'?mode=ro',uri=True);dst=sqlite3.connect(backup/'reports.sqlite3')
    try:src.backup(dst)
    finally:dst.close();src.close()
try:
    for name,content in contents.items():
        tmp=root/(name+'.public-update.tmp');tmp.write_text(content,encoding='utf-8');os.replace(tmp,root/name)
except Exception:
    for name in expected:shutil.copy2(backup/name,root/name)
    raise
print('Nyilvanos lista frissites telepitve. Inditas: py server.py. A lakossagi es admin PWA-t is toltse ujra Ctrl+R-rel.')
