(async()=>{
 'use strict';const $=s=>document.querySelector(s),params=new URLSearchParams(location.search),compact=params.has('compact');document.body.classList.toggle('compact',compact);
 const note=$('#status');const progress=s=>{note.hidden=false;note.textContent=s;};
 try{
  const reg=await navigator.serviceWorker.register('/game-assets-sw.js',{scope:'/',updateViaCache:'none'});await navigator.serviceWorker.ready;
  if(!navigator.serviceWorker.controller)await new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true}));
  const L=window.Laya,req=window.__pirateRequire;req(836);req(838);req(2277).OverWrite.register();
  L.init(innerWidth,Math.max(100,innerHeight-(compact?0:115)),L.WebGL);$('#canvas').append(L.Render.canvas);L.stage.bgColor='#0d1928';L.stage.scaleMode='noscale';L.SoundManager.muted=true;L.URL.basePath=location.origin+'/game/';
  const flags=req(18).default;flags.isLocal=true;flags.enableKtx=false;flags.allConfig={resourcesUpdateConfig:{verName:'offline'},gameConfig:{productCode:'hw_en',channelJsonConfigs:{clientPath:L.URL.basePath,refFlag:'En',langType:'en'}}};
  const query=new URL(location.href);query.searchParams.set('productCode','hw_en');query.searchParams.set('lang','en');history.replaceState(null,'',query);req(81).default.init();L.URL.basePath=location.origin+'/game/';
  const wait=start=>new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Model reference loading timed out.')),30000);start(()=>{clearTimeout(timer);resolve();});});
  await wait(done=>L.ResourceVersion.enable('/game/version.json',L.Handler.create(null,done),L.ResourceVersion.FILENAME_VERSION));
  const Ref=req(29).default;Ref.refFlag='En';Ref.nRefCount={countEn:10};await Ref.it.loadPreRef();await Ref.it.loadMainRef();
  const translations=await(await fetch('/game/i18n/en.json')).json();L.Text.langPacks=translations;req(14).LangMgr.it.saveLangType('en');
  const data=await(await fetch('/data/hub-data.json')).json(),character=data.characters.find(c=>c.id===Number(params.get('character')));if(!character)throw Error('Character is absent from the captured roster.');
  $('#name').textContent=character.name+' · Skin studio';const choices=[{id:character.id,name:'Original · '+character.name},...character.skinIds.map(id=>data.skins.find(s=>s.id===id)).filter(Boolean)];
  if(character.skinIds.includes(16059004))choices.push({id:16059004,name:'Halloween King · transformed',transformed:true});
  for(let i=0;i<choices.length;i++){const o=document.createElement('option');o.value=i;o.textContent=choices[i].name;$('#skin').append(o);}
  let models=[],serial=0,compare=false,paused=false,motion='idle',zoom=1;
  const pattern={idle:/idle|stand|daiji/i,run:/run|walk|move|pao/i,attack:/attack|atk|gongji/i,skill:/skill|super|jineng/i};
  function fit(){const w=innerWidth,h=Math.max(100,innerHeight-(compact?0:115));L.stage.size(w,h);const cols=compare?Math.min(models.length,w<600?2:3):1,rows=Math.ceil(models.length/cols),cw=w/cols,ch=h/rows;
   models.forEach((m,i)=>{const col=i%cols,row=Math.floor(i/cols),body=ch-(compact?0:38);m.sprite?.scale(1.8*zoom*Math.min(cw/350,body/340),1.8*zoom*Math.min(cw/350,body/340));m.sprite?.pos(cw*(col+.5),row*ch+body*.92);if(m.label){m.label.pos(col*cw+6,row*ch+ch-32);m.label.width=cw-12;}});
  }
  function play(){for(const m of models){if(!m.names.length)continue;const name=m.names.includes(motion)?motion:m.names.find(n=>pattern[motion]?.test(n))||m.names[0];m.sprite.play(name,true,true);if(paused)m.sprite.paused();}}
  async function show(){const id=++serial;for(const m of models){m.sprite?.destroy(true);m.label?.destroy(true);}models=[];progress('Loading original sprite textures…');const selected=compare?choices:[choices[Number($('#skin').value)||0]];
   try{await Promise.all(selected.map(c=>new Promise((resolve,reject)=>{const base=c.id===character.id,ref=base?req(48).GeneralRefMgr.it.getGeneralRef(c.id):req(48).GeneralRefMgr.it.getGeneralSkinRef(c.id);let path=base?`spine/role/${c.id}.sk`:`spine/roleSkin/${c.id}.sk`;
    try{const style=req(58).SpineStyleRefMgr.it.getRef(ref.ani||c.id);if(style?.name)path=req(22).getAsset(style.name)||path;}catch(_){}
    if(c.transformed)path='spine/roleSkin/16059004_bianshen.sk';const sprite=new L.Skeleton(),m={sprite,names:[],label:null};models.push(m);L.stage.addChild(sprite);const timer=setTimeout(()=>reject(Error('Could not load '+c.name+'. Try selecting it again.')),30000);
    sprite.load(path,L.Handler.create(null,()=>{clearTimeout(timer);if(id!==serial)return resolve();if(!sprite.templet)return reject(Error('No model template for '+c.name));for(let n=0;n<sprite.getAnimNum();n++)m.names.push(sprite.getAniNameByIndex(n));if(!compact){m.label=new L.Text();Object.assign(m.label,{text:c.name,color:'#9ed9ec',font:'Arial',fontSize:13,align:'center',overflow:'hidden'});L.stage.addChild(m.label);}resolve();}),0);
   })));if(id!==serial)return;const previous=motion;$('#motion').replaceChildren();const names=[...new Set([...Object.keys(pattern),...models.flatMap(m=>m.names)])];for(const name of names){const o=document.createElement('option');o.value=name;o.textContent=name;$('#motion').append(o);}$('#motion').value=names.includes(previous)?previous:names[0];motion=$('#motion').value;fit();play();note.hidden=true;$('#count').textContent=models.length+' original model'+(models.length===1?'':'s');document.body.dataset.modelsReady=String(models.length);
   }catch(e){if(id===serial)progress(e.message);}}
  $('#skin').onchange=()=>{compare=false;show();};$('#compare').onclick=()=>{compare=true;show();};$('#single').onclick=()=>{compare=false;show();};$('#motion').onchange=()=>{motion=$('#motion').value;play();};$('#pause').onclick=()=>{paused=!paused;$('#pause').textContent=paused?'Resume':'Pause';if(paused)models.forEach(m=>m.sprite.paused());else play();};$('#zoom').oninput=()=>{zoom=Number($('#zoom').value);fit();};addEventListener('resize',fit);if(!compact)$('#controls').hidden=false;await show();
 }catch(e){progress('Sprite preview: '+e.message);}
})();
