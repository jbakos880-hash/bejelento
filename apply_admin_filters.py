from pathlib import Path
from datetime import datetime
import ast,shutil,os
root=Path(__file__).resolve().parent
for name in ['server.py','admin.html','admin_filter_support.py','admin-filters.js']:
    if not (root/name).is_file():raise SystemExit('Hianyzo fajl: '+name+'. Tegye a csomagot a server.py melle.')
s=(root/'server.py').read_text(encoding='utf-8');a=(root/'admin.html').read_text(encoding='utf-8')
if 'install_admin_filters(app' in s or '/admin-filters.js' in a:raise SystemExit('A szurofrissites mar telepitve van. Nem tortent modositas.')
marker="if __name__=='__main__':"
required=['id="reports"','id="panel"','/publication-admin.js','/delete-admin.js','/admin/pwa/admin.js']
if s.count(marker)!=1 or a.count('</body>')!=1 or not all(x in a for x in required):raise SystemExit('Eltero fajlszerkezet. Nem tortent modositas; kuldje el az aktualis server.py es admin.html fajlt.')
s=s.replace(marker,'from admin_filter_support import install as install_admin_filters\ninstall_admin_filters(app, ROOT)\n\n'+marker,1);a=a.replace('</body>','<script src="/admin-filters.js"></script></body>',1)
ast.parse(s);ast.parse((root/'admin_filter_support.py').read_text(encoding='utf-8'))
backup=root/('admin-filter-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
for name in ['server.py','admin.html']:shutil.copy2(root/name,backup/name)
try:
    for name,content in [('server.py',s),('admin.html',a)]:
        p=root/(name+'.filters.tmp');p.write_text(content,encoding='utf-8');os.replace(p,root/name)
except Exception:
    for name in ['server.py','admin.html']:shutil.copy2(backup/name,root/name)
    raise
print('Adminszurok telepitve. Inditsa ujra: py server.py. Admin PWA: Ctrl+R.')
