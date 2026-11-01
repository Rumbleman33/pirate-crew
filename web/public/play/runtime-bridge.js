(function () {
  "use strict";
  if(parent!==window)document.body.classList.add("embedded");

  const nativeFetch = window.fetch.bind(window);
  const diagnostics = [];
  const initializedReads = new Map();
  const state = { ready: false, starting: null, account: null, initialized: false, missingAssets: [], unsupported: [], networkBlocked: [] };
  const gameBase = new URL("/game/", location.href).href;
  let req, L, net, facade, transport, schemas;
  const responseNames = new Map();
  let refreshing = false;

  function publish(type, detail) {
    const event = { type, detail };
    window.dispatchEvent(new CustomEvent(type, { detail }));
    if (parent !== window) parent.postMessage(event, location.origin);
  }

  function status(message, phase = "loading") {
    state.phase = phase;
    state.message = message;
    publish("pirate-runtime-status", { phase, message, ready: state.ready });
    const panel = document.getElementById("runtime-message");
    if (panel && phase !== "ready") {
      panel.hidden = false;
      panel.querySelector("p").textContent = message;
    }
  }

  function problem(message, extra) {
    const item = { message: String(message), detail: extra || null, at: new Date().toISOString() };
    diagnostics.push(item);
    if (diagnostics.length > 100) diagnostics.shift();
    publish("pirate-runtime-error", item);
    console.warn("[Pirates offline]", message, extra || "");
    return item;
  }

  function allowedUrl(value) {
    const url = new URL(typeof value === "string" ? value : value?.url || String(value), location.href);
    if (url.protocol === "data:") return url;
    if (url.origin !== location.origin) {
      const item = { url: url.origin + url.pathname, at: new Date().toISOString() };
      state.networkBlocked.push(item);
      publish("pirate-runtime-network-blocked", item);
      throw new Error("Offline client blocked external network destination: " + url.origin);
    }
    return url;
  }

  // Defense in depth: the iframe CSP also excludes every remote destination.
  window.fetch = function (resource, options) { allowedUrl(resource); return nativeFetch(resource, options); };
  const xhrOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    allowedUrl(url);
    return xhrOpen.call(this, method, url, ...rest);
  };
  const NativeWebSocket = window.WebSocket;
  window.WebSocket = class OfflineWebSocket extends NativeWebSocket {
    constructor(url, protocols) {
      const parsed = new URL(url, location.href);
      if (parsed.host !== location.host) throw new Error("Offline client blocked an external WebSocket");
      super(url, protocols);
    }
  };
  if (navigator.sendBeacon) navigator.sendBeacon = function (url) { allowedUrl(url); return false; };
  window.addEventListener("error", function (event) {
    const target = event.target;
    if (target && target !== window && (target.src || target.href)) {
      const url = target.src || target.href;
      state.missingAssets.push(url);
      problem("Original client asset did not load", { url });
    }
    else if (event.error) problem("Original client error", event.error.stack || event.message);
  }, true);
  window.addEventListener("unhandledrejection", event => problem("Original client promise rejected", String(event.reason?.stack || event.reason)));

  async function api(path, body) {
    const response = await nativeFetch(path, {
      credentials: "same-origin",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      method: body === undefined ? "GET" : "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data;
    try { data = await response.json(); } catch { throw new Error(`Local API ${path} returned HTTP ${response.status} without JSON`); }
    if (!response.ok || data.ok === false) {
      const error = new Error(typeof data.error === "string" ? data.error : data.error?.message || data.message || `Local command unavailable (HTTP ${response.status})`);
      error.capability = data.capability;
      error.code = data.errorCode || data.error?.code;
      throw error;
    }
    return data;
  }

  async function localCommand(id, payload) {
    const code = Number(id);
    const data = code === 70000
      ? await api("/api/gm", { command: payload?.command || "", arg: payload?.arg || "" })
      : await api("/api/command", { id: code, payload: payload || {} });
    return data;
  }

  function responseType(id) { return req(501).CmdProto[String(id)]?.[1]; }
  function encodePayload(name,data,writer=window.protobuf.Writer.create()) {
    for(const f of schemas[name]?.fields||[]){
      const raw=data?.[f.name];if(raw===undefined&&!f.required)continue;
      for(let value of (f.repeated?(Array.isArray(raw)?raw:[]):[raw])){
        const wire=['message','string','bytes'].includes(f.type)?2:['double','fixed64','sfixed64'].includes(f.type)?1:['float','fixed32','sfixed32'].includes(f.type)?5:0;
        writer.uint32((f.number<<3)|wire);
        if(f.type==='message')encodePayload(f.message,value||{},writer.fork()).ldelim();
        else writer[f.type](value??(f.type==='string'?'':f.type==='bytes'?[]:f.type==='bool'?false:0));
      }
    }
    return writer;
  }
  function offlinePayload(reply){
    if(!reply?._offlinePayload)return reply;
    const {_offlinePayload:p,...body}=reply;
    if(!['CmdSettlementStage','CmdSettlementBrawl'].includes(p.schema))throw Error('Unknown local settlement payload.');
    body[p.field||'settlementData']=encodePayload(p.schema,p.value).finish();
    return body;
  }
  function encodeResponse(id, reply) {
    reply=offlinePayload(reply);
    const type = responseType(id);
    if (!type) return new Uint8Array();
    if (typeof type.encode === "function") return type.encode(reply || {}).finish();
    let name = responseNames.get(type);
    if (!name) { name = Object.keys(net).find(key => net[key] === type); responseNames.set(type, name); }
    // Empty response messages are omitted by the captured metadata extractor.
    // Their original decoder accepts empty bytes; required-field decoders still
    // reject missing schemas explicitly rather than accepting invented data.
    if (!name || !schemas[name]) return new Uint8Array();
    function encode(name, data, writer) {
      for (const field of schemas[name]?.fields || []) {
        const raw = data?.[field.name];
        if (raw === undefined && !field.required) continue;
        const values = field.repeated ? (Array.isArray(raw) ? raw : []) : [raw];
        for (let value of values) {
          const wire = field.type === "message" || field.type === "string" || field.type === "bytes" ? 2 : field.type === "double" || /^(s?fixed64)$/.test(field.type) ? 1 : field.type === "float" || /^(s?fixed32)$/.test(field.type) ? 5 : 0;
          writer.uint32((field.number << 3) | wire);
          if (field.type === "message") encode(field.message, value || {}, writer.fork()).ldelim();
          else {
            if (value === undefined || value === null) value = field.type === "string" ? "" : field.type === "bytes" ? [] : field.type === "bool" ? false : 0;
            writer[field.type](value);
          }
        }
      }
      return writer;
    }
    return encode(name, reply || {}, window.protobuf.Writer.create()).finish();
  }
  function normalize(id, reply) {
    const type = responseType(id);
    if (!type) return reply || {};
    return type.decode(encodeResponse(id, reply));
  }
  let lastAppliedRevision=0;
  function staleResult(result){return Number(result.revision||0)>0&&Number(result.revision)<lastAppliedRevision;}
  function emitBroadcasts(result) {
    if(staleResult(result))return false;
    lastAppliedRevision=Math.max(lastAppliedRevision,Number(result.revision||0));
    document.body.dataset.offlineRevision=String(lastAppliedRevision);
    for (const broadcast of result.broadcasts || []) {
      try { transport.event(String(broadcast.id), normalize(broadcast.id, broadcast.data)); }
      catch (error) { problem(`Local broadcast ${broadcast.id} could not update the original client`, error.message); }
    }
    publish("pirate-offline-state-changed", { capability: result.capability || null });
    return true;
  }

  function applyClientAction(action) {
    if (!action || !state.ready) return;
    try {
      if(action.type==='bossPractice'){
        openMain();const args=req(82).InsArg.argInsIdLv(201,1);args.insRef={...args.insRef,cost:'',time:-1,timeType:0};args.offlineBossPractice=true;args.leaveConfirm=false;
        state.practiceUid=action.data.uid;args.practiceGeneralIds=action.generalIds;args.practiceName=action.name;
        facade.sendNotification(req(6).NotifyName.MapInsOpen,args);return;
      }
      const flags = req(18).default;
      if (action.type === "assetPreview") {
        req(15).ViewMgr.it.popByName("GMTest");
        req(15).ViewMgr.it.push(req(1191).GmSpineView, {character:1,monster:2,projectile:3}[action.category] || 1);
      } else if (action.type === "hide") {
        flags.hideMainViewUI = action.hidden;
        facade.eventAll(req(6).NotifyName.HideMainViewUI);
      } else if (action.type === "LayaGC") L.Resource.destroyUnusedResources();
      else if (action.type === "moveSpeed") flags.gmMoveSpeedRate = action.value;
      else if (action.type === "freeRoam") {
        state.freeRoam = action.enabled;
        publish("pirate-runtime-reload", {reason:"Exploration settings updated"});
      }
      else if (action.type === "rebirthAll") facade.sendNotification(req(6).NotifyName.MapActorAllRebirthDebug);
      else if (action.type === "stageFb") req(15).ViewMgr.it.push(req(445).MazeDialog, action.refId);
      else if (action.type === "mapTransfer") {
        // Re-enter from the saved destination so an instance exit animation or
        // stale SceneProxy initializer cannot overwrite a GM teleport.
        publish("pirate-runtime-reload", {reason:"Traveling to the selected island", view:"main"});
      } else if (action.type === "instanceLevel") {
        const instance = req(37).InsProxy.re.getInsVO(action.refId);
        if (instance) instance.lv = action.level;
      } else if (action.type === "serverAge") {
        req(309).LoginGameProxy.re._openServerTime = action.openServerTime;
        req(20).C_Player.openServerTime = action.openServerTime;
        facade.eventAll(req(6).NotifyName.HourRefresh || "OfflineWorldAgeChanged");
      } else if (action.type === "addMonster") {
        const scene = req(64).SceneMgr.it.curSceneObj;
        if (!scene) {problem("Monster state saved; open a loaded local map to render its actors");return;}
        for (const monster of action.monsters) {
          const ref = req(71).MonsterRefMgr.it.getMonsterRef(monster.refId);
          const point = new (req(65).ScenePos)(monster.x, monster.y);
          const actor = req(140).SpriteFactory.createMonster(scene.ref, ref, point);
          actor.setPos(point.x, point.y);actor.enterScene(scene);actor.addTo(req(42).MapFacade.it.objLayer);actor.changeState(req(13).EActorState.Idle);
        }
      }
    } catch (error) {problem("Local visual action requires more client state", error.stack || error.message);}
  }

  function applyResult(result) {if(emitBroadcasts(result)!==false)applyClientAction(result.clientAction);}

  async function aggregate(payload) {
    const data = [];
    for (const id of payload.cmdCode || []) {
      const result = await localCommand(Number(id), {});
      const type = responseType(id);
      if (!type) throw new Error(`Original response schema missing for command ${id}`);
      data.push({ cmdCode: Number(id), data: encodeResponse(id, result.reply) });
      emitBroadcasts(result);
    }
    return { data };
  }

  function installTransport() {
    const Network = req(26).default;
    Network.prototype.connect = async function () { this._netStatus = 1; return true; };
    Network.prototype.disconnect = function () { this._netStatus = 0; };
    Network.prototype.send = async function (id, payload) {
      const code = Number(id);
      if (code === 1024) return aggregate(payload || {});
      try {
        const result = await localCommand(code, payload);
        applyResult(result);
        const reply = normalize(code, result.reply);
        if (code === 70000 && state.ready) await refreshOriginalData();
        return reply;
      } catch (error) {
        problem(`Offline command ${code}: ${error.message}`, { capability: error.capability || "unsupported" });
        throw error;
      }
    };
    transport = Network.it;
    transport._netStatus = 1;
  }

  function silenceLiveServices() {
    const log = req(154).LogEventMgr;
    for (const name of ["sendClientEvent", "sendClientEventAppStart", "sendLogEvent", "sendLog", "report"]) {
      if (typeof log?.[name] === "function") log[name] = function () {};
    }
    const Http = req(308).Http;
    if (Http) {
      Http.post = async function (url) { throw new Error("The offline runtime does not use live HTTP services: " + String(url).split("?")[0]); };
      if (Http.get) Http.get = Http.post;
    }
    const Pay = req(49).PayProxy;
    if (Pay?.prototype) Pay.prototype.requestPayProducts = async function () { return []; };
  }

  async function fetchJson(path, required = true) {
    const response = await nativeFetch(path, { credentials: "same-origin" });
    if (!response.ok) {
      state.missingAssets.push(path);
      if (required) throw new Error(`Missing original client file ${path} (HTTP ${response.status})`);
      return null;
    }
    return response.json();
  }

  function waitForHandler(start, description, timeout = 18000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(description + " timed out; check missing local asset diagnostics")), timeout);
      try { start(() => { clearTimeout(timer); resolve(); }); } catch (error) { clearTimeout(timer); reject(error); }
    });
  }

  function offlineConfiguration() {
    return {
      resourcesUpdateConfig: { verName: "offline" },
      gameConfig: { appName: "Pirates Offline", productCode: "hw_en", userType: 20,
        channelPackCode: "offline", partitionKey: "offline", smallChannelSimpleName: "offline",
        bridgeUrl: "/offline/", channelJsonConfigs: { clientPath: gameBase, refFlag: "En", langType: "en", openGMChat: "OFFLINE_GM", openLog: "0", openDownloadZip: "0" } },
    };
  }

  async function loadOriginalResources() {
    status("Loading original UI layouts and local reference tables…");
    if (window.PirateOfflineEnglish) await window.PirateOfflineEnglish.ready;
    const [preui, ui, availableVersion, translations, replacement] = await Promise.all([
      fetchJson("/game/preui.json"), fetchJson("/game/ui.json"), fetchJson("/game/version.json"),
      fetchJson("/game/i18n/en.json", false), fetchJson("/game/en_replace.json", false),
    ]);
    // The shipped debug layout references an obsolete standalone texture.
    // Its original atlas frame is available in the captured UI atlas.
    function repairDebugSkins(value) {
      if (typeof value === "string") return value === "single/uncompression/jgg_05.png" ? "ui/jgg/jgg_05.png" : value;
      if (Array.isArray(value)) return value.map(repairDebugSkins);
      if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, repairDebugSkins(child)]));
      return value;
    }
    L.View.uiMap = Object.assign({}, preui, repairDebugSkins(ui));
    if (window.PirateOfflineEnglish) L.View.uiMap = window.PirateOfflineEnglish.translateLayout(L.View.uiMap);
    if (translations) L.Text.langPacks = translations;
    if (replacement) req(233).OWUi.version = replacement;
    if (availableVersion) {
      await waitForHandler(done => L.ResourceVersion.enable("/game/version.json", L.Handler.create(null, done), L.ResourceVersion.FILENAME_VERSION), "Local asset version map");
    }
    await waitForHandler(done => L.AtlasInfoManager.enable("/game/fileconfig.json", L.Handler.create(null, done)), "Original texture atlas map");
    const Ref = req(29).default;
    Ref.refFlag = "En";
    Ref.nRefCount = { countEn: 10 };
    await Ref.it.loadPreRef();
    await Ref.it.loadMainRef();
    if (!Ref.it.isLoadMainRef) throw new Error("Original reference tables did not finish loading");
    const language = req(14).LangMgr.it;
    language.saveLangType("en");
    // Mirror LoginCmd.ResVerActiveEnd without invoking its live SDK bootstrap.
    req(5).default.brief = req(5).default.briefEN;
    window.PirateOfflineEnglish?.install(L, req);
    const fonts = req(156).default;
    fonts.init();
    status("Loading the original game fonts…");
    await fonts.loadBMFonts();
    await fonts.preloadTTF();
  }

  function collectInitializers() {
    initializedReads.clear();
    const proxies = facade.model.proxyMap;
    for (const name of Object.keys(proxies)) {
      const proxy = proxies[name];
      let entries;
      try { entries = proxy.getInitReqFns(); } catch (error) { problem(`Original proxy ${name} initialization lookup failed`, error.message); continue; }
      if (!entries) continue;
      for (const entry of Array.isArray(entries) ? entries : [entries]) {
        if (entry?.cmdCode && typeof entry.fn === "function") initializedReads.set(Number(entry.cmdCode), { name, fn: entry.fn });
      }
    }
    // Voyage has no recovered startup initializer, although the captain level
    // cap and One Piece window both read its cached title and objective map.
    initializedReads.set(2100,{name:'VoyageProxy',fn:reply=>{
      const proxy=req(193).VoyageProxy.re;
      proxy._title=Number(reply.title)||1;proxy._taskDict.clear();proxy.setTasks(reply.tasks||[]);
      proxy.sendNotification(req(7).CmdCode.VoyageInfo);
    }});
  }

  async function refreshOriginalData() {
    if (refreshing) return;
    refreshing = true;
    try {
      for (const [id, initializer] of initializedReads) {
        try {
          const result = await localCommand(id, {});
          if(staleResult(result))continue;
          // A full gem snapshot replaces slots, including slots now empty.
          if(Number(id)===1350)req(79).EquipProxy.re._equipDict.clear();
          if(Number(id)===2700)req(161).MountProxy.re._mountDict.clear();
          if(Number(id)===10100)req(162).GemProxy.re._gemSlotInfoDict.clear();
          initializer.fn(normalize(id, result.reply));
          emitBroadcasts(result);
        } catch (error) {
          if (!state.unsupported.some(item => item.id === id)) state.unsupported.push({ id, proxy: initializer.name, message: error.message });
          problem(`Original ${initializer.name} data ${id} unavailable`, error.message);
        }
      }
      // Equipment snapshots replace native VOs; repaint slot widgets after the
      // replacement so workbench equips cannot leave a stale empty slot.
      if(state.ready)facade.sendNotification(req(7).CmdCode.EquipDress);
      if(state.ready){
        facade.sendNotification(req(7).CmdCode.UniqueInfo);
        facade.sendNotification(req(7).CmdCode.TalentActive);
        facade.sendNotification(req(7).CmdCode.TalentAdvanceActive);
        facade.sendNotification(req(7).CmdCode.MountStageUp);
      }
    } finally { refreshing = false; }
  }

  function openGM() {
    if (!state.ready) throw new Error("Original client is still loading");
    req(15).ViewMgr.it.popAllWithoutMainUI();
    req(15).ViewMgr.it.push(req(366).GMTest);
    return { opened: "GMTest" };
  }

  function openFeature(name, args) {
    if (!state.ready) throw new Error("Original client is still loading");
    const value = typeof name === "number" ? name : req(3).EFnId[name];
    if (value === undefined) throw new Error(`Original feature ${name} is not in EFnId`);
    req(15).ViewMgr.it.popByName("GMTest");
    const ids=req(3).EFnId, notify=req(6), jump=req(420).JumpFnVO;
    // Character detail tabs have no standalone command. Open their original
    // parent view with the requested tab and a valid owned character.
    const roleTabs=[ids.Level,ids.Star,ids.Equip,ids.Skill,ids.Gem,ids.Potential,ids.Unique];
    if(roleTabs.includes(Number(value))){
      const proxy=req(35).GeneralProxy.re;
      const generalId=Number(args?.generalId||args||proxy.curSelect||proxy.getGenerals(true)[0]?.generalId||Object.keys(state.snapshot.generals)[0]);
      req(15).ViewMgr.it.popByName("GeneralRole");
      req(15).ViewMgr.it.push(req(1870).GeneralRole,jump.create(Number(value),generalId));
      return {feature:name,id:Number(value),generalId};
    }
    let parentId=Number(value);const visited=new Set();
    while(!facade.hasCommand(notify.getOpenName(parentId))&&!visited.has(parentId)){
      visited.add(parentId);const parent=req(52).default.it.getFnRef(parentId)?.parentId;
      if(!parent)throw new Error(`Feature ${name} has no captured standalone window.`);
      parentId=Number(parent);
    }
    // Preserve the original child JumpFnVO so the parent selects its proper tab.
    facade.sendNotification(notify.getOpenName(parentId),jump.create(Number(value),args));
    return { feature: name, id: Number(value), parentId };
  }

  function getFeatures() {
    if (!state.ready) return [];
    return Object.entries(req(3).EFnId).filter(([name, id]) => !/^\d+$/.test(name) && /^\d+$/.test(String(id))).filter(([,id])=>Number(id)!==4900).map(([name, id]) => ({name, id:Number(id)}));
  }

  function getWorldStatus() {
    if (!state.ready) return {phase:"loading"};
    const manager=req(64).SceneMgr.it, scene=manager.curSceneObj;
    return {sceneId:manager.curScene, mapId:manager.curMapId, desiredSceneId:req(62).SceneProxy.re.transfer?.toSceneId, crewCount:scene?.myActors?.length || 0, monsterCount:scene?.monsters?.size() || 0};
  }

  function leaveViews(all) {
    if (!state.ready) throw new Error("Original client is still loading");
    const views=req(15).ViewMgr.it;
    const candidates=(views._mediators||[]).slice().reverse().filter(v=>v.getMediatorName()!==req(362).MainView.NAME);
    for(const view of (all?candidates:candidates.slice(0,1))){
      const name=view.getMediatorName(), index=views._mediators.indexOf(view);
      if(index>=0)views._mediators.splice(index,1);
      try{view.removeTween?.();views.onPopCompleted(view);}
      catch(error){
        // A partially initialized native window must never trap the captain.
        try{view.getViewComponent()?.removeSelf();}catch{}
        try{facade.removeMediator(name);}catch{}
        problem(`Closed incomplete ${name} window`,error.message);
      }
    }
    const top=views.getTop();
    if(top){top.setVisible(true);const node=top.getViewComponent();if(node)node.mouseEnabled=true;}
    views._isPop=false;views.clearLoading();views.adjustMask();
    return {opened:top?.getMediatorName()||"MainView"};
  }
  function stopPractice(){if(state.practiceUid){const uid=state.practiceUid;state.practiceUid=null;api('/api/gm',{command:'endBossPractice',arg:String(uid)}).catch(error=>problem('Practice exit',error.message));}}
  function goBack(){if(state.practiceUid)return openMain();return leaveViews(false);}
  function openMain() {
    const practice=(req(15).ViewMgr.it._mediators||[]).find(view=>view._args?.offlineBossPractice);
    if(practice)return practice.__practiceLeave?practice.__practiceLeave():practice.insSettle(false,'leave');
    stopPractice();
    window.PirateCombatTools?.stopChallenge();
    leaveViews(true);
    if (!req(15).ViewMgr.it.getMediator(req(362).MainView.NAME)) facade.sendNotification(req(6).NotifyName.OpenMainView);
    return { opened: "MainView" };
  }

  function startChallenge(team,name){if(!state.ready)throw Error('Original client is still loading');return window.PirateCombatTools.startChallenge(team,name,normalize);}

  async function boot(accountInfo) {
    if(accountInfo?.localSession)await window.PirateBrowserSession.bind(accountInfo.localSession);
    state.account = accountInfo || null;
    if (!window.Laya || typeof window.__pirateRequire !== "function") throw new Error("Prepared original game scripts did not load. Run tools/prepare_runtime.py and verify /game/library.js and /game/bundle-offline.js.");
    req = window.__pirateRequire;
    L = window.Laya;
    const snapshot = await api("/api/me/snapshot");
    if(snapshot.activeInstance?.practice)await api('/api/gm',{command:'endBossPractice',arg:String(snapshot.activeInstance.data.uid)});
    schemas = await api("/api/schemas");
    state.snapshot = snapshot;
    state.freeRoam = snapshot.settings?.freeRoam !== false;
    status("Starting the recovered LayaAir browser engine…");
    req(836);
    net = window.net;
    req(838);
    req(2277).OverWrite.register();
    req(131).default.init();
    const flags = req(18).default;
    const config = offlineConfiguration();
    flags.allConfig = config;
    flags.isLocal = true;
    flags.enableGuide = false;
    flags.enableNotice = false;
    flags.openBeLog = false;
    flags.hasAd = false;
    flags.hideRecharge = true;
    flags.enableKtx = false;
    const query = new URL(location.href);
    query.searchParams.set("productCode", "hw_en");
    query.searchParams.set("channelId", "offline");
    query.searchParams.set("lang", "en");
    query.searchParams.delete("verType");
    history.replaceState(null, "", query);
    req(81).default.init();
    flags.isLocal = true;
    L.URL.basePath = gameBase;
    L.SoundManager.muted = true;
    installTransport();
    silenceLiveServices();
    facade = req(11).AppFacade.it;
    // Match the original startup order: views can consult registered proxies.
    new (req(1616).BootstrapCommands)().execute();
    new (req(1598).BootstrapModels)().execute();
    req(195).default.it.init();
    req(15).ViewMgr.it.init();
    await loadOriginalResources();
    const login = req(57).LoginProxy.re;
    login.allConfig = config;
    login._loginCheck = { resultCode: 1, serverSign: "offline", loginCheckTime: Date.now() };
    status("Loading the offline player into the original client…");
    const loginResult = await localCommand(1001, { clientVO: { serverId: 1, openId: "offline", userType: 20 } });
    const playerReply = normalize(1001, loginResult.reply);
    if (!playerReply.player) throw new Error("Local PlayerLogin response has no original CmdPlayerVO; original UI cannot be initialized");
    req(309).LoginGameProxy.re.onRegRspAndLoginRsp(playerReply);
    collectInitializers();
    await refreshOriginalData();
    flags.isEnterGame = true;
    state.initialized = true;
    state.ready = true;
    window.PirateCombatTools?.install(req,publish,api);
    window.PirateTestingUI?.install(req,api,publish,normalize);
    state.playerId = String(playerReply.playerId || playerReply.player?.playerId || "offline");
    // The original startup normally creates MainView before any debug dialog.
    // Preserve that root order so scene/crew loading continues behind the GM UI.
    req(183).default.prototype.tipsOpen = function () {};
    req(1220).LoginDialogMgr.it.launch = function () {};
    req(561).PrivilegeTempDialogMgr.it.launch = function () {};
    const npc = req(163).SceneNpc.prototype;
    const isWorldRoute = obj => state.freeRoam && obj.ref && Number(obj.ref.sceneId) > 0 && Number(obj.ref.sceneId) < 100 && [1,2,5,6,7].includes(Number(obj.ref.type));
    const taskGate = Object.getOwnPropertyDescriptor(npc, "mainTaskCmp");
    if (taskGate?.get && !npc.__offlineRoam) {
      Object.defineProperty(npc, "mainTaskCmp", {...taskGate, get:function(){return isWorldRoute(this) ? true : taskGate.get.call(this);}});
      const originalCheck = npc.checkCanUse;
      npc.checkCanUse = function(...args) {
        if (isWorldRoute(this)) {this._canUse=true;this.showName();this.handleEvent(false);return;}
        return originalCheck.apply(this,args);
      };
      npc.__offlineRoam = true;
    }
    // Free-roam NPC unlocks also satisfy the client's automatic town selector.
    // Honor the saved world destination for this first scene only; subsequent
    // normal return-to-town actions keep the original selector.
    const savedScene = Number(snapshot.scene?.mapId);
    if (savedScene > 0 && savedScene < 100) {
      Object.defineProperty(req(62).SceneProxy.re, "enterSceneId", {configurable:true, get:function(){delete this.enterSceneId;return savedScene;}});
    }
    openMain();
    if (new URL(location.href).searchParams.get("bootView") !== "main") openGM();
    document.getElementById("runtime-message").hidden = true;
    status(`Original GM panel ready · ${initializedReads.size} original data initializers · ${state.unsupported.length} unavailable`, "ready");
    return { ready: true, playerId: state.playerId, initializationCommands: Array.from(initializedReads.keys()), unsupported: state.unsupported };
  }

  async function start(accountInfo) {
    if (state.ready) return { ready: true, playerId: state.playerId };
    if (!state.starting) {
      state.starting = boot(accountInfo).catch(error => {
        state.ready = false;
        state.starting = null;
        status(error.message, "error");
        const node = document.getElementById("runtime-error");
        if (node) node.textContent = error.stack || error.message;
        problem("Original client could not start", error.stack || error.message);
        throw error;
      });
    }
    return state.starting;
  }

  window.PirateOfflineRuntime = { start, openGM, openFeature, openMain, finishPractice:stopPractice, goBack, startChallenge, refresh: refreshOriginalData, applyResult, getFeatures, getWorldStatus,
    getStatus: () => ({ ...state, snapshot: undefined, starting: Boolean(state.starting), diagnostics: diagnostics.slice() }) };
  document.getElementById("runtime-gm")?.addEventListener("click", () => { try { openGM(); } catch (error) { problem(error.message); } });
  document.getElementById("runtime-main")?.addEventListener("click", () => { try { openMain(); } catch (error) { problem(error.message); } });
  document.getElementById("runtime-back")?.addEventListener("click",()=>{try{goBack();}catch(error){problem(error.message);}});
  window.addEventListener("keydown",event=>{if(event.key==="Escape"&&state.ready){event.preventDefault();try{goBack();}catch(error){problem(error.message);}}});
  publish("pirate-runtime-status", { phase: "waiting", message: "Original runtime scripts loaded; waiting for a local account", ready: false });
})();
