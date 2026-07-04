let selectedTopic='general', selectedCP='none';
const STEPS=[
  {key:'upload',label:'Uploading video',icon:'📤'},
  {key:'audio',label:'Extracting audio',icon:'🎵'},
  {key:'transcribe',label:'Analyzing video',icon:'🧠'},
  {key:'analyze',label:'Finding best moments',icon:'🎯'},
  {key:'clips',label:'Cutting & processing',icon:'✂️'},
  {key:'captions',label:'Applying protection & captions',icon:'🛡️'},
  {key:'done',label:'Done!',icon:'🎉'},
];
let jobId=null,timer=null;
let useUrlMode = false;
let selectedCapStyle = 'classic';
function selectCapStyle(el, style) {
  document.querySelectorAll('.cap-style').forEach(x => {
    x.style.background = '#0f0f1a';
    x.style.borderColor = '#2d2d4e';
  });
  el.style.background = '#13132a';
  el.style.borderColor = '#a78bfa';
  selectedCapStyle = style;
}
document.getElementById('captions').addEventListener('change', function(){
  document.getElementById('captionStyleSection').style.display = this.checked ? 'flex' : 'none';
});
function selectTopic(el,t){document.querySelectorAll('.topic').forEach(x=>x.classList.remove('active'));el.classList.add('active');selectedTopic=t;}
function selectCP(el,t){document.querySelectorAll('.cp-item').forEach(x=>x.classList.remove('active'));el.classList.add('active');selectedCP=t;
  const mirror=document.getElementById('mirror');
  const speed=document.getElementById('speed');
  const pitch=document.getElementById('pitch');
  const colorgrade=document.getElementById('colorgrade');
  if(t==='none'){mirror.checked=false;speed.checked=false;pitch.checked=false;colorgrade.checked=false;}
  else if(t==='light'){mirror.checked=false;speed.checked=true;pitch.checked=false;colorgrade.checked=true;}
  else if(t==='medium'){mirror.checked=true;speed.checked=true;pitch.checked=true;colorgrade.checked=true;}
  else if(t==='strong'){mirror.checked=true;speed.checked=true;pitch.checked=true;colorgrade.checked=true;}
}
document.getElementById('file').onchange=e=>{
  if(e.target.files[0]){document.getElementById('chosen').textContent='✅ '+e.target.files[0].name;document.getElementById('btn').disabled=false;}
};
function renderSteps(cur,errStep){
  const idx=STEPS.findIndex(s=>s.key===cur);
  document.getElementById('steps').innerHTML=STEPS.map((s,i)=>{
    let ic='',tc='',icon=s.icon;
    if(s.key===errStep){ic='error';icon='❌';}
    else if(i<idx){ic='done';icon='✅';tc='done';}
    else if(i===idx){ic='active';tc='active';}
    return `<div class="step"><div class="sicon ${ic}">${icon}</div><div class="stext ${tc}">${s.label}</div></div>`;
  }).join('');
  document.getElementById('fill').style.width=Math.min(100,Math.round(idx/(STEPS.length-1)*100))+'%';
}
function uploadWithProgress(formData) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const pct = Math.round((e.loaded / e.total) * 100);
      document.getElementById('fill').style.width = pct + '%';
      document.getElementById('uploadPct').textContent = pct + '%';
    };
    xhr.onload = () => {
      let data;
      try { data = JSON.parse(xhr.responseText); }
      catch (e) { reject(new Error('Unexpected server response.')); return; }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new Error(data.error || 'Upload failed'));
    };
    xhr.onerror = () => reject(new Error('Network error during upload.'));
    xhr.send(formData);
  });
}
async function start(){
  const f=document.getElementById('file').files[0];
  if(!f && !useUrlMode)return;
  document.getElementById('btn').disabled=true;
  document.getElementById('err').style.display='none';
  document.getElementById('prog').style.display='block';
  document.getElementById('results').style.display='none';
  renderSteps('upload',null);
  document.getElementById('uploadPct').style.display='block';
  document.getElementById('uploadPct').textContent='0%';
  document.getElementById('prog').scrollIntoView({behavior:'smooth'});
  const fd=new FormData();
  if(useUrlMode){
  } else {
    fd.append('video',f);
  }
  fd.append('num_clips',document.getElementById('num').value);
  fd.append('clip_length',document.getElementById('len').value);
  fd.append('topic',selectedTopic);
  fd.append('cp_level',selectedCP);
  fd.append('captions',document.getElementById('captions').checked?'1':'0');
  fd.append('caption_style', selectedCapStyle);
  fd.append('reframe',document.getElementById('reframe').checked?'1':'0');
  fd.append('mirror',document.getElementById('mirror').checked?'1':'0');
  fd.append('colorgrade',document.getElementById('colorgrade').checked?'1':'0');
  fd.append('speed',document.getElementById('speed').checked?'1':'0');
  fd.append('pitch',document.getElementById('pitch').checked?'1':'0');
  fd.append('music',document.getElementById('music').checked?'1':'0');
  try{
    const d=await uploadWithProgress(fd);
    if(!d.job_id)throw new Error(d.error||'Upload failed');
    jobId=d.job_id;
    document.getElementById('uploadPct').style.display='none';
    renderSteps('audio',null);
    timer=setInterval(poll,3000);
  }catch(e){showErr(e.message);}
}
async function poll(){
  try{
    const r=await fetch('/status/'+jobId);const d=await r.json();
    renderSteps(d.step,d.error_step||null);
    if(d.step==='done'&&d.clips&&d.clips.length>0){clearInterval(timer);showResults(d.clips);}
    else if(d.status==='error'){clearInterval(timer);showErr(d.message||'Error. Please try again.');}
  }catch(e){}
}
function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    btn.style.background = '#14532d';
    btn.style.color = '#4ade80';
    setTimeout(() => { btn.textContent = orig; btn.style.background = ''; btn.style.color = ''; }, 1500);
  });
}
function showResults(clips){
  document.getElementById('prog').style.display='none';
  document.getElementById('results').style.display='block';
  document.getElementById('cliplist').innerHTML=clips.map((c,i)=>{
    const s=c.virality_score||70;
    const bc=s>=75?'high':s>=50?'mid':'low';
    const em=s>=75?'🔥':s>=50?'⚡':'📊';
    const protections = c.protections||[];
    const ptags = protections.length ? protections.map(p=>`<span class="cp-tag">${p}</span>`).join('') : '';
    const titleEsc = (c.title||"").replace(/`/g,"'");
    const descEsc = (c.description||"").replace(/`/g,"'");
    return `<div class="clip-item"><div class="clip-top">
      <div class="clip-title">${i+1}. ${c.title}</div>
      <div class="clip-meta"><span class="badge ${bc}">${em} ${s}/100</span><span class="tag2">⏱ ${c.duration}s</span>${c.has_captions?'<span class="tag2">💬</span>':''}</div>
    </div>${ptags?`<div class="cp-tags">${ptags}</div>`:''}
    ${titleEsc ? `<div class="meta-box">
      <div class="meta-label">📝 Title <button class="copy-btn" onclick="copyText(this.dataset.text, this)" data-text="${titleEsc}">Copy</button></div>
      <div class="meta-text">${c.title}</div>
    </div>` : ''}
    ${descEsc ? `<div class="meta-box">
      <div class="meta-label">📋 Description <button class="copy-btn" onclick="copyText(this.dataset.text, this)" data-text="${descEsc}">Copy</button></div>
      <div class="meta-text">${c.description}</div>
    </div>` : ''}
    <div class="clip-reason">${c.reason}</div>
    <a class="dl-btn" href="/download/${jobId}/${c.filename}" download="${c.filename}">⬇️ Download Clip ${i+1}</a>
    </div>`;
  }).join('');
  document.getElementById('results').scrollIntoView({behavior:'smooth'});
}
function showErr(m){document.getElementById('btn').disabled=false;document.getElementById('prog').style.display='none';document.getElementById('uploadPct').style.display='none';const e=document.getElementById('err');e.textContent='❌ '+m;e.style.display='block';}
function resetApp(){document.getElementById('results').style.display='none';document.getElementById('uploadPct').style.display='none';document.getElementById('file').value='';document.getElementById('chosen').textContent='';document.getElementById('btn').disabled=true;window.scrollTo({top:0,behavior:'smooth'});}
