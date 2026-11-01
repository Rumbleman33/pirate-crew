(function(){
 'use strict';
 const $=s=>document.querySelector(s),frame=$('#game-frame'),nav=$('nav[aria-label="Offline tools"]'),panels=$('#tool-panel');
 const runtime=()=>frame.contentWindow?.PirateOfflineRuntime,combat=()=>frame.contentWindow?.PirateCombatTools;
 const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 async function api(path,body){const r=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const v=await r.json();if(!r.ok||v.ok===false)throw Error(v.detail||v.error?.message||v.error||'Request failed.');return v;}
 function panel(id,label){const b=el('button',label,'nav');b.dataset.tab=id;nav.append(b);const p=el('section',undefined,'tool-tab');p.dataset.panel=id;p.hidden=true;panels.append(p);b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(n=>n.classList.toggle('active',n===b));document.querySelectorAll('[data-panel]').forEach(n=>n.hidden=n!==p);p.dispatchEvent(new Event('opened'));};return p;}
 function field(parent,label,tag='input'){const l=el('label',label),input=document.createElement(tag);input.setAttribute('aria-label',label);l.append(input);parent.append(l);return input;}
 function button(parent,label,fn){const b=el('button',label);parent.append(b);b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){status.textContent=e.message;}finally{b.disabled=b.dataset.locked==='true';}};return b;}
 function download(name,data){const a=el('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),5000);}
 const status=el('p','','sandbox-status');status.setAttribute('role','status');panels.prepend(status);
 const tableCache=new Map();async function refs(name){if(!tableCache.has(name)){const rows=[];let offset=0,total=1;while(offset<total){const page=await api(`/api/references/${name}?limit=500&offset=${offset}`);rows.push(...page.rows);offset+=page.rows.length;total=page.total;if(!page.rows.length)break;}tableCache.set(name,rows);}return tableCache.get(name);}
 async function apply(cid,payload){const r=await api('/api/command',{id:cid,payload});runtime()?.applyResult(r);await runtime()?.refresh();return r.reply;}
 async function gm(command,arg=''){if(frame.contentWindow?.PirateTestingUI)return frame.contentWindow.PirateTestingUI.run(command,arg);const r=await api('/api/gm',{command,arg});runtime()?.applyResult(r);await runtime()?.refresh();return r;}

 const testingPanel=panel('training-tools','⚑ Training & test presets');
 testingPanel.append(el('h2','Training & test presets'),el('p','Choose talents, captain and character levels separately. Free presets use captured caps and preserve assignments.'));
 button(testingPanel,'Open native boss selector',()=>frame.contentWindow.PirateTestingUI.show('boss'));
 button(testingPanel,'Open native level selector',()=>frame.contentWindow.PirateTestingUI.show('presets'));
 for(const [text,command] of [['Max all pets','maxPets'],['Max all mounts','maxMounts'],['Max all treasures','maxTreasures'],['Max all ships','maxShips'],['Max all Haki','maxHaki'],['Max all four systems','maxAllSystems']])button(testingPanel,text,()=>gm(command));
 testingPanel.append(el('p','Boss practice is also in More → Training. It uses your deployed crew, captured boss stats and the Impel Down arena; it grants no rewards or progression. One Piece objectives are automatically complete at every promotion tier.'));

 // Equipment/artifact/One Piece controls complement their original game windows.
 const gearPanel=panel('equipment-tools','⚔ Gear, artifacts & One Piece');gearPanel.append(el('h2','Gear, artifacts & One Piece'),el('p','Three copies of every captured gear variant are preloaded. Equip requirements still apply. Artifact effects are combat passives; they do not all add visible CP.'));
 const hero=field(gearPanel,'Owned character','select'),artifact=field(gearPanel,'Artifact for this character','select'),artifactState=el('p','','sandbox-status');gearPanel.append(artifactState);
 const activateArtifact=button(gearPanel,'Activate artifact',()=>apply(3501,{refId:Number(artifact.value)}).then(refreshGear)),upgradeArtifact=button(gearPanel,'Upgrade artifact +1',()=>apply(3502,{refId:Number(artifact.value)}).then(refreshGear));
 button(gearPanel,'Open original artifact screen',()=>runtime().openFeature('Unique',{generalId:Number(hero.value)}));
 const gearSelect=field(gearPanel,'Owned gear (matching class; requirements shown)','select');
 button(gearPanel,'Equip selected gear',()=>apply(1351,{generalId:Number(hero.value),equipId:gearSelect.value}).then(refreshGear));
 button(gearPanel,'Unequip selected gear',()=>apply(1352,{equipId:gearSelect.value}).then(refreshGear));
 button(gearPanel,'Toggle gear lock',()=>apply(1355,{equipId:gearSelect.value}).then(refreshGear));
 button(gearPanel,'Identify selected gear',()=>apply(1360,{equipId:gearSelect.value}).then(refreshGear));
 button(gearPanel,'Open original gear screen',()=>runtime().openFeature('Equip',{generalId:Number(hero.value)}));
 const gearState=el('p','','sandbox-status');gearPanel.append(gearState,el('h3','One Piece / Voyage'));
 const voyageState=el('p','','sandbox-status'),voyageTasks=el('div');gearPanel.append(voyageState,voyageTasks);
 button(gearPanel,'Promote One Piece title',()=>apply(2101,{}).then(refreshGear));button(gearPanel,'Open original One Piece screen',()=>runtime().openFeature('Voyage'));
 button(gearPanel,'Complete current objectives for testing',async()=>{await gm('completeVoyageTasks');await refreshGear();});
 gearPanel.append(el('small','The test shortcut only makes current objectives claimable. Claim them and promote normally. Gear preloads do not count as forged equipment.'));
 let gearBusy=false;
 async function refreshGear(){if(gearBusy)return;gearBusy=true;try{
  const [snapshot,generals,uniques,equips,titles,tasks]=await Promise.all([api('/api/me/snapshot'),refs('GeneralRef'),refs('UniqueRef'),refs('EquipRef'),refs('VoyageTitleRef'),refs('VoyageTaskRef')]);
  const names=new Map(generals.map(r=>[Number(r.refId),{...r,name:r.generalName||r.name}]));const old=hero.value;hero.replaceChildren(...Object.values(snapshot.generals).map(g=>new Option(`${names.get(g.generalId)?.name||g.generalId} · Lv.${g.level}${uniques.some(u=>Number(u.generalId)===g.generalId)?' · artifact':''}`,g.generalId)));if([...hero.options].some(o=>o.value===old))hero.value=old;
  const gid=Number(hero.value),g=snapshot.generals[hero.value],ur=uniques.find(r=>Number(r.generalId)===gid);artifact.replaceChildren();if(ur)artifact.add(new Option(ur.name,ur.refId));
  const owned=snapshot.uniques?.[ur?.refId];artifactState.textContent=ur?`${ur.name}: ${owned?'level '+owned.lv:'not activated'}. Costs and maximum follow the captured rows.`:'No captured artifact for this character.';
  activateArtifact.disabled=!ur||!!owned;upgradeArtifact.disabled=!ur||!owned||Number(owned.lv)>=5;
  activateArtifact.dataset.locked=String(activateArtifact.disabled);upgradeArtifact.dataset.locked=String(upgradeArtifact.disabled);
  const definitions=new Map(equips.map(r=>[Number(r.refId),r])),current=gearSelect.value,typ=Number(names.get(gid)?.type);
  const options=snapshot.equipment.filter(e=>Number(definitions.get(e.equipRefId)?.generalType)===typ).map(e=>{const r=definitions.get(e.equipRefId);return {e,r};}).sort((a,b)=>Number(b.e.generalId===gid)-Number(a.e.generalId===gid)||Number(a.r.needLevel)-Number(b.r.needLevel)||Number(b.r.order)-Number(a.r.order));
  gearSelect.replaceChildren(...options.map(({e,r})=>new Option(`${r.name} · Lv.${r.needLevel} · slot ${r.part}${e.generalId?' · worn by '+(names.get(e.generalId)?.name||e.generalId):''}${e.lock?' · locked':''} · #${e.equipId}`,e.equipId)));
  if([...gearSelect.options].some(o=>o.value===current))gearSelect.value=current;
  gearState.textContent=`${snapshot.equipment.length.toLocaleString()} actual gear pieces · bag capacity ≥10,000 · ${Number(snapshot.inventory['109']||0).toLocaleString()} achievement points. Character Lv.${g?.level||1}.`;
  const info=(await api('/api/command',{id:2100,payload:{}})).reply,title=titles.find(r=>Number(r.refId)===info.title);voyageState.textContent=`${title?.name||info.title} · captain level cap ${title?.maxLevel||'?'} · your captain Lv.${snapshot.player.level}`;
  voyageTasks.replaceChildren();for(const task of info.tasks){const row=tasks.find(r=>Number(r.refId)===task.refId),box=el('div',undefined,'sandbox-row');box.append(el('p',`${row?.name||task.refId}: ${task.progress} · ${task.state===3?'claimed':task.state===2?'ready to claim':'in progress'}`));if(task.state===2)button(box,'Claim objective',()=>apply(2102,{taskRefId:task.refId}).then(refreshGear));voyageTasks.append(box);}
 }finally{gearBusy=false;}}
 hero.onchange=()=>refreshGear().catch(e=>status.textContent=e.message);gearPanel.addEventListener('opened',()=>refreshGear().catch(e=>status.textContent=e.message));

 const logPanel=panel('combat-log','☷ Combat log & inspect');logPanel.append(el('h2','Live combat log'),el('p','Calculated damage, applied HP/shield changes, skills, buffs and deaths are separate phases. Calculated and echoed damage must not be added together. Recording is bounded to 2,000 events.'));
 const logging=field(logPanel,'Record combat','input');logging.type='checkbox';logging.onchange=()=>combat()?.setLogging(logging.checked);
 const filter=field(logPanel,'Filter actor, skill, event or ID');filter.placeholder='crit, buff, 2000001…';
 const eventBox=el('div',undefined,'sandbox-events');logPanel.append(eventBox);let eventRows=[];
 function renderEvents(){const term=filter.value.toLowerCase(),rows=eventRows.filter(e=>!term||JSON.stringify(e).toLowerCase().includes(term)).slice(-120).reverse();eventBox.replaceChildren(...rows.map(e=>{const d=el('details'),summary=el('summary',`#${e.sequence} ${e.phase} · ${e.actor?.name||e.attacker?.name||''}${e.hpChange!==undefined?' · HP '+e.hpChange:''}`);d.append(summary,el('pre',JSON.stringify(e,null,2)));return d;}));}
 filter.oninput=renderEvents;button(logPanel,'Export combat log',()=>download('pirate-combat-log.json',{version:1,events:eventRows}));button(logPanel,'Clear log',()=>{eventRows=[];combat()?.clear();renderEvents();});
 logPanel.append(el('h3','Inspect mobs, bosses and fighters'));
 const inspectMode=field(logPanel,'Click actors in the game to inspect','input');inspectMode.type='checkbox';inspectMode.onchange=()=>combat()?.setInspect(inspectMode.checked);
 const actorList=field(logPanel,'Current scene actors','select');button(logPanel,'Refresh actors',()=>{actorList.replaceChildren(...(combat()?.listActors()||[]).map(a=>new Option(`${a.name} · ${a.refId} · HP ${a.hp}/${a.maxHp}`,a.uid)));});button(logPanel,'Inspect selected actor',()=>combat().inspect(actorList.value));
 const inspected=el('div');logPanel.append(inspected);let lastInspection;
 const matrixFile=field(logPanel,'Import your loadout matrix JSON','input');matrixFile.type='file';matrixFile.accept='.json,application/json';let matrix={version:1,entries:[]};try{matrix=JSON.parse(localStorage.getItem('pirate-loadout-matrix')||JSON.stringify(matrix));}catch{}
 matrixFile.onchange=async()=>{try{const file=matrixFile.files[0];if(!file||file.size>2e6)throw Error('Select a matrix JSON file smaller than 2 MB.');const value=JSON.parse(await file.text());if(value.version!==1||!Array.isArray(value.entries)||value.entries.length>5000||value.entries.some(r=>!Number.isInteger(r.enemyRefId)||!Array.isArray(r.recommendations)))throw Error('Expected version 1 with entries [{enemyRefId,recommendations:[{type,refId,reason}]}].');matrix=value;localStorage.setItem('pirate-loadout-matrix',JSON.stringify(value));if(lastInspection)renderInspection(lastInspection);status.textContent=`Loaded ${value.entries.length} enemy recommendation rules.`;}catch(e){status.textContent=e.message;}finally{matrixFile.value='';}};
 button(logPanel,'Download matrix template',()=>download('loadout-matrix-template.json',{version:1,entries:[{enemyRefId:100101,recommendations:[{type:'petSkill',refId:401,reason:'Replace this example with your measured recommendation.',source:'Your model / experiment'}]}]}));
 function renderInspection(d){lastInspection=d;inspected.replaceChildren(el('h3',`${d.name} · ${d.refId}`),el('p',`HP ${d.hp}/${d.maxHp} · shield ${d.shield} · ${d.encounterLevel===null?'world actor; no separate level was supplied':'encounter level '+d.encounterLevel}`),el('small',d.source));for(const stat of d.stats){const row=el('div',undefined,'sandbox-stat');row.append(el('span',`${stat.name} (${stat.key})`),el('b',stat.value.toLocaleString()));inspected.append(row);}const extra=el('details');extra.append(el('summary','Skills, buffs and raw inspection'),el('pre',JSON.stringify(d,null,2)));inspected.append(extra,el('h3','Loadout recommendations'));const recs=matrix.entries.filter(r=>r.enemyRefId===d.refId);if(!recs.length)inspected.append(el('p','No matrix rule has been supplied for this enemy yet.'));for(const rule of recs)for(const r of rule.recommendations){const row=el('div',undefined,'sandbox-row');row.append(el('b',`${r.type} ${r.refId}`),el('p',String(r.reason||'')),el('small',String(r.source||'Imported user matrix')));inspected.append(row);}}
 window.addEventListener('message',e=>{if(e.origin!==location.origin||e.source!==frame.contentWindow)return;if(e.data.type==='pirate-combat-events'){eventRows.push(...e.data.detail);eventRows=eventRows.slice(-2000);if(!logPanel.hidden)renderEvents();}if(e.data.type==='pirate-actor-inspected')renderInspection(e.data.detail);if(e.data.type==='pirate-inspect-error')status.textContent=e.data.detail;if(e.data.type==='pirate-runtime-status'&&e.data.detail.ready){combat()?.setLogging(logging.checked);combat()?.setInspect(inspectMode.checked);}if(e.data.type==='pirate-challenge-result')status.textContent=`Local snapshot practice: ${e.data.detail.result}. This result is not a synchronized server match.`;});
 logPanel.addEventListener('opened',renderEvents);

 const socialPanel=panel('social','♧ Friends, chat & PvP lobby');socialPanel.append(el('h2','Friends & sandbox lobbies'),el('p','Online features use your assigned captain identity. Ready shares only the selected team and combat stats. Your inventory and local save are not uploaded.'));
 let connected=false,username='',roomId='',chatTarget='',socialBusy=false,roomData=null,serverOffset=0;
 const socialStatus=el('p','','sandbox-status');socialPanel.append(socialStatus);
 const socialApi=(path,body)=>api('/sandbox-social/'+path,body);
 button(socialPanel,'Connect social features',async()=>{const auth=await api('/api/social-session',{});username=auth.username;connected=true;roomId=localStorage.getItem('pirate-room-'+username)||'';await pollSocial();});
 const friendsList=el('div'),friend=field(socialPanel,'Captain username');friend.placeholder='Enter a registered username';friend.maxLength=24;
 button(socialPanel,'Send friend request',()=>socialApi('friend',{username:friend.value,action:'request'}).then(pollSocial));socialPanel.append(friendsList,el('h3','PvP lobby'));
 const roomName=field(socialPanel,'Lobby name');roomName.maxLength=60;button(socialPanel,'Create lobby',async()=>{const r=await socialApi('create',{name:roomName.value});roomId=r.id;localStorage.setItem('pirate-room-'+username,roomId);await pollSocial();});
 const roomList=el('div'),roomView=el('div');socialPanel.append(roomList,roomView,el('h3','Messages'));
 const targetSelect=field(socialPanel,'Chat with','select'),chat=el('div',undefined,'sandbox-chat'),message=field(socialPanel,'Message');message.maxLength=1000;socialPanel.append(chat);
 targetSelect.onchange=()=>{chatTarget=targetSelect.value;pollChat().catch(e=>socialStatus.textContent=e.message);};
 button(socialPanel,'Send message',async()=>{const target=chatTarget.startsWith('room:')?{room:chatTarget.slice(5)}:{recipient:chatTarget};await socialApi('messages',{...target,text:message.value});message.value='';await pollChat();});
 async function pollChat(){if(!chatTarget)return;const key=chatTarget.startsWith('room:')?'room':'recipient',value=chatTarget.replace(/^room:/,'');const r=await socialApi(`messages?${key}=${encodeURIComponent(value)}`);chat.replaceChildren(...r.messages.slice().reverse().map(m=>el('p',`${m.sender} · ${new Date(m.created).toLocaleTimeString()}\n${m.body}`)));chat.scrollTop=chat.scrollHeight;}
 async function shareReady(){const s=await api('/api/me/snapshot'),stats=await api('/api/stats'),team=Object.values(s.generals).filter(g=>g.isSelect).slice(0,10).map(g=>({generalId:g.generalId,level:g.level,star:g.star,skinId:g.skinId,attrs:stats[String(g.generalId)]?.values||{},skillIds:g.skillIds,entryInfos:g.entryInfos||[]}));const roster=(await api('/api/command',{id:1300,payload:{}})).reply.generals;for(const g of team)g.entryInfos=roster.find(r=>r.generalId===g.generalId)?.entryInfos||[];await socialApi('ready',{room:roomId,ready:true,team});await pollSocial();}
 async function pollSocial(){if(!connected||socialBusy)return;socialBusy=true;try{
  const s=await socialApi('state'),local=await api('/api/me');if(s.username!==local.account.username){connected=false;throw Error('Captain changed. Reconnect social features for this account.');}serverOffset=s.serverTime-Date.now();socialStatus.textContent=`Connected as ${s.username}. Friends, chat and lobby settings sync online; game saves remain local.`;
  const accepted=[];friendsList.replaceChildren();for(const f of s.friends){const other=f.sender===username?f.recipient:f.sender,box=el('div',undefined,'sandbox-row'),presence=s.captains.find(c=>c.username===other);box.append(el('b',`${other} · ${presence&&Date.now()+serverOffset-presence.last_seen<45000?'online':'offline'}`),el('p',f.status));if(f.status==='accepted'){accepted.push(other);button(box,'Remove friend',()=>socialApi('friend',{username:other,action:'remove'}).then(pollSocial));}if(f.status==='pending'&&f.recipient===username){button(box,'Accept',()=>socialApi('friend',{username:other,action:'accept'}).then(pollSocial));button(box,'Decline',()=>socialApi('friend',{username:other,action:'decline'}).then(pollSocial));}friendsList.append(box);}
  targetSelect.replaceChildren(...accepted.map(u=>new Option(u,u)));if(roomId)targetSelect.add(new Option('Current lobby','room:'+roomId));if([...targetSelect.options].some(o=>o.value===chatTarget))targetSelect.value=chatTarget;chatTarget=targetSelect.value;
  roomList.replaceChildren();for(const r of s.rooms){const box=el('div',undefined,'sandbox-row');box.append(el('b',r.name),el('p',`${r.host} · ${r.status}`));if(r.status==='open')button(box,r.id===roomId?'View lobby':'Join lobby',async()=>{await socialApi('join',{room:r.id});roomId=r.id;localStorage.setItem('pirate-room-'+username,roomId);await renderRoom();});roomList.append(box);}
  await renderRoom();await pollChat();
 }catch(e){socialStatus.textContent=e.message;if(/expired|not found/i.test(e.message)){roomId='';localStorage.removeItem('pirate-room-'+username);}}finally{socialBusy=false;}}
 let roomSignature='';
 async function renderRoom(){if(!roomId){roomView.replaceChildren();return;}const data=await socialApi('room?room='+encodeURIComponent(roomId));roomData=data;serverOffset=data.serverTime-Date.now();const signature=JSON.stringify(data);if(signature===roomSignature)return;roomSignature=signature;
  // Preserve settings while the host edits an input across polling refreshes.
  if(roomView.contains(document.activeElement)&&['INPUT','SELECT'].includes(document.activeElement.tagName))return;
  const r=data.room,host=r.host===username;roomView.replaceChildren(el('h3',r.name),el('p',`Host: ${r.host} · ${r.status}`),el('p','','sandbox-countdown'));
  for(const m of data.members){const box=el('details',undefined,'sandbox-row');box.append(el('summary',`${m.username} · ${m.ready?'ready':'not ready'} · ${m.team.length} fighters`),el('pre',JSON.stringify(m.team,null,2)));roomView.append(box);}
  button(roomView,'Share current team & ready',shareReady);button(roomView,'Not ready',()=>socialApi('ready',{room:roomId,ready:false,team:[]}).then(pollSocial));
  const enabled=field(roomView,'Enable lobby countdown','input');enabled.type='checkbox';enabled.checked=r.settings.timerEnabled;enabled.disabled=!host;
  const seconds=field(roomView,'Countdown seconds');seconds.type='number';seconds.min='5';seconds.max='300';seconds.value=r.settings.countdownSeconds;seconds.disabled=!host;
  if(host){button(roomView,'Apply host timer settings',()=>socialApi('settings',{room:roomId,timerEnabled:enabled.checked,countdownSeconds:Number(seconds.value)}).then(pollSocial));button(roomView,'Start lobby',()=>socialApi('start',{room:roomId}).then(pollSocial));button(roomView,'Reset lobby / cancel countdown',()=>socialApi('reset',{room:roomId}).then(pollSocial));}
  const started=r.status==='started'||r.status==='countdown'&&Date.now()+serverOffset>=r.deadline;
  if(started&&data.members.length===2){button(roomView,'Run local snapshot PvP practice',async()=>{const other=data.members.find(m=>m.username!==username);if(!other?.team.length)throw Error('The other captain must share a team first.');await runtime().startChallenge(other.team,other.username);});roomView.append(el('p','Practice runs the native combat client against the shared team snapshot. Each captain runs their own local fight; this is not a synchronized authoritative match.'));}
  button(roomView,host?'Close lobby':'Leave lobby',async()=>{await socialApi('leave',{room:roomId});roomId='';localStorage.removeItem('pirate-room-'+username);roomSignature='';await pollSocial();});
 }
 setInterval(()=>{if(connected&&!socialPanel.hidden)pollSocial();},3000);
 setInterval(()=>{const out=roomView.querySelector('.sandbox-countdown');if(out&&roomData){const r=roomData.room;out.textContent=r.status==='countdown'?`Starts in ${Math.max(0,Math.ceil((r.deadline-Date.now()-serverOffset)/1000))}s`:'Lobby timer '+(r.settings.timerEnabled?'enabled':'off');if(r.status==='countdown'&&r.deadline<=Date.now()+serverOffset&&roomData.members.length===2&&!roomView.textContent.includes('Run local snapshot')){roomSignature='';renderRoom().catch(()=>{});}}},500);
 socialPanel.addEventListener('opened',()=>{if(connected)pollSocial();});

 // Shared, server-authenticated game assistant. The provider key never reaches this browser.
 const guidePanel=panel('guide-assistant','✦ Game-file assistant');guidePanel.append(el('h2','Ask the game files'),el('p','Ask in plain English. Answers use the guides, captured tables and offline rules, with source links. No model download or personal API key is needed.'));
 const question=field(guidePanel,'Game question','textarea');question.rows=4;question.maxLength=1000;
 const answer=el('div'),aiStatus=el('p','','sandbox-status');guidePanel.append(aiStatus,answer);
 button(guidePanel,'Ask game assistant',async()=>{
  aiStatus.textContent='Looking up the game files…';
  try{await api('/api/social-session',{});const result=await api('/game-assistant/answer',{question:question.value});answer.replaceChildren(el('h3','Game assistant'),el('p',result.answer));for(const source of result.sources||[]){const a=el('a',`[${source.id}] ${source.title}`);a.href=source.url;a.target='_blank';a.rel='noopener';answer.append(a,el('br'));}aiStatus.textContent=result.mode==='groq'?'Answered using the shared Groq service and approved references.':'Answer limited to the available game evidence.';}catch(e){aiStatus.textContent=e.message+' You can still search the game sources below.';}
 });
 let knowledge;
 button(guidePanel,'Search game sources',async()=>{
  knowledge ||= await (await fetch('/knowledge/index.json')).json();const {retrieve}=await import('/knowledge/retrieval.mjs');
  const ranked=retrieve(knowledge.documents,question.value,6).map(d=>({d}));
  answer.replaceChildren(el('h3','Matching game sources'));if(!ranked.length)answer.append(el('p','No matching game reference was found.'));for(const {d} of ranked){const box=el('div',undefined,'sandbox-row');box.append(el('b',d.title),el('p',d.text));const a=el('a','Open source');a.href=d.source;a.target='_blank';a.rel='noopener';box.append(a);answer.append(box);}aiStatus.textContent='Source search works without an AI connection once the references are cached.';
 });
 guidePanel.append(el('small','Game questions and relevant public reference excerpts are sent to Groq. Passwords, saves and private chats are excluded. Shared free-tier limits apply.'));
})();
