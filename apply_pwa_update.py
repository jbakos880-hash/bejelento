from pathlib import Path
from datetime import datetime
import ast,shutil
root=Path(__file__).resolve().parent
for n in ['server.py','index.html','pwa_support.py','pwa/manifest.webmanifest','pwa/sw.js','pwa/pwa.js','pwa/offline.html','pwa/icon-192.png','pwa/icon-512.png','pwa/apple-touch-icon.png']:
    if not (root/n).is_file():raise SystemExit('Hianyzo fajl: '+n)
s=(root/'server.py').read_text(encoding='utf-8');html=(root/'index.html').read_text(encoding='utf-8')
if 'install_pwa(app' in s:raise SystemExit('A PWA-alap mar telepitve van.')
marker="if __name__=='__main__':"
if s.count(marker)!=1 or '</head>' not in html or '</body>' not in html:raise SystemExit('Nem a vart fajlszerkezet. Nem tortent modositas.')
addition='from pwa_support import install as install_pwa\ninstall_pwa(app, ROOT)\n\n'
s=s.replace(marker,addition+marker,1)
tags='<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#153d3b"><link rel="apple-touch-icon" href="/pwa/apple-touch-icon.png">'
html=html.replace('</head>',tags+'</head>',1).replace('</body>','<script src="/pwa/pwa.js"></script></body>',1)
ast.parse(s)
backup=root/('pwa-code-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
for n in ['server.py','index.html']:shutil.copy2(root/n,backup/n)
(root/'server.py').write_text(s,encoding='utf-8');(root/'index.html').write_text(html,encoding='utf-8')
print('PWA-alap telepitve. Inditsa ujra: py server.py')
