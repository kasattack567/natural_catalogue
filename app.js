const state={query:'',gender:'All',brands:new Set(),materials:new Set(),categories:new Set(),price:'All',availableOnly:true,sort:'featured'};
const $=s=>document.querySelector(s); const $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));

function uniqueSorted(values){return [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b));}
function filterButton(label,attr,value){return `<button class="filter-chip" data-${attr}="${esc(value)}">${esc(label)}</button>`;}

function buildDynamicFilters(){
  const brands=uniqueSorted(window.CATALOG.map(p=>p.brand));
  const materials=uniqueSorted(window.CATALOG.flatMap(p=>p.materials.map(m=>m.name)));
  const categories=uniqueSorted(window.CATALOG.map(p=>p.category));
  $('#brandFilters').innerHTML=brands.map(v=>filterButton(v,'brand',v)).join('');
  $('#materialFilters').innerHTML=materials.map(v=>filterButton(v,'material',v)).join('');
  $('#categoryFilters').innerHTML=categories.map(v=>filterButton(v,'category',v)).join('');

  $$('[data-brand]').forEach(el=>el.addEventListener('click',()=>toggleSet(state.brands,el.dataset.brand,el)));
  $$('[data-material]').forEach(el=>el.addEventListener('click',()=>toggleSet(state.materials,el.dataset.material,el)));
  $$('[data-category]').forEach(el=>el.addEventListener('click',()=>toggleSet(state.categories,el.dataset.category,el)));
}

function matches(p){
  const hay=[p.brand,p.name,p.gender,p.category,p.color,p.materialText,...p.materials.map(m=>m.name)].join(' ').toLowerCase();
  if(state.query && !hay.includes(state.query.toLowerCase())) return false;
  if(state.gender!=='All' && p.gender!==state.gender) return false;
  if(state.brands.size && !state.brands.has(p.brand)) return false;
  if(state.materials.size && !p.materials.some(m=>state.materials.has(m.name))) return false;
  if(state.categories.size && !state.categories.has(p.category)) return false;
  if(state.availableOnly && !p.available) return false;
  if(state.price==='under50' && p.price>=50) return false;
  if(state.price==='50to100' && (p.price<50 || p.price>100)) return false;
  if(state.price==='over100' && p.price<=100) return false;
  return true;
}

function filtered(){
  const arr=window.CATALOG.filter(matches);
  if(state.sort==='priceLow') arr.sort((a,b)=>a.price-b.price);
  if(state.sort==='priceHigh') arr.sort((a,b)=>b.price-a.price);
  if(state.sort==='brand') arr.sort((a,b)=>a.brand.localeCompare(b.brand));
  return arr;
}

function productCard(p){
  const img=p.image?`<img src="${esc(p.image)}" alt="${esc(p.name)}" loading="lazy" onerror="this.style.display='none';this.parentElement.style.background='linear-gradient(145deg,#e5e2d7,#f7f5ef)'">`:'';
  return `<article class="card">
    <div class="image-wrap">${img}<span class="badge ${p.available?'':'sold'}">${p.available?'Natural fibres':'Currently unavailable'}</span></div>
    <div class="card-body">
      <div class="brandline">${esc(p.brand)} · ${esc(p.gender)}</div>
      <div class="product-name">${esc(p.name)}</div>
      <div class="meta"><div class="material">${esc(p.materialText)}</div><div class="price">${esc(p.currency)}${Number(p.price).toFixed(Number(p.price)%1?2:0)}</div></div>
      <div class="card-actions"><button class="details-link" data-details="${esc(p.id)}">Composition</button>${p.url?`<a class="buy-link" href="${esc(p.url)}" target="_blank" rel="noopener" ${p.available?'':'aria-disabled="true"'}>View at ${esc(p.brand)} →</a>`:''}</div>
    </div>
  </article>`;
}

function render(){
  const items=filtered();
  $('#grid').innerHTML=items.length?items.map(productCard).join(''):`<div class="empty">No products match those filters yet.</div>`;
  $('#resultCount').textContent=`${items.length} ${items.length===1?'product':'products'}`;
  renderActive();
  $$('.nav-link').forEach(b=>b.classList.toggle('active',b.dataset.gender===state.gender));
  document.querySelectorAll('[data-details]').forEach(b=>b.addEventListener('click',()=>openProduct(b.dataset.details)));
}

