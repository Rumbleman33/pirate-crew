// Runtime secret contains salted verification keys, never plaintext passwords.
// Nothing from this secret is included in browser assets or rendered pages.
const encoder=new TextEncoder();
const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});
const fromHex=s=>Uint8Array.from(s.match(/../g)||[],v=>parseInt(v,16));
const toHex=b=>Array.from(new Uint8Array(b),v=>v.toString(16).padStart(2,'0')).join('');
async function key(bytes){return crypto.subtle.importKey('raw',bytes,{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);}
async function sign(bytes,text){return toHex(await crypto.subtle.sign('HMAC',await key(bytes),encoder.encode(text)));}
async function verify(bytes,text,signature){if(!/^[0-9a-f]{64}$/.test(signature||''))return false;return crypto.subtle.verify('HMAC',await key(bytes),fromHex(signature),encoder.encode(text));}
export const validCaptain=u=>/^[a-z][a-z0-9_]{2,23}$/.test(u||'');
async function storageKey(config){const digest=await crypto.subtle.digest('SHA-256',encoder.encode('pirate-captain-verifier-at-rest-v1:'+config.signingKey));return crypto.subtle.importKey('raw',digest,'AES-GCM',false,['encrypt','decrypt']);}
export async function sealVerifier(config,value,username){const iv=crypto.getRandomValues(new Uint8Array(12)),encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:encoder.encode(username)},await storageKey(config),encoder.encode(value));return 'v1.'+toHex(iv)+'.'+toHex(encrypted);}
export async function openVerifier(config,value,username){if(!value.startsWith('v1.'))return value;const [,iv,data]=value.split('.');return new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:fromHex(iv),additionalData:encoder.encode(username)},await storageKey(config),fromHex(data)));}
export async function captainRecord(env,config,username){
 if(Object.hasOwn(config.users||{},username))return {...config.users[username],username,displayName:`Test Captain ${username.slice(-2)}`,playerId:9900000000000+Number(username.slice(-2))};
 if(!env.DB||!validCaptain(username))return null;
 const record=await env.DB.prepare('SELECT username,display_name AS displayName,player_id AS playerId,salt,password_hash AS passwordHash FROM registered_captains WHERE username=?').bind(username).first();
 if(record){const stored=record.passwordHash;record.passwordHash=await openVerifier(config,stored,username);if(!stored.startsWith('v1.'))await env.DB.prepare('UPDATE registered_captains SET password_hash=? WHERE username=? AND password_hash=?').bind(await sealVerifier(config,stored,username),username,stored).run();}return record;
}
export async function captainSession(request,env){
 try{const token=(request.headers.get('Cookie')||'').split(';').map(s=>s.trim()).find(s=>s.startsWith('pirate_session='))?.slice(15),parts=(token||'').split('.');
  if(parts.length!==2)return null;const payload=atob(parts[0]),config=JSON.parse(env.CAPTAIN_AUTH_CONFIG||'null');
  if(!config?.signingKey||!await verify(fromHex(config.signingKey),payload,parts[1]))return null;
  const s=JSON.parse(payload);return s.purpose==='social'&&s.expires>Date.now()&&validCaptain(s.username)&&await captainRecord(env,config,s.username)?s.username:null;
 }catch{return null;}
}
export async function captainAuth(request,env){
 const url=new URL(request.url),denied=()=>json({detail:'Incorrect test username or password.'},401);
 if(request.method!=='POST')return json({detail:'Method not allowed.'},405);
 if(request.headers.get('Origin')&&request.headers.get('Origin')!==url.origin)return json({detail:'Origin not allowed.'},403);
 if(url.pathname==='/captain-auth/logout')return new Response('{}',{headers:{'Content-Type':'application/json','Set-Cookie':'pirate_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0','Cache-Control':'no-store'}});
 if(Number(request.headers.get('Content-Length')||0)>4096)return json({detail:'Request too large.'},413);
 try{
  const config=JSON.parse(env.CAPTAIN_AUTH_CONFIG||'null');if(!config?.users||!config.signingKey)return json({detail:'Test login verification is temporarily unavailable.'},503);
  const raw=await request.text();if(raw.length>4096)return json({detail:'Request too large.'},413);
  const body=JSON.parse(raw),username=String(body.username||'').trim().toLowerCase();
  if(url.pathname==='/captain-auth/register'){
   if(request.headers.get('Origin')!==url.origin)return json({detail:'Origin not allowed.'},403);
   if(!env.DB)return json({detail:'Account creation is temporarily unavailable.'},503);
   if(!validCaptain(username))return json({detail:'Use 3–24 lowercase letters, numbers or underscores, starting with a letter.'},400);
   const salt=String(body.salt||''),passwordHash=String(body.passwordHash||'');
   if(!/^[0-9a-f]{32}$/.test(salt)||!/^[0-9a-f]{64}$/.test(passwordHash))return json({detail:'Invalid account verification fields.'},400);
   if(await captainRecord(env,config,username))return json({detail:'That username is already taken.'},409);
   const now=Date.now(),bucket=Math.floor(now/3600000),address=request.headers.get('CF-Connecting-IP')||'local-preview',digest=(await sign(fromHex(config.signingKey),address)).slice(0,24);
   const allowed=await env.DB.prepare('INSERT INTO ai_usage (key,count,expires) VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1 WHERE count<5 RETURNING count').bind(`signup:${digest}:${bucket}`,now+7200000).first();
   if(!allowed)return json({detail:'Account creation limit reached. Please try again later.'},429);
   const random=crypto.getRandomValues(new Uint8Array(4));let playerId=0;for(const v of random)playerId=playerId*256+v;playerId+=9000000000000;
   try{await env.DB.prepare('INSERT INTO registered_captains (username,display_name,player_id,salt,password_hash,created) VALUES (?,?,?,?,?,?)').bind(username,username,playerId,salt,await sealVerifier(config,passwordHash,username),now).run();}catch{return json({detail:'That username is already taken, or registration is temporarily unavailable.'},409);}
   return json({ok:true,account:{username,displayName:username,playerId,gm:true}},201);
  }
  const record=await captainRecord(env,config,username);
  if(!validCaptain(username)||!record)return denied();
  if(url.pathname==='/captain-auth/challenge'){
   const payload=JSON.stringify({username,nonce:toHex(crypto.getRandomValues(new Uint8Array(24))),expires:Date.now()+120000});
   const challenge=btoa(payload)+'.'+await sign(fromHex(config.signingKey),payload);
   return json({username,salt:record.salt,iterations:240000,challenge});
  }
  if(url.pathname==='/captain-auth/verify'){
   const parts=String(body.challenge||'').split('.');if(parts.length!==2)return denied();
   const payload=atob(parts[0]);if(!await verify(fromHex(config.signingKey),payload,parts[1]))return denied();
   const challenge=JSON.parse(payload);if(challenge.username!==username||challenge.expires<Date.now()||challenge.expires>Date.now()+120000)return denied();
   if(!await verify(fromHex(record.passwordHash),String(body.challenge),body.proof))return denied();
   const session=JSON.stringify({purpose:'social',username,expires:Date.now()+12*3600000,nonce:toHex(crypto.getRandomValues(new Uint8Array(16)))});
   const token=btoa(session)+'.'+await sign(fromHex(config.signingKey),session);
   const response=json({ok:true,username,account:{username,displayName:record.displayName,playerId:record.playerId,gm:true}});response.headers.set('Set-Cookie',`pirate_session=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200${url.protocol==='https:'?'; Secure':''}`);return response;
  }
  return json({detail:'Not found.'},404);
 }catch{return denied();}
}
