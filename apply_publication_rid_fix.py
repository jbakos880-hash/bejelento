from pathlib import Path
from datetime import datetime
import ast,re,shutil,os
root=Path(__file__).resolve().parent
p=root/'public_support.py'
if not p.is_file():raise SystemExit('Hianyzo public_support.py. Tegye ezt a frissitot a server.py melle.')
s=p.read_text(encoding='utf-8')
tree=ast.parse(s)
functions=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='publication_read']
if len(functions)!=1:raise SystemExit('Nem vart kodszerkezet. Nem tortent modositas.')
f=functions[0]
args=[a.arg for a in f.args.args]
if args==['u','rid']:raise SystemExit('Ez a javitas mar telepitve van.')
if args!=['u']:raise SystemExit('Eltero fuggveny. Nem tortent modositas.')
pattern=r'def publication_read\(u\):'
if len(re.findall(pattern,s))!=1:raise SystemExit('Eltero fajlformatum. Nem tortent modositas.')
new=re.sub(pattern,'def publication_read(u, rid):',s,count=1)
ast.parse(new)
backup=p.with_name('public_support.py.backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
shutil.copy2(p,backup)
tmp=p.with_suffix('.py.fix.tmp');tmp.write_text(new,encoding='utf-8');os.replace(tmp,p)
print('Javitas telepitve. Inditsa ujra a szervert: py server.py. Az admin PWA-ban Ctrl+R.')
