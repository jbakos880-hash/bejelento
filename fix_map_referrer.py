from pathlib import Path
from datetime import datetime
import shutil,ast
root=Path(__file__).resolve().parent
p=root/'server.py'
if not p.is_file():raise SystemExit('A javitot a server.py melle masolja.')
s=p.read_text(encoding='utf-8')
old="r.headers['Referrer-Policy']='same-origin'"
new="r.headers['Referrer-Policy']='strict-origin-when-cross-origin'"
if new in s:raise SystemExit('A beallitas mar javitva van. Ha tovabbra is blokkolt, ne ismetelje a lekereseket: tovabbi ellenorzes szukseges.')
if s.count(old)!=1:raise SystemExit('Nem a vart szervervaltozat. Nem modositottunk semmit.')
updated=s.replace(old,new,1);ast.parse(updated)
backup=p.with_name('server-before-map-referrer-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.py.bak')
shutil.copy2(p,backup);p.write_text(updated,encoding='utf-8')
print('Referer-szabaly javitva. Inditsa ujra a szervert: py server.py')
