import {spawnSync} from 'node:child_process';import fs from 'node:fs';
const python=process.env.PIRATE_PYTHON||'python';
function run(cmd,args){const r=spawnSync(cmd,args,{stdio:'inherit'});if(r.error)throw r.error;if(r.status!==0)process.exit(r.status||1);}
run(python,['-X','utf8','-m','unittest','discover','-s','tests','-p','test_*.py']);
for(const name of fs.readdirSync('tests').filter(n=>n.endsWith('.mjs')&&n.startsWith('test-')))run(process.execPath,['tests/'+name]);
if(fs.existsSync('engine/data/tables/GeneralRef.csv'))run(python,['tools/project.py','integration']);else console.log('Captured-data integration suite not run: import a permitted local asset pack first. Source-only tests completed.');
