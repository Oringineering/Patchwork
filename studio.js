'use strict';
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let files = {}, selected = '', context = new Set(), reviews = [], current = null, busy = false, configured = false, controller = null, projectVersion = 0;
const bytes = s => new TextEncoder().encode(s).length;
const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; };
function toast(text){$('#toast').textContent=text;$('#toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').classList.remove('show'),3500)}
function activity(text,kind=''){$('#activity').textContent=text;$('#activity').className=kind}
function route(){const studio=location.hash==='#studio'||(location.pathname==='/studio'&&!location.hash);$('#home-view').hidden=studio;$('#studio-view').hidden=!studio;document.title=studio?'Repair studio · Patchwork':'Patchwork · Make the next change a considered one.';if(studio||!location.hash||location.hash==='#home')window.scrollTo(0,0);else requestAnimationFrame(()=>document.getElementById(location.hash.slice(1))?.scrollIntoView())}
window.addEventListener('hashchange',route);route();
async function json(path,body,signal){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});const d=await r.json();if(!r.ok)throw Error(d.error||'The request failed.');return d}
async function connection(){try{const r=await fetch('/api/status');if(!r.ok)throw Error();const d=await r.json();configured=d.configured;$('#connection').textContent=configured?'● Model configured':'○ Model unavailable';$('#model-info').textContent=d.model;$('#setup').hidden=d.hosted;$('#key-hint').textContent=d.hosted?'Hosted demo: the key is configured on the server. You do not need your own key.':'Local mode: connect a Token Factory key for this server session.';enable()}catch{$('#connection').textContent='○ Connection unavailable';$('#key-hint').textContent='Start the Python server to connect to the repair service.'}}
connection();
$('#settings-open').onclick=()=>$('#settings').showModal();
$$('.close-dialog').forEach(b=>b.onclick=()=>b.closest('dialog').close());
$('#setup').onsubmit=async e=>{e.preventDefault();const key=$('#key').value;$('#key').value='';try{await json('/api/config',{key});await connection();$('#settings').close();toast('Model connection configured')}catch(e){toast(e.message)}};
function enable(){$('#run').disabled=busy||!selected||!configured||!$('#source').value.trim()||!$('#bug').value.trim();$('#export-project').disabled=busy||!Object.keys(files).length;$('#source').readOnly=busy;$('#bug').readOnly=busy;$('#zip').disabled=busy;$('#paste-open').disabled=busy;$('#new-project').disabled=busy;$$('[data-sample]').forEach(b=>b.disabled=busy)}
function hideReview(){current=null;$('#review').hidden=true}
function renderFiles(){
 const query=$('#file-search').value.toLowerCase();$('#file-count').textContent=Object.keys(files).length;
 $('#file-list').replaceChildren(...Object.keys(files).filter(n=>n.toLowerCase().includes(query)).map(name=>{const b=el('button',undefined,'file-btn'+(name===selected?' active':''));b.append(el('span',name.split('.').pop(),'ext'),el('span',name));b.title=name;b.onclick=()=>{if(busy)return;selectFile(name)};return b}));
 $('#context-files').replaceChildren(...Object.keys(files).filter(n=>n!==selected).map(name=>{const label=el('label');const box=el('input');box.type='checkbox';box.checked=context.has(name);box.disabled=busy;box.onchange=()=>{if(box.checked){if(context.size>=5||[...context,name].reduce((a,k)=>a+bytes(files[k]),0)>40000){box.checked=false;toast('Choose up to 5 context files totalling 40 KB.');return}context.add(name)}else context.delete(name);$('#context-count').textContent=context.size+' selected'};label.append(box,document.createTextNode(name));return label}));
 $('#context-count').textContent=context.size+' selected';enable()
}
function selectFile(name){selected=name;context.delete(name);$('#selected-name').textContent=name;$('#source').value=files[name];$('#source').hidden=false;$('#editor-empty').hidden=true;$('#source-meta').textContent=name.split('.').pop().toUpperCase();sourceMeta();renderFiles()}
function sourceMeta(){$('#source-size').textContent=($('#source').value.split('\n').length)+' lines · '+(bytes($('#source').value)/1000).toFixed(1)+' KB'}
$('#source').oninput=()=>{if(selected)files[selected]=$('#source').value;sourceMeta();enable()};
$('#bug').oninput=()=>{$('#bug-count').textContent=$('#bug').value.length+' / 1200';enable()};
$('#file-search').oninput=renderFiles;
function setProject(next){files=next;selected='';context.clear();reviews=[];projectVersion++;renderHistory();hideReview();$('#file-search').value='';selectFile(Object.keys(files)[0]);$('#upload-note').replaceChildren()}
function mayReplace(){return !Object.keys(files).length||confirm('Replace this workspace? Export first if you want to keep its files and reviews.')}
async function sample(kind){if(busy||!mayReplace())return;location.hash='studio';busy=true;enable();activity('Loading example…','busy');const name=kind==='average'?'calculator.py':'slug.py';try{const names=[name,'test_'+name];const contents=await Promise.all(names.map(async n=>{const r=await fetch('/sample/'+n);if(!r.ok)throw Error('Could not load the sample.');return r.text()}));setProject(Object.fromEntries(names.map((n,i)=>[n,contents[i]])));context.add(names[1]);$('#bug').value=kind==='average'?'average([1, 2]) should return 1.5, but returns 1. Preserve the function interface and existing nonempty-list behaviour.':'slug("Hello   World") should return "hello-world", but creates repeated hyphens. Preserve the function interface.';$('#bug').oninput();activity('Example loaded. Its existing tests are selected as model context.')}catch(e){activity(e.message,'error')}finally{busy=false;renderFiles()}}
$$('[data-sample]').forEach(b=>b.onclick=()=>sample(b.dataset.sample));
async function upload(file){if(!file||busy)return;if(file.size>2000000){toast('Choose a ZIP smaller than 2 MB.');return}if(!mayReplace())return;busy=true;enable();activity('Reading the project archive…','busy');location.hash='studio';try{const arr=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<arr.length;i+=32768)binary+=String.fromCharCode(...arr.subarray(i,i+32768));const d=await json('/api/upload',{zip:btoa(binary)});setProject(d.files);if(d.skipped.length){const det=el('details');det.append(el('summary',d.skipped.length+' entries skipped; exports contain workspace files only.'),el('p',d.skipped.join(', ')));$('#upload-note').append(det)}activity(d.count+' text files loaded. Choose the target and describe the bug.')}catch(e){activity(e.message,'error')}finally{busy=false;$('#zip').value='';renderFiles()}}
$('#zip').onchange=e=>upload(e.target.files[0]);
$('#drop').ondragover=e=>{e.preventDefault();$('#drop').classList.add('drag')};
$('#drop').ondragleave=()=>$('#drop').classList.remove('drag');
$('#drop').ondrop=e=>{e.preventDefault();$('#drop').classList.remove('drag');upload(e.dataTransfer.files[0])};
$('#paste-open').onclick=()=>$('#paste-dialog').showModal();
$('#paste-form').onsubmit=e=>{e.preventDefault();const name=$('#filename').value.trim().replaceAll('\\','/'),source=$('#paste-code').value;if(!/^[\w./ -]+\.(py|js|ts|jsx|tsx|html|css|json|md|txt|yaml|yml)$/i.test(name)||name.startsWith('/')||name.split('/').includes('..')){toast('Use a relative filename with a supported extension.');return}if(bytes(source)>30000){toast('Keep the repair source under 30 KB.');return}if(!files[name]&&Object.keys(files).length>=40){toast('A workspace supports up to 40 files.');return}if(files[name]&&!confirm('Replace the existing '+name+'?'))return;files[name]=source;selectFile(name);$('#paste-dialog').close();$('#paste-code').value='';location.hash='studio';toast('Source added to workspace')};
$('#new-project').onclick=()=>{if(!mayReplace())return;files={};selected='';context.clear();reviews=[];projectVersion++;hideReview();renderHistory();$('#source').value='';$('#source').hidden=true;$('#editor-empty').hidden=false;$('#selected-name').textContent='Choose your starting point';$('#source-meta').textContent='NO FILE SELECTED';$('#source-size').textContent='No source loaded';$('#bug').value='';$('#bug').oninput();$('#upload-note').replaceChildren();activity('');renderFiles()};
function lists(selector,items,empty){$(selector).replaceChildren(...(items.length?items:[empty]).map(v=>el('li',v)))}
function tab(name){$$('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===name)));$$('.tab-content').forEach(p=>p.hidden=p.id!=='tab-'+name)}
$$('[data-tab]').forEach(b=>b.onclick=()=>tab(b.dataset.tab));
$$('[role=tab]').forEach((b,i)=>b.onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const tabs=$$('[role=tab]');const next=tabs[(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length];next.click();next.focus()}});
function renderReview(r){
 current=r;$('#review').hidden=false;$('#review-title').textContent=r.filename;$('#review-state').textContent=r.decision||r.status;
 $('#review-meta').textContent=r.model+' · '+(r.usage?.total_tokens||0)+' tokens · '+r.elapsed+'s · '+r.context_files.length+' context files';
 $('#diagnosis').textContent=r.diagnosis;lists('#changes',r.changes,'No changes described.');lists('#risks',r.risks,'No additional risks were identified by the model. This is not a guarantee.');
 $('#replacement').textContent=r.proposed;
 let add=0,remove=0;
 $('#diff').replaceChildren(...(r.diff?r.diff.split('\n'):['No change proposed.']).map((line,i)=>{let type='';if(line.startsWith('@@')||line.startsWith('+++')||line.startsWith('---'))type='meta';else if(line.startsWith('+')){type='add';add++}else if(line.startsWith('-')){type='remove';remove++}const n=el('div',undefined,'diff-line '+type);n.append(el('span',String(i+1),'line-no'),document.createTextNode(line||' '));return n}));
 $('#diff-count').textContent='+'+add+' / −'+remove;
 $('#checks').replaceChildren(...[['Original',r.before_check],['Proposed',r.after_check]].map(([title,c])=>{const box=el('div',undefined,'check '+c.state);box.append(el('strong',title+' · '+c.label),el('p',c.detail),el('span',c.state==='passed'?'SYNTAX PASSED':c.state==='failed'?'SYNTAX FAILED':'NOT CHECKED','tag'+(c.state==='passed'?'':' warm')));return box}));
 $('#test-list').replaceChildren(...r.suggested_tests.map(t=>{const a=el('article',undefined,'test-card');a.append(el('h3',t.name),el('pre',t.code));return a}));
 if(!r.suggested_tests.length)$('#test-list').append(el('p','The model did not suggest regression tests.','muted'));
 $('#accept').disabled=busy||!!r.decision||!r.diff||r.after_check.state==='failed';$('#reject').disabled=busy||!!r.decision;
 tab('overview');renderHistory()
}
function renderHistory(){$('#history').replaceChildren(...reviews.map((r,i)=>{const b=el('button');b.append(document.createTextNode(r.filename),el('small',(r.decision||'Review required')+' · '+r.elapsed+'s'));b.onclick=()=>{renderReview(r);$('#review').scrollIntoView({behavior:'smooth',block:'start'})};return b}));if(!reviews.length)$('#history').append(el('p','Completed reviews appear here.','muted empty-rail'))}
$('#run').onclick=async()=>{
 if(busy||!selected)return;const source=$('#source').value;if(bytes(source)>30000){activity('Keep the target source under 30 KB.','error');return}
 busy=true;enable();renderFiles();controller=new AbortController();$('#cancel').hidden=false;$('#run').textContent='Preparing review…';let seconds=0;const timer=setInterval(()=>activity('Nemotron is preparing your review · '+(++seconds)+'s','busy'),1000);const timeout=setTimeout(()=>controller.abort(),105000);activity('Sending the selected source and context to Nemotron…','busy');
 const report=$('#bug').value, name=selected, generation=projectVersion;const ctx=Object.fromEntries([...context].filter(n=>n!==name).map(n=>[n,files[n]]));
 try{const r=await json('/api/propose',{filename:name,source,description:report,context:ctx},controller.signal);if(projectVersion!==generation)return;r.report=report;r.projectVersion=generation;r.decision='';reviews.unshift(r);if(reviews.length>12)reviews.pop();renderReview(r);activity('Review ready. Syntax checks are shown separately from suggested tests.');$('#review').scrollIntoView({behavior:'smooth',block:'start'})}
 catch(e){activity(e.name==='AbortError'?'Stopped waiting. The server may still finish the model request; it may still consume tokens. Your source is unchanged.':e.message,'error')}
 finally{clearInterval(timer);clearTimeout(timeout);busy=false;controller=null;$('#cancel').hidden=true;$('#run').innerHTML='Generate repair <span>↗</span>';renderFiles();if(current)renderReview(current)}
};
$('#cancel').onclick=()=>controller?.abort();
$('#accept').onclick=()=>{if(!current||busy)return;if(current.projectVersion!==projectVersion||files[current.filename]!==current.original){toast('The source has changed since this review. Generate a fresh repair before accepting.');return}files[current.filename]=current.proposed;current.decision='ACCEPTED';selectFile(current.filename);renderReview(current);toast('Accepted into the browser workspace. Export to take it with you.')};
$('#reject').onclick=()=>{if(!current||busy)return;current.decision='KEPT ORIGINAL';renderReview(current);toast('Proposal dismissed. Workspace source unchanged.')};
function download(content,name,type='text/plain'){const a=document.createElement('a'),url=URL.createObjectURL(content instanceof Blob?content:new Blob([content],{type}));a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
$('#export-project').onclick=async()=>{try{const r=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({files})});if(!r.ok)throw Error((await r.json()).error);download(await r.blob(),'patchwork-workspace.zip');toast('Exported supported workspace files.')}catch(e){toast(e.message)}};
$('#export-diff').onclick=()=>{if(current)download(current.diff,'patchwork-repair.patch')};
$('#export-report').onclick=()=>{if(!current)return;const r=current;const report={product:'Patchwork',exported_at:new Date().toISOString(),...r};delete report.projectVersion;download(JSON.stringify(report,null,2),'patchwork-review.json','application/json')};
$('#copy').onclick=async()=>{try{await navigator.clipboard.writeText(current.proposed);toast('Replacement copied')}catch{toast('Clipboard unavailable. Use the replacement tab or export the workspace.')}};
window.addEventListener('beforeunload',e=>{if(Object.keys(files).length){e.preventDefault();e.returnValue=''}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&!$('#run').disabled){e.preventDefault();$('#run').click()}});
