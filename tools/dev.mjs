import fs from 'node:fs';
import {spawnSync,spawn} from 'node:child_process';
import {randomBytes} from 'node:crypto';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');process.chdir(root);
const python=process.env.PIRATE_PYTHON||'python';
function run(file,args){const r=spawnSync(file,args,{stdio:'inherit',shell:process.platform==='win32'&&file==='npm'});if(r.error)throw r.error;if(r.status!==0)process.exit(r.status||1);}
if(!fs.existsSync('node_modules/wrangler/bin/wrangler.js'))run('npm',['ci','--no-audit','--no-fund']);
run(python,['tools/project.py','build']);fs.mkdirSync('.local',{recursive:true});
if(!fs.existsSync('.local/dev.vars'))fs.writeFileSync('.local/dev.vars','CAPTAIN_AUTH_CONFIG='+JSON.stringify({users:{},signingKey:randomBytes(32).toString('hex')})+'\n',{mode:0o600});
run(process.execPath,['node_modules/wrangler/bin/wrangler.js','d1','migrations','apply','DB','--local','--config','wrangler.jsonc']);
const child=spawn(process.execPath,['node_modules/wrangler/bin/wrangler.js','dev','--local','--config','wrangler.jsonc','--env-file','.local/dev.vars','--ip','127.0.0.1','--port',process.env.PORT||'8787','--inspector-port','0'],{stdio:'inherit'});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));child.on('exit',code=>process.exit(code||0));
