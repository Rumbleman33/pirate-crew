(function () {
  "use strict";
  const patterns = { idle:/idle|stand|daiji/i, run:/run|walk|move|pao/i, attack:/attack|atk|gongji/i, skill:/skill|super|jineng/i };
  let current = null, serial = 0;
  let lastStatus = {status:"closed", phase:"closed", animations:[], models:[], skinIds:[], currentAnimation:null};
  function modelDescription(item) {
    return {skinId:item.skinId,generalId:item.generalId,title:item.title,variant:item.variant,loaded:item.loaded,
      animations:item.animations.slice(),currentAnimation:item.animation||null,assetUrl:item.assetUrl};
  }
  function describe(active) {
    return {mode:active.mode,skinId:active.skinIds[0],skinIds:active.skinIds.slice(),generalId:active.generalId,title:active.title,
      models:active.items.map(modelDescription),animations:active.animations.slice(),motionCounts:{...active.motionCounts},
      currentAnimation:active.animation,animation:active.animation,motion:active.motion,loop:active.loop,paused:active.paused,
      scale:active.scale,zoom:active.zoom,baseScale:active.baseScale,assetUrl:active.items.length===1?active.items[0].assetUrl:null};
  }
  function publish(status, extra={}) {
    const detail={status,phase:status,...(current?describe(current):{mode:null,skinId:null,skinIds:[],generalId:null,title:"Skin studio",
      models:[],animations:[],motionCounts:{},currentAnimation:null,loop:true,paused:false,zoom:3}),...extra};
    lastStatus=detail;
    window.dispatchEvent(new CustomEvent("pirate-skin-status",{detail}));
    if(parent!==window)parent.postMessage({type:"pirate-skin-status",detail},location.origin);
    return detail;
  }
  function requireReady() {
    if(!window.Laya||!window.__pirateRequire||!window.PirateOfflineRuntime?.getStatus?.().ready)
      throw new Error("Start the original offline game client before opening Skin studio.");
    return {L:window.Laya,req:window.__pirateRequire};
  }
  function text(L,value,fontSize,color,bold=false) {
    const label=new L.Text();Object.assign(label,{text:value,font:"Arial",fontSize,color,bold,mouseEnabled:false});return label;
  }
  function button(active,caption,onClick) {
    const {L}=active,node=new L.Sprite();node.mouseEnabled=true;node.size(112,42);
    node.graphics.drawRect(0,0,112,42,"#18384e","#437c99",1);
    const label=text(L,caption,16,"#eefaff",true);Object.assign(label,{width:112,height:42,align:"center",valign:"middle"});
    node.addChild(label);node.on(L.Event.CLICK,active,event=>{event?.stopPropagation?.();onClick();});return node;
  }
  function pauseWorld(active) {
    active.runtimeTools=document.getElementById("runtime-tools");
    if(active.runtimeTools){active.toolsDisplay=active.runtimeTools.style.display;active.runtimeTools.style.display="none";}
    const flags=active.req(18).default;active.worldPause={flags,isGameStop:flags.isGameStop,contexts:[]};flags.isGameStop=true;
    const manager=active.req(64).SceneMgr.it,visited=new Set();
    const pauseScene=scene=>{const context=scene?.context;if(!context||visited.has(context))return;visited.add(context);
      active.worldPause.contexts.push({context,pause:context.pause});context.pause=true;};
    manager.sceneMap?.forEach?.(pauseScene);pauseScene(manager.curSceneObj);
  }
  function restoreWorld(active) {
    if(active.runtimeTools)active.runtimeTools.style.display=active.toolsDisplay;
    if(!active.worldPause)return;
    for(const item of active.worldPause.contexts)item.context.pause=item.pause;
    active.worldPause.flags.isGameStop=active.worldPause.isGameStop;active.worldPause=null;
  }
  function metadata(req,skinId,options={}) {
    const skinRef=req(48).GeneralRefMgr.it.getGeneralSkinRef(skinId);
    const baseRef=skinRef?null:req(48).GeneralRefMgr.it.getGeneralRef(skinId);
    const ref=skinRef||baseRef;
    if(!ref)throw new Error(`Model ${skinId} is absent from the captured character and skin tables.`);
    const generalId=Number(skinRef?ref.generalId:ref.refId);
    let assetPath=skinRef?`spine/roleSkin/${skinId}.sk`:`spine/role/${generalId}.sk`;
    try {const style=req(58).SpineStyleRefMgr.it.getRef(ref.ani||skinId);if(style?.name)assetPath=req(22).getAsset(style.name)||assetPath;}
    catch(_){/* Use this skin's local path, never another model. */}
    const variant=options.variant==="transformed"?"transformed":"normal";
    if(variant==="transformed") {
      if(skinId!==16059004)throw new Error("Only the captured Halloween King skin has this transformation model.");
      assetPath="spine/roleSkin/16059004_bianshen.sk";
    }
    const resolved=new URL(assetPath,new URL("/game/",location.href));
    if(resolved.origin!==location.origin||!resolved.pathname.startsWith("/game/"))throw new Error("Skin studio only loads locally captured game assets.");
    let title=req(14).LangMgr.it.translate(skinRef?(ref.name||`Skin ${skinId}`):(ref.generalName||`Character ${generalId}`));
    if(baseRef)title="Default · "+title;
    if(skinId===16055005)title="Panda Blackbeard";
    if(variant==="transformed")title+=" · transformation";
    return {skinId,generalId,title,assetPath,assetUrl:resolved.href,variant,animations:[],animation:null,loaded:false};
  }
  function fit(active) {
    if(active!==current||active.overlay.destroyed)return;
    const {L,overlay}=active,width=L.stage.width,height=L.stage.height;
    overlay.size(width,height);overlay.graphics.clear();overlay.graphics.drawRect(0,0,width,height,"#071622");
    active.heading.pos(26,25);active.heading.width=Math.max(100,width-174);
    active.subtitle.pos(26,69);active.subtitle.width=Math.max(100,width-52);
    active.animationLabel.pos(26,104);active.animationLabel.width=Math.max(100,width-52);
    active.closeButton.pos(width-138,24);
    const buttonColumns=Math.max(1,Math.floor((width-52)/124));
    const buttonRows=Math.max(1,Math.ceil(active.animationButtons.length/buttonColumns));
    const footerHeight=58+buttonRows*48,top=145,gap=12,availableHeight=Math.max(150,height-top-footerHeight-16);
    const count=active.items.length,columns=count===1?1:Math.min(count,width>=1050?3:width>=480?2:1),rows=Math.ceil(count/columns);
    const cellWidth=(width-52-gap*(columns-1))/columns,cellHeight=(availableHeight-gap*(rows-1))/rows;
    active.items.forEach((item,i)=>{
      item.card.pos(26+(i%columns)*(cellWidth+gap),top+Math.floor(i/columns)*(cellHeight+gap));item.card.size(cellWidth,cellHeight);
      item.card.graphics.clear();item.card.graphics.drawRect(0,0,cellWidth,cellHeight,"#0b2433","#20495a",1);
      const labelHeight=Math.min(72,Math.max(48,cellHeight*0.22)),bodyHeight=Math.max(30,cellHeight-labelHeight);
      item.viewport.size(cellWidth,bodyHeight);item.viewport.scrollRect=new L.Rectangle(0,0,cellWidth,bodyHeight);
      item.caption.pos(10,bodyHeight+5);item.caption.width=Math.max(30,cellWidth-20);item.caption.height=Math.max(26,labelHeight-22);
      item.caption.fontSize=cellWidth<210?14:18;
      item.pose.pos(10,cellHeight-21);item.pose.width=Math.max(30,cellWidth-20);
      // Keep one stable body camera for all variants; animation effect bounds
      // would otherwise shrink a model whenever its effect extends offscreen.
      item.scale=active.baseScale*active.zoom*Math.min(cellWidth/350,bodyHeight/340);
      if(item.skeleton?.templet){item.skeleton.scale(item.scale,item.scale);item.skeleton.pos(cellWidth/2,bodyHeight*0.92);}
    });
    active.scale=active.items[0]?.scale||1;
    active.animationButtons.forEach((node,i)=>node.pos(26+(i%buttonColumns)*124,height-footerHeight+Math.floor(i/buttonColumns)*48));
    active.hint.pos(26,height-45);active.hint.width=Math.max(100,width-52);
  }
  function dispose(active) {
    clearTimeout(active.timeout);active.L.stage.off(active.L.Event.RESIZE,active,active.resize);
    active.L.loader.off(active.L.Event.ERROR,active,active.loadError);active.L.timer.clearAll(active);
    for(const item of active.items){try{item.skeleton?.stop?.();}catch(_){}}
    if(active.overlay&&!active.overlay.destroyed)active.overlay.destroy(true);
    restoreWorld(active);
    // Never clear shared templates/textures used by equipped world models.
  }
  function close() {
    const active=current;if(!active)return {closed:true};
    const detail=describe(active);current=null;serial+=1;dispose(active);
    if(!active.settled){active.settled=true;const error=new Error("Skin preview closed before loading completed.");error.code="PREVIEW_CLOSED";active.reject(error);}
    publish("closed",{...detail,currentAnimation:null,animation:null});
    return {closed:true,skinIds:active.skinIds.slice(),skinId:active.skinIds[0]};
  }
  function fail(active,reason) {
    if(active!==current||active.settled)return;
    const error=reason instanceof Error?reason:new Error(String(reason));error.skinStatusReported=true;active.settled=true;
    publish("error",{error:error.message});current=null;serial+=1;dispose(active);active.reject(error);
  }
  function readyActive() {
    if(!current||!current.items.length||current.items.some(item=>!item.loaded))throw new Error("Open a loaded skin comparison before changing playback.");
    return current;
  }
  function finishPlayback(active,name,motion,loop) {
    active.animation=name;active.motion=motion;active.loop=Boolean(loop);
    active.animationLabel.text=`${motion?motion[0].toUpperCase()+motion.slice(1):name} · ${active.paused?"Paused":active.loop?"Looping":"Playing once"}`;
    for(const item of active.items)if(active.paused)item.skeleton.paused();
    fit(active);publish("playing");return describe(active);
  }
  function play(name,loop=true) {
    const active=readyActive(),animation=String(name);
    if(!active.animations.includes(animation))throw new Error(`Animation '${animation}' is not available on every compared model.`);
    for(const item of active.items){item.animation=animation;item.pose.text=animation;item.skeleton.play(animation,Boolean(loop),true);}
    return finishPlayback(active,animation,null,loop);
  }
  function playMotion(motion,loop=true) {
    const active=readyActive(),pattern=patterns[String(motion)];
    if(!pattern||!active.motionCounts[motion])throw new Error(`No compared model has a captured ${motion} animation.`);
    const names=[];
    for(const item of active.items){
      const animation=item.animations.find(name=>name.toLowerCase()===motion)||item.animations.find(name=>pattern.test(name));
      const fallback=item.animations.find(name=>patterns.idle.test(name))||item.animations[0];
      item.animation=animation||fallback;item.skeleton.play(item.animation,Boolean(loop),true);
      item.pose.text=animation||`${motion} unavailable · idle`;names.push(item.animation);
    }
    return finishPlayback(active,names.every(name=>name===names[0])?names[0]:motion,motion,loop);
  }
  function setPaused(value) {
    const active=readyActive();active.paused=Boolean(value);
    for(const item of active.items)active.paused?item.skeleton.paused():item.skeleton.resume();
    active.animationLabel.text=`${active.motion||active.animation} · ${active.paused?"Paused":active.loop?"Looping":"Playing once"}`;
    publish(active.paused?"paused":"playing");return describe(active);
  }
  function setZoom(value) {
    const active=readyActive(),requested=Number(value);if(!Number.isFinite(requested))throw new Error("Preview zoom must be a number.");
    active.zoom=Math.max(0.5,Math.min(8,requested));fit(active);publish("zoom");return describe(active);
  }
  function createCard(active,item) {
    const {L}=active;item.card=new L.Sprite();item.viewport=new L.Sprite();item.skeleton=new L.Skeleton();
    item.caption=text(L,item.title,18,"#eefaff",true);item.caption.wordWrap=true;item.pose=text(L,"Loading…",14,"#9ce7cc");
    item.viewport.addChild(item.skeleton);item.card.addChild(item.viewport);item.card.addChild(item.caption);item.card.addChild(item.pose);active.overlay.addChild(item.card);
  }
  function finishLoad(active) {
    if(active!==current||active.items.some(item=>!item.loaded))return;
    clearTimeout(active.timeout);active.L.loader.off(active.L.Event.ERROR,active,active.loadError);
    active.animations=active.items[0].animations.filter(name=>active.items.every(item=>item.animations.includes(name)));
    for(const [motion,pattern] of Object.entries(patterns))active.motionCounts[motion]=active.items.filter(item=>item.animations.some(name=>pattern.test(name))).length;
    for(const motion of Object.keys(patterns)){
      if(!active.motionCounts[motion])continue;
      const node=button(active,motion[0].toUpperCase()+motion.slice(1),()=>playMotion(motion,active.loop));active.animationButtons.push(node);active.overlay.addChild(node);
    }
    if(active.motionCounts[active.requestedMotion])playMotion(active.requestedMotion,active.loop);
    else if(active.animations.length)play(active.animations[0],active.loop);
    else{
      for(const item of active.items){item.animation=item.animations[0];item.skeleton.play(item.animation,active.loop,true);item.pose.text=item.animation;}
      finishPlayback(active,"Individual captured animations",null,active.loop);
    }
    active.L.timer.frameOnce(2,active,()=>{
      if(current!==active||active.settled)return;fit(active);active.settled=true;publish("ready");active.resolve(describe(active));
    });
  }
  async function open(skinIds,options,mode) {
    close();
    try{
      const setup=requireReady();
      if(!Array.isArray(skinIds)||!skinIds.length||skinIds.length>32)throw new Error("Choose between 1 and 32 skins to compare.");
      const ids=[...new Set(skinIds.map(value=>{const id=Number(value);if(!Number.isSafeInteger(id)||id<=0)throw new Error("Choose a valid captured skin ID.");return id;}))];
      const items=ids.map(id=>metadata(setup.req,id,{variant:options.variants?.[id]||options.variant}));
      if(new Set(items.map(item=>item.generalId)).size!==1)throw new Error("Choose skins belonging to the same character for comparison.");
      if(mode==="comparison"&&options.includeTransformations!==false&&ids.includes(16059004)&&!items.some(item=>item.variant==="transformed"))items.push(metadata(setup.req,16059004,{variant:"transformed"}));
      const id=++serial;
      return await new Promise((resolve,reject)=>{
        const {L,req}=setup,requestedZoom=Number(options.zoom);
        const active={id,L,req,mode,skinIds:ids,generalId:items[0].generalId,items,
          title:String(options.title||(mode==="comparison"?"Skin comparison":items[0].title)),animations:[],motionCounts:{},animation:null,motion:null,
          requestedMotion:options.motion||"idle",loop:options.loop!==false,paused:options.animated===false||options.paused===true,
          scale:1,baseScale:1.8,zoom:Number.isFinite(requestedZoom)?Math.max(0.5,Math.min(8,requestedZoom)):1,
          settled:false,resolve,reject,animationButtons:[]};current=active;
        try{
          pauseWorld(active);const overlay=active.overlay=new L.Sprite();
          Object.assign(overlay,{name:"PirateOfflineSkinStudio",zOrder:2000000000,mouseEnabled:true,mouseThrough:false});L.stage.addChild(overlay);
          active.heading=text(L,active.title,28,"#f2f9ff",true);
          active.subtitle=text(L,`${items.length} original model${items.length===1?"":"s"} · character ${active.generalId}`,17,"#99becd");
          active.animationLabel=text(L,"Loading captured animations…",17,"#ffcf8e");
          active.hint=text(L,"Preview only · local world paused · no save changes",15,"#9ce7cc");active.closeButton=button(active,"Close",close);
          for(const item of items)createCard(active,item);
          [active.heading,active.subtitle,active.animationLabel,active.hint,active.closeButton].forEach(node=>overlay.addChild(node));
          active.resize=()=>fit(active);L.stage.on(L.Event.RESIZE,active,active.resize);
          active.loadError=url=>{const failed=String(url||""),item=items.find(item=>failed.includes(String(item.skinId)));if(item)fail(active,`Could not load ${item.title}: ${failed}`);};
          L.loader.on(L.Event.ERROR,active,active.loadError);
          active.timeout=setTimeout(()=>fail(active,"The selected skin models did not finish loading. Check their captured .sk and PNG files."),30000);
          fit(active);publish("loading");
          for(const item of items)item.skeleton.load(item.assetPath,L.Handler.create(active,()=>{
            if(current!==active||id!==serial||active.overlay.destroyed||item.skeleton.destroyed)return;
            try{
              if(!item.skeleton.templet)throw new Error(`${item.title} loaded without a parsed template.`);
              for(let i=0;i<item.skeleton.getAnimNum();i+=1){const name=item.skeleton.getAniNameByIndex(i);if(name&&!item.animations.includes(name))item.animations.push(name);}
              if(!item.animations.length)throw new Error(`${item.title} has no captured animations.`);
              item.loaded=true;active.subtitle.text=`${items.filter(model=>model.loaded).length}/${items.length} original models loaded · character ${active.generalId}`;finishLoad(active);
            }catch(error){fail(active,error);}
          }),0);
        }catch(error){fail(active,error);}
      });
    }catch(error){if(!current&&error.code!=="PREVIEW_CLOSED"&&!error.skinStatusReported)publish("error",{error:error.message});throw error;}
  }
  function preview(skinId,options={}){return open([skinId],options,"single");}
  function compare(skinIds,options={}){return open(skinIds,options,"comparison");}
  window.PirateOfflineSkins={preview,compare,play,playMotion,setZoom,setPaused,close,
    getStatus:()=>({...lastStatus,skinIds:lastStatus.skinIds.slice(),animations:lastStatus.animations.slice(),models:lastStatus.models.map(model=>({...model,animations:model.animations.slice()}))})};
})();
