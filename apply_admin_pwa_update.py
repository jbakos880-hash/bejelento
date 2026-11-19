from pathlib import Path
from datetime import datetime
import ast,hashlib,shutil,os
ROOT=Path(__file__).resolve().parent
EXPECTED={'server.py': '694f1f0655e6de81dcae56a5b5a34ee0e57041446ad34dfe01e88549bc59a834', 'admin.html': '0ba2409543503eefe61469812b31ee1091d25e8659f6b5c2912b1dc1b9bbef79'}
for name,expected in EXPECTED.items():
    p=ROOT/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
        raise SystemExit('Eltero vagy hianyzo fajl: '+name+'. Nem tortent modositas; ezt a frissitest a feltoltott valtozathoz keszitettuk.')
for name in ['admin_pwa_support.py','admin_pwa/admin.updated.html','admin_pwa/admin.js','admin_pwa/sw.js','admin_pwa/manifest.webmanifest','admin_pwa/icon-192.png','admin_pwa/icon-512.png','admin_pwa/apple-touch-icon.png','admin_pwa/offline.html']:
    if not (ROOT/name).is_file():raise SystemExit('Hianyzo csomagfajl: '+name)
s=(ROOT/'server.py').read_text(encoding='utf-8')
marker="if __name__=='__main__':"
if s.count(marker)!=1:raise SystemExit('Nem vart szerver szerkezet. Nem tortent modositas.')
s=s.replace(marker,'from admin_pwa_support import install as install_admin_pwa\ninstall_admin_pwa(app, db, current, error, ROOT)\n\n'+marker,1)
ast.parse(s);ast.parse((ROOT/'admin_pwa_support.py').read_text(encoding='utf-8'))
a=(ROOT/'admin_pwa/admin.updated.html').read_text(encoding='utf-8')
backup=ROOT/('admin-pwa-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
for name in EXPECTED:shutil.copy2(ROOT/name,backup/name)
try:
    for name,content in [('server.py',s),('admin.html',a)]:
        temp=ROOT/(name+'.admin-update.tmp');temp.write_text(content,encoding='utf-8');os.replace(temp,ROOT/name)
except Exception:
    for name in EXPECTED:shutil.copy2(backup/name,ROOT/name)
    raise
print('Sikeres frissites. Inditas: py server.py | Admin: http://localhost:8000/admin/')
