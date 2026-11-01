import {spawnSync} from 'node:child_process';import fs from 'node:fs';
const alias=process.argv[process.argv.indexOf('--alias')+1];
if(!/^pr-\d+$/.test(alias||''))throw Error('Use --alias pr-<number>.');
if(!process.env.CLOUDFLARE_API_TOKEN||!process.env.CLOUDFLARE_ACCOUNT_ID)throw Error('Configure the separate preview environment first; see docs/DEPLOYMENT.md.');
const r=spawnSync(process.execPath,['node_modules/wrangler/bin/wrangler.js','versions','upload','--config','wrangler.preview.jsonc','--preview-alias',alias],{encoding:'utf8'});
process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');if(r.status!==0)process.exit(r.status||1);
if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,'### Source preview\n\n```text\n'+r.stdout+'\n```\n');
