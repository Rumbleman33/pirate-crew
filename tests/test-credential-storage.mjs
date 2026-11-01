import assert from 'node:assert/strict';
import {sealVerifier,openVerifier,captainRecord} from '../cloud/captain-auth.mjs';
const config={signingKey:'ab'.repeat(32),users:{}},plain='12'.repeat(32),username='test_encryption';
const encrypted=await sealVerifier(config,plain,username);assert.ok(encrypted.startsWith('v1.'));assert.ok(!encrypted.includes(plain));assert.equal(await openVerifier(config,encrypted,username),plain);
await assert.rejects(openVerifier(config,encrypted,'another_captain'));await assert.rejects(openVerifier(config,encrypted.slice(0,-2)+'ff',username));
let stored=plain;const env={DB:{prepare(sql){return {bind(...args){return {first:async()=>({username,passwordHash:stored,salt:'cd'.repeat(16)}),run:async()=>{if(sql.startsWith('UPDATE'))stored=args[0];}};}};}}};
assert.equal((await captainRecord(env,config,username)).passwordHash,plain);assert.ok(stored.startsWith('v1.'));assert.equal((await captainRecord(env,config,username)).passwordHash,plain);
console.log('Server verifier storage: encrypted, username-bound, authenticated, legacy migration preserves login.');
