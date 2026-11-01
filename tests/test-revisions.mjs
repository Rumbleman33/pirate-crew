import vm from 'node:vm';import fs from 'node:fs';import assert from 'node:assert/strict';
const source=fs.readFileSync('web/public/play/runtime-bridge.js','utf8');
const section=source.slice(source.indexOf('  let lastAppliedRevision=0;'),source.indexOf('  function applyClientAction('));
const events=[],document={body:{dataset:{}}};
const context=vm.createContext({document,transport:{event:(id,data)=>events.push({id,data})},normalize:(id,data)=>data,publish(){},problem(){}});vm.runInContext(section,context);
context.emitBroadcasts({revision:200,broadcasts:[{id:1007,data:{power:4480}}]});
context.emitBroadcasts({revision:100,broadcasts:[{id:1007,data:{power:4440}}]});
assert.equal(events.length,1);assert.equal(events[0].data.power,4480);assert.equal(document.body.dataset.offlineRevision,'200');
console.log('Cross-window revision regression: an older power update cannot overwrite a newer one.');
