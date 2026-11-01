export const types={characterLevel:'Character levels',characterStar:'Character stars',skinStar:'Skin stars',treasureStar:'Treasure stars',petStage:'Pet stages',gemMaster:'Gem Master',petBookMaster:'Pet Book mastery',basicTalent:'Basic Talent nodes',advancedTalent:'Advanced Talent nodes'};
export function rowsFor(data,growth,type,id){
 if(type==='characterLevel')return growth.levels[String(id)]||[];
 if(type==='characterStar')return growth.stars[String(id)]||[];
 if(type==='skinStar')return data.skins.find(r=>r.id===Number(id))?.stars||[];
 if(type==='treasureStar')return data.treasures.find(r=>r.id===Number(id))?.stages||[];
 if(type==='petStage')return data.pets.find(r=>r.id===Number(id))?.stages||[];
 return data.progression[type]||[];
}
export function stepKey(type){return type==='characterLevel'?'level':type==='characterStar'||type==='skinStar'||type==='treasureStar'?'star':type.endsWith('Talent')?'node':'stage';}
export function bounds(data,growth,type,id){const rows=rowsFor(data,growth,type,id),key=stepKey(type);return{min:type==='characterLevel'?1:0,max:Math.max(0,...rows.map(r=>r[key])),rows,key};}
export function listFor(data,type){if(type.startsWith('character'))return data.characters;if(type==='skinStar')return data.skins;if(type==='treasureStar')return data.treasures;if(type==='petStage')return data.pets;return[{id:type,name:types[type]}];}
export function sumCosts(entries){const totals=new Map();for(const row of entries)for(const cost of row||[]){const id=Number(cost.id),count=Number(cost.count);if(!Number.isSafeInteger(id)||!Number.isFinite(count)||count<0)throw Error('Invalid captured material cost.');totals.set(id,(totals.get(id)||0)+count);}return[...totals].filter(([,n])=>n>0).map(([id,count])=>({id,count})).sort((a,b)=>a.id-b.id);}
export function planUpgrade(data,growth,type,id,from,to){
 if(!Object.hasOwn(types,type))throw Error('Choose a supported upgrade track.');
 const b=bounds(data,growth,type,id);if(!b.rows.length)throw Error('No captured stages for this selection.');
 if(!Number.isSafeInteger(from)||!Number.isSafeInteger(to)||from<b.min||to> b.max||to<=from)throw Error(`Choose whole stages from ${b.min} to ${b.max}, with the target above the current stage.`);
 const byKey=new Map(b.rows.map(r=>[r[b.key],r])),steps=[];let requiredStar=0,requiredLevel=0;
 for(let n=from;n<to;n++){
  let row,cost;
  if(type==='skinStar'&&n===0){row=data.skins.find(r=>r.id===Number(id));cost=row.activationCost;}
  else if(['characterLevel','characterStar','skinStar'].includes(type)){row=byKey.get(n);cost=row?.nextCost;}
  else {row=byKey.get(n+1);cost=type.endsWith('Talent')?row?.cost:row?.costToReach;}
  if(!row||!Array.isArray(cost)||!cost.length)throw Error(`Captured cost for ${n} → ${n+1} is unavailable.`);
  requiredStar=Math.max(requiredStar,byKey.get(n+1)?.requiredStar||0);requiredLevel=Math.max(requiredLevel,row.requiredLevel||0);
  steps.push({from:n,to:n+1,cost});
 }
 return{type,id,from,to,steps,totals:sumCosts(steps.map(r=>r.cost)),attributes:byKey.get(to)?.attributes||[],requiredStar,requiredLevel};
}
export function craftingCosts(totals,recipes){const available=new Map(recipes.filter(r=>r.reward?.length===1&&r.reward[0].count>0).map(r=>[Number(r.reward[0].id),r]));const expanded=totals.map(item=>{const r=available.get(item.id);if(!r||r.cost.some(c=>c.id===item.id))return[item];const crafts=Math.ceil(item.count/r.reward[0].count);return r.cost.map(c=>({id:c.id,count:c.count*crafts}));});return sumCosts(expanded);}
export function offerPrice(required,quantity,price,limit=0){if(!Number.isFinite(required)||required<0||!Number.isFinite(quantity)||quantity<=0||!Number.isFinite(price)||price<0||!Number.isSafeInteger(limit)||limit<0)throw Error('Enter a positive guaranteed pack quantity, a nonnegative price and a whole purchase limit.');const packs=Math.ceil(required/quantity);return{packs,total:Math.round(packs*price*100)/100,exceedsLimit:limit>0&&packs>limit};}
