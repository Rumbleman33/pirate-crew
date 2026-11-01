import vm from 'node:vm';import fs from 'node:fs';import assert from 'node:assert/strict';
const records=new Map();
const db={objectStoreNames:{contains:()=>true},createObjectStore(){},close(){},transaction(){const tx={objectStore:()=>({get(key){const r={};queueMicrotask(()=>{r.result=records.get(key);r.onsuccess?.();});return r;},put(value,key){records.set(key,value);queueMicrotask(()=>tx.oncomplete?.());}})};return tx;}};
const indexedDB={open(){const r={};queueMicrotask(()=>{r.result=db;r.onsuccess?.();});return r;}};
const code=fs.readFileSync('web/public/engine-worker.js','utf8').split('const ready=')[0];
function context(){const c=vm.createContext({importScripts(){},indexedDB,crypto,TextEncoder,TextDecoder,Uint8Array,Promise,Set,Map,console,setTimeout,clearTimeout,navigator:{}});vm.runInContext(code+'\nglobalThis.helpers={wrapLocal,openLocal};',c);return c.helpers;}
const value='cd'.repeat(32),first=context(),encrypted=await first.wrapLocal(value,'pirate01');assert.ok(!encrypted.includes(value));assert.equal(await first.openLocal(encrypted,'pirate01'),value);
await assert.rejects(first.openLocal(encrypted,'pirate02'));
const key=records.get('local-verifier');assert.equal(key.extractable,false);await assert.rejects(crypto.subtle.exportKey('raw',key));
const reloaded=context();assert.equal(await reloaded.openLocal(encrypted,'pirate01'),value);
console.log('Cached verifier encryption survives worker reload, rejects another captain, and keeps its device key non-extractable.');
