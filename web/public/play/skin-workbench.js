(function () {
  "use strict";
  const frame = document.getElementById("game-frame");
  const tools = document.getElementById("tool-panel");
  const nav = document.querySelector(".sidebar nav");
  if (!frame || !tools || !nav) return;
  const state = { loaded:false, loading:null, rows:[], characters:[], featured:[], characterId:null, skinId:null,
    previewOpen:false, mode:null, busy:false, animations:[], motionCounts:{}, motion:null, animation:null, paused:false, zoom:1, request:0 };
  const tab = document.createElement("button");
  tab.type="button"; tab.className="nav"; tab.dataset.tab="skins";
  tab.innerHTML="◉ <span>Skin studio</span><em class='skin-nav-badge'>COMPARE</em>";
  nav.insertBefore(tab, nav.querySelector("[data-tab=inventory]"));
  const panel=document.createElement("section"); panel.className="tool-tab"; panel.dataset.panel="skins"; panel.hidden=true;
  panel.innerHTML=`
    <div class="section-heading"><span class="eyebrow">ORIGINAL ANIMATED MODELS</span><h2>Skin studio</h2><p>Choose a character. Compare their captured skins together, or open one at full size.</p></div>
    <div id="skin-status" class="skin-status" role="status" aria-live="polite">Choose a character to start.</div>
    <section id="skin-character-browser" aria-label="Choose a character">
      <label for="skin-character-search">Find a character<input id="skin-character-search" type="search" placeholder="Name or character ID" autocomplete="off"></label>
      <p id="skin-character-count" class="skin-note"></p><div id="skin-character-grid" class="skin-character-grid"></div>
      <details class="skin-featured-section"><summary>Halloween & requested skins</summary><div id="featured-skins" class="skin-featured"></div></details>
    </section>
    <section id="skin-character-detail" hidden aria-label="Selected character skins">
      <button id="skin-change-character" type="button" class="quiet skin-back">← Change character</button>
      <div class="skin-character-heading"><img id="skin-character-portrait" alt=""><div><span class="eyebrow">SELECTED CHARACTER</span><h3 id="skin-character-name"></h3><p id="skin-character-summary" class="skin-note"></p></div></div>
      <div class="skin-compare-actions"><button id="skin-compare-all" type="button" class="primary">Compare all skins</button><button id="skin-close" type="button">Close preview · resume world</button></div>
      <p id="skin-comparison-note" class="skin-note">All models appear together in the game area. Previewing never changes your save.</p>
      <div id="skin-card-grid" class="skin-card-grid"></div>
      <div class="skin-playback"><h3>Animation playback</h3><div class="skin-presets"><button type="button" data-skin-motion="idle">Idle</button><button type="button" data-skin-motion="run">Run</button><button type="button" data-skin-motion="attack">Attack</button><button type="button" data-skin-motion="skill">Skill</button></div>
        <label for="skin-animation">Shared animation</label><div class="skin-row"><select id="skin-animation"><option value="">Open a preview first</option></select><button type="button" id="skin-play">Play</button></div>
        <label class="skin-loop"><input type="checkbox" id="skin-loop" checked> Loop animation</label>
        <button id="skin-pause" type="button">Pause models</button>
        <div class="skin-zoom-heading"><label for="skin-zoom">Model zoom</label><output id="skin-zoom-value" for="skin-zoom">1×</output></div><div class="skin-zoom-controls"><button type="button" id="skin-zoom-out" aria-label="Zoom model out">−</button><input type="range" id="skin-zoom" min="0.5" max="8" step="0.25" value="1" aria-label="Model zoom"><button type="button" id="skin-zoom-in" aria-label="Zoom model in">+</button></div><button type="button" id="skin-zoom-reset" class="quiet skin-zoom-reset">Reset zoom</button>
        <div id="skin-variant-field" hidden><label for="skin-model-variant">Single-model appearance</label><select id="skin-model-variant"><option value="normal">Normal</option><option value="transformed">King transformation</option></select></div>
        <p id="skin-current-animation" class="skin-current">No model preview open.</p><p id="skin-animation-summary" class="skin-note"></p>
      </div>
    </section>`;
  tools.append(panel);
  const $=selector=>panel.querySelector(selector), all=selector=>Array.from(panel.querySelectorAll(selector));
  const runtime=()=>frame.contentWindow?.PirateOfflineRuntime;
  const studio=()=>frame.contentWindow?.PirateOfflineSkins;
  function ready(){try{return Boolean(runtime()?.getStatus?.().ready&&studio());}catch(_){return false;}}
  const selectedCharacter=()=>state.characters.find(c=>c.id===state.characterId);
  const characterSkins=id=>state.rows.filter(row=>Number(row.generalId)===Number(id));
  function message(value,kind=""){const node=$("#skin-status");node.textContent=value;node.className="skin-status"+(kind?" "+kind:"");}
  function element(tag,text,cls=""){const node=document.createElement(tag);node.textContent=text;node.className=cls;return node;}
  function artwork(src,alt,cls=""){const img=document.createElement("img");img.src=src;img.alt=alt;img.className=cls;img.loading="lazy";img.addEventListener("error",()=>{img.hidden=true;});return img;}
  function skinArt(row){return `/game/icon/skinCard/${row.generalId}_${String(Number(row.skinId)%1000).padStart(3,"0")}.png`;}
  async function api(path,body){
    const response=await fetch(path,{credentials:"same-origin",method:body===undefined?"GET":"POST",headers:body===undefined?{}:{"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body)});
    const data=await response.json();if(!response.ok||data.ok===false)throw new Error(typeof data.detail==="string"?data.detail:data.error?.message||data.message||`Local request failed (${response.status})`);return data;
  }
  function action(fn){return(...args)=>Promise.resolve().then(()=>fn(...args)).catch(error=>{if(!["PREVIEW_CLOSED","PREVIEW_CANCELLED","PREVIEW_REPLACED"].includes(error.code))message(error.message||String(error),"error");});}
  function clearPlayback(){state.previewOpen=false;state.mode=null;state.animations=[];state.motionCounts={};state.motion=null;state.animation=null;$("#skin-current-animation").textContent="No model preview open.";$("#skin-animation-summary").textContent="";syncAnimationOptions();updateControls();}
  function updateControls(){
    const canPreview=ready()&&!state.busy;
    $("#skin-compare-all").disabled=!canPreview||!state.characterId;
    $("#skin-close").disabled=!state.previewOpen;
    $("#skin-pause").disabled=!state.previewOpen||typeof studio()?.setPaused!=="function";
    $("#skin-pause").textContent=state.paused?"Resume models":"Pause models";
    for(const node of all("[data-preview-skin]"))node.disabled=!canPreview;
    for(const node of all("[data-equip-skin]"))node.disabled=state.busy;
    $("#skin-animation").disabled=!state.previewOpen||!$("#skin-animation").value;
    $("#skin-play").disabled=!state.previewOpen||!$("#skin-animation").value;
    for(const node of all("#skin-loop,#skin-zoom,#skin-zoom-out,#skin-zoom-in,#skin-zoom-reset"))node.disabled=!state.previewOpen;
    const patterns={idle:/idle|stand|daiji/i,run:/run|walk|move|pao/i,attack:/attack|atk|gongji/i,skill:/skill|super|jineng/i};
    for(const node of all("[data-skin-motion]"))node.disabled=!state.previewOpen||!(state.motionCounts[node.dataset.skinMotion]>0||state.animations.some(n=>patterns[node.dataset.skinMotion].test(n)));
  }
  function syncAnimationOptions(){
    const select=$("#skin-animation"),previous=select.value;select.replaceChildren();
    for(const motion of ["idle","run","attack","skill"]){if(state.motionCounts[motion]>0){const o=element("option",motion[0].toUpperCase()+motion.slice(1)+" · match per model");o.value="@"+motion;select.append(o);}}
    if(state.animations.length){const group=element("optgroup","");group.label="Exact shared names";for(const name of state.animations){const o=element("option",name);o.value=name;group.append(o);}select.append(group);}
    if(!select.options.length){const o=element("option","Open a preview first");o.value="";select.append(o);}
    const wanted=state.motion?"@"+state.motion:state.animation||previous;
    if(Array.from(select.options).some(o=>o.value===wanted))select.value=wanted;
  }
  function syncAnimations(detail){
    if(Array.isArray(detail.animations))state.animations=detail.animations.slice();
    if(detail.motionCounts)state.motionCounts={...detail.motionCounts};
    else if(state.mode!=="comparison")state.motionCounts={};
    if(typeof detail.loop==="boolean")$("#skin-loop").checked=detail.loop;
    if(typeof detail.paused==="boolean")state.paused=detail.paused;
    if(Number.isFinite(detail.zoom)){state.zoom=detail.zoom;$("#skin-zoom").value=String(detail.zoom);$("#skin-zoom-value").textContent=`${detail.zoom}×`;}
    state.motion=detail.motion||null;state.animation=detail.currentAnimation||detail.animation||null;
    syncAnimationOptions();
    if(state.previewOpen){const count=detail.models?.length||detail.skinIds?.length||1;$("#skin-current-animation").textContent=`${detail.title||selectedCharacter()?.name||"Selected skin"} · ${state.motion||state.animation||"ready"} · ${state.paused?"paused":$("#skin-loop").checked?"looping":"once"}`;$("#skin-animation-summary").textContent=state.mode==="comparison"?`${count} original models. Presets choose the corresponding action for each model; unsupported actions are marked in its tile.`:`${state.animations.length} original animations available.`;}
  }
  function handleStatus(detail){
    if(detail.generalId&&state.characterId&&Number(detail.generalId)!==state.characterId)return;
    if(Array.isArray(detail.skinIds)&&detail.skinIds.length&&state.characterId&&!detail.skinIds.some(id=>Number(id)===state.characterId||characterSkins(state.characterId).some(row=>Number(row.skinId)===Number(id))))return;
    if(detail.status==="closed"){clearPlayback();message(state.characterId?"Preview closed. Your local world has resumed.":"Choose a character to start.");return;}
    if(detail.status==="error"){clearPlayback();message(detail.error||"Original model preview failed.","error");return;}
    state.mode=detail.mode||state.mode;state.previewOpen=["loading","ready","playing"].includes(detail.status)||state.previewOpen;
    syncAnimations(detail);
    if(detail.status==="loading")message(`Loading ${detail.title||selectedCharacter()?.name||"selected models"}…`,"loading");
    else if(detail.status==="ready")message(state.mode==="comparison"?`${selectedCharacter()?.name||detail.title}: comparing all captured skins. The local world is paused.`:`${detail.title} is ready. The local world is paused.`);
    updateControls();
  }
  function renderCharacters(){
    const query=$("#skin-character-search").value.trim().toLowerCase();
    const filtered=state.characters.filter(c=>`${c.name} ${c.id}`.toLowerCase().includes(query));
    $("#skin-character-count").textContent=`${filtered.length} of ${state.characters.length} characters · ${state.rows.length} captured alternate skins`;
    const grid=$("#skin-character-grid");grid.replaceChildren();
    for(const character of filtered){
      const count=characterSkins(character.id).length,control=document.createElement("button");control.type="button";control.className="skin-character-card";control.dataset.skinCharacter=character.id;control.setAttribute("aria-label",`${character.name}, ${count} ${count===1?"skin":"skins"}`);
      const text=document.createElement("span");text.append(element("strong",character.name),element("small",`${count} ${count===1?"skin":"skins"}`));control.append(artwork(`/game/icon/generalCard/${character.id}.png`,""),text);control.addEventListener("click",action(()=>selectCharacter(character.id)));grid.append(control);
    }
    if(!filtered.length)grid.append(element("p","No matching characters.","skin-note"));
  }
  function renderSkins(){
    const character=selectedCharacter(),rows=characterSkins(state.characterId),grid=$("#skin-card-grid");grid.replaceChildren();
    $("#skin-character-name").textContent=character?.name||`Character ${state.characterId}`;
    $("#skin-character-summary").textContent=`Default appearance + ${rows.length} captured alternate ${rows.length===1?"skin":"skins"}`;
    const portrait=$("#skin-character-portrait");portrait.hidden=false;portrait.src=`/game/icon/generalCard/${state.characterId}.png`;portrait.alt=character?.name||"Selected character";portrait.onerror=()=>{portrait.hidden=true;};
    $("#skin-comparison-note").textContent="Compare the default appearance and every captured skin together, including available transformations. Previewing never changes your save.";
    const baseCard=document.createElement("article");baseCard.className="skin-choice-card";
    baseCard.append(artwork(`/game/icon/generalCard/${state.characterId}.png`,"Default appearance"),element("h4","Default appearance"));
    const basePreview=element("button","Preview");basePreview.type="button";basePreview.dataset.previewSkin=state.characterId;basePreview.addEventListener("click",action(()=>preview(state.characterId)));baseCard.append(basePreview);grid.append(baseCard);
    for(const row of rows){
      const id=Number(row.skinId),card=document.createElement("article");card.className="skin-choice-card";card.dataset.skinCard=id;
      if(id===state.skinId)card.classList.add("selected");
      const name=state.featured.find(f=>Number(f.skinId)===id)?.title||row.name||`Skin ${id}`;
      card.append(artwork(skinArt(row),name),element("h4",name),element("small",`Skin ${id}`));
      const controls=document.createElement("div");controls.className="skin-card-actions";
      const previewButton=element("button","Preview");previewButton.type="button";previewButton.dataset.previewSkin=id;previewButton.addEventListener("click",action(()=>preview(id)));
      const equipButton=element("button","Equip");equipButton.type="button";equipButton.dataset.equipSkin=id;equipButton.setAttribute("aria-label",`Equip ${name}`);equipButton.addEventListener("click",action(()=>equipSkin(id)));
      controls.append(previewButton,equipButton);card.append(controls);grid.append(card);
    }
    $("#skin-variant-field").hidden=state.skinId!==16059004;updateControls();
  }
  async function selectCharacter(id,{autoPreview=true}={}){
    await loadOptions();id=Number(id);if(!state.characters.some(c=>c.id===id))throw new Error("Choose a captured character.");
    closeViewer(false);state.characterId=id;state.skinId=null;$("#skin-character-browser").hidden=true;$("#skin-character-detail").hidden=false;$("#skin-model-variant").value="normal";renderSkins();
    const rows=characterSkins(id);
    message(ready()?`${selectedCharacter().name}: ready to compare the default model and ${rows.length} skins.`:"The original game is loading. Compare this character’s skins when it is ready.");
    if(autoPreview&&ready())return compareAll();
  }
  async function compareAll(){
    if(!ready())throw new Error("The original offline client is still loading.");
    const rows=characterSkins(state.characterId);if(!state.characterId)throw new Error("Choose a captured character.");
    if(typeof studio().compare!=="function")throw new Error("Refresh the game to load the comparison viewer.");
    const request=++state.request;state.busy=true;state.mode="comparison";state.skinId=null;renderSkins();updateControls();
    try{const result=await studio().compare([state.characterId,...rows.map(r=>Number(r.skinId))],{title:selectedCharacter().name,motion:"idle",loop:$("#skin-loop").checked,zoom:1});if(request===state.request)handleStatus({...result,status:"ready"});return result;}
    finally{if(request===state.request){state.busy=false;updateControls();}}
  }
  async function preview(id){
    await loadOptions();id=Number(id);const row=state.rows.find(r=>Number(r.skinId)===id),base=state.characters.find(c=>c.id===id);if(!row&&!base)throw new Error("Choose a captured skin or default character.");
    const owner=row?Number(row.generalId):base.id;
    if(state.characterId!==owner)await selectCharacter(owner,{autoPreview:false});
    if(!ready())throw new Error("The original offline client is still loading.");
    const changed=state.skinId!==id;state.skinId=id;if(changed)$("#skin-model-variant").value="normal";
    const request=++state.request;state.busy=true;state.mode="single";state.motionCounts={};renderSkins();
    try{const result=await studio().preview(id,{variant:id===16059004?$("#skin-model-variant").value:"normal"});if(request===state.request)handleStatus({...result,status:"ready",mode:"single"});return result;}
    finally{if(request===state.request){state.busy=false;updateControls();}}
  }
  function closeViewer(showMessage=true){
    state.request++;state.busy=false;try{studio()?.close();}catch(_){}clearPlayback();
    if(showMessage)message(state.characterId?"Preview closed. Your local world has resumed.":"Choose a character to start.");
  }
  async function equipSkin(id){
    id=Number(id);if(!state.rows.some(row=>Number(row.skinId)===id))throw new Error("Choose the skin you want to equip.");
    closeViewer(false);state.busy=true;updateControls();
    try{const result=await api("/api/gm",{command:"equipSkin",arg:String(id)});if(ready()){await runtime().applyResult(result);await runtime().refresh();}message(result.message||"The selected skin is equipped in this local crew.");return result;}
    finally{state.busy=false;updateControls();}
  }
  function play(){const name=$("#skin-animation").value;if(!name)return;if(name.startsWith("@"))return playMotion(name.slice(1));const result=studio().play(name,$("#skin-loop").checked);handleStatus({...result,status:"playing"});return result;}
  function playMotion(motion){if(!state.previewOpen)return;const result=studio().playMotion(motion,$("#skin-loop").checked);handleStatus({...result,status:"playing"});return result;}
  function setZoom(value){const result=studio().setZoom(Number(value));syncAnimations(result);updateControls();return result;}
  async function loadOptions(){
    if(state.loaded)return;if(state.loading)return state.loading;
    state.loading=(async()=>{
      const [skins,generals,featured]=await Promise.all([api("/api/references/GeneralSkinRef?limit=500"),api("/api/references/GeneralRef?limit=500"),api("/featured-skins.json")]);
      state.rows=(skins.rows||[]).filter(row=>Number(row.skinId)>0&&Number(row.generalId)>0);state.featured=Array.isArray(featured)?featured:[];
      state.characters=(generals.rows||[]).map(row=>({id:Number(row.refId||row.generalId),name:row.generalName||row.name||`Character ${row.refId}`})).filter(row=>row.id).sort((a,b)=>a.name.localeCompare(b.name));
      state.loaded=true;renderCharacters();const shortcuts=$("#featured-skins");shortcuts.replaceChildren();
      for(const item of state.featured){const row=state.rows.find(r=>Number(r.skinId)===Number(item.skinId));if(!row)continue;const control=element("button",item.title);control.type="button";control.dataset.featuredSkin=item.skinId;control.addEventListener("click",action(()=>selectCharacter(row.generalId)));shortcuts.append(control);}
    })().finally(()=>{state.loading=null;});return state.loading;
  }
  async function selectPanel(){
    document.querySelectorAll("[data-panel]").forEach(node=>node.hidden=node.dataset.panel!=="skins");document.querySelectorAll("[data-tab]").forEach(node=>node.classList.toggle("active",node.dataset.tab==="skins"));
    await loadOptions();updateControls();if(!state.characterId)message("Choose a character to compare their skins.");
  }
  tab.addEventListener("click",action(selectPanel));
  $("#skin-character-search").addEventListener("input",renderCharacters);
  $("#skin-change-character").addEventListener("click",()=>{closeViewer(false);state.characterId=null;state.skinId=null;$("#skin-character-detail").hidden=true;$("#skin-character-browser").hidden=false;renderCharacters();message("Choose a character to compare their skins.");$("#skin-character-search").focus();});
  $("#skin-compare-all").addEventListener("click",action(compareAll));$("#skin-close").addEventListener("click",()=>closeViewer());
  $("#skin-play").addEventListener("click",action(play));$("#skin-animation").addEventListener("change",action(play));
  $("#skin-pause").addEventListener("click",action(()=>{const result=studio().setPaused(!state.paused);syncAnimations(result);updateControls();}));
  $("#skin-loop").addEventListener("change",action(()=>{if(state.previewOpen)return play();}));
  $("#skin-zoom").addEventListener("input",action(()=>setZoom($("#skin-zoom").value)));
  $("#skin-zoom-out").addEventListener("click",action(()=>setZoom(state.zoom-.25)));$("#skin-zoom-in").addEventListener("click",action(()=>setZoom(state.zoom+.25)));$("#skin-zoom-reset").addEventListener("click",action(()=>setZoom(state.mode==="comparison"?1:3)));
  $("#skin-model-variant").addEventListener("change",action(()=>{if(state.skinId)return preview(state.skinId);}));
  for(const node of all("[data-skin-motion]"))node.addEventListener("click",action(()=>playMotion(node.dataset.skinMotion)));
  document.addEventListener("click",event=>{if(event.target.closest("#open-main,#open-original-gm,#original-gm,#logout"))closeViewer(false);const other=event.target.closest("[data-tab]");if(other&&other.dataset.tab!=="skins")closeViewer(false);},true);
  document.getElementById("feature-select")?.addEventListener("change",()=>closeViewer(false),true);
  frame.addEventListener("load",()=>{state.request++;state.busy=false;clearPlayback();try{for(const id of ["runtime-main","runtime-gm"])frame.contentDocument?.getElementById(id)?.addEventListener("click",()=>closeViewer(false),true);}catch(_){}});
  window.addEventListener("message",event=>{
    if(event.origin!==location.origin||event.source!==frame.contentWindow)return;
    if(event.data?.type==="pirate-skin-status")handleStatus(event.data.detail||{});
    else if(event.data?.type==="pirate-runtime-status"){if(event.data.detail?.ready&&!state.previewOpen)message(state.characterId?"Original client ready. Compare the selected character’s skins.":"Choose a character to compare their skins.");updateControls();}
  });
  window.PirateOfflineSkinWorkbench={open:selectPanel,selectCharacter,compareAll,preview,close:closeViewer,equipSkin,getStatus:()=>({...state,loading:Boolean(state.loading),rows:undefined,characters:undefined})};
  updateControls();
})();
