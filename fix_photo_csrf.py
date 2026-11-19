from pathlib import Path
from datetime import datetime
import ast, shutil
p=Path(__file__).resolve().parent/'server.py'
if not p.is_file():raise SystemExit('Nem talalhato a server.py. Masolja a javitot a projekt mappajaba.')
s=p.read_text(encoding='utf-8')
old="if request.path not in ('/api/login','/api/reports'):"
new="if request.path not in ('/api/login','/api/reports','/api/reports-with-photos'):"
if new in s:raise SystemExit('Ez a javitas mar szerepel a fajlban.')
if s.count(old)!=1:raise SystemExit('Nem a vart kodvaltozat: nem modositottunk semmit. Kerjen segitseget.')
updated=s.replace(old,new,1);ast.parse(updated)
backup=p.with_name('server-before-photo-csrf-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.py.bak')
shutil.copy2(p,backup);p.write_text(updated,encoding='utf-8')
print('Javitas kesz. Az adminmuveletek CSRF-vedelme megmaradt. Inditsa ujra: py server.py')
