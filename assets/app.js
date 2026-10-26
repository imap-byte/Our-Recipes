import {loadRecipeData, showLoadError} from './recipe-loader.js';
(async function () {
try {

'use strict';
const DB=await loadRecipeData();
const {recipes,photos,scans,categories,metadata}=DB;
const $=(id)=>document.getElementById(id);
const ICONS=['⌂','🥗','🍗','🥙','🐟','🧀','🍜','🥔','🥘','🥖','🍰','🍨'];
const CATPIC={'סלטים וממרחים':'tabbouleh','בשרי':'roast-chicken','פרווה':'stuffed-pepper','דגים':'salmon','חלבי':'crepes','מרקים':'soup','תוספות':'kugel','פשטידות':'mushroom-pie','לחמים ומאפים':'challah','עוגות ועוגיות':'cheesecake','קינוחים ומנות אחרונות':'berry-mousse'};
let fishKind='הכל';
const FISH_KINDS=['הכל','סלמון','מושט','טונה','סטייק טונה'];
const PAGE_SIZE=48;
let chosen='הכל',favoritesOnly=false,query='',sort='popular',year='all',limit=PAGE_SIZE,active=null,prevFocus=null;
const ids=new Set(recipes.map(r=>r.id));
const redirects=DB.redirects||{};
const resolveId=(id)=>Number(redirects[String(id)]||id);
let favorites=new Set();try{favorites=new Set(JSON.parse(localStorage.getItem('my-recipe-favorites')||'[]').map(id=>resolveId(id)).filter(id=>ids.has(id)))}catch(e){}
function norm(s){return String(s||'').normalize('NFKD').replace(/[\u0591-\u05c7]/g,'').replace(/[־–—'״׳"`]/g,'').toLowerCase().trim()}
function sourceLink(r,mid){if(!mid&&r.sourceUrl)return r.sourceUrl;return 'https://mail.google.com/mail/u/?authuser=imaplusprog%40gmail.com#all/'+encodeURIComponent(mid||r.mid)}
function html(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function toast(msg){$('toast').textContent=msg;$('toast').classList.remove('hidden');clearTimeout(toast.t);toast.t=setTimeout(()=>$('toast').classList.add('hidden'),2200)}
function saveFavorites(){try{localStorage.setItem('my-recipe-favorites',JSON.stringify([...favorites]))}catch(e){}}
function setFav(id){if(favorites.has(id))favorites.delete(id);else favorites.add(id);saveFavorites();render();if(active?.id===id)openRecipe(id,false);}
function catCount(c){return c==='הכל'?recipes.length:recipes.filter(r=>r.cat===c).length}
function setup(){
 $('hero-count').textContent=metadata.total; $('hero-categories').textContent=categories.length-1;
 $('hero-photo').src=photos['focaccia'];
 $('sidebar-nav').innerHTML=categories.map((c,i)=>`<button type="button" class="navitem ${i===0?'active':''}" data-cat="${html(c)}"><span class="navicon">${ICONS[i]}</span><span>${html(i===0?'כל המתכונים':c)}</span><span class="navcount">${catCount(c)}</span></button>`).join('');
 $('category-cards').innerHTML=categories.slice(1).map(c=>`<button type="button" class="catbox" data-cat="${html(c)}"><img class="catphoto" src="${photos[CATPIC[c]]}" alt="תמונת המחשה לקטגוריית ${html(c)}"/><div class="cattext"><strong>${html(c)}</strong><small>${catCount(c)} מתכונים</small></div></button>`).join('');
 document.querySelectorAll('[data-cat]').forEach(el=>el.addEventListener('click',()=>{chosen=el.dataset.cat;fishKind='הכל';favoritesOnly=false;limit=PAGE_SIZE;render();$('search-scroll-anchor').scrollIntoView({behavior:'smooth',block:'start'})}));
 $('search').addEventListener('input',e=>{query=e.target.value;limit=PAGE_SIZE;render()});
 $('sort').addEventListener('change',e=>{sort=e.target.value;render()});
 $('year').addEventListener('change',e=>{year=e.target.value;limit=PAGE_SIZE;render()});
 $('fav-top').addEventListener('click',()=>{favoritesOnly=!favoritesOnly;limit=PAGE_SIZE;render();$('recipes').scrollIntoView({behavior:'smooth',block:'start'})});
 const surpriseRecipe=()=>{const pool=getResults();if(!pool.length){toast('לא נמצאו מתכונים בסינון הנוכחי');return;}const r=pool[Math.floor(Math.random()*pool.length)];openRecipe(r.id)};
 $('surprise').addEventListener('click',surpriseRecipe);
 $('surprise-floating').addEventListener('click',surpriseRecipe);
 $('clear').addEventListener('click',clearFilters);
 $('clear-empty').addEventListener('click',clearFilters);
 $('loadmore').addEventListener('click',()=>{limit+=PAGE_SIZE;render()});
 const updateFloatingActions=()=>{
   $('back-to-top').classList.toggle('hidden',window.scrollY<650);
   $('surprise-floating').classList.toggle('hidden',$('surprise').getBoundingClientRect().bottom>8);
 };
 $('back-to-top').addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
 window.addEventListener('scroll',updateFloatingActions,{passive:true});
 window.addEventListener('resize',updateFloatingActions,{passive:true});
 updateFloatingActions();
 document.addEventListener('keydown',e=>{
   if(!active)return;
   if(e.key==='Escape'){closeRecipe();return}
   if(e.altKey||e.ctrlKey||e.metaKey||/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName||''))return;
   if(e.key==='ArrowLeft'){e.preventDefault();switchRecipe('next')}
   else if(e.key==='ArrowRight'){e.preventDefault();switchRecipe('prev')}
 });
 window.addEventListener('hashchange',()=>{const m=location.hash.match(/^#recipe-(\d+)$/);if(m){let id=+m[1];if(ids.has(resolveId(id)))openRecipe(resolveId(id),false)}else if(active)closeRecipe(false)});
 const initial=location.hash.match(/^#recipe-(\d+)$/);if(initial&&ids.has(resolveId(+initial[1])))openRecipe(resolveId(+initial[1]),false);
 render();
}
function clearFilters(){chosen='הכל';fishKind='הכל';favoritesOnly=false;query='';sort='popular';year='all';limit=PAGE_SIZE;$('search').value='';$('sort').value='popular';$('year').value='all';render()}
function matches(r){if(chosen!=='הכל'&&r.cat!==chosen)return false;if(chosen==='דגים'&&fishKind!=='הכל'&&!norm(r.title).includes(norm(fishKind)))return false;if(favoritesOnly&&!favorites.has(r.id))return false;if(year!=='all'&&String(r.year)!==year)return false;
 if(!norm(query))return true;const words=norm(query).split(/\s+/).filter(Boolean);
 const hay=norm([r.title,...(r.aliases||[]),r.cat,r.year,...r.ingredients,...r.steps,r.note,r.author,r.creditLabel,r.sourceSharer].join(' '));return words.every(x=>hay.includes(x));}
function getResults(){const items=recipes.filter(matches);
 if(sort==='new')items.sort((a,b)=>b.year-a.year||b.id-a.id);
 else if(sort==='old')items.sort((a,b)=>a.year-b.year||a.id-b.id);
 else if(sort==='az')items.sort((a,b)=>a.title.localeCompare(b.title,'he'));
 return items;}
function render(){
 $('fish-subtypes').classList.toggle('hidden',chosen!=='דגים'||favoritesOnly);
 if(chosen==='דגים'&&!favoritesOnly){
   const subtypeCount=k=>recipes.filter(r=>r.cat==='דגים'&&(k==='הכל'||norm(r.title).includes(norm(k)))).length;
   $('fish-subtypes').innerHTML='<b>🐟 סוג הדג:</b> '+FISH_KINDS.map(k=>`<button type="button" class="fish-chip ${fishKind===k?'active':''}" data-fish="${html(k)}">${html(k==='הכל'?'כל הדגים':k)} <span>${subtypeCount(k)}</span></button>`).join('');
   $('fish-subtypes').querySelectorAll('[data-fish]').forEach(b=>b.addEventListener('click',()=>{fishKind=b.dataset.fish;limit=PAGE_SIZE;render()}));
 }
 let filtered=getResults();let display=filtered.slice(0,limit);
 $('result-count').textContent='';
 $('results-title').textContent=favoritesOnly?'♡ המתכונים שסימנת':chosen==='הכל'?'כל המתכונים':chosen;
 $('clear').classList.toggle('hidden',!(chosen!=='הכל'||fishKind!=='הכל'||favoritesOnly||query||year!=='all'||sort!=='popular'));
 $('fav-top').textContent=favoritesOnly?'♥ הצגת כל המתכונים':'♡ המועדפים שלי';
 document.querySelectorAll('[data-cat]').forEach(el=>{el.classList.toggle(el.classList.contains('navitem')?'active':'chosen',el.dataset.cat===chosen&&!favoritesOnly)});
 $('recipes').innerHTML=display.map(r=>`<article class="recipe"><button class="coverbtn" data-open="${r.id}" aria-label="פתיחת ${html(r.title)}"><img src="${photos[r.photo]}" alt="תמונת המחשה בלבד: ${html(r.title)}"/><span class="ribbon">${html(r.cat)}</span></button><button class="heart ${favorites.has(r.id)?'on':''}" data-fav="${r.id}" aria-label="${favorites.has(r.id)?'הסרה מהמועדפים':'הוספה למועדפים'}" title="מועדפים">${favorites.has(r.id)?'♥':'♡'}</button><div class="rcnt"><button data-open="${r.id}" class="rtitle">${html(r.title)}</button><span class="creditbadge ${r.creditKind==='כותבת לא זוהתה'?'unknown':''}">${r.creditKind==='שולחת'?'✉':'✍'} ${html(r.creditLabel)}</span><p class="rsub">${html(r.ingredients.length?r.ingredients.slice(0,3).join(' · '):'דף מקור סרוק — המרכיבים וההכנה מופיעים בצילום המקורי')}</p><div class="rmeta"><span>◷ ${r.year}</span><span>${r.scan?'▣ כולל צילום מקור':''}</span><strong>${r.ingredients.length?'מתכון כתוב':'דף סרוק'}</strong></div></div></article>`).join('');
 $('recipes').querySelectorAll('[data-open]').forEach(el=>el.addEventListener('click',()=>openRecipe(+el.dataset.open)));
 $('recipes').querySelectorAll('[data-fav]').forEach(el=>el.addEventListener('click',()=>setFav(+el.dataset.fav)));
 $('empty').classList.toggle('hidden',filtered.length>0);
 $('more').classList.toggle('hidden',filtered.length<=display.length);
 $('display-progress').textContent=`מוצגים ${display.length} מתוך ${filtered.length} מתכונים`;
 $('display-progress').classList.toggle('hidden',filtered.length===0);
}
function recipeNeighbors(id){
 let list=getResults();
 let pos=list.findIndex(r=>r.id===id);
 if(pos<0){list=recipes;pos=list.findIndex(r=>r.id===id)}
 return {prev:pos>0?list[pos-1].id:null,next:pos>=0&&pos<list.length-1?list[pos+1].id:null,pos,total:list.length};
}
function switchRecipe(direction){
 if(!active)return;
 const siblings=recipeNeighbors(active.id);
 const id=direction==='next'?siblings.next:siblings.prev;
 if(id===null)return;
 try{history.replaceState({},'',`#recipe-${id}`)}catch(e){}
 openRecipe(id,false);
}
function openRecipe(id,changeHash=true){let r=recipes.find(x=>x.id===id);if(!r)return;
 if(!active)prevFocus=document.activeElement;active=r;if(changeHash)history.pushState({},'',`#recipe-${id}`);
 document.body.style.overflow='hidden';
 const neighbors=recipeNeighbors(id);
 const ing=r.ingredients.length?`<div class="ingredients">${r.ingredients.map((x,i)=>`<label class="ingredient"><input type="checkbox" data-ingredient="${i}"><span>${html(x)}</span></label>`).join('')}</div>`:'<p class="missing">במהדורה המקורית מתכון זה נשמר כצילום של דף מתכון. הכמויות נמצאות בדף המצולם המוצג בהמשך.</p>';
 const meth=r.steps.length?`<ol class="steps">${r.steps.map(x=>`<li>${html(x)}</li>`).join('')}</ol>`:'<p class="missing">שלבי ההכנה מופיעים בדף המקור המצולם להלן. מומלץ להגדיל את הצילום ולקרוא את המקור עצמו.</p>';
 $('dialog-root').innerHTML=`<div class="overlay" id="overlay"><article class="dialog" role="dialog" aria-modal="true" aria-label="${html(r.title)}"><button class="close" id="close-dialog" title="סגירה" aria-label="סגירה">×</button><div class="dhero"><img alt="תמונת המחשה בלבד" src="${photos[r.photo]}"></div><div class="dbody"><div class="dtag">${html(r.cat)} · תמונת המחשה</div><h2>${html(r.title)}</h2>${r.aliases?.length?`<p style="color:#736657;margin:0 0 12px;font-size:13px"><strong>שמות נוספים:</strong> ${html(r.aliases.join(" · "))}</p>`:""}<div class="dline"><span>📆 ${r.year}</span><span class="creditbadge ${r.creditKind==='כותבת לא זוהתה'?'unknown':''}">${r.creditKind==='שולחת'?'✉':'✍'} ${html(r.creditLabel)}</span>${r.sourceSharer?`<span class="source-sharer" title="מידע על העברת ההודעה או פרסום המתכון">↪ ${html(r.sourceSharerKind)}: ${html(r.sourceSharer)}</span>`:""}${r.scan?'<span>▣ יש צילום מקור</span>':''}</div><div class="dactions"><button id="fav-dialog">${favorites.has(id)?'♥ שמור במועדפים':'♡ הוספה למועדפים'}</button><button id="print-dialog">⎙ הדפסת מתכון</button><button id="copy-dialog">▣ העתקת מתכון</button><a href="${sourceLink(r)}" target="_blank" rel="noopener noreferrer">↗ ${r.sourceUrl?'גיליון המקור':'הודעת המקור בג׳ימייל'}</a>${(r.sources||[]).filter(s=>s.mid!==r.mid).map((s,i)=>`<a href="${sourceLink(r,s.mid)}" target="_blank" rel="noopener noreferrer">↗ מקור נוסף ${i+1}</a>`).join("")}</div><div class="dcontent"><section class="dblock"><h3>מה צריך?</h3>${ing}</section><section class="dblock"><h3>איך מכינים?</h3>${meth}</section></div>${r.note?`<div class="dnote"><b>הערות ומידע מהמקור</b>${html(r.note)}</div>`:''}${r.scan?`<section class="sourcephoto"><h3>▣ צילום דף המתכון המקורי${r.scanExtra?.length?' (כולל המשך)':''}</h3>${[r.scan,...(r.scanExtra||[])].map((k,i)=>`<img class="scanpage" data-scan="${html(k)}" src="${scans[k]}" alt="צילום דף המקור ${i+1}" title="לחצי לפתיחת הצילום בגודל מלא"><small class="scancaption">דף מקור ${i+1}</small>`).join('')}<small>התמלול מופיע למעלה; במקרה של ספק יש להשוות לצילום המקור.</small></section>`:''}<p style="font-size:11px;line-height:1.7;color:#978b80;margin-top:22px">צילום האוכל בכותרת הוא תמונת המחשה, ולא צילום של המנה המקורית.</p></div><nav class="recipe-navigator" aria-label="מעבר בין מתכונים"><button type="button" id="recipe-prev" ${neighbors.prev===null?'disabled':''} aria-label="למתכון הקודם">→ הקודם</button><span>מתכון ${neighbors.pos+1} מתוך ${neighbors.total}</span><button type="button" id="recipe-next" ${neighbors.next===null?'disabled':''} aria-label="למתכון הבא">הבא ←</button></nav></article></div>`;
 $('close-dialog').addEventListener('click',closeRecipe);
 $('recipe-prev').addEventListener('click',()=>switchRecipe('prev'));
 $('recipe-next').addEventListener('click',()=>switchRecipe('next'));
 $('overlay').addEventListener('click',e=>{if(e.target.id==='overlay')closeRecipe()});
 $('fav-dialog').addEventListener('click',()=>setFav(id));
 $('print-dialog').addEventListener('click',()=>printRecipe(r));
 $('copy-dialog').addEventListener('click',()=>copyRecipe(r));
 $('dialog-root').querySelectorAll('.ingredient input').forEach(el=>el.addEventListener('change',()=>el.closest('label').classList.toggle('checked',el.checked)));
 $('dialog-root').querySelectorAll('[data-scan]').forEach(el=>el.addEventListener('click',()=>{let k=el.dataset.scan;let w=window.open('','_blank');if(!w){toast('הדפדפן חסם את פתיחת הצילום');return}w.document.write('<!doctype html><html lang="he"><meta charset="utf-8"><title>צילום מקור</title><body style="margin:0;text-align:center;background:#ede8e1"><img src="'+scans[k]+'" style="max-width:100%;height:auto"></body></html>');w.document.close()}));
 $('close-dialog').focus();
}
function closeRecipe(changeHash=true){active=null;$('dialog-root').innerHTML='';document.body.style.overflow='';if(changeHash&&location.hash.startsWith('#recipe-')){try{history.pushState({},'',location.href.split('#')[0])}catch(e){location.hash=''}};if(prevFocus?.focus)prevFocus.focus()}
function printRecipe(r){let a=$('printonly');a.innerHTML=`<h1>${html(r.title)}</h1>${r.aliases?.length?`<p>שמות נוספים: ${html(r.aliases.join(" · "))}</p>`:""}<p>${html(r.cat)} · ${r.year} · ${html(r.creditLabel)} · מקור: ${r.sourceUrl?'גיליון Excel':'Gmail'}</p>${r.sourceSharer?`<p>מידע על שיתוף המקור: ${html(r.sourceSharerKind)} - ${html(r.sourceSharer)}</p>`:''}${r.ingredients.length?`<h2>מצרכים</h2><ul>${r.ingredients.map(x=>`<li>${html(x)}</li>`).join('')}</ul>`:''}${r.steps.length?`<h2>אופן ההכנה</h2><ol>${r.steps.map(x=>`<li>${html(x)}</li>`).join('')}</ol>`:''}${r.note?`<p class="printnote">${html(r.note)}</p>`:''}${r.scan?`<h2>דפי מקור</h2>${[r.scan,...(r.scanExtra||[])].map(k=>`<img src="${scans[k]}" style="max-width:95%;max-height:85vh;float:none;display:block;object-fit:contain;">`).join('')}`:''}`;window.print()}
async function copyRecipe(r){let t=[r.title,r.aliases?.length?'שמות נוספים: '+r.aliases.join(' · '):'','קטגוריה: '+r.cat,'קרדיט כותבת: '+r.creditLabel,r.sourceSharer?'מקור שיתוף: '+r.sourceSharerKind+' - '+r.sourceSharer:'',r.ingredients.length?'\nמצרכים:\n'+r.ingredients.map(x=>'• '+x).join('\n'):'המתכון נשמר כצילום של מסמך המקור',r.steps.length?'\nאופן הכנה:\n'+r.steps.map((x,i)=>(i+1)+'. '+x).join('\n'):'',r.note?'\nהערה: '+r.note:''].filter(Boolean).join('\n');
 try{await navigator.clipboard.writeText(t);toast('המתכון הועתק ללוח')}catch(e){let ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();toast('המתכון הועתק ללוח')}}
document.getElementById('site').hidden=false;
setup();
document.getElementById('load-status').hidden=true;

} catch (error) { showLoadError(error); }
})();
