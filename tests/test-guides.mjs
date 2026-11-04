import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {GUIDE_CONTENT} from '../web/public/guide-content.mjs';
import {filterEntities,safeIconPath,STACKING_ROWS,validatedRankings} from '../web/public/guide-experience.mjs';
const ids=['pets','mounts','treasures','gems','gear','ships','posters','skins','relics','damage','control','drops','characters','new-player','halloween'];
assert.deepEqual(Object.keys(GUIDE_CONTENT).sort(),ids.sort());
for(const [id,g]of Object.entries(GUIDE_CONTENT)){
 assert.ok(g.sections.length>=7,`${id}: substantive chapters`);
 assert.ok(g.priorities.some(p=>p.tier==='S'),`${id}: opening priority list`);
 assert.ok(g.checklist.length>=3&&g.faq.length>=2,`${id}: actionable reference`);
 assert.ok(g.sections.every(s=>s.paragraphs?.length||s.bullets?.length||s.table),`${id}: no empty chapters`);
 assert.ok(!/https?:\/\//.test(JSON.stringify(g)),`${id}: no external guide dependency`);
}
assert.ok(STACKING_ROWS.some(r=>r.join(' ').includes('Latest application wins')));
assert.equal(safeIconPath('/game/icon/item/pet.abcdef.png'),'/game/icon/item/pet.abcdef.png');
for(const bad of ['https://x/img.png','javascript:alert(1)','/game/../secret','/game/a" onerror="x'])assert.equal(safeIconPath(bad),null);
const sample=[{id:'42',name:'Megalo',quality:'5',fields:{attrs:'Attack +3'},related:[{rows:[{effect:'Healing 67.5%'}]}]}];
assert.equal(filterEntities(sample,'HEALING').length,1);assert.equal(filterEntities(sample,'42').length,1);assert.equal(filterEntities(sample,'no match').length,0);
const ui=readFileSync(new URL('../web/public/guide-experience.mjs',import.meta.url),'utf8');
assert.ok(!ui.includes('innerHTML'));assert.ok(!ui.includes("node('iframe'"));
console.log('Guides: complete chapter coverage, internal reading, tier identity, safe icon paths and nested catalog search passed.');

const catalog={build:'34521',systems:{pets:[{id:'1'},{id:'2'}]}};
const base={status:'passed',engineHash:'verified-hash',scenarios:['equal-stats'],entries:[{entityId:'1',tier:'S',reason:'Measured result'}],coverage:[{id:'1',status:'passed'}]};
assert.equal(validatedRankings({build:'34521',systems:{pets:base}},'pets',catalog),null,'incomplete coverage must never produce rankings');
assert.equal(validatedRankings({build:'33382',systems:{pets:{...base,coverage:[{id:'1',status:'passed'},{id:'2',status:'passed'}]}}},'pets',catalog),null,'old capture cannot rank current data');
assert.ok(validatedRankings({build:'34521',systems:{pets:{...base,coverage:[{id:'1',status:'passed'},{id:'2',status:'passed'}]}}},'pets',catalog));
const {petIsolatedResults:isolated}=await import('../web/public/pet-isolated-results.mjs');
assert.equal(isolated.tested,75);assert.equal(isolated.rows.length,75);assert.equal(new Set(isolated.rows.map(r=>r.petId)).size,75);
assert.ok(isolated.rows.every(r=>r.status==='PASS'));assert.ok(isolated.seedCount>=16);
for(const role of isolated.roles){assert.ok(role.metric&&role.description);assert.ok(isolated.rows.every(r=>r[role.metric]!==undefined));}
console.log('Isolated pet report: all75 unique candidates passed, role metrics and conditions present.');