function renderActive(){
  const chips=[];
  if(state.gender!=='All') chips.push(state.gender);
  state.brands.forEach(v=>chips.push(v));
  state.materials.forEach(v=>chips.push(v));
  state.categories.forEach(v=>chips.push(v));
  if(state.price!=='All') chips.push({under50:'Under £50','50to100':'£50–£100',over100:'£100+'}[state.price]);
  if(state.query) chips.push(`“${state.query}”`);
  $('#activeFilters').innerHTML=chips.map(x=>`<span class="active-chip">${esc(x)}</span>`).join('');
}

function toggleDrawer(force){$('#filterOverlay').classList.toggle('open',force??!$('#filterOverlay').classList.contains('open'));}
function toggleSet(set,val,el){set.has(val)?set.delete(val):set.add(val);el.classList.toggle('selected',set.has(val));}
function syncDrawer(){
  $$('[data-brand]').forEach(el=>el.classList.toggle('selected',state.brands.has(el.dataset.brand)));
  $$('[data-material]').forEach(el=>el.classList.toggle('selected',state.materials.has(el.dataset.material)));
  $$('[data-category]').forEach(el=>el.classList.toggle('selected',state.categories.has(el.dataset.category)));
  $$('[data-price]').forEach(el=>el.classList.toggle('selected',state.price===el.dataset.price));
  $('#availabilitySwitch').classList.toggle('on',state.availableOnly);
}
function resetFilters(){state.brands.clear();state.materials.clear();state.categories.clear();state.price='All';state.availableOnly=true;syncDrawer();render();}

function openProduct(id){
  const p=window.CATALOG.find(x=>x.id===id); if(!p)return;
  $('#modalImage').src=p.image||''; $('#modalImage').style.display=p.image?'block':'none';
  $('#modalBrand').textContent=`${p.brand} · ${p.gender}`; $('#modalName').textContent=p.name; $('#modalPrice').textContent=`${p.currency}${p.price}`;
  $('#modalComposition').innerHTML=p.materials.map(m=>`<div class="composition-row"><span>${esc(m.name)}</span><strong>${m.percent}%</strong></div>`).join('');
  $('#modalMeta').innerHTML=`${esc(p.color)} · ${esc(p.category)}<br><strong>Retailer composition:</strong> ${esc(p.materialText)}<br>Composition checked ${esc(p.verified)}${p.available?'':' · currently unavailable online'}`;
  if(p.url){$('#modalBuy').href=p.url;$('#modalBuy').textContent=`View at ${p.brand} →`;$('#modalBuy').style.display=p.available?'inline-block':'none';}
  else{$('#modalBuy').style.display='none';}
  $('#productModal').classList.add('open');
}
function closeProduct(){$('#productModal').classList.remove('open');}

$('#searchForm').addEventListener('submit',e=>{e.preventDefault();state.query=$('#searchInput').value.trim();render();});
$('#searchInput').addEventListener('input',e=>{if(!e.target.value){state.query='';render();}});
$$('.nav-link').forEach(b=>b.addEventListener('click',()=>{state.gender=b.dataset.gender;render();}));
$('#filterButton').addEventListener('click',()=>{syncDrawer();toggleDrawer(true)}); $('#mobileFilterButton').addEventListener('click',()=>{syncDrawer();toggleDrawer(true)}); $('#closeFilters').addEventListener('click',()=>toggleDrawer(false));
$('#filterOverlay').addEventListener('click',e=>{if(e.target.id==='filterOverlay')toggleDrawer(false)});
$$('[data-price]').forEach(el=>el.addEventListener('click',()=>{state.price=state.price===el.dataset.price?'All':el.dataset.price;syncDrawer()}));
$('#availabilitySwitch').addEventListener('click',()=>{state.availableOnly=!state.availableOnly;syncDrawer()});
$('#clearFilters').addEventListener('click',resetFilters); $('#applyFilters').addEventListener('click',()=>{render();toggleDrawer(false)});
$('#sort').addEventListener('change',e=>{state.sort=e.target.value;render();});
$('#productModal').addEventListener('click',e=>{if(e.target.id==='productModal')closeProduct()}); $('#modalClose').addEventListener('click',closeProduct);
document.addEventListener('keydown',e=>{if(e.key==='Escape'){toggleDrawer(false);closeProduct()}});

buildDynamicFilters();
render();
