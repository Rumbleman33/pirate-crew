(function(){
 'use strict';let req,api,publish,normalize,catalogPromise;
 const skin='ui/gg/an_04_02.png',comboSkin='ui/jgg/jgg_163.png';
 function button(parent,label,x,y,width,handler){const b=new Laya.Button(skin,label);b.size(width,64);b.pos(x,y);b.stateNum=1;b.sizeGrid='15,15,15,15';b.labelSize=23;b.labelColors='#ffffff';b.labelStroke=3;b.labelStrokeColor='#5d210b';parent.addChild(b);b.on(Laya.Event.CLICK,b,async event=>{event.stopPropagation();b.disabled=true;try{await handler();}catch(e){publish('pirate-runtime-error',{message:e.message});req(1).default.showTips(e.message);}finally{if(!b.destroyed)b.disabled=false;}});return b;}
 function select(parent,labels,x,y,width=420){const c=new Laya.ComboBox(comboSkin,labels.map(x=>String(x).replaceAll(',',' ')).join(','));c.size(width,48);c.pos(x,y);c.stateNum=1;c.sizeGrid='6,6,6,6';c.labelSize=22;c.labelColors='#241b12';c.itemSize=22;c.visibleNum=6;c.list.vScrollBarSkin='';c.list.scrollBar.touchScrollEnable=true;c.list.scrollBar.mouseWheelEnable=true;c.itemColors='#45331a,#fff3c8,#f1c15f,#241b12,#704514';parent.addChild(c);return c;}
 function label(parent,text,x,y,width=440){const l=new Laya.Label(text);l.pos(x,y);l.width=width;l.fontSize=22;l.color='#493018';l.wordWrap=true;parent.addChild(l);return l;}
 const catalog=()=>catalogPromise||=api('/api/testing/catalog');
 async function run(command,arg=''){
  const result=await api('/api/gm',{command,arg:String(arg)});if(!result.ok)throw Error(result.error?.message||'Test command failed');
  window.PirateOfflineRuntime.applyResult(result);
  if(command==='talentLevel'||command==='talentAll'){await req(260).TalentProxy.re.sendTalentInfo();req(11).AppFacade.it.sendNotification(req(7).CmdCode.TalentActive);req(11).AppFacade.it.sendNotification(req(7).CmdCode.TalentAdvanceActive);req(15).ViewMgr.it.getMediator('TalentMainView')?.updateData();}
  else if(command!=='bossPractice')await window.PirateOfflineRuntime.refresh();
  if(command==='maxShips'||command==='maxAllSystems'){await req(76).ShipsProxy.re.sendShipList();for(const id of ['ShipStar','ShipBuild'])req(11).AppFacade.it.sendNotification(req(7).CmdCode[id]);req(11).AppFacade.it.sendNotification(req(6).NotifyName.TreasureListRefresh);}
  if(command==='maxHaki'){await req(342).SuitProxy.re.sendSuitInfo();req(11).AppFacade.it.sendNotification(req(7).CmdCode.SuitStageUp);}
  req(1).default.showTips(result.message);return result;
 }
 function show(mode='boss'){req(15).ViewMgr.it.push(TestingDialog,mode);}
 let TestingDialog,PracticeLineup;
 function showResult(win,name,leave){req(15).ViewMgr.it.push(TestingDialog,{mode:'result',win,name,leave});}
 function install(r,a,p,n){req=r;api=a;publish=p;normalize=n;
  TestingDialog=class extends req(10).default{
   init(){this.toDialog();this.setViewComponent(new(req(0).mui.ui.map.SceneNpcBossDialogUI)());}
   async onInitUI(){const view=this.view,options=this.getArgs(),mode=typeof options==='string'?options:options.mode;view.listItem.visible=false;view.lblTips.visible=false;view.uiPower.visible=false;view.imgSk.visible=false;view.btn.visible=false;view.lblTitle.text=mode==='boss'?'Boss practice':'Sandbox setup';
    for(let i=0;i<view.numChildren;i++){const node=view.getChildAt(i);if(node.skin?.includes('ywboss_2')||(mode!=='boss'&&node.skin?.includes('ywboss_1')))node.visible=false;}
    const data=await catalog();if(view.destroyed)return;for(const row of data.bosses)row.name=window.PirateOfflineEnglish?.translate(row.name)||row.name;
    if(mode==='boss'){
     view.imgSk.visible=true;label(view,'Captured stats - no rewards or progression',45,355);
     const kinds=['tower','map','challenge'],groups=['Impel Down floors','Regular map bosses','Island-unlock challenges'];
     const group=select(view,groups.map((name,i)=>`${name} (${data.bosses.filter(b=>b.kind===kinds[i]).length})`),45,400);
     const search=new Laya.TextInput();search.size(420,48);search.pos(45,460);search.fontSize=22;search.color='#241b12';search.bgColor='#e2d4ae';search.prompt='Search name, island or floor number';search.padding='8,8,8,8';view.addChild(search);
     const boss=select(view,[],45,520);let choices=[];
     const count=label(view,'',45,578);
     const preview=()=>{const row=choices[boss.selectedIndex];count.text=`${choices.length} matches - scroll / search`;view.btn.disabled=!row;if(!row){view.imgSk.visible=false;return;}view.imgSk.visible=true;req(1).default.regScript(view.imgSk,req(372).MonsterModelScript).flush('OfflineTestingDialog',row.monsterIds[0]);view.lblTitle.fontSize=24;view.lblTitle.width=460;view.lblTitle.height=60;view.lblTitle.centerX=0;view.lblTitle.wordWrap=true;view.lblTitle.text=row.name;};
     const update=()=>{const query=search.text.trim().toLowerCase();choices=data.bosses.filter(b=>b.kind===kinds[group.selectedIndex]&&(!query||(/^\d+$/.test(query)?b.id===Number(query):b.name.toLowerCase().includes(query))));boss.labels=choices.map(b=>`${b.id}: ${b.name}`.replaceAll(',',' ')).join(',');boss.selectedIndex=choices.length?0:-1;preview();};
     group.selectHandler=Laya.Handler.create(this,()=>{search.text='';update();},null,false);boss.selectHandler=Laya.Handler.create(this,preview,null,false);search.on(Laya.Event.INPUT,this,update);group.selectedIndex=0;update();
     view.btn.visible=true;view.btn.y=650;view.btn.label='Choose lineup & fight';view.btn.on(Laya.Event.CLICK,this,()=>{const row=choices[boss.selectedIndex];if(!row)return;this.onBtnClose();req(15).ViewMgr.it.push(PracticeLineup,row);});
    }else if(mode==='result'){
     view.lblTitle.text=options.win?'Practice victory':'Practice defeat';label(view,options.name||'Boss practice',45,160);label(view,'Practice complete. No rewards or progression were changed.',45,275);
     button(view,'Choose another boss',45,425,420,async()=>{this.destroy();await options.leave();show('boss');});
     view.btn.visible=true;view.btn.label='Return to map';view.btn.on(Laya.Event.CLICK,this,async()=>{this.destroy();await options.leave();});
     this.onBtnClose=async()=>{this.destroy();await options.leave();};
    }else{
     label(view,'Free testing presets. Existing assignments stay intact.',45,135);
     for(const [i,title,cmd,levels] of [[0,'Talents','talentLevel',data.talentLevels],[1,'Captain','captainLevel',data.captainLevels],[2,'Crew','charactersLevel',data.characterLevels]]){
      const pick=select(view,levels.map(n=>`${title} level ${n}`),45,185+i*72,220);pick.selectedIndex=Math.max(0,levels.indexOf(115));button(view,'Set level',285,178+i*72,180,()=>run(cmd,levels[pick.selectedIndex]));
     }
     for(const [i,text,cmd] of [[0,'Max pets','maxPets'],[1,'Max mounts','maxMounts'],[2,'Max treasures','maxTreasures'],[3,'Max ships','maxShips']])button(view,text,45+(i%2)*230,410+Math.floor(i/2)*75,210,()=>run(cmd));
     view.btn.visible=true;view.btn.label='Max all four systems';view.btn.on(Laya.Event.CLICK,this,()=>run('maxAllSystems').catch(e=>req(1).default.showTips(e.message)));
    }
   }
  };TestingDialog.NAME='OfflineTestingDialog';
  class PracticePlayer extends req(1583).default{
   setData(g){this._vo=g;this.uiItem.dataSource=g;this.uiItem.update(req(3).EGeneralItemType.None);this.boxSelect.visible=this.practiceOwner.practiceIds.includes(g.generalId);}
   onClick(){if(this._vo)this.practiceOwner.toggle(this._vo.generalId);}
  }
  class PracticeSlot extends req(1469).default{
   setData(ref,index){this._vo=null;this.boxLevelUnlok.visible=index>=this.practiceOwner.capacity;this.boxSelect.visible=false;this.imgRole.visible=false;if(this.boxLevelUnlok.visible)return;const g=req(35).GeneralProxy.re.getGeneral(this.practiceOwner.practiceIds[index]);this._vo=g;if(g){this.imgRole.visible=true;const script=req(1).default.regScript(this.imgRole,req(182).default);script.onRemove();script.generalId=g.generalId;script.skinId=g.skinId;script.flush();}else this.boxSelect.visible=true;}
   onClick(){if(this._vo)this.practiceOwner.toggle(this._vo.generalId);}
  }
  PracticeLineup=class extends req(1585).TowerLineupDialog{
   init(){this._atlasNames=['res/atlas/ui/tower.atlas'];super.init();}
   async onInitUI(){this.boss=this.getArgs();this.capacity=Math.min(10,req(35).GeneralProxy.re.getActiveFights().length);const snapshot=await api('/api/me/snapshot');if(this.view.destroyed)return;const owned=new Set(req(35).GeneralProxy.re.getAllGeneral().map(g=>g.generalId));this.practiceIds=(snapshot.settings.practiceGenerals||req(35).GeneralProxy.re.getGenerals(true).map(g=>g.generalId)).filter(g=>owned.has(g)).slice(0,this.capacity);if(!this.practiceIds.length)this.practiceIds=req(35).GeneralProxy.re.getAllGeneral().slice(0,1).map(g=>g.generalId);this.view.listPlayer.itemRender=PracticePlayer;this.view.listBattle.itemRender=PracticeSlot;super.onInitUI();}
   updateData(){if(!this.practiceIds)return;const proxy=req(35).GeneralProxy.re;this.view.listPlayer.array=proxy.getAllGeneral().slice().sort((a,b)=>b.getPower()-a.getPower());this.view.listBattle.array=req(48).GeneralRefMgr.it.getGeneralFightRefs();this.view.lbIsBattle.text=`Practice lineup ${this.practiceIds.length}/${this.capacity}`;this.view.lblPower.text=`Power: ${req(5).default.brief(proxy.getGeneralsPower(this.practiceIds))}`;}
   listPlayerRenderHandler(cell,index){cell.practiceOwner=this;cell.setData(this.view.listPlayer.array[index]);}
   listBattleRenderHandler(cell,index){cell.practiceOwner=this;cell.setData(this.view.listBattle.array[index],index);cell.setScale();}
   toggle(id){const index=this.practiceIds.indexOf(id);if(index>=0){if(this.practiceIds.length===1)return req(1).default.showTips('Keep at least one fighter.');this.practiceIds.splice(index,1);}else{if(this.practiceIds.length>=this.capacity)return req(1).default.showTips('All unlocked crew slots are filled.');this.practiceIds.push(id);}this.updateData();}
   onClickBtnOkeBattle(){this.practiceIds=req(35).GeneralProxy.re.getAllGeneral().slice().sort((a,b)=>b.getPower()-a.getPower()).slice(0,this.capacity).map(g=>g.generalId);this.updateData();}
   async onClickBtnBat(){if(this.__starting)return;this.__starting=true;try{const row=this.boss,ids=this.practiceIds.slice();this.destroy();await run('bossPractice',JSON.stringify({kind:row.kind,id:row.id,generals:ids}));}catch(e){req(1).default.showTips(e.message);}finally{this.__starting=false;}}
  };PracticeLineup.NAME='OfflinePracticeLineup';
  function wrap(object,name,fn){const original=object?.[name];if(!original||original.__testingUI)return;const next=function(...args){const result=original.apply(this,args);fn.call(this,args);return result;};next.__testingUI=true;object[name]=next;}
  const more=req(1729).MoreFnMain.prototype,originalFns=more.getFnsByPlayType;more.getFnsByPlayType=function(){return originalFns.call(this).map(group=>group.filter(fn=>fn.fnId!==4900));};
  for(const [id,name] of [[2206,'ShipsDockSub'],[2231,'ShipsCabinLvView']]){const proto=req(id)[name].prototype,original=proto.updateUI;proto.updateUI=function(...args){this.info=req(76).ShipsProxy.re.info;return original.apply(this,args);};}
  wrap(req(1729).MoreFnMain.prototype,'onSelectTab',function(args){const v=this.view;if(v.__practiceButton)v.__practiceButton.destroy();if(args[0]===1){v.img.height+=86;v.__practiceButton=button(v.img,'Boss practice',25,v.img.height-77,v.img.width-50,()=>show('boss'));}});
  wrap(req(1906).TalentMainView.prototype,'onInitUI',function(){button(this.view,'Set levels…',80,135,230,()=>show('presets'));button(this.view,'Max talents',440,135,230,()=>run('talentAll'));});
  for(const [id,name,cmd] of [[1998,'MountMain','maxMounts'],[2016,'PetMainView','maxPets'],[2205,'ShipsMain','maxShips'],[1866,'TreasureSub','maxTreasures'],[1991,'SuitMain','maxHaki']])wrap(req(id)[name].prototype,'onInitUI',function(){button(this.view,'Max for testing',460,135,230,()=>run(cmd));});
 }
 window.PirateTestingUI={install,show,showResult,run};
})();
