// Bind every read/write to the captain connected in this window. A different
// tab can replace the cookie at any time; the server checks the same intent.
export async function socialRequest({api,connected,username,disconnect},path,body){
 if(!connected||!username)throw Error('Connect social features for this captain first.');
 const local=await api('/api/me');
 if(local.account.username!==username){disconnect();throw Error('Captain changed. Reconnect social features for this account.');}
 try{return await api('/sandbox-social/'+path,body,{'X-Pirate-Captain':username});}
 catch(error){if(error.status===401||error.code==='CAPTAIN_MISMATCH')disconnect();throw error;}
}
