import {captainSession,validCaptain,captainRecord} from './captain-auth.mjs';
const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});
const valid=validCaptain;
const pair=(a,b)=>[a,b].sort().join(':');
const clean=(value,max)=>String(value||'').replace(/[\u0000-\u0008\u000b-\u001f]/g,'').trim().slice(0,max);
export async function social(request,env){
 const u=await captainSession(request,env);if(!u)return json({error:'Connect your captain to social features first.'},401);
 if(!env.DB)return json({error:'Social storage is unavailable.'},503);
 const url=new URL(request.url),db=env.DB,now=Date.now();
 if(request.method!=='GET'&&request.method!=='POST')return json({error:'Method not allowed.'},405);
 if(request.method==='POST'&&request.headers.get('Origin')!==url.origin)return json({error:'Origin not allowed.'},403);
 let body={};if(request.method==='POST'){const raw=await request.text();if(raw.length>50000)return json({error:'Request too large.'},413);try{body=JSON.parse(raw);}catch{return json({error:'Invalid JSON.'},400);}}
 const run=(sql,...args)=>db.prepare(sql).bind(...args).run(),all=async(sql,...args)=>(await db.prepare(sql).bind(...args).all()).results,one=(sql,...args)=>db.prepare(sql).bind(...args).first();
 const member=async id=>(await one('SELECT * FROM room_members WHERE room=? AND username=?',id,u))||(await one('SELECT host FROM rooms WHERE id=? AND host=?',id,u));
 const membersFor=async room=>{
  const rows=await all('SELECT username,ready,team,joined FROM room_members WHERE room=? ORDER BY joined',room.id);
  if(!rows.some(r=>r.username===room.host))rows.unshift({username:room.host,ready:0,team:'[]',joined:room.created});
  const after=Number(JSON.parse(room.settings).readyAfter||0);
  return rows.map(r=>({...r,ready:r.ready&&r.joined>=after?1:0,team:JSON.parse(r.team)}));
 };
 try{
  await run('INSERT INTO captains(username,last_seen) VALUES(?,?) ON CONFLICT(username) DO UPDATE SET last_seen=excluded.last_seen',u,now);
  const action=url.pathname.slice('/sandbox-social/'.length);
  if(action==='state'&&request.method==='GET'){
   const friends=await all('SELECT * FROM friends WHERE sender=? OR recipient=?',u,u);
   const captains=await all('SELECT username,last_seen FROM captains');
   const rooms=await all("SELECT id,host,name,status,settings,deadline,created FROM rooms WHERE status!='closed' AND created>? ORDER BY created DESC LIMIT 20",now-86400000);
   return json({username:u,serverTime:now,friends,captains,rooms:rooms.map(r=>({...r,settings:JSON.parse(r.settings)}))});
  }
  if(action==='friend'&&request.method==='POST'){
   const other=String(body.username||'').trim().toLowerCase();if(!valid(other)||other===u)return json({error:'Choose another captain.'},400);
   if(!await captainRecord(env,JSON.parse(env.CAPTAIN_AUTH_CONFIG),other))return json({error:'No captain has that username.'},404);
   const id=pair(u,other),row=await one('SELECT * FROM friends WHERE id=?',id);
   if(body.action==='request'){
    if(row&&row.status!=='declined')return json({error:'A request or friendship already exists.'},409);
    await run('INSERT INTO friends(id,sender,recipient,status,updated) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET sender=excluded.sender,recipient=excluded.recipient,status=excluded.status,updated=excluded.updated',id,u,other,'pending',now);
   }else if(body.action==='accept'||body.action==='decline'){
    if(!row||row.recipient!==u||row.status!=='pending')return json({error:'No incoming request from this captain.'},403);
    await run('UPDATE friends SET status=?,updated=? WHERE id=?',body.action==='accept'?'accepted':'declined',now,id);
   }else if(body.action==='remove')await run('DELETE FROM friends WHERE id=? AND (sender=? OR recipient=?)',id,u,u);
   else return json({error:'Unknown friend action.'},400);
   return json({ok:true});
  }
  if(action==='messages'){
   const recipient=String(body.recipient||url.searchParams.get('recipient')||''),room=String(body.room||url.searchParams.get('room')||'');
   if(room){if(!await member(room))return json({error:'Join this lobby to read or send chat.'},403);}
   else if(!valid(recipient)||!(await one("SELECT id FROM friends WHERE id=? AND status='accepted'",pair(u,recipient))))return json({error:'Direct chat requires an accepted friend.'},403);
   if(request.method==='GET')return json({messages:room?await all('SELECT id,sender,body,created FROM messages WHERE room=? ORDER BY created DESC LIMIT 60',room):await all('SELECT id,sender,body,created FROM messages WHERE room IS NULL AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?)) ORDER BY created DESC LIMIT 60',u,recipient,recipient,u)});
   const text=clean(body.text,1000);if(!text)return json({error:'Write a message first.'},400);
   const recent=await one('SELECT COUNT(*) AS n FROM messages WHERE sender=? AND created>?',u,now-60000);if(recent.n>=20)return json({error:'Message limit reached. Try again shortly.'},429);
   await run('INSERT INTO messages(id,sender,recipient,room,body,created) VALUES(?,?,?,?,?,?)',crypto.randomUUID(),u,room?null:recipient,room||null,text,now);return json({ok:true});
  }
  if(action==='create'&&request.method==='POST'){
   const active=await one("SELECT COUNT(*) AS n FROM rooms WHERE host=? AND status!='closed' AND created>?",u,now-86400000);if(active.n>=3)return json({error:'Close an existing lobby before creating another.'},409);
   const id=crypto.randomUUID(),name=clean(body.name,60)||`${u}'s lobby`;
   // Host membership is derived from the room: creating a lobby is one atomic
   // insert rather than a room/member pair which could be partially initialized.
   await run('INSERT INTO rooms(id,host,name,status,settings,deadline,created) VALUES(?,?,?,?,?,?,?)',id,u,name,'open',JSON.stringify({timerEnabled:false,countdownSeconds:30,readyAfter:0}),null,now);
   return json({ok:true,id});
  }
  const id=String(body.room||url.searchParams.get('room')||''),room=await one('SELECT * FROM rooms WHERE id=?',id);
  if(!room||room.created<now-86400000)return json({error:'Lobby not found or expired.'},404);
  if(action==='join'&&request.method==='POST'){
   if(room.status!=='open')return json({error:'This lobby is no longer open.'},409);
   if(room.host!==u)await run('INSERT OR IGNORE INTO room_members(id,room,username,ready,team,joined) SELECT ?,?,?,0,?,? WHERE (SELECT COUNT(*) FROM room_members WHERE room=? AND username!=?)<1',id+':'+u,id,u,'[]',now,id,room.host);
   if(!await member(id))return json({error:'This lobby is full.'},409);return json({ok:true});
  }
  if(!await member(id))return json({error:'You are not a member of this lobby.'},403);
  if(action==='room'&&request.method==='GET')return json({room:{...room,settings:JSON.parse(room.settings)},members:await membersFor(room),serverTime:now});
  if(action==='leave'&&request.method==='POST'){
   if(room.host===u)await run("UPDATE rooms SET status='closed',deadline=NULL WHERE id=?",id);
   else {await run("UPDATE rooms SET status='open',deadline=NULL WHERE id=?",id);await run('DELETE FROM room_members WHERE room=? AND username=?',id,u);}
   return json({ok:true});
  }
  if(action==='ready'&&request.method==='POST'){
   if(room.status!=='open')return json({error:'Reset the lobby before changing teams.'},409);
   const team=body.team;
   if(!Array.isArray(team)||team.length>10||team.some(r=>!Number.isInteger(r.generalId)||!r.attrs||typeof r.attrs!=='object')||JSON.stringify(team).length>30000)return json({error:'Invalid shared team.'},400);
   await run('INSERT INTO room_members(id,room,username,ready,team,joined) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET ready=excluded.ready,team=excluded.team,joined=excluded.joined',id+':'+u,id,u,body.ready&&team.length?1:0,JSON.stringify(team),now);return json({ok:true});
  }
  if(room.host!==u)return json({error:'Only the host can control lobby timers and starts.'},403);
  if(action==='settings'&&request.method==='POST'){
   const settings={...JSON.parse(room.settings),timerEnabled:body.timerEnabled===true,countdownSeconds:Math.max(5,Math.min(300,Math.trunc(Number(body.countdownSeconds)||30)))};
   const deadline=room.status==='countdown'&&settings.timerEnabled?now+settings.countdownSeconds*1000:null;
   await run('UPDATE rooms SET settings=?,deadline=?,status=? WHERE id=?',JSON.stringify(settings),deadline,room.status==='countdown'&&!settings.timerEnabled?'open':room.status,id);return json({ok:true});
  }
  if(action==='start'&&request.method==='POST'){
   const members=await membersFor(room);
   if(members.length!==2||members.some(r=>!r.ready||!r.team.length))return json({error:'Both captains must share a team and be ready.'},409);
   const settings=JSON.parse(room.settings),deadline=settings.timerEnabled?now+settings.countdownSeconds*1000:null;
   await run('UPDATE rooms SET status=?,deadline=? WHERE id=?',settings.timerEnabled?'countdown':'started',deadline,id);return json({ok:true});
  }
  if(action==='reset'&&request.method==='POST'){
   await run("UPDATE rooms SET status='open',deadline=NULL,settings=? WHERE id=?",JSON.stringify({...JSON.parse(room.settings),readyAfter:now}),id);return json({ok:true});
  }
  return json({error:'Unknown social action.'},404);
 }catch{return json({error:'Social request failed. Please try again.'},500);}
}
