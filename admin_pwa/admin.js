(()=>{'use strict';
const panel=document.getElementById('panel'),box=document.getElementById('admin-notification-controls'),msg=document.getElementById('admin-notification-status');
const enable=document.getElementById('admin-notification-enable'),disable=document.getElementById('admin-notification-disable'),test=document.getElementById('admin-notification-test'),install=document.getElementById('admin-install');
if(!panel||!box||!msg||!enable||!disable||!test)return;
const supported=window.isSecureContext&&'serviceWorker' in navigator&&'PushManager' in window&&'Notification' in window;
let reg=null,key=null,busy=false,preparing=false,active=false,promptEvent=null,who=null;
function loggedIn(){return typeof user!=='undefined'&&user&&!panel.hidden}
function preference(){return 'polgardi-admin-push-v1:'+user.id}
function wanted(){try{return localStorage.getItem(preference())!=='off'}catch{return true}}
function remember(v){try{localStorage.setItem(preference(),v)}catch{}}
function buttons(){box.hidden=!loggedIn();enable.disabled=!supported||!reg||!key||busy||active;disable.disabled=!supported||busy;test.disabled=!active||busy}
function decode(v){const s=atob(v.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-v.length%4)%4));return Uint8Array.from(s,c=>c.charCodeAt(0))}
function currentUser(id){return loggedIn()&&user.id===id}
async function save(sub,id){if(!currentUser(id))throw Error('A bejelentkezés megváltozott.');await api('/api/push/subscribe',{subscription:sub.toJSON()});if(!currentUser(id))throw Error('A bejelentkezés megváltozott.');active=true}
async function prepare(){
 if(!loggedIn()||preparing||busy)return;
 if(!supported){msg.textContent='iPhone-on a kezdőképernyőre telepített admint nyissa meg. A pushhoz iOS 16.4 vagy újabb szükséges.';buttons();return}
 preparing=true;const id=user.id;who=id;
 try{
  reg=await navigator.serviceWorker.register('/admin/sw.js',{scope:'/admin/',updateViaCache:'none'});
  if(!reg.active)await new Promise((resolve,reject)=>{const w=reg.installing||reg.waiting;if(!w)return reject(Error('Frissítse az alkalmazást.'));if(w.state==='activated')return resolve();w.addEventListener('statechange',()=>{if(w.state==='activated')resolve();else if(w.state==='redundant')reject(Error('Nem aktiválódott az értesítéskezelő.'))})});
  const config=await api('/api/push/config');if(!currentUser(id))return;key=decode(config.publicKey);
  const sub=await reg.pushManager.getSubscription();if(!currentUser(id))return;
  if(sub&&wanted()&&Notification.permission==='granted'){
   await save(sub,id);msg.textContent='Háttérértesítések bekapcsolva. Az appot nem kell nyitva tartania.';
  }else{active=false;msg.textContent=Notification.permission==='denied'?'Az értesítés tiltva van. Engedélyezze az iPhone értesítési beállításaiban.':'Koppintson az Értesítések bekapcsolása gombra a háttérértesítésekhez.'}
 }catch(e){if(currentUser(id))msg.textContent=e.message||'Az értesítések előkészítése nem sikerült.'}
 finally{preparing=false;buttons()}
}
enable.onclick=()=>{
 if(!loggedIn()||busy||!reg||!key)return;
 const id=user.id;busy=true;buttons();
 const subscribing=reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key});
 (async()=>{try{const sub=await subscribing;await save(sub,id);remember('on');msg.textContent='Háttérértesítések bekapcsolva. Lezárt telefonon is fogadhat értesítést.'}catch(e){msg.textContent=e.message||'Nem sikerült engedélyezni az értesítéseket.'}finally{busy=false;buttons()}})();
};
disable.onclick=async()=>{
 if(!loggedIn()||busy||!reg)return;busy=true;buttons();
 try{const sub=await reg.pushManager.getSubscription();if(sub){await api('/api/push/unsubscribe',{endpoint:sub.endpoint});await sub.unsubscribe()}remember('off');active=false;msg.textContent='Ezen az eszközön az értesítések kikapcsolva.'}catch(e){msg.textContent=e.message}finally{busy=false;buttons()}
};
test.onclick=async()=>{
 if(!loggedIn()||busy||!active)return;busy=true;buttons();
 try{const sub=await reg.pushManager.getSubscription();if(!sub)throw Error('Kapcsolja be újra az értesítéseket.');await api('/api/push/test',{endpoint:sub.endpoint});msg.textContent='Szerveroldali teszt sorba állítva. Az értesítés külön érkezik; ez még nem kézbesítési visszaigazolás.'}catch(e){msg.textContent=e.message}finally{busy=false;buttons()}
};
new MutationObserver(()=>{if(!loggedIn()){active=false;key=null;who=null;msg.textContent='Kijelentkezve. A szerver kijelentkezéskor minden ehhez az adminhoz tartozó eszközfeliratkozást töröl.';buttons()}else prepare()}).observe(panel,{attributes:true,attributeFilter:['hidden']});
window.addEventListener('focus',()=>{if(loggedIn())prepare()});
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();promptEvent=e;if(install)install.hidden=false});
if(install)install.onclick=async()=>{if(!promptEvent)return;const p=promptEvent;promptEvent=null;install.hidden=true;await p.prompt();await p.userChoice};
window.addEventListener('appinstalled',()=>{if(install)install.hidden=true});
navigator.serviceWorker?.addEventListener('message',async e=>{
 if(e.data?.type!=='ADMIN_NOTIFICATION_CLICK'||!loggedIn())return;
 const pending=[...document.querySelectorAll('#reports .local')].some(p=>/Még nincs elmentve|Mentés folyamatban|mentés sikere nem igazolható/i.test(p.textContent));
 const filled=[...panel.querySelectorAll('input,textarea')].some(x=>x.value.trim()!=='');
 if((pending||filled)&&!window.confirm('Nem mentett módosítás lehet az oldalon. Frissíti a listát?'))return;
 if(typeof loading!=='undefined'&&loading)return;
 const button=document.getElementById('refresh');if(button)button.disabled=true;
 try{await load();msg.textContent='A bejelentéslista frissült.'}catch(e){msg.textContent=e.message}finally{if(button)button.disabled=false}
});
for(const p of box.querySelectorAll('p'))if(p!==msg&&(/Tartsa nyitva|tartsa nyitva|lekicsinyítve/.test(p.textContent)))p.textContent='A háttérértesítésekhez engedély szükséges. Az értesítés nem tartalmaz személyes adatot. Kijelentkezéskor az admin összes eszközfeliratkozása törlődik; a többi eszközön az admin újbóli megnyitása után regisztrálható újra.';
buttons();prepare();
})();
