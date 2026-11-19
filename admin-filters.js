(()=>{'use strict';
const root=document.getElementById('reports'),panel=document.getElementById('panel');if(!root||!panel||document.getElementById('admin-report-filters'))return;
const states=['Beérkezett','Folyamatban','Megoldva','Elutasítva'];
const categories=['Úthiba, kátyú','Közvilágítás','Illegális hulladék','Zöldterület, fa','Közterületi berendezés','Egyéb probléma'];
function matches(category,status,selectedCategory,selectedStatus){return (!selectedCategory||category===selectedCategory)&&(!selectedStatus||status===selectedStatus)}
const box=document.createElement('section');box.id='admin-report-filters';box.style.cssText='padding:16px;background:#e7f0eb;border:1px solid #cbded2;border-radius:12px;margin:16px 0';
const controls=document.createElement('div');controls.style.cssText='display:flex;gap:12px;flex-wrap:wrap;align-items:end';
function select(label,all,options,id){const l=document.createElement('label');l.textContent=label;const s=document.createElement('select');s.id=id;for(const value of ['',...options]){const o=document.createElement('option');o.value=value;o.textContent=value||all;s.append(o)}l.append(s);controls.append(l);return s}
const category=select('Kategória','Minden kategória',categories,'admin-filter-category'),status=select('Állapot','Minden állapot',states,'admin-filter-status');
const reset=document.createElement('button');reset.type='button';reset.textContent='Szűrők törlése';controls.append(reset);const count=document.createElement('p');count.setAttribute('role','status');count.setAttribute('aria-live','polite');const note=document.createElement('p');note.textContent='A szűrés a mentett ügyállapot alapján működik. A szűrőváltás nem ment és nem tölt újra adatokat. Új bejelentésekhez használja a Frissítés gombot.';box.append(controls,count,note);
const heading=root.previousElementSibling;if(heading?.tagName==='H2')heading.before(box);else root.before(box);
const saved=new WeakMap();let queued=false;
function apply(){queued=false;const articles=[...root.children].filter(e=>e.tagName==='ARTICLE');let visible=0;
for(const article of articles){const title=article.querySelector('h3')?.textContent||'';const categoryText=title.replace(/^#\d+\s*[–-]\s*/,'').trim();const stateSelect=[...article.querySelectorAll('select')].find(s=>s.options.length===states.length&&[...s.options].every(o=>states.includes(o.value)));let state=saved.get(article);if(state===undefined){state=stateSelect?.value||'';saved.set(article,state)}
const savedMessage=[...article.querySelectorAll('.local')].map(p=>p.textContent).find(t=>t.startsWith('Állapot mentve: '));if(savedMessage){const confirmed=savedMessage.slice('Állapot mentve: '.length).trim();if(states.includes(confirmed)){state=confirmed;saved.set(article,state)}}
const show=matches(categoryText,state,category.value,status.value);article.hidden=!show;if(show)visible++;
}
count.textContent=articles.length?(visible+' / '+articles.length+' bejelentés látható.'+(visible===0?' Nincs találat a kiválasztott feltételekkel.':'')):'Még nincs betöltött bejelentés.';
}
function schedule(){if(!queued){queued=true;queueMicrotask(apply)}}
category.onchange=status.onchange=apply;reset.onclick=()=>{category.value=status.value='';apply()};
new MutationObserver(schedule).observe(root,{childList:true,subtree:true,characterData:true});root.addEventListener('change',schedule);
new MutationObserver(()=>{if(panel.hidden){category.value=status.value=''}schedule()}).observe(panel,{attributes:true,attributeFilter:['hidden']});apply();
})();