const stop=new Set('a an the is are was were be been why how what when where which do does did it its me my i you your us our of to for from on in at with without all any some can could should would will have has and or but than then that this these those game please tell explain give work working'.split(' '));
export function normalize(text){return String(text).replace(/([a-z])([A-Z])/g,'$1 $2').toLowerCase().replace(/\bcp\b/g,'combat power').replace(/one piece/g,'voyage').replace(/impel down/g,'tower').replace(/blackbeard|marshall d\.? teach/g,'teach').replace(/\bhaki\b/g,'suit').replace(/unequipped|unassigned|not equipped|not applied/g,'unassigned').replace(/\b(pets|mounts|talents|treasures|ships|skins|characters|levels|bonuses|slots|gems)\b/g,w=>({bonuses:'bonus',characters:'character'}[w]||w.slice(0,-1)));}
const tokens=text=>normalize(text).match(/[a-z0-9_]+/g)||[];
const topicNames=['mount','pet','talent','treasure','ship','fruit','suit','gem','gear','artifact','voyage','tower','skin','crew','power'];
export function retrieve(documents,question,limit=8){
 const normalized=normalize(question);
 if(/ignore (all|previous|instructions)|system prompt|president|election|weather|recipe for|password|api.?key|credit card|write (?:a |me )?(?:poem|essay|script)|unrelated/.test(normalized))return [];
 const words=[...new Set(tokens(question).filter(w=>w.length>1&&!stop.has(w)))];if(!words.length)return [];
 const topics=topicNames.filter(t=>words.includes(t)),entity=/panda/.test(normalized)?'panda':null;
 const primary=topics.filter(t=>!['crew','power'].includes(t));
 const candidates=[];const df=new Map(words.map(w=>[w,0]));
 for(const d of documents){
  const title=normalize(d.title),text=normalize(d.text),combined=title+' '+text;
  if(entity&&!combined.includes(entity))continue;
  if((primary.length?primary:topics).length&&!(primary.length?primary:topics).some(t=>(d.topics||[]).includes(t)||new RegExp('\\b'+t+'\\b').test(combined)))continue;
  const titleSet=new Set(tokens(title)),counts=new Map();for(const token of tokens(text))if(df.has(token))counts.set(token,(counts.get(token)||0)+1);
  const matches=words.filter(w=>titleSet.has(w)||counts.has(w));
  if(matches.length<Math.min(d.kind==='code'&&primary.length?1:2,words.length))continue;
  for(const w of matches)df.set(w,df.get(w)+1);
  candidates.push({d,titleSet,counts,length:Math.max(40,text.length/5),matches});
 }
 const count=candidates.length;if(!count)return [];
 for(const row of candidates){row.score=0;for(const w of row.matches){const idf=Math.log(1+(count-df.get(w)+.5)/(df.get(w)+.5)),tf=row.counts.get(w)||0;row.score+=idf*(tf*2.2/(tf+1.2*(.25+.75*row.length/180))+(row.titleSet.has(w)?3:0));}
  row.score*=.5+row.matches.length/words.length;
  if(row.d.kind==='answer')row.score*=2.8;
  if(/stats?|math|formula|power/.test(normalized)&&row.d.kind==='code')row.score*=1.3;
  if(/stat/.test(normalized)&&/StarRef|LvRef/.test(row.d.title))row.score*=1.5;
  if(/stat/.test(normalized)&&!words.some(w=>/^\d+$/.test(w))){if(row.d.maxRow)row.score*=1.2;else if(row.d.baseRow)row.score*=1.1;}
 }
 candidates.sort((a,b)=>b.score-a.score);const best=candidates[0].score,groups=new Map(),result=[];
 for(const row of candidates){if(row.score<best*.18)continue;const key=row.d.group||row.d.source;const cap=row.d.kind==='table'?2:3;if((groups.get(key)||0)>=cap)continue;groups.set(key,(groups.get(key)||0)+1);result.push(row.d);if(result.length===limit)break;}
 if(result[0]?.source.startsWith('/knowledge/code/')&&!result.some(d=>d.kind==='code')){const code=candidates.find(r=>r.d.kind==='code'&&r.d.source===result[0].source);if(code){if(result.length===limit)result.pop();result.push(code.d);}}
 return result;
}
