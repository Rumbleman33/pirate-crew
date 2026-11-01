(function () {
  "use strict";
  const CJK = /[\u3400-\u9fff\uf900-\ufaff]/;
  const CJK_RUN = /[\u3400-\u9fff\uf900-\ufaff]+/g;
  const DISPLAY_FIELDS = new Set(["text", "label", "labels", "prompt", "placeholder", "toolTip", "title", "headerLabels"]);
  const dictionary = Object.create(null);
  const cache = new Map();
  const leftovers = new Map();
  const metadata = { ready: false, sourceEntries: 0, parentEntries: 0, supplementalEntries: 0, mappings: 0, hooks: [], warnings: [] };
  let templates = [];
  let trie = Object.create(null);

  function englishSource(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value.translations || value.map || value : {};
  }

  async function readMap(path, required) {
    try {
      const response = await fetch(path, { credentials: "same-origin" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return englishSource(await response.json());
    } catch (error) {
      if (required) metadata.warnings.push(`English mapping ${path} unavailable: ${error.message}`);
      return {};
    }
  }

  function regexEscape(value) { return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
  function indexMaps() {
    templates = [];
    trie = Object.create(null);
    for (const [source, target] of Object.entries(dictionary)) {
      if (!CJK.test(source) || typeof target !== "string" || CJK.test(target)) continue;
      if (/^[\u3400-\u9fff\uf900-\ufaff]{2,28}$/.test(source) && target.length <= 110) {
        let node = trie;
        for (const char of source) node = node[char] || (node[char] = Object.create(null));
        node.$ = target;
      }
      if (source.length > 1000 || !/\{\d+\}|%[sd]/.test(source)) continue;
      const tokens = [];
      let cursor = 0, pattern = "^";
      for (const match of source.matchAll(/\{(\d+)\}|%([sd])/g)) {
        pattern += regexEscape(source.slice(cursor, match.index)) + "([\\s\\S]*?)";
        tokens.push(match[1] === undefined ? { type: "percent", token: match[0] } : { type: "brace", token: match[0], index: Number(match[1]) });
        cursor = match.index + match[0].length;
      }
      pattern += regexEscape(source.slice(cursor)) + "$";
      templates.push({ regex: new RegExp(pattern), target, tokens, source });
    }
    templates.sort((a, b) => b.source.length - a.source.length);
    metadata.mappings = Object.keys(dictionary).length;
    cache.clear();
  }

  function protectedIdentifier(value) {
    return /^(?:https?:\/\/|wss?:\/\/|(?:res|spine|icon|ui|ref[A-Za-z]*)\/)[^\s<>]+$/i.test(value)
      || /^\s*[\[{]/.test(value) && /"(?:command|generalId|refId|skinId|messageId|arg)"\s*:/.test(value);
  }

  function translateRun(value) {
    if (Object.prototype.hasOwnProperty.call(dictionary, value)) return dictionary[value];
    const result = [];
    for (let i = 0; i < value.length;) {
      let node = trie, end = i, match = null, consumed = i;
      while (end < value.length && (node = node[value[end]])) {
        end += 1;
        if (node.$) { match = node.$; consumed = end; }
      }
      if (match) { result.push(match); i = consumed; }
      else { result.push(value[i]); i += 1; }
    }
    return result.join(" ").replace(/([\u3400-\u9fff])\s+(?=[\u3400-\u9fff])/g, "$1");
  }

  function translatePlain(value) {
    if (Object.prototype.hasOwnProperty.call(dictionary, value)) return dictionary[value];
    const trimmed = value.trim();
    if (trimmed !== value && Object.prototype.hasOwnProperty.call(dictionary, trimmed)) return value.replace(trimmed, dictionary[trimmed]);
    const normalizedNewlines = value.replace(/\\n/g, "\n");
    if (normalizedNewlines !== value && Object.prototype.hasOwnProperty.call(dictionary, normalizedNewlines)) return dictionary[normalizedNewlines];
    for (const template of templates) {
      const match = template.regex.exec(value);
      if (!match) continue;
      const braces = new Map();
      const percents = [];
      template.tokens.forEach((token, i) => { if (token.type === "brace") braces.set(token.index, match[i + 1]); else percents.push(match[i + 1]); });
      let percent = 0;
      return template.target.replace(/\{(\d+)\}|%[sd]/g, (token, index) => index === undefined ? percents[percent++] ?? token : braces.get(Number(index)) ?? token);
    }
    // Chinese calendar output can contain variable dates absent from the packs.
    let result = value.replace(/(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日/g, (_, y, m, d) => `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`);
    result = result.replace(CJK_RUN, translateRun);
    return result;
  }

  function translate(value) {
    if (typeof value !== "string" || !CJK.test(value) || protectedIdentifier(value)) return value;
    if (cache.has(value)) return cache.get(value);
    let result;
    if (Object.prototype.hasOwnProperty.call(dictionary, value)) result = dictionary[value];
    else if (/<\/?[a-z][^>]*>/i.test(value)) {
      // Preserve markup, URLs, colors, asset attributes and IDs byte-for-byte.
      result = value.split(/(<[^>]*>)/g).map(part => part.startsWith("<") ? part : translatePlain(part)).join("");
    } else result = translatePlain(value);
    if (CJK.test(result)) {
      const visible = result.replace(/<[^>]*>/g, "");
      if (CJK.test(visible)) leftovers.set(visible, (leftovers.get(visible) || 0) + 1);
      if (leftovers.size > 1000) leftovers.delete(leftovers.keys().next().value);
    }
    if (cache.size > 6000) cache.clear();
    cache.set(value, result);
    return result;
  }

  function translateLayout(value, nodeType = "") {
    if (Array.isArray(value)) return value.map(item => translateLayout(item, nodeType));
    if (!value || typeof value !== "object") return value;
    const type = value.type || nodeType;
    const copy = {};
    for (const [key, entry] of Object.entries(value)) {
      if (typeof entry === "string" && DISPLAY_FIELDS.has(key)) {
        // Initial editable contents can be command templates or identifiers.
        copy[key] = key === "text" && /^(?:TextInput|Input|TextArea)$/.test(type) ? entry : translate(entry);
      } else copy[key] = translateLayout(entry, key === "props" ? type : "");
    }
    return copy;
  }

  function wrapSetter(proto, key, L, isHtml = false, skipInput = false) {
    if (!proto) return;
    const original = Object.getOwnPropertyDescriptor(proto, key);
    if (!original?.set || original.set.pirateEnglish) return;
    if (original.configurable === false) { metadata.warnings.push(`Cannot wrap non-configurable ${key} property`); return; }
    const setter = function (value) {
      const editable = skipInput && L.Input && this instanceof L.Input;
      return original.set.call(this, editable ? value : translate(value));
    };
    setter.pirateEnglish = true;
    Object.defineProperty(proto, key, { ...original, set: setter });
    const label = `${proto.constructor?.name || "Laya"}.${key}${isHtml ? " (markup preserved)" : ""}`;
    if (!metadata.hooks.includes(label)) metadata.hooks.push(label);
  }

  function visitStage(L, mutate = false) {
    const stack = L?.stage ? [L.stage] : [];
    const seen = new Set();
    const remaining = new Map();
    let visited = 0, translated = 0, displayStrings = 0;
    while (stack.length && visited < 50000) {
      const node = stack.pop();
      if (!node || node.destroyed || seen.has(node)) continue;
      seen.add(node); visited += 1;
      const editable = L.Input && node instanceof L.Input;
      for (const key of ["text", "innerHTML", "prompt"]) {
        if (editable && key !== "prompt") continue;
        let value;
        try { value = node[key]; } catch (_) { continue; }
        if (typeof value !== "string" || !value.length) continue;
        displayStrings += 1;
        if (mutate) {
          const result = translate(value);
          if (result !== value) { try { node[key] = result; value = result; translated += 1; } catch (_) { /* Report below instead. */ } }
        }
        const visible = key === "innerHTML" ? value.replace(/<[^>]*>/g, "") : value;
        if (CJK.test(visible)) remaining.set(visible, (remaining.get(visible) || 0) + 1);
      }
      for (let i = 0; i < Number(node.numChildren || 0); i += 1) {
        try { stack.push(node.getChildAt(i)); } catch (_) { /* Destroyed between frames. */ }
      }
    }
    return { scope: "original-rendered-stage", visitedNodes: visited, displayStrings, translatedStrings: translated,
      remainingUnique: remaining.size, remainingOccurrences: Array.from(remaining.values()).reduce((a, b) => a + b, 0),
      remaining: Array.from(remaining, ([text, count]) => ({ text, count })).slice(0, 150) };
  }

  function install(L = window.Laya, req = window.__pirateRequire) {
    if (!L) return { installed: false, reason: "Original engine not loaded" };
    L.Text.langPacks = { ...(L.Text.langPacks || {}), ...dictionary };
    wrapSetter(L.Text?.prototype, "text", L, false, true);
    wrapSetter(L.Input?.prototype, "prompt", L);
    wrapSetter(L.HTMLDivElement?.prototype, "innerHTML", L, true);
    const helpersReady = typeof window.net === "object" && typeof Object.getOwnPropertyDescriptor(Function.prototype, "it")?.get === "function";
    if (req && metadata.ready && helpersReady) {
      try {
        const language = req(14).LangMgr.it;
        if (language) {
          language.saveLangType("en");
          if (!language.translate.pirateEnglish) {
            const original = language.translate;
            const wrapped = function (value) { return translate(original.call(this, value)); };
            wrapped.pirateEnglish = true;
            language.translate = wrapped;
          }
        }
        const proto = req(366).GMTest.prototype;
        if (!proto.onSelectCmd.pirateEnglish) {
          const original = proto.onSelectCmd;
          const wrapped = function (index) {
            const result = original.call(this, index);
            if (this.view?.lblInput?.text === "guildAuction:<交易ID>") this.view.lblInput.text = "guildAuction:<tradeId>";
            return result;
          };
          wrapped.pirateEnglish = true;
          proto.onSelectCmd = wrapped;
        }
      } catch (error) {
        // Before bootstrap, singleton helpers are not yet installed. The next
        // runtime status event installs these hooks after original OWUi setup.
        if (!/saveLangType|undefined|null|\.it|\.re/.test(error.message)) metadata.warnings.push(error.message);
      }
    }
    if (window.moment?.locale) window.moment.locale("en");
    const audit = visitStage(L, true);
    return { installed: true, ...metadata, ...audit };
  }

  function announce() {
    const detail = { ...metadata, ...visitStage(window.Laya, false) };
    window.dispatchEvent(new CustomEvent("pirate-english-status", { detail }));
    if (parent !== window) parent.postMessage({ type: "pirate-english-status", detail }, location.origin);
    return detail;
  }

  const ready = Promise.all([
    readMap("/game/i18n/en.json", true), readMap("/english-extra.json", false), readMap("/offline-english-extra.json", true),
  ]).then(([source, parentExtra, supplemental]) => {
    metadata.sourceEntries = Object.keys(source).length;
    metadata.parentEntries = Object.keys(parentExtra).length;
    metadata.supplementalEntries = Object.keys(supplemental).length;
    for (const map of [source, parentExtra, supplemental]) {
      for (const [key, value] of Object.entries(map)) if (typeof value === "string") dictionary[key] = value;
    }
    for (const key of Object.keys(dictionary)) if (dictionary[dictionary[key]] && dictionary[key] !== key) dictionary[key] = dictionary[dictionary[key]];
    indexMaps();
    metadata.ready = true;
    install();
    announce();
    return { ...metadata };
  });

  window.PirateOfflineEnglish = { ready, install, translate, translateLayout,
    audit: () => ({ ...metadata, ...visitStage(window.Laya, false) }),
    getLeftovers: () => Array.from(leftovers, ([text, count]) => ({ text, count })).sort((a, b) => b.count - a.count) };
  window.addEventListener("pirate-runtime-status", event => {
    if (!metadata.ready) return;
    install();
    if (event.detail?.ready) { announce(); setTimeout(announce, 1200); }
  });
})();
