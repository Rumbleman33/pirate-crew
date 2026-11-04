"""Build a private self-contained review copy from authored source and local assets."""
import base64,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
    pub=ROOT/'web/public';assets=ROOT/'.local/assets'
    content=(pub/'guide-content.mjs').read_text().replace('export const ','const ')
    results=(pub/'pet-isolated-results.mjs').read_text().replace('export const ','const ')
    results=re.sub(r'export default[^;]+;?', '', results)
    ui=(pub/'guide-experience.mjs').read_text()
    ui=re.sub(r'^import .*?;\n','',ui,flags=re.M).replace('export async function ','async function ').replace('export function ','function ').replace('export const ','const ')
    catalog=json.loads((assets/'data/guide-catalog.json').read_text())
    for entries in catalog['systems'].values():
        for e in entries:
            if e.get('icon'):
                path=assets/e['icon'].lstrip('/')
                if path.is_file():e['icon']='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
    ui=ui.replace("fetch('/data/guide-catalog.json')",'Promise.resolve({ok:true,json:()=>Promise.resolve(PREVIEW_CATALOG)})')
    ui=ui.replace("fetch('/data/guide-rankings.json')",'Promise.resolve({ok:false})')
    ui=ui.replace("typeof value==='string'&&/^", "typeof value==='string'&&value.startsWith('data:image/png;base64,')?value:typeof value==='string'&&/^")
    language=(pub/'site-language.mjs').read_text().replace('export const ','const ').replace('export function ','function ')
    language=language.replace("css.href = new URL('./site-language.css', import.meta.url).href;", "css.href = 'data:text/css,';")
    css='\n'.join((pub/f).read_text() for f in ['style.css','futuristic.css','guide-experience.css','site-language.css'])
    boot="""const parent=document.getElementById('content');async function route(){parent.replaceChildren();const [page,id]=location.hash.slice(1).split('/');if(page==='guide')await renderGuide(parent,id);else await renderLibrary(parent);window.scrollTo(0,0);}window.addEventListener('hashchange',route);route();"""
    script='const PREVIEW_CATALOG='+json.dumps(catalog,ensure_ascii=False)+';\n'+content+'\n'+results+'\n'+ui+'\n'+language+'\n'+boot+'\nmountSiteLanguage();'
    script=script.replace('</script','<\\/script')
    html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pirate Crew — Guide Review</title><style>'+css+'</style><body><header class="site-header"><div class="header-inner"><a class="brand" href="#guides"><strong>PIRATE CREW / GUIDE REVIEW</strong></a><span>Private review copy · captured build 34521</span></div></header><main id="content" tabindex="-1"></main><script type="module">'+script+'</script></body></html>'
    out=ROOT/'.local/Guide-Review.html';out.parent.mkdir(exist_ok=True);out.write_text(html);print(out)
if __name__=='__main__':build()
