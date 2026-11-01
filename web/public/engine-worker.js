importScripts('/pyodide/pyodide.js');
let chain=Promise.resolve();const ports=new Set();
const localScopes=new Map();
let saveTimer;
const persist=py=>new Promise((resolve,reject)=>py.FS.syncfs(false,error=>error?reject(error):resolve()));
function scheduleSave(py){if(saveTimer)return;saveTimer=setTimeout(()=>{saveTimer=null;chain=chain.then(()=>persist(py)).catch(()=>status('Local save could not be written. Export your save before closing.'));},750);}
function status(text){for(const p of ports)p.postMessage({type:'status',text});}
const hex=b=>Array.from(new Uint8Array(b),n=>n.toString(16).padStart(2,'0')).join('');
const unhex=s=>Uint8Array.from(s.match(/../g)||[],n=>parseInt(n,16));
let deviceKeyPromise;
async function deviceKey(){return deviceKeyPromise||=(async()=>{
 const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('pirate-device-keyring-v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('keys');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
 let key=await new Promise((resolve,reject)=>{const r=db.transaction('keys').objectStore('keys').get('local-verifier');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
 if(!key){key=await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);await new Promise((resolve,reject)=>{const t=db.transaction('keys','readwrite');t.objectStore('keys').put(key,'local-verifier');t.oncomplete=resolve;t.onerror=()=>reject(t.error);});}db.close();return key;
})();}
async function wrapLocal(value,username){const iv=crypto.getRandomValues(new Uint8Array(12)),data=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:new TextEncoder().encode(username)},await deviceKey(),new TextEncoder().encode(value));return 'v1.'+hex(iv)+'.'+hex(data);}
async function openLocal(value,username){if(!value.startsWith('v1.'))return value;const [,iv,data]=value.split('.');return new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:unhex(iv),additionalData:new TextEncoder().encode(username)},await deviceKey(),unhex(data)));}
async function writerLock(){if(!navigator.locks)return;await new Promise((resolve,reject)=>{navigator.locks.request('pirate-runtime-writer-v1',async()=>{resolve();await new Promise(()=>{});}).catch(reject);});}
async function derive(password,salt){const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveBits']);return hex(await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',iterations:240000,salt},key,256));}
async function verifyAssignedLogin(username,password){
 let response;try{response=await fetch('/captain-auth/challenge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});}catch{throw Error('Connect to the internet for this account’s first sign-in on this device. Later sign-ins work offline.');}
 if(!response.ok)throw Error(response.status===503?'Test login verification is temporarily unavailable.':'Incorrect test username or password.');
 const challenge=await response.json();if(challenge.username!==username||challenge.iterations!==240000||!/^[0-9a-f]{32}$/.test(challenge.salt))throw Error('Invalid login verification response.');
 const hash=await derive(password,unhex(challenge.salt)),key=await crypto.subtle.importKey('raw',unhex(hash),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 const proof=hex(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(challenge.challenge)));
 const verified=await fetch('/captain-auth/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,challenge:challenge.challenge,proof})});
 if(!verified.ok)throw Error('Incorrect test username or password.');const result=await verified.json();if(result.ok!==true||result.username!==username)throw Error('Login verification failed.');
 return {salt:challenge.salt,hash,account:result.account};
}
const ready=(async()=>{status('Opening saved profiles…');await writerLock();status('Loading browser Python…');const py=await loadPyodide({indexURL:'/pyodide/'});status('Loading original tables…');
 const archive=new Uint8Array(await(await fetch('/simulation.zip?v=20261031-2',{cache:'no-store'})).arrayBuffer());py.FS.mkdirTree('/pirates');py.unpackArchive(archive,'zip',{extractDir:'/pirates'});
 py.FS.mkdirTree('/pirates/runtime');py.FS.mount(py.FS.filesystems.IDBFS,{},'/pirates/runtime');await new Promise((r,j)=>py.FS.syncfs(true,e=>e?j(e):r()));
 if(!py.FS.analyzePath('/pirates/runtime/accounts.json').exists){const users={};for(let i=1;i<=10;i++){const username='pirate'+String(i).padStart(2,'0'),salt=crypto.getRandomValues(new Uint8Array(16)),seed=hex(crypto.getRandomValues(new Uint8Array(32)));users[username]={username,displayName:'Test Captain '+String(i).padStart(2,'0'),playerId:9900000000000+i,salt:hex(salt),passwordHash:await derive(seed,salt),gm:true};}py.FS.writeFile('/pirates/runtime/accounts.json',JSON.stringify({version:1,localOnly:true,users}));}
 for(const path of ['/pirates/runtime/browser-logins.txt','/pirates/TEST-LOGINS.txt'])if(py.FS.analyzePath(path).exists)py.FS.unlink(path);
 const records=JSON.parse(py.FS.readFile('/pirates/runtime/accounts.json',{encoding:'utf8'}));for(const record of Object.values(records.users))if(!record.passwordHash.startsWith('v1.'))record.passwordHash=await wrapLocal(record.passwordHash,record.username);py.FS.writeFile('/pirates/runtime/accounts.json',JSON.stringify(records));
 py.globals.set('_webcrypto_hash','');await py.runPythonAsync("import sys\nsys.path.insert(0,'/pirates')\nfrom offline_accounts import OfflineAccounts\nOfflineAccounts._hash=staticmethod(lambda password,salt:_webcrypto_hash)\nimport browser_api");await new Promise((r,j)=>py.FS.syncfs(false,e=>e?j(e):r()));status('Browser simulator ready.');return py;})();
onconnect=e=>{const port=e.ports[0];let captainUsername,scopeToken;ports.add(port);port.start();port.onmessage=e=>{const m=e.data;if(m.type==='ready'){ready.then(()=>port.postMessage({id:m.id,ready:true,build:16})).catch(e=>port.postMessage({id:m.id,error:String(e)}));return;}
 chain=chain.then(async()=>{try{const py=await ready;
  if(m.type==='bind'){if(!localScopes.has(m.request.token))throw Error('Local captain session expired. Sign in again.');captainUsername=localScopes.get(m.request.token);scopeToken=m.request.token;port.postMessage({id:m.id,bound:true});return;}
  if(captainUsername===undefined){const path='/pirates/runtime/browser-session.json';captainUsername=py.FS.analyzePath(path).exists?JSON.parse(py.FS.readFile(path,{encoding:'utf8'})).username||null:null;}
  if(m.request.url==='/api/social-session'){
   const records=JSON.parse(py.FS.readFile('/pirates/runtime/accounts.json',{encoding:'utf8'})),record=records.users[captainUsername];
   if(!record)throw Error('Sign into a test captain first.');
   let response=await fetch('/captain-auth/challenge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:record.username})});
   if(!response.ok)throw Error('Online captain verification is unavailable.');const challenge=await response.json();
   if(challenge.username!==record.username||challenge.salt!==record.salt)throw Error('Sign out and sign back in with your assigned password to connect social features.');
   const key=await crypto.subtle.importKey('raw',unhex(await openLocal(record.passwordHash,record.username)),{name:'HMAC',hash:'SHA-256'},false,['sign']);
   const proof=hex(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(challenge.challenge)));
   response=await fetch('/captain-auth/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:record.username,challenge:challenge.challenge,proof})});
   if(!response.ok)throw Error('Social sign-in failed. Sign in again with your assigned password.');
   port.postMessage({id:m.id,result:{status:200,data:{ok:true,username:record.username}}});return;
  }
  if(m.request.url==='/api/logout')await fetch('/captain-auth/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).catch(()=>{});
  if(['/api/browser-logins','/api/import-logins'].includes(m.request.url)){port.postMessage({id:m.id,result:{status:404,data:{detail:'Not available.'}}});return;}
  if(m.request.url==='/api/register'){
   const username=String(m.request.body?.username||'').trim().toLowerCase(),password=String(m.request.body?.password||'');
   if(!/^[a-z][a-z0-9_]{2,23}$/.test(username))throw Error('Use 3–24 letters, numbers or underscores, starting with a letter.');
   if(password.length<8||password.length>128)throw Error('Choose a password of 8–128 characters.');
   const salt=hex(crypto.getRandomValues(new Uint8Array(16))),hash=await derive(password,unhex(salt));
   const response=await fetch('/captain-auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,salt,passwordHash:hash})});
   const value=await response.json();if(!response.ok)throw Error(value.detail||'Account creation failed.');
   port.postMessage({id:m.id,result:{status:201,data:{ok:true,account:value.account}}});return;
  }
  if(m.request.url==='/api/login'){
   const username=String(m.request.body?.username||'').trim().toLowerCase(),password=String(m.request.body?.password||''),records=JSON.parse(py.FS.readFile('/pirates/runtime/accounts.json',{encoding:'utf8'}));
   let record=Object.hasOwn(records.users,username)?records.users[username]:null,hash=record?await derive(password,unhex(record.salt)):null,cached=null;
   if(record)try{cached=await openLocal(record.passwordHash,username);}catch{}
   if(!record||hash!==cached){
    const assigned=await verifyAssignedLogin(username,password);
    if(!assigned.account||assigned.account.username!==username||!Number.isSafeInteger(assigned.account.playerId))throw Error('Invalid captain identity response.');
    record={...assigned.account,salt:assigned.salt,passwordHash:await wrapLocal(assigned.hash,username),gm:true};records.users[username]=record;hash=assigned.hash;
    py.FS.writeFile('/pirates/runtime/accounts.json',JSON.stringify(records));
   }
   if(!/^[a-z][a-z0-9_]{2,23}$/.test(username))throw Error('Invalid captain username.');
   if(!py.FS.analyzePath('/pirates/runtime/saves/'+username+'.json').exists){py.globals.set('_verified_username',username);py.runPython('browser_api.STORE._write(_verified_username,browser_api.STORE._seed(_verified_username))');py.globals.set('_verified_username','');}
   py.globals.set('_webcrypto_hash',record.passwordHash);
  }
  py.globals.set('_port_captain',captainUsername);py.runPython('browser_api.username=_port_captain');py.globals.set('_browser_request',JSON.stringify(m.request));const result=JSON.parse(py.runPython('browser_api.request(_browser_request)'));captainUsername=py.runPython('browser_api.username');py.globals.set('_port_captain',null);py.globals.set('_browser_request','');py.globals.set('_webcrypto_hash','');
  if(result.data?.account&&captainUsername){if(!scopeToken||localScopes.get(scopeToken)!==captainUsername){scopeToken=hex(crypto.getRandomValues(new Uint8Array(32)));localScopes.set(scopeToken,captainUsername);}result.data.account.localSession=scopeToken;}
  if(m.request.url==='/api/logout'&&scopeToken){localScopes.delete(scopeToken);scopeToken=null;}
  if(m.request.method!=='GET'&&(m.request.url!=='/api/command'||result.data?.broadcasts?.length)){
   if(m.request.url==='/api/command'&&[50004,50006,50010,50013].includes(Number(m.request.body?.id)))scheduleSave(py);
   else {clearTimeout(saveTimer);saveTimer=null;await persist(py);}
  }
  port.postMessage({id:m.id,result});
 }catch(error){port.postMessage({id:m.id,error:String(error.message||error)});}});};};
