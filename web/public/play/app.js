(function () {
  "use strict";
  const $ = selector => document.querySelector(selector);
  const $$ = selector => Array.from(document.querySelectorAll(selector));
  const app = {account:null, snapshot:null, gm:[], catalog:[], schemas:{}, refs:new Map(), runtimeReady:false, logs:[], errors:0};
  const frame = $("#game-frame");
  $("#go-back").addEventListener("click",()=>runtime()?.goBack());
  const savePanel = $("[data-panel=save]");
  savePanel.insertBefore($("#server-age-template").content.cloneNode(true), savePanel.querySelector("h3"));
  const explore=document.createElement("div");explore.className="subcard";
  explore.innerHTML='<h3>Explore every island</h3><label><input id="free-roam" type="checkbox" checked> Free roam: open every island and fog area</label><button id="apply-free-roam">Apply exploration mode</button><label>Destination<select id="world-map-select"></select></label><button id="visit-world-map" class="primary">Visit island</button><p>Travel freely without completing the story. Character rescues and achievement rewards keep their own progress.</p>';
  $("[data-panel=world] .section-heading").after(explore);
  const supplies=document.createElement("div");supplies.className="subcard";
  supplies.innerHTML='<h3>Test supplies</h3><p>9,999+ of every usable item, including mount/pet copies, treasures, shards and crafting materials. High-cost resources have larger stocks. Activate and upgrade at your own pace.</p><button id="restock-test-items">Restock test supplies</button>';
  savePanel.prepend(supplies);
  supplies.querySelector('button').addEventListener('click',async()=>{try{const result=await api('/api/gm',{command:'stockTestItems',arg:''});if(result.ok===false)throw Error(result.error?.message||'Restock failed');await runtime()?.applyResult(result);await refreshState();await runtime()?.refresh();toast('Test supplies restocked; upgrades kept.');}catch(e){toast(e.message,true);}});
  let toastTimer, searchTimer, stateRefreshTimer;
  const pretty = value => JSON.stringify(value, null, 2);

  async function api(path, body) {
    const response = await fetch(path, {credentials:"same-origin", method:body === undefined ? "GET" : "POST", headers:body === undefined ? {} : {"Content-Type":"application/json"}, body:body === undefined ? undefined : JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : data.error?.message || data.error || `Local request failed (${response.status})`);
    return data;
  }
  function toast(message, error=false) {
    clearTimeout(toastTimer); $("#toast").textContent=message; $("#toast").classList.toggle("error", error); $("#toast").hidden=false;
    toastTimer=setTimeout(()=>{$("#toast").hidden=true;},6500);
  }
  function log(message, detail) {
    app.logs.unshift(`${new Date().toLocaleTimeString()}  ${message}${detail ? "\n"+ (typeof detail === "string" ? detail : pretty(detail)) : ""}`);
    app.logs=app.logs.slice(0,60); $("#runtime-log").textContent=app.logs.join("\n\n");
  }
  function runtime() {return frame.contentWindow?.PirateOfflineRuntime;}
  function rows(value) {return Array.isArray(value) ? value : Object.values(value || {});}
  async function refs(table) {
    if (!app.refs.has(table)) {const all=[];let offset=0,total=1;while(offset<total){const page=await api(`/api/references/${table}?limit=500&offset=${offset}`);all.push(...page.rows);total=page.total;offset+=page.rows.length;if(!page.rows.length)break;}app.refs.set(table,all);}
    return app.refs.get(table);
  }
  function button(text, handler, cls="") {const b=document.createElement("button");b.textContent=text;b.className=cls;b.addEventListener("click",()=>Promise.resolve(handler()).catch(e=>toast(e.message,true)));return b;}
  function text(tag,content,cls="") {const e=document.createElement(tag);e.textContent=content;e.className=cls;return e;}
  function entryId(row) {return Number(row.generalId ?? row.refId ?? row.id ?? 0);}
  function inventoryCount(id) {const value=app.snapshot?.inventory?.[String(id)];return typeof value === "number" ? value : Number(value?.count || 0);}
  async function refreshState() {
    app.snapshot=await api("/api/me/snapshot");
    $("#captain-name").textContent=app.snapshot.player.nickname;
    $("#captain-level").textContent=`Level ${app.snapshot.player.level}`;
    $("#currency-list").replaceChildren();
    const power=app.snapshot.player.attrs.find(attr=>attr.attrType===1000)?.attrValue || 0;
    const powerRow=text("div","","currency-row");powerRow.append(text("span","Crew power"),text("b",Math.round(power).toLocaleString()));$("#currency-list").append(powerRow);
    for (const [id,name] of [[101,"Diamonds"],[102,"Beli"],[103,"Meat"]]) {
      const row=text("div","","currency-row");row.append(text("span",name),text("b",inventoryCount(id).toLocaleString()));$("#currency-list").append(row);
    }
    $("#save-status").textContent="Saved locally · "+new Date().toLocaleTimeString();
    if(document.activeElement?.id!=="server-age") $("#server-age").value=app.snapshot.settings.serverAgeDays ?? Math.floor((Date.now()-app.snapshot.player.openServerTime)/86400000);
    $("#free-roam").checked=app.snapshot.settings.freeRoam !== false;
    if (!$("[data-panel=characters]").hidden) await renderCharacters();
    if (!$("[data-panel=inventory]").hidden) await renderInventory();
    refreshBuildTools();
    return app.snapshot;
  }
  async function refreshRuntime() {if(app.runtimeReady) try{await runtime().refresh();}catch(e){log("Original client refresh",e.message);}}
  async function gm(command,arg="") {
    const result=await api("/api/gm",{command,arg:String(arg)});
    $("#gm-result").textContent=pretty(result).slice(0,12000);
    if(!result.ok){toast(result.error?.message || "Offline command failed",true);return result;}
    if(app.runtimeReady) runtime().applyResult(result);
    toast(`${command} applied to ${app.account.username}'s offline save.`);
    log(`Offline GM · ${command}`,result.reply || result.capability);
    await refreshState();
    if (!["mapTransfer","freeRoam"].includes(result.clientAction?.type)) await refreshRuntime();
    return result;
  }
  function selectTab(name) {
    $$("[data-tab]").forEach(e=>e.classList.toggle("active",e.dataset.tab===name));
    $$("[data-panel]").forEach(e=>e.hidden=e.dataset.panel!==name);
    if(name==="characters") renderCharacters().catch(e=>toast(e.message,true));
    if(name==="inventory") renderInventory().catch(e=>toast(e.message,true));
    if(name==="save") renderCoverage().catch(e=>toast(e.message,true));
    if(name==="boosts") prepareBuildTools().catch(e=>toast(e.message,true));
  }
  async function renderCharacters() {
    const definitions=await refs("GeneralRef"), byId=new Map(definitions.map(r=>[Number(r.refId),r]));
    const list=$("#character-list");list.replaceChildren();
    for(const general of rows(app.snapshot.generals).sort((a,b)=>entryId(a)-entryId(b))) {
      const id=entryId(general), def=byId.get(id) || {};
      const card=text("article","","character-card"),top=text("div","","card-top"),image=document.createElement("img");
      image.src=`/game/icon/generalCard/${id}.png`;image.alt=def.generalName || `Character ${id}`;image.addEventListener("error",()=>{image.hidden=true;},{once:true});
      const info=text("div","");info.append(text("strong",def.generalName || `Character ${id}`),text("small",`ID ${id}`),text("span",`Level ${general.level || 1} · ★ ${general.star || 0}`));top.append(image,info);
      const actions=text("div","","card-actions");
      actions.append(button("Upgrade 1 level",async()=>{const result=await api("/api/command",{id:1301,payload:{generalId:id}});$("#gm-result").textContent=pretty(result);if(!result.ok)throw new Error(result.error?.message || "Upgrade unavailable");await refreshState();await refreshRuntime();toast("Character upgraded using local materials.");}),button("Give 100 fragments",()=>gm("addItem",`1_${id}_100`)));
      card.append(top,actions);list.append(card);
    }
  }
  async function renderInventory() {
    const defs=await refs("ItemRef"), byId=new Map(defs.map(r=>[Number(r.refId),r]));
    const list=$("#inventory-list");list.replaceChildren();
    const items=Object.entries(app.snapshot.inventory).map(([id,item])=>({id:Number(id),count:typeof item==="number"?item:item.count})).filter(i=>i.count>0).sort((a,b)=>a.id-b.id);
    for(const item of items) {
      const row=text("div","","inventory-row"),info=text("div","");info.append(text("strong",byId.get(item.id)?.name || `Item ${item.id}`),text("small",`ID ${item.id}`));row.append(info,text("b",Number(item.count).toLocaleString()));list.append(row);
    }
    if(!items.length)list.append(text("p","Your hold is empty. Use the GM panel to give items."));
  }
  async function searchItems() {
    const q=$("#item-search").value.trim(), target=$("#item-search-results"); target.replaceChildren();if(!q)return;
    const data=await api(`/api/references/ItemRef?q=${encodeURIComponent(q)}&limit=35`);
    for(const row of data.rows){const e=text("div","","reference-result");e.append(text("span",`${row.refId} · ${row.name}`),button("Give 100",()=>gm("addItem",`1_${row.refId}_100`)));target.append(e);}
  }
  const boostsButton=text('button','✧ Build & boosts','nav');boostsButton.dataset.tab='boosts';document.querySelector('nav[aria-label="Offline tools"]').append(boostsButton);
  const boostsPanel=text('section','','tool-tab');boostsPanel.dataset.panel='boosts';boostsPanel.hidden=true;document.querySelector('#tool-panel').append(boostsPanel);
  boostsPanel.innerHTML='<div class="section-heading"><span class="eyebrow">OFFLINE BUILD TESTING</span><h2>Treasures, gems & boosts</h2><p>Give a copy, then activate or equip it. Bonuses follow the captured rules and apply to the relevant characters.</p></div><div class="subcard"><h3>Treasures</h3><label>Treasure<select id="boost-treasure"></select></label><p id="boost-treasure-info"></p><button id="boost-give-treasure">Give 1 treasure copy</button><button id="boost-star-treasure" class="primary">Activate / +1 treasure star</button><label>Material<select id="boost-material"></select></label><label>Quantity<input id="boost-material-count" type="number" min="1" max="10000" value="1"></label><button id="boost-give-material">Give selected materials</button><button id="boost-add-material">Add materials to treasure</button></div><div class="subcard"><h3>Character gems</h3><label>Character<select id="boost-character"></select></label><label>Gem type<select id="boost-gem-type"></select></label><label>Gem level<select id="boost-gem"></select></label><label>Equipment slot<select id="boost-slot"></select></label><p id="boost-gem-info"></p><button id="boost-give-gem">Give 1 selected gem</button><button id="boost-equip-gem" class="primary">Equip gem</button><button id="boost-remove-gem">Remove equipped gem</button></div><div class="subcard"><h3>Shared power boosts</h3><p id="boost-shared-info"></p><button id="boost-give-points">Give 100 Talent points</button><button id="boost-talent">Activate next basic Talent</button><button id="boost-give-advanced">Give 10 advanced-Talent currency</button><button id="boost-advanced">Activate next advanced Talent</button><button id="boost-give-powder">Give 100 Gem Powder</button><button id="boost-master">Upgrade Gem Master one stage</button><p>Upgrades spend the same captured materials as the original menus. Character level, star and material limits still apply.</p></div><p id="boost-result" class="form-message" role="status"></p>';
  let boostDefinitions=null;
  async function prepareBuildTools(){
    if(!boostDefinitions){
      const [treasures,materials,gems,slots,types,stars,generals,items]=await Promise.all(['TreasureRef','TreasureMaterialRef','GemRef','GemSlotRef','GemTypeRef','TreasureStarRef','GeneralRef','ItemRef'].map(refs));boostDefinitions={treasures,materials,gems,slots,types,stars,generals,items};
      const fill=(node,rows,name)=>{node.replaceChildren();for(const row of rows){const option=text('option',name(row));option.value=row.refId;node.append(option);}};
      fill($('#boost-treasure'),treasures,r=>r.name+' · '+r.refId);fill($('#boost-material'),materials,r=>items.find(i=>Number(i.refId)===Number(r.refId))?.name||'Material '+r.refId);fill($('#boost-gem-type'),types,r=>r.name);
      $('#boost-treasure').onchange=refreshBuildTools;$('#boost-character').onchange=refreshBuildTools;$('#boost-slot').onchange=refreshBuildTools;
      $('#boost-gem-type').onchange=()=>{const type=Number($('#boost-gem-type').value);fill($('#boost-gem'),gems.filter(g=>Number(g.type)===type).sort((a,b)=>Number(a.level)-Number(b.level)),r=>`Level ${r.level} · ${r.name}`);refreshBuildTools();};$('#boost-gem').onchange=refreshBuildTools;$('#boost-gem-type').onchange();
      const action=(id,fn)=>$(id).onclick=async()=>{const b=$(id);b.disabled=true;try{await fn();await refreshState();await refreshRuntime();refreshBuildTools();$('#boost-result').textContent='Applied to this captain’s offline save.';}catch(e){$('#boost-result').textContent=e.message;toast(e.message,true);}finally{b.disabled=false;}};
      const command=async(id,payload={})=>{const result=await api('/api/command',{id,payload});if(!result.ok)throw Error(result.error?.message||'Upgrade unavailable');if(app.runtimeReady)await runtime().applyResult(result);return result;};
      const give=async(id,count)=>{const r=await gm('addItem',`1_${id}_${count}`);if(!r.ok)throw Error(r.error?.message||'Grant failed');};
      const quantity=()=>{const n=Number($('#boost-material-count').value);if(!Number.isSafeInteger(n)||n<1||n>10000)throw Error('Choose a quantity between 1 and 10000.');return n;};
      action('#boost-give-treasure',()=>give($('#boost-treasure').value,1));action('#boost-star-treasure',()=>command(3321,{refId:Number($('#boost-treasure').value)}));
      action('#boost-give-material',()=>give($('#boost-material').value,quantity()));action('#boost-add-material',()=>command(3322,{refId:Number($('#boost-treasure').value),addNum:{refId:Number($('#boost-material').value),count:quantity()}}));
      action('#boost-give-gem',()=>give($('#boost-gem').value,1));action('#boost-equip-gem',()=>command(10101,{slotInfos:[{generalId:Number($('#boost-character').value),slotRefId:Number($('#boost-slot').value),itemId:Number($('#boost-gem').value)}]}));
      action('#boost-remove-gem',()=>command(10102,{slotInfos:[{generalId:Number($('#boost-character').value),slotRefId:Number($('#boost-slot').value)}]}));
      action('#boost-give-points',()=>give(105,100));action('#boost-talent',()=>command(1501));action('#boost-give-advanced',()=>give(1012,10));action('#boost-advanced',()=>command(1502));action('#boost-give-powder',()=>give(1065,100));action('#boost-master',()=>command(10103));
    }
    refreshBuildTools();
  }
  function refreshBuildTools(){
    if(!boostDefinitions||!app.snapshot)return;const d=boostDefinitions,s=app.snapshot,selected=$('#boost-character').value;
    $('#boost-character').replaceChildren();for(const general of Object.values(s.generals)){const def=d.generals.find(r=>Number(r.refId)===Number(general.generalId));const o=text('option',`${def?.generalName||general.generalId} · Lv ${general.level} · ★${general.star}`);o.value=general.generalId;$('#boost-character').append(o);}if([...$('#boost-character').options].some(o=>o.value===selected))$('#boost-character').value=selected;
    const treasureId=Number($('#boost-treasure').value),treasure=d.treasures.find(r=>Number(r.refId)===treasureId),owned=s.treasures?.[treasureId];const names=String(treasure?.generals||'').split('#').map(id=>d.generals.find(r=>r.refId===id||Number(r.refId)===Number(id))?.generalName).filter(Boolean);const star=d.stars.find(r=>Number(r.refId)===treasureId&&Number(r.star)===Number(owned?.star||1));
    $('#boost-treasure-info').textContent=`${owned?'Active · star '+owned.star:'Not active'} · ${inventoryCount(treasureId)} copies in bag. Affects: ${names.join(', ')}. Installed materials: ${(owned?.materials||[]).map(m=>(d.items.find(i=>Number(i.refId)===Number(m.refId))?.name||m.refId)+' × '+m.count).join(', ')||'none'}. Limits: ${String(star?.materialLimit||'').split('#').filter(Boolean).map(v=>{const [id,count]=v.split('_');return (d.items.find(i=>Number(i.refId)===Number(id))?.name||id)+' × '+count;}).join(', ')||'activate first'}.`;
    const slotSelect=$('#boost-slot'),oldSlot=slotSelect.value,type=Number($('#boost-gem-type').value);slotSelect.replaceChildren();for(const slot of d.slots.filter(r=>String(r.types).split('#').map(Number).includes(type))){const o=text('option',`Equipment ${slot.equipPart}, socket ${slot.index} · requires ★${slot.star}`);o.value=slot.refId;slotSelect.append(o);}if([...slotSelect.options].some(o=>o.value===oldSlot))slotSelect.value=oldSlot;
    const equipped=s.gemSlots?.find(r=>Number(r.generalId)===Number($('#boost-character').value)&&Number(r.slotRefId)===Number(slotSelect.value));const gem=d.gems.find(r=>Number(r.refId)===Number($('#boost-gem').value));$('#boost-gem-info').textContent=`${inventoryCount(Number(gem?.refId))} selected gems in bag. Equipped: ${equipped?(d.gems.find(r=>Number(r.refId)===Number(equipped.itemId))?.name||equipped.itemId):'none'}.`;
    $('#boost-shared-info').textContent=`Basic Talents: ${s.talent?.refIds?.length||0} · Advanced Talents: ${s.talent?.advanceIds?.length||0} · Gem Master stage: ${s.gemBookStage||0}.`;
  }

  function renderGmOptions() {
    const select=$("#gm-command");select.replaceChildren();
    for(const item of app.gm){const option=document.createElement("option");option.value=item.command;option.textContent=item.command;select.append(option);}
    updateGmArg();
  }
  function updateGmArg() {
    const entry=app.gm.find(x=>x.command===$("#gm-command").value);$("#gm-arg").value=entry?.exampleArg || "";$("#gm-description").textContent=entry?.description || "";
  }
  function requestTemplate(type,depth=0) {
    if(depth>3)return {};
    const result={};for(const field of app.schemas[type]?.fields || []) result[field.name]=field.repeated?[]:field.type==="message"?requestTemplate(field.message,depth+1):field.type==="string"?"":field.type==="bool"?false:field.type==="bytes"?[]:0;return result;
  }
  function renderProtocol() {
    const q=$("#protocol-search").value.toLowerCase(),select=$("#protocol-command");select.replaceChildren();
    for(const command of app.catalog.filter(c=>c.sendable && `${c.id} ${c.name}`.toLowerCase().includes(q))){const o=document.createElement("option");o.value=command.id;o.textContent=`${command.id} · ${command.name}`;select.append(o);}
    updateProtocolPayload();
  }
  function updateProtocolPayload(){const command=app.catalog.find(c=>c.id===Number($("#protocol-command").value));$("#protocol-payload").value=pretty(requestTemplate(command?.request));}
  async function renderCoverage(){
    const cap=await api("/api/capabilities");$("#coverage-detail").textContent=pretty(cap);
    const counts=[["Offline GM actions",cap.gmCommands?.length || 0],["Implemented protocol handlers",cap.implementedCommandIds?.length || 0],["Initialization placeholders",cap.initializationStubIds?.length || 0],["Unsupported protocol entries",cap.unsupportedCommandIds?.length || 0]];
    $("#coverage-summary").replaceChildren();for(const [name,count]of counts){const e=text("div","","coverage-stat");e.append(text("span",name),text("b",String(count)));$("#coverage-summary").append(e);}
    $("#diagnostics").textContent=pretty(await api("/api/diagnostics")).slice(0,20000);
  }
  async function prepareWorld(){const [monsters,maps]=await Promise.all([api("/api/references/MonsterRef?limit=80"),api("/api/world-maps")]);const select=$("#monster-select");for(const monster of monsters.rows){const option=document.createElement("option");option.value=monster.refId;option.textContent=`${monster.refId} · ${monster.name || monster.monsterName || "Monster"}`;select.append(option);}const destinations=$("#world-map-select");destinations.replaceChildren();for(const map of maps){const option=document.createElement("option");option.value=map.refId;option.textContent=`${map.refId} · ${map.name}`;destinations.append(option);}destinations.value=String(app.snapshot.scene.mapId);}
  function runtimeFailure(error){app.runtimeReady=false;app.errors++;$("#runtime-error-count").textContent=`(${app.errors} diagnostics)`;$("#runtime-status").textContent="Original client needs attention";$("#runtime-detail").textContent=error.message || String(error);$("#runtime-cover").hidden=false;$("#retry-runtime").hidden=false;log("Original runtime",error.stack || error.message || String(error));}
  async function startRuntime(options={}){
    app.runtimeReady=false;$("#runtime-cover").hidden=false;$("#retry-runtime").hidden=true;
    frame.onload=async()=>{try{if(!runtime())throw new Error("Original runtime bridge did not load.");await runtime().start(app.account);app.runtimeReady=true;$("#runtime-cover").hidden=true;$("#runtime-status").textContent="Original client ready · full offline GM";const select=$("#feature-select");select.replaceChildren();const placeholder=document.createElement("option");placeholder.value="";placeholder.textContent="Original features…";select.append(placeholder);for(const feature of runtime().getFeatures()){const option=document.createElement("option");option.value=feature.name;option.textContent=`${feature.id} · ${feature.name}`;select.append(option);}}catch(error){runtimeFailure(error);}};
    frame.src="/play/runtime.html?v=20261031-2"+(options?.view==="main"?"&bootView=main":"");
  }
  async function enter(account){
    app.account=account;$("#login-screen").hidden=true;$("#workspace").hidden=false;$("#account-tools").hidden=false;$("#account-label").textContent=`${account.username} · GM`;
    const [gmData,catalogData,schemas]=await Promise.all([api("/api/gm-commands"),api("/api/catalog"),api("/api/schemas")]);app.gm=gmData;app.catalog=catalogData.commands;app.schemas=schemas;
    renderGmOptions();renderProtocol();await refreshState();prepareWorld().catch(e=>log("World definitions",e.message));await startRuntime();
  }
  async function original(action,...args){if(!app.runtimeReady)throw new Error("The original game client is still loading. Offline GM commands in the workbench remain available.");return runtime()[action](...args);}
  $("#login-form").addEventListener("submit",async event=>{event.preventDefault();const b=$("#login-submit");b.disabled=true;$("#login-message").textContent="Opening this captain's local save…";try{const result=await api("/api/login",{username:$("#username").value.trim(),password:$("#password").value});$("#password").value="";await enter(result.account);}catch(e){$("#login-message").textContent=e.message;}finally{b.disabled=false;}});
  $("#logout").addEventListener("click",async()=>{const button=$("#logout");button.disabled=true;try{await api("/api/logout",{});app.runtimeReady=false;app.account=null;app.snapshot=null;clearTimeout(stateRefreshTimer);frame.src="about:blank";$("#workspace").hidden=true;$("#account-tools").hidden=true;$("#login-screen").hidden=false;$("#login-message").textContent="Signed out. Your saved captains are kept.";}catch(e){toast(e.message,true);}finally{button.disabled=false;}});
  $$("[data-tab]").forEach(e=>e.addEventListener("click",()=>selectTab(e.dataset.tab)));
  $$("[data-gm]").forEach(e=>e.addEventListener("click",()=>gm(e.dataset.gm,e.dataset.arg).catch(x=>toast(x.message,true))));
  $("#grant-item").addEventListener("click",()=>gm("addItem",`1_${$("#item-id").value}_${$("#item-count").value}`).catch(e=>toast(e.message,true)));
  $("#remove-item").addEventListener("click",()=>gm("subItem",`1_${$("#item-id").value}_${$("#item-count").value}`).catch(e=>toast(e.message,true)));
  $("#gm-command").addEventListener("change",updateGmArg);$("#run-gm").addEventListener("click",()=>gm($("#gm-command").value,$("#gm-arg").value).catch(e=>toast(e.message,true)));
  $("#refresh-characters").addEventListener("click",()=>refreshState().catch(e=>toast(e.message,true)));
  $("#item-search").addEventListener("input",()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>searchItems().catch(e=>toast(e.message,true)),180);});
  $("#transfer-map").addEventListener("click",()=>gm("mapTransfer",$("#map-id").value).catch(e=>toast(e.message,true)));
  $("#visit-world-map").addEventListener("click",()=>gm("mapTransfer",$("#world-map-select").value).catch(e=>toast(e.message,true)));
  $("#apply-free-roam").addEventListener("click",()=>gm("freeRoam",$("#free-roam").checked ? "1":"0").catch(e=>toast(e.message,true)));
  $("#set-speed").addEventListener("click",()=>gm("moveSpeed",$("#move-speed").value).catch(e=>toast(e.message,true)));
  $("#run-battle").addEventListener("click",async()=>{try{const result=await api("/api/battle",{monsterRefId:Number($("#monster-select").value),count:Number($("#battle-count").value)});$("#world-result").textContent=pretty(result);await refreshState();await refreshRuntime();}catch(e){toast(e.message,true);}});
  $("#protocol-search").addEventListener("input",renderProtocol);$("#protocol-command").addEventListener("change",updateProtocolPayload);
  $("#run-protocol").addEventListener("click",async()=>{try{const result=await api("/api/command",{id:Number($("#protocol-command").value),payload:JSON.parse($("#protocol-payload").value)});$("#protocol-result").textContent=pretty(result).slice(0,40000);if(app.runtimeReady && result.ok)await runtime().applyResult(result);await refreshState();await refreshRuntime();}catch(e){$("#protocol-result").textContent=e.message;toast(e.message,true);}});
  $("#export-save").addEventListener("click",async()=>{const response=await fetch("/api/export");const a=document.createElement("a");a.href=URL.createObjectURL(await response.blob());a.download=`${app.account.username}-offline.json`;a.click();});
  $("#import-save").addEventListener("click",()=>$("#import-file").click());
  $("#import-file").addEventListener("change",async event=>{try{const file=event.target.files[0];if(!file)return;const result=await api("/api/import",JSON.parse(await file.text()));if(result.ok===false)throw new Error(result.error?.message || "Import failed");await refreshState();await startRuntime({view:"main"});toast("Local save imported.");}catch(e){toast(e.message,true);}finally{event.target.value="";}});
  $("#reset-save").addEventListener("click",async()=>{if(!confirm(`Reset ${app.account.username}'s offline save to its starting state? Export it first if you want to keep it.`))return;try{await api("/api/reset",{});await refreshState();await startRuntime({view:"main"});toast("This captain's local save was reset.");}catch(e){toast(e.message,true);}});
  $("#refresh-diagnostics").addEventListener("click",()=>renderCoverage().catch(e=>toast(e.message,true)));
  $("#set-server-age").addEventListener("click",()=>gm("serverAge",$("#server-age").value).catch(e=>toast(e.message,true)));
  $("#toggle-tools").addEventListener("click",()=>$("#workspace").classList.toggle("tools-hidden"));
  $("#original-gm").addEventListener("click",()=>original("openGM").catch(e=>toast(e.message,true)));
  $("#open-original-gm").addEventListener("click",()=>original("openGM").catch(e=>toast(e.message,true)));
  $("#open-main").addEventListener("click",()=>original("openMain").catch(e=>toast(e.message,true)));
  $("#feature-select").addEventListener("change",event=>{if(event.target.value)original("openFeature",event.target.value).catch(e=>toast(e.message,true));event.target.value="";});
  $("#refresh-runtime").addEventListener("click",()=>refreshRuntime());$("#retry-runtime").addEventListener("click",startRuntime);
  window.addEventListener("message",event=>{
    if(event.origin!==location.origin || event.source!==frame.contentWindow || !event.data?.type)return;
    const {type,detail}=event.data;
    if(type==="pirate-runtime-status") {$("#runtime-status").textContent=detail.message;$("#runtime-detail").textContent=detail.message;log(detail.message);if(detail.ready){app.runtimeReady=true;$("#runtime-cover").hidden=true;}}
    else if(type==="pirate-runtime-error"){app.errors++;$("#runtime-error-count").textContent=`(${app.errors} diagnostics)`;log(detail.message,detail.detail);}
    else if(type==="pirate-runtime-network-blocked")log("Blocked non-local request",detail.url);
    else if(type==="pirate-runtime-reload")setTimeout(()=>startRuntime({view:detail.view}),100);
    else if(type==="pirate-english-status")log(`English display · ${detail.mappings} mapped phrases · ${detail.remainingUnique} untranslated strings in current view`,detail.remainingUnique ? detail.remaining : undefined);
    else if(type==="pirate-runtime-command" || type==="pirate-offline-state-changed") {
      clearTimeout(stateRefreshTimer);stateRefreshTimer=setTimeout(()=>refreshState().catch(()=>{}),180);
    }
  });
  api("/api/me").then(result=>{if(!app.account)return enter(result.account);}).catch(()=>{if(!app.account)$("#login-screen").hidden=false;});
  let worldStatusText="";
  setInterval(()=>{if(!app.runtimeReady || !runtime()?.getWorldStatus)return;const world=runtime().getWorldStatus();const value=`OFFLINE · SCENE ${world.sceneId || world.desiredSceneId || "LOADING"} · ${world.crewCount || 0} CREW ACTORS`;$("#client-mode").textContent=value;if(value!==worldStatusText){worldStatusText=value;log("World status",world);}},1500);
})();
