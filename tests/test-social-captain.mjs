import {DatabaseSync} from 'node:sqlite';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
import {social} from '../cloud/social.mjs';
import {socialRequest} from '../web/public/play/social-client.mjs';
const db=new DatabaseSync(':memory:');
for(const name of fs.readdirSync('cloud/migrations').sort())db.exec(fs.readFileSync('cloud/migrations/'+name,'utf8'));
let writes=0;
const DB={prepare(sql){return {bind(...args){const stmt=db.prepare(sql);return {first:async()=>stmt.get(...args)||null,all:async()=>({results:stmt.all(...args)}),run:async()=>{writes++;return stmt.run(...args);}};}};}};
const origin='https://synthetic.invalid',signingKey='17'.repeat(32);
const env={DB,CAPTAIN_AUTH_CONFIG:JSON.stringify({signingKey,users:{pirate01:{},pirate02:{}}})};
function cookie(username,expires=Date.now()+60000){const payload=JSON.stringify({purpose:'social',username,expires});return 'pirate_session='+btoa(payload)+'.'+createHmac('sha256',Buffer.from(signingKey,'hex')).update(payload).digest('hex');}
async function request(session,expected,path,body){return social(new Request(origin+'/sandbox-social/'+path,{method:body===undefined?'GET':'POST',headers:{Origin:origin,Cookie:session,...(expected?{'X-Pirate-Captain':expected}:{})},body:body===undefined?undefined:JSON.stringify(body)}),env);}
async function call(username,path,body){const r=await request(cookie(username),username,path,body),value=await r.json();assert.equal(r.status,200,JSON.stringify(value));return value;}
const room=(await call('pirate01','create',{name:'Synthetic lobby'})).id;
await call('pirate02','join',{room});
await call('pirate01','friend',{username:'pirate02',action:'request'});await call('pirate02','friend',{username:'pirate01',action:'accept'});
const actions={create:{name:'wrong identity'},friend:{username:'pirate01',action:'remove'},messages:{recipient:'pirate01',text:'wrong identity'},join:{room},ready:{room,ready:true,team:[]},settings:{room},start:{room},reset:{room},leave:{room}};
for(const [action,body] of Object.entries(actions)){
 const before=writes;const r=await request(cookie('pirate02'),'pirate01',action,body);assert.equal(r.status,409,action);assert.equal((await r.json()).code,'CAPTAIN_MISMATCH');assert.equal(writes,before,action+' must not write even presence');
}
for(const expected of [null,'PIRATE01','other_captain']){const before=writes;assert.equal((await request(cookie('pirate01'),expected,'state')).status,409);assert.equal(writes,before);}
assert.equal((await request(cookie('pirate01',0),'pirate01','create',{})).status,401);
assert.equal((await request('','pirate01','create',{})).status,401);
const team=[{generalId:1,attrs:{1:100}}];
await call('pirate01','ready',{room,ready:true,team});await call('pirate02','ready',{room,ready:true,team});await call('pirate01','start',{room});
await call('pirate01','reset',{room});assert.ok((await call('pirate01','room?room='+room)).members.every(m=>!m.ready));
await call('pirate01','messages',{recipient:'pirate02',text:'Synthetic message'});assert.equal((await call('pirate02','messages?recipient=pirate01')).messages.length,1);
// Reproduce a cookie switch between the client's local identity check and write.
let disconnected=0,local='pirate01',session=cookie('pirate02'),network=0;
const api=async(path,body,headers)=>{if(path==='/api/me')return {account:{username:local}};network++;const r=await request(session,headers['X-Pirate-Captain'],path.slice('/sandbox-social/'.length),body),value=await r.json();if(!r.ok)throw Object.assign(Error(value.error),{status:r.status,code:value.code});return value;};
const client={api,connected:true,username:'pirate01',disconnect:()=>disconnected++};
const before=writes;await assert.rejects(socialRequest(client,'create',{}),/Captain changed/);assert.equal(disconnected,1);assert.equal(writes,before);
local='pirate02';network=0;await assert.rejects(socialRequest(client,'create',{}),/Captain changed/);assert.equal(network,0);
await assert.rejects(socialRequest({...client,connected:false},'create',{}),/Connect social/);assert.equal(network,0);
await socialRequest({...client,username:'pirate02'},'create',{name:'Reconnected correctly'});
session='';await assert.rejects(socialRequest({...client,username:'pirate02'},'state'),/Connect your captain/);
assert.equal(disconnected,3);
const conflicts=async(path)=>{if(path==='/api/me')return {account:{username:'pirate01'}};throw Object.assign(Error('Lobby full'),{status:409});};
await assert.rejects(socialRequest({...client,api:conflicts},'join',{room}),/Lobby full/);assert.equal(disconnected,3,'A normal lobby conflict must keep the captain connected');
db.close();console.log('Social captain binding: all write routes, private reads, cookie switches, logout, reconnect and normal SQLite service flows passed.');
