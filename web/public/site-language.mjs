/** Whole-document translation. Provider work stays local when the browser supports Translator.
 * Other browsers require an explicitly configured provider; the default makes no text uploads.
 * An optional provider implements create({sourceLanguage,targetLanguage}) -> {translate(text),destroy?}.
 */
export const LANGUAGES = Object.freeze([
  ['en','English'],['es','Español'],['pt','Português'],['fr','Français'],
  ['de','Deutsch'],['tr','Türkçe'],['id','Bahasa Indonesia'],['vi','Tiếng Việt'],
  ['ru','Русский'],['ar','العربية'],['zh','中文（简体）'],
]);
// These authored labels make navigation usable even without an automatic translator.
export const NAV_TRANSLATIONS = Object.freeze({
  es:['Inicio','Jugar','Biblioteca de guías','Personajes','Planificador de mejoras','Tesoros y mascotas','Atlas del mundo','Tablas de referencia','Fuentes','Idioma','Restaurar inglés'],
  pt:['Início','Jogar','Biblioteca de guias','Personagens','Planejador de melhorias','Tesouros e mascotes','Atlas do mundo','Tabelas de referência','Fontes','Idioma','Restaurar inglês'],
  fr:['Accueil','Jouer','Bibliothèque de guides','Personnages','Planificateur des améliorations','Trésors et familiers','Atlas du monde','Tableaux de référence','Sources','Langue','Rétablir l’anglais'],
  de:['Startseite','Spielen','Anleitungen','Charaktere','Verbesserungsplaner','Schätze und Begleiter','Weltatlas','Referenztabellen','Quellen','Sprache','Englisch wiederherstellen'],
  tr:['Ana sayfa','Oyna','Rehber kütüphanesi','Karakterler','Geliştirme planlayıcısı','Hazineler ve evcil hayvanlar','Dünya atlası','Referans tabloları','Kaynaklar','Dil','İngilizceye dön'],
  id:['Beranda','Main','Perpustakaan panduan','Karakter','Perencana peningkatan','Harta dan peliharaan','Atlas dunia','Tabel referensi','Sumber','Bahasa','Kembali ke bahasa Inggris'],
  vi:['Trang chủ','Chơi','Thư viện hướng dẫn','Nhân vật','Lập kế hoạch nâng cấp','Kho báu và thú cưng','Bản đồ thế giới','Bảng tham khảo','Nguồn','Ngôn ngữ','Khôi phục tiếng Anh'],
  ru:['Главная','Играть','Библиотека руководств','Персонажи','Планировщик улучшений','Сокровища и питомцы','Атлас мира','Справочные таблицы','Источники','Язык','Вернуть английский'],
  ar:['الرئيسية','العب','مكتبة الأدلة','الشخصيات','مخطط الترقيات','الكنوز والحيوانات الأليفة','أطلس العالم','الجداول المرجعية','المصادر','اللغة','استعادة الإنجليزية'],
  zh:['首页','开始游戏','指南库','角色','升级规划','宝藏与宠物','世界地图','参考表','来源','语言','恢复英语'],
});
const NAV_ROUTES = ['home','play','guides','crew','planner','collection','world','tables','notes'];
const STORAGE_KEY = 'pirate-crew:language';
const EXCLUDED = 'script,style,noscript,pre,code,kbd,samp,input,textarea,select,option,[contenteditable]:not([contenteditable="false"]),[translate="no"],[data-no-translate],.notranslate';
export function normalizeLocale(value) {
  return LANGUAGES.some(([locale]) => locale === value) ? value : 'en';
}
export function readLanguage(storage) {
  try { return normalizeLocale(storage?.getItem(STORAGE_KEY)); } catch { return 'en'; }
}
export function saveLanguage(storage, locale) {
  try { storage?.setItem(STORAGE_KEY, normalizeLocale(locale)); return Boolean(storage); } catch { return false; }
}
/** Mask exact stats, version strings and numeric identifiers before machine translation. */
export function protectNumbers(text) {
  const values = [];
  const masked = text.replace(/\d+(?:[.,:/_-]\d+)*(?:%|\+)?/g, value => {
    values.push(value); return `__PC_NUMBER_${values.length - 1}__`;
  });
  return { text: masked, restore(result) {
    if (typeof result !== 'string') throw new Error('Translation provider returned invalid text.');
    for (let i = 0; i < values.length; i++) {
      const token = `__PC_NUMBER_${i}__`;
      if (result.split(token).length !== 2) throw new Error('Translation changed a protected number.');
      result = result.replace(token, values[i]);
    }
    if (/__PC_NUMBER_\d+__/.test(result)) throw new Error('Translation returned an invalid number marker.');
    return result;
  }};
}
export function browserTranslationProvider(environment = globalThis) {
  return { name: 'Browser on-device translation', async create(options) {
    if (!environment.Translator) throw new Error('Page translation is unavailable in this browser. Use English or a desktop browser with on-device translation.');
    const availability = await environment.Translator.availability(options);
    if (availability === 'unavailable') throw new Error('This language is unavailable in this browser.');
    return environment.Translator.create(options);
  }};
}
/** Small state machine kept separate from the DOM for error and race testing. */
export function createLanguageController({provider, apply, restore, status, storage, applied = () => {}}) {
  let generation = 0, session = null, locale = 'en';
  return {
    get locale() { return locale; },
    async choose(requested) {
      const next = normalizeLocale(requested), ticket = ++generation;
      const previousSession = session; session = null;
      previousSession?.destroy?.();
      restore(); locale = 'en'; applied('en');
      if (next === 'en') { saveLanguage(storage, 'en'); status('English original.', 'ready'); return true; }
      status('Preparing translation. Your browser may need to download a language model…', 'loading');
      let candidate;
      try {
        candidate = await provider.create({sourceLanguage:'en', targetLanguage:next});
        if (ticket !== generation) { candidate.destroy?.(); return false; }
        await apply(candidate, () => ticket === generation);
        if (ticket !== generation) { candidate.destroy?.(); return false; }
        session = candidate; locale = next; applied(next); saveLanguage(storage, next);
        status('Page text translated. Images, editable fields and game canvas keep their original text. Machine translations can contain errors.', 'ready');
        return true;
      } catch (error) {
        candidate?.destroy?.();
        if (ticket !== generation) return false;
        restore(); locale = 'en'; applied('en'); saveLanguage(storage, 'en');
        status(`${error?.message || 'Translation failed.'} English has been restored.`, 'error'); return false;
      }
    },
    async refresh() {
      if (!session) return;
      const ticket = generation;
      try { await apply(session, () => ticket === generation); }
      catch { if (ticket === generation) { status('New page content could not be translated. Choose English to restore the page, or select the language again to retry.', 'error'); } }
    },
    destroy() { generation++; session?.destroy?.(); session = null; restore(); locale = 'en'; applied('en'); },
  };
}
export function mountSiteLanguage({document = globalThis.document, storage, provider, target} = {}) {
  if (!document?.body) return null;
  if (document.querySelector('[data-site-language]')) return null;
  const environment = document.defaultView || globalThis;
  if (storage === undefined) { try { storage = environment.localStorage; } catch { storage = null; } }
  provider ||= browserTranslationProvider(environment);
  const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = new URL('./site-language.css', import.meta.url).href; document.head.append(css);
  const box = document.createElement('div'); box.className = 'site-language'; box.dataset.siteLanguage = ''; box.translate = false;
  const label = document.createElement('label'); label.textContent = 'Language'; label.htmlFor = 'site-language-select';
  const picker = document.createElement('select'); picker.id = label.htmlFor; picker.setAttribute('aria-describedby','site-language-status');
  for (const [locale, name] of LANGUAGES) { const option = document.createElement('option'); option.value = locale; option.textContent = name; option.lang = locale; picker.append(option); }
  const reset = document.createElement('button'); reset.type = 'button'; reset.textContent = 'Restore English';
  const state = document.createElement('span'); state.id = 'site-language-status'; state.setAttribute('role','status'); state.setAttribute('aria-live','polite'); state.textContent = 'English original. Translation availability depends on your browser.';
  box.append(label, picker, reset, state);
  const attribution = document.createElement('small'); attribution.textContent = provider.name || 'Configured translation provider'; box.append(attribution);
  (target || document.querySelector('.header-inner') || document.querySelector('header') || document.body).append(box);
  const sources = new WeakMap(), rendered = new WeakMap(), touched = new Set();
  function entries() {
    for (const node of touched) if (!node.isConnected) touched.delete(node);
    const found = [], walker = document.createTreeWalker(document.body, 4);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!node.nodeValue?.trim() || node.parentElement?.closest(EXCLUDED)) continue;
      if (sources.has(node) && node.nodeValue === rendered.get(node)) continue;
      sources.set(node, node.nodeValue); found.push(node); touched.add(node);
    }
    return found;
  }
  const manualLabels = new Map();
  function restore() {
    for (const [node, original] of manualLabels) { node.textContent = original; node.removeAttribute('lang'); }
    manualLabels.clear(); label.textContent = 'Language'; reset.textContent = 'Restore English';
    for (const node of touched) {
      if (node.nodeValue === rendered.get(node)) node.nodeValue = sources.get(node);
      rendered.delete(node);
    }
    touched.clear();
  }
  const controller = createLanguageController({provider, storage, restore,
    status(message, kind) { state.textContent = message; box.dataset.state = kind; picker.setAttribute('aria-busy', String(kind === 'loading')); picker.value = kind === 'error' ? 'en' : picker.value; },
    applied(locale) { document.documentElement.lang = locale; document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr'; picker.value = locale; },
    async apply(session, active) {
      // Stage translations before writing: failed batches never leave a half-translated initial page.
      const pending = [];
      for (const node of entries()) {
        if (!active()) return;
        const source = sources.get(node), protectedText = protectNumbers(source);
        const translated = protectedText.restore(await session.translate(protectedText.text));
        pending.push([node, source, translated]);
      }
      if (!active()) return;
      for (const [node, source, translated] of pending) {
        if (node.isConnected && node.nodeValue === source) { node.nodeValue = translated; rendered.set(node, translated); }
      }
    },
  });
  function manualNavigation(requested) {
    const labels = NAV_TRANSLATIONS[requested];
    if (!labels) return;
    for (let i = 0; i < NAV_ROUTES.length; i++) {
      for (const node of document.querySelectorAll(`.primary-nav [data-route="${NAV_ROUTES[i]}"]`)) {
        if (!manualLabels.has(node)) manualLabels.set(node, node.textContent);
        node.textContent = labels[i]; node.lang = requested;
      }
    }
    label.textContent = labels[9]; reset.textContent = labels[10];
  }
  let uiGeneration = 0;
  picker.addEventListener('change', async () => {
    const request = ++uiGeneration;
    const requested = normalizeLocale(picker.value);
    const succeeded = await controller.choose(requested);
    if (request !== uiGeneration || succeeded || requested === 'en') return;
    manualNavigation(requested);
    state.textContent += ' Only navigation labels have been translated; guide content is still English.';
    saveLanguage(storage, requested);
  });
  reset.addEventListener('click', () => { uiGeneration++; controller.choose('en'); });
  let timer;
  const observer = new environment.MutationObserver(records => {
    if (!records.some(record => !box.contains(record.target))) return;
    environment.clearTimeout(timer); timer = environment.setTimeout(() => controller.refresh(), 160);
  });
  observer.observe(document.body, {subtree:true, childList:true, characterData:true});
  const remembered = readLanguage(storage);
  if (remembered !== 'en') {
    // Model downloads require a user gesture; do not silently initiate them at page load.
    manualNavigation(remembered);
    state.textContent = 'Saved navigation language applied. Guide content is still English. Choose a language to translate the full page.';
    picker.value = 'en';
  }
  return {refresh: () => controller.refresh(), destroy() { observer.disconnect(); environment.clearTimeout(timer); controller.destroy(); box.remove(); css.remove(); }};
}
