(function(){
 'use strict';
 let req,publish,api,enabled=false,inspectMode=false,seq=0,queue=[],events=[],timer,challenge=null;
 const safe=fn=>{try{return fn();}catch{return null;}};
 const actorId=a=>a?{uid:String(safe(()=>a.getID())??a.uid??a.id??''),refId:Number(a.ref?.refId??a.ref?.generalId??a.id??0),name:String(a.ref?.generalName??a.ref?.name??a.name??'Actor')}:null;
 function readAttrRefs(){const refs=[];req(320).AttrRefMgr.it.eachIV(r=>{if(r.attr)refs.push(r);return true;});return refs;}
 function hp(a){const h=a?.hpInfo;return {hp:Number(safe(()=>h.getHp())??0),maxHp:Number(safe(()=>h.getMaxHp())??h?.maxHp??0),shield:Number(safe(()=>h.getShieldHp())??0)};}
 function emit(phase,data){if(!enabled)return;const item={sequence:++seq,time:Date.now(),elapsed:Math.round(performance.now()),sceneId:Number(safe(()=>req(64).SceneMgr.it.curScene)||0),phase,...data};events.push(item);if(events.length>2000)events.shift();queue.push(item);if(queue.length>500)queue.shift();if(!timer)timer=setTimeout(()=>{publish('pirate-combat-events',queue);queue=[];timer=null;},100);}
 function wrap(object,name,handler){const original=object?.[name];if(typeof original!=='function'||original.__pirateObserved)return;const fn=function(...args){return handler.call(this,original,args);};fn.__pirateObserved=true;object[name]=fn;}
 function actors(){const s=safe(()=>req(64).SceneMgr.it.curSceneObj),all=[...(s?.actors?.values?.()||[]),...(s?.monsters?.values?.()||[])];return [...new Set(all)].filter(a=>a&&!a.destroyed);}
 function details(actor){
  const refs=readAttrRefs();
  const stats=refs.map(r=>({id:Number(r.refId),name:String(r.name||r.attr),key:r.attr,value:Number(safe(()=>actor.getAttrs(Number(r.refId)))||0)})).filter(r=>Number.isFinite(r.value));
  const buffs=safe(()=>actor.buffComponent.buffs.values())||[];
  return {...actorId(actor),...hp(actor),campId:String(actor.campId??''),stats,
   skills:(safe(()=>actor.skillComponent.toSkillList())||[]).map(s=>Number(s.skillId??s.ref?.skillId??s)),
   buffs:buffs.map(b=>({id:Number(b.ref?.refId??b.ref?.buffId??b.id??0),name:String(b.ref?.name||'Buff')})),
   source:'Live native actor: getAttrs includes active attribute modifiers. HP/shield are current values.'};
 }
 async function inspect(uid){const a=actors().find(a=>actorId(a).uid===String(uid));if(!a)throw Error('This actor has left the scene. Refresh the actor list.');const d=details(a);const snapshot=await api('/api/me/snapshot');const encounter=snapshot.activeInstance?.data||safe(()=>req(37).InsProxy.re.insData);d.encounterLevel=encounter?.lv??null;d.instanceRefId=encounter?.refId??null;publish('pirate-actor-inspected',d);return d;}
 function stopChallenge(){if(challenge?.poll)clearInterval(challenge.poll);if(challenge){challenge=null;safe(()=>req(37).InsProxy.re.insData=null);}}
 async function startChallenge(opponent,opponentName,normalize){
  if(!Array.isArray(opponent)||!opponent.length||opponent.length>10)throw Error('The shared team is empty or too large.');
  stopChallenge();window.PirateOfflineRuntime.openMain();
  const snapshot=await api('/api/me/snapshot'),roster=(await api('/api/command',{id:1300,payload:{}})).reply.generals.filter(g=>g.isSelect).slice(0,10);
  if(!roster.length)throw Error('Deploy a crew first.');
  const attrRefs=readAttrRefs(),keys=new Map(attrRefs.flatMap(r=>[[String(r.refId),Number(r.refId)],[r.attr,Number(r.refId)]]));
  const ownId=Number(snapshot.playerId),otherId=ownId+100000,uid=Date.now()*10,sprites=[];
  function add(g,n,own){const attrs=own?g.attrs.filter(a=>keys.has(String(a.key))).map(a=>({key:keys.get(String(a.key)),value:Number(a.doubleValue??a.int64Value??0)})):Object.entries(g.attrs||{}).filter(([k,v])=>keys.has(k)&&Number.isFinite(Number(v))).map(([k,v])=>({key:keys.get(k),value:Math.max(-1e12,Math.min(1e12,Number(v)))}));const hpValue=Math.max(1,attrs.find(a=>a.key===2)?.value||100),pos={x:(own?800:1300)+(n%3)*60,y:700+Math.floor(n/3)*100,dir:own?0:180},id=Number(g.generalId);if(!safe(()=>req(48).GeneralRefMgr.it.getGeneralRef(id)))throw Error('Shared team contains an unknown character.');sprites.push({uid:uid+(own?0:100)+n+1,id,type:1,attrs,skillList:g.skillIds||[],entryIds:g.entryInfos||[],skinId:g.skinId||0,footprintId:0,playerId:own?ownId:otherId,campId:own?ownId:otherId,labile:{uid:uid+(own?0:100)+n+1,pos,hp:{max:hpValue,cur:hpValue,shield:0}},brithPos:pos});}
  roster.forEach((g,n)=>add(g,n,true));opponent.forEach((g,n)=>add(g,n,false));
  const data={uid,refId:601,lv:1,sprites,rewards:[],startTime:Date.now(),players:[{playerId:ownId,name:snapshot.player.nickname,lv:snapshot.player.level,campId:ownId},{playerId:otherId,name:opponentName,lv:Math.max(...opponent.map(g=>Number(g.level)||1)),campId:otherId}]};
  const args=req(82).InsArg.argInsIdLv(601,1);if(!args)throw Error('The captured arena configuration is unavailable.');args.insRef={...args.insRef,cost:'',time:-1,timeType:0};args.offlineChallenge=true;args.leaveConfirm=false;
  challenge={ownId,otherId,ready:false,scene:null,started:Date.now(),result:null};
  req(37).InsProxy.re.insData=normalize(51002,{data}).data;
  req(11).AppFacade.it.sendNotification(req(6).NotifyName.MapInsOpen,args);
  challenge.poll=setInterval(()=>{if(!challenge?.ready||challenge.result)return;const list=challenge.scene?.actors?.values?.()||[];const alive=list.filter(a=>(safe(()=>a.hpInfo.getHp())||0)>0);const mine=alive.some(a=>Number(a.playerId)===ownId),enemy=alive.some(a=>Number(a.playerId)===otherId);if(mine&&enemy){challenge.deadAt=null;return;}if(!challenge.deadAt){challenge.deadAt=Date.now();return;}if(Date.now()-challenge.deadAt<1500)return;challenge.result=mine?'victory':enemy?'defeat':'draw';publish('pirate-challenge-result',{result:challenge.result,elapsed:Date.now()-challenge.started,opponent:opponentName});},250);
  return {started:true,mode:'local-snapshot-practice'};
 }
 function install(r,p,a){req=r;publish=p;api=a;
  wrap(req(453).InsMainView.prototype,'insSettle',function(original,args){
   if(!this._args?.offlineBossPractice)return original.apply(this,args);
   if(!this.__practiceLeave)this.__practiceLeave=()=>{
    if(this.__practiceLeaving)return this.__practiceLeaving;
    this._enterReviveSelect=false;this._resultWin=true;
    this.__practiceLeaving=Promise.resolve(this.onCloseResultView()).then(()=>window.PirateOfflineRuntime.finishPractice());return this.__practiceLeaving;
   };
   if(args[1]==='leave')return this.__practiceLeave();
   if(this.__practiceEnded)return;this.__practiceEnded=true;this._showResult=true;this.view.timer.clearAll(this);req(64).SceneMgr.it.stopTick();this._scene?.stopFrameUpdate();
   window.PirateTestingUI.showResult(!!args[0],this._args.practiceName,this.__practiceLeave);
  });
  wrap(req(453).InsMainView.prototype,'loadScene',function(original,args){if(this._args?.offlineBossPractice)this._args.insRef={...this._args.insRef,time:-1,timeType:0,name:'Boss practice'};return original.apply(this,args);});
  wrap(req(1285).TowerInsCtrl.prototype,'insTickStart',function(original,args){if(this._args?.offlineBossPractice)return req(106).BaseInsCtrl.prototype.insTickStart.call(this,false);return original.apply(this,args);});
  const baseName=Object.getOwnPropertyDescriptor(req(106).BaseInsCtrl.prototype,'insName');if(baseName?.get)Object.defineProperty(req(1285).TowerInsCtrl.prototype,'insName',{configurable:true,get(){return this._args?.offlineBossPractice?this._args.practiceName:baseName.get.call(this);}});
  const towerIDs=Object.getOwnPropertyDescriptor(req(1285).TowerInsCtrl.prototype,'generalIDs');
  if(towerIDs?.get)Object.defineProperty(req(1285).TowerInsCtrl.prototype,'generalIDs',{configurable:true,get(){return this._args?.offlineBossPractice?(this._args.practiceGeneralIds||req(35).GeneralProxy.re.getGenerals(true).map(g=>g.generalId)):towerIDs.get.call(this);}});
  wrap(req(1907).TalentActivationSub.prototype,'update',function(original,args){
   const result=original.apply(this,args),owner=this;
   if(!this.__maxTalents){
    const base=this.btnAc,b=new Laya.Button(base.skin,'Max all');
    b.name='offlineMaxAllTalents';b.size(118,74);b.pos(142,168);b.stateNum=1;b.labelSize=20;b.labelColors='#ffffff';b.labelStroke=base.labelStroke||4;b.labelStrokeColor=base.labelStrokeColor||'#4d1000';b.sizeGrid=base.sizeGrid;
    this.img.addChild(b);this.__maxTalents=b;
    this.boxActivation.x=14;this.boxActivation.width=118;base.width=118;base.labelSize=20;
    this.imgActivation.x=24;this.imgActivation.scale(.75,.75);
    b.on(Laya.Event.CLICK,this,async event=>{
     event.stopPropagation();b.disabled=true;b.label='Working…';
     try{const result=await api('/api/gm',{command:'talentAll',arg:''});if(result.ok===false)throw Error(result.error?.message||'Talent unlock failed.');window.PirateOfflineRuntime.applyResult(result);await req(260).TalentProxy.re.sendTalentInfo();req(11).AppFacade.it.sendNotification(req(7).CmdCode.TalentActive);req(11).AppFacade.it.sendNotification(req(7).CmdCode.TalentAdvanceActive);req(15).ViewMgr.it.getMediator('TalentMainView')?.updateData();if(!owner.destroyed)owner.onBtnClose();}
     catch(error){publish('pirate-runtime-error',{message:error.message});if(!b.destroyed){b.disabled=false;b.label='Max all';}}
    });
   }
   return result;
  });
  wrap(req(2005).MountRein.prototype,'updateUI',function(original,args){
   const stage=req(161).MountProxy.re.getMountStage(),row=req(160).MountRefMgr.it.getStageRef(stage),max=row&&Number(row.endExp)<=Number(row.startExp);let result;
   if(max){const end=row.endExp;row.endExp=Number(row.startExp)+1;try{result=original.apply(this,args);}finally{row.endExp=end;}this.view.prog.value=1;this.view.lblProg.text='MAX';}
   else result=original.apply(this,args);
   if(this.view){this.view.btnAuto.disabled=!!max;this.view.btnUp.disabled=!!max;}
   return result;
  });
  // Native auto-equip does not apply its manual appraisal check. Enforce it
  // at the shared eligibility predicate so comparisons and auto-equip agree.
  wrap(req(1131).EquipVO.prototype,'isCanWear',function(original,args){return this.isAuthed()&&original.apply(this,args);});
  wrap(req(30).RpgUtil,'calcDamage',function(original,args){
   if(!enabled)return original.apply(this,args);
   const rolls=[],random=Math.random;let result;Math.random=function(){const v=random();rolls.push(v);return v;};
   try{result=original.apply(this,args);return result;}finally{Math.random=random;if(result){const values={};for(const [key,value] of Object.entries(result))if(['number','boolean','string'].includes(typeof value))values[key]=value;emit('calculated',{attacker:actorId(args[0]),target:actorId(args[1]),skillRate:args[2],attackType:args[3],skillId:args[4],effectId:args[5],rolls,result:values});}}
  });
  for(const name of ['subHp','addHp','onServerDamage','onDead'])wrap(req(360).Sprite.prototype,name,function(original,args){if(!enabled)return original.apply(this,args);const before=hp(this),result=original.apply(this,args),after=hp(this);emit(name==='onDead'?'death':name==='onServerDamage'?'server-applied':'hp-applied',{actor:actorId(this),method:name,source:actorId(name==='subHp'?args[2]:name==='addHp'?args[1]:args[0]),requestedAmount:typeof args[0]==='number'?args[0]:null,before,after,hpChange:after.hp-before.hp,shieldChange:after.shield-before.shield});return result;});
  for(const name of ['addBuff','removeBuff'])wrap(req(1031).BuffComponent.prototype,name,function(original,args){const result=original.apply(this,args);emit(name,{actor:actorId(this.owner),buffId:Number(args[0]?.refId??args[0]?.buffId??args[0]??0),source:actorId(args[1]),target:actorId(args[2]),skillId:args[3],effectId:args[4]});return result;});
  wrap(req(271).Skill.prototype,'invoke',function(original,args){emit('skill-cast',{actor:actorId(args[0]),skillId:Number(this.ref?.skillId||0),name:this.ref?.name||'',at:args[1]});return original.apply(this,args);});
  wrap(req(540).JoystickScript.prototype,'mouseDown',function(original,args){
   if(inspectMode){const event=args[0],hit=actors().filter(a=>a.display?.visible!==false&&safe(()=>a.checkClick(event.stageX,event.stageY))).reverse()[0];if(hit){inspect(actorId(hit).uid).catch(e=>publish('pirate-inspect-error',e.message));return;}}
   return original.apply(this,args);
  });
  wrap(req(30).RpgUtil,'isServerDamage',function(original,args){const a=args[0]?.owner||args[0];return challenge&&a?.scene?.context?.insType===11?false:original.apply(this,args);});
  wrap(req(321).TrajectorySprite.prototype,'isApplyDamage',function(original,args){return challenge&&this.owner?.scene?.context?.insType===11?true:original.apply(this,args);});
  wrap(req(1280).ArenaInsCtrl.prototype,'sceneCreated',function(original,args){const result=original.apply(this,args);if(this._args?.offlineChallenge&&challenge){challenge.scene=args[0];args[0].isTest=true;challenge.ready=true;for(const actor of args[0].actors.values()){safe(()=>Object.defineProperty(actor.context,'isPVP',{configurable:true,value:true}));if(!actor.selfActor){const ref=req(432).BehaviorRefMgr.it.getBehivorTreeRef('bhv_arena');actor.spriteAiComponent.behaviorTree=req(433).BehaviorMgr.it.createBehaviorTree(ref);}}}return result;});
  wrap(req(1280).ArenaInsCtrl.prototype,'insLeave',function(original,args){if(this._args?.offlineChallenge){const active=!!challenge;stopChallenge();if(active)window.PirateOfflineRuntime.openMain();return;}return original.apply(this,args);});
  for(const method of ['checkRebirth','onBtnWaive'])wrap(req(453).InsMainView.prototype,method,function(original,args){if(this._args?.offlineBossPractice){if(method==='onBtnWaive')return this.insSettle(false,'leave');if(!this._showResult&&this._isInsLoad&&this._scene?.myActors?.length&&this._scene.myActorsAllDead)this.insSettle(false);return;}if((this._args||safe(()=>this.getArgs()))?.offlineChallenge){if(method==='onBtnWaive'){stopChallenge();window.PirateOfflineRuntime.openMain();}return;}return original.apply(this,args);});
  // Render the real occupied items and one extra screen of empty cells. Keep
  // the actual server capacity for labels and validation instead of allocating
  // thousands of empty native VOs for every unused slot.
  wrap(req(1912).BagMainView.prototype,'onSelectTab',function(original,args){const types=[1,2,3,4],capa=req(50).ItemProxy.re.getBagCapa(types[Number(args[0])]);if(!capa)return original.apply(this,args);const max=capa.max;capa.max=Math.min(max,Math.max(0,Number(capa.cur))+40);try{return original.apply(this,args);}finally{capa.max=max;if(this.view?.lbItemNum)this.view.lbItemNum.text=capa.cur+'/'+max;}});
 }
 window.PirateCombatTools={install,startChallenge,stopChallenge,setLogging:value=>{enabled=!!value;return enabled;},setInspect:value=>{inspectMode=!!value;return inspectMode;},listActors:()=>actors().map(a=>({...actorId(a),...hp(a)})),inspect,getEvents:()=>events.slice(),clear:()=>{events=[];queue=[];}};
})();
