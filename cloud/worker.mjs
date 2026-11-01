import {captainAuth} from './captain-auth.mjs';
import {social} from './social.mjs';
import {gameAssistant} from './game-assistant.mjs';
import aliases from './asset-aliases.json';
export default {async fetch(request,env){
 const url=new URL(request.url);
 if(url.pathname==='/health')return Response.json({ok:true,service:'pirate-crew',localAccountsOnly:!env.PRODUCTION});
 if(url.pathname.startsWith('/captain-auth/'))return captainAuth(request,env);
 if(url.pathname.startsWith('/sandbox-social/'))return social(request,env);
 if(url.pathname==='/game-assistant/answer')return gameAssistant(request,env);
 if(Object.hasOwn(aliases,url.pathname)){url.pathname=aliases[url.pathname];return env.ASSETS.fetch(new Request(url,request));}
 const result=await env.ASSETS.fetch(request);
 if(!url.pathname.startsWith('/game/')&&!url.pathname.startsWith('/assets/')){const headers=new Headers(result.headers);headers.set('Cache-Control','no-cache');headers.set('X-Content-Type-Options','nosniff');return new Response(result.body,{status:result.status,headers});}
 return result;
}};
