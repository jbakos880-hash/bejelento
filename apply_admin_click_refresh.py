from pathlib import Path
from datetime import datetime
import shutil,os
root=Path(__file__).resolve().parent
p=root/'admin_pwa'/'admin.js'
if not p.is_file():raise SystemExit('Hianyzo admin_pwa/admin.js. Tegye ezt a frissitot a server.py melle.')
s=p.read_text(encoding='utf-8')
old="navigator.serviceWorker?.addEventListener('message',e=>{if(e.data?.type==='ADMIN_NOTIFICATION_CLICK'&&loggedIn())msg.textContent='Értesítésből nyitotta meg az alkalmazást. A bejelentések megtekintéséhez kattintson a Frissítés gombra.'});"
new="navigator.serviceWorker?.addEventListener('message',async e=>{\nif(e.data?.type!=='ADMIN_NOTIFICATION_CLICK'||!loggedIn())return;\nconst pending=[...document.querySelectorAll('#reports .local')].some(p=>/Még nincs elmentve|Mentés folyamatban|mentés sikere nem igazolható/i.test(p.textContent));\nconst filled=[...panel.querySelectorAll('input,textarea')].some(x=>x.value.trim()!=='');\nif((pending||filled)&&!window.confirm('Nem mentett módosítás, folyamatban lévő mentés vagy kitöltött adminűrlap lehet az oldalon. A frissítés felülírhatja ezeket. Frissíti a listát?')){msg.textContent='Az automatikus frissítést megszakította. Mentse a módosításokat, majd kattintson a Frissítés gombra.';return;}\nif(loading){msg.textContent='A lista betöltése már folyamatban van. Ha az új bejelentés nem jelenik meg, kattintson a Frissítés gombra.';return;}\nconst button=document.getElementById('refresh');button.disabled=true;\ntry{await load();if(loggedIn())msg.textContent='A bejelentéslista az értesítésre kattintás után frissült.';}\ncatch(err){if(!(err instanceof SessionEnded))msg.textContent='A lista frissítése nem sikerült: '+(err.message||'Kapcsolati hiba.');}\nfinally{button.disabled=false;}\n});"
if s.count(old)!=1:raise SystemExit('Eltero vagy mar frissitett admin.js. Nem tortent modositas.')
backup=p.with_name('admin.js.backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
shutil.copy2(p,backup)
temp=p.with_suffix('.js.tmp');temp.write_text(s.replace(old,new,1),encoding='utf-8');os.replace(temp,p)
print('Sikeres frissites. Az adminalkalmazasban toltsuk ujra az oldalt Ctrl+R-rel. Szerverujrainditas nem szukseges.')
