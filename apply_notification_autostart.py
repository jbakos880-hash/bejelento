from pathlib import Path
from datetime import datetime
import hashlib,shutil,os
root=Path(__file__).resolve().parent
p=root/'admin_pwa'/'admin.js';replacement=root/'notification_auto_update'/'admin.updated.js'
if not p.is_file() or not replacement.is_file():raise SystemExit('Hianyzo admin_pwa/admin.js vagy notification_auto_update/admin.updated.js. A csomagot a server.py melle masolja.')
if hashlib.sha256(p.read_bytes()).hexdigest()!='be7463e797ce3bba12e9713c2ea63580bafc996606af6f7969275529ff48699f':raise SystemExit('Eltero vagy mar frissitett admin.js. Nem tortent modositas; ne kerulje meg az ellenorzest.')
backup=p.with_name('admin.js.before-autostart-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
shutil.copy2(p,backup)
tmp=p.with_suffix('.js.auto.tmp');tmp.write_bytes(replacement.read_bytes());os.replace(tmp,p)
print('Automatikus ertesitesfigyeles telepitve. Az admin PWA-ban Ctrl+R. Szerverujrainditas nem szukseges.')
