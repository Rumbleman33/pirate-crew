"""Portable build/import/release tools. No game-server downloads or credentials."""
from pathlib import Path, PurePosixPath
import argparse, ast, csv, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / '.local/assets'
DATA = ROOT / 'engine/data'
DENIED = {'accounts.json', 'sessions.json', 'browser-session.json', 'test-logins.txt', 'browser-logins.txt', '.dev.vars'}
TREES = {'game', 'pyodide', 'assets', 'data', 'documents', 'knowledge', 'references', 'vendor'}
EXTRA = {'asset-routing.json'}

def safe_name(name):
    p = PurePosixPath(name.replace('\\', '/'))
    return bool(name) and not p.is_absolute() and not re.match(r'^[A-Za-z]:', name) and '..' not in p.parts and not any(x.lower() in DENIED or x.lower() in {'runtime', 'saves', 'backups', '.git'} or (x.startswith('.env') and x!='.env.example') for x in p.parts)

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

def import_pack(source):
    source = Path(source).expanduser().resolve()
    if (source/'public/simulation.zip').is_file(): source = source/'public'
    if not (source/'simulation.zip').is_file(): raise ValueError('Select the v15 public directory containing simulation.zip, game/ and pyodide/.')
    planned = []
    for top in sorted(TREES | EXTRA | {'play'}):
        target = source/top
        if target.is_symlink(): raise ValueError('Symlink imports are not supported.')
        paths = sorted(target.rglob('*')) if target.is_dir() else [target]
        for path in paths:
            if path.is_symlink(): raise ValueError('Symlink imports are not supported.')
            if not path.is_file(): continue
            rel = path.relative_to(source).as_posix()
            if top == 'play' and path.name not in {'english-extra.json','offline-english-extra.json','offline-english-coverage.json','featured-skins.json'}: continue
            if not safe_name(rel): raise ValueError(f'Private or unsafe import path rejected: {rel}')
            planned.append((path, rel))
    archive = source/'simulation.zip'
    with zipfile.ZipFile(archive) as z:
        selected = []
        for item in z.infolist():
            name = item.filename
            if not (name.startswith('data/') or name in {'public/game/i18n/en.json','public/english-extra.json','public/offline-english-extra.json'}): continue
            if not safe_name(name): raise ValueError(f'Unsafe simulation entry: {name}')
            if item.file_size > 40_000_000: raise ValueError('Unexpectedly large simulation entry.')
            if not item.is_dir(): selected.append(item)
        if sum(i.file_size for i in selected) > 100_000_000: raise ValueError('Simulation data exceeds import limit.')
        manifests = []
        for item in selected:
            dest = ROOT/'engine'/item.filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = z.read(item); dest.write_bytes(data)
            manifests.append({'path':'engine/'+item.filename,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    for path, rel in planned:
        dest=ASSETS/rel; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path,dest)
        manifests.append({'path':rel,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
    write_json(ROOT/'.local/import-manifest.json', {'version':1,'files':manifests})
    print(f'Imported {len(manifests)} local files. No accounts, secrets or captured Python modules were imported.')
    validate()

def validate(directory=None):
    directory=Path(directory) if directory else DATA/'tables'
    # Unconditional seed/read dependencies, plus the existing boss contracts.
    required={'GeneralRef':['refId','type','speed'],'MonsterRef':['refId'],
              'SceneRef':['refId'],'TowerLevelRef':['refId','monsterId'],
              'MountStageRef':['refId','startExp','endExp'],
              'VoyageTitleRef':['refId','maxLevel','next','attrs']}
    rows={};errors=[]
    for path in sorted(directory.glob('*.csv')):
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader=csv.DictReader(f)
            if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)):errors.append(path.name+': missing or duplicate column');continue
            values=list(reader)
            if any(None in r or any(v is None for v in r.values()) for r in values): errors.append(path.name+': malformed CSV row')
            rows[path.stem]=values
            for key in required.get(path.stem,[]):
                if key not in reader.fieldnames:errors.append(path.name+': missing '+key)
    for table in required:
        if not rows.get(table):errors.append('Required table missing or empty: '+table)
    keys={'GeneralRef':('refId',),'MonsterRef':('refId',),'SceneRef':('refId',),'TowerLevelRef':('refId',),'GeneralSkinRef':('skinId',),'GeneralLvRef':('generalId','lv'),'SuitStageRef':('refId','part','stageLv'),'ShipsStarRef':('refId','star')}
    for table,columns in keys.items():
        seen=set()
        for row in rows.get(table,[]):
            key=tuple(row.get(k) for k in columns)
            if None in key or '' in key or key in seen:errors.append(f'{table}: duplicate/invalid key {key}')
            seen.add(key)
    monster_ids={r.get('refId') for r in rows.get('MonsterRef',[])};scene_ids={r.get('refId') for r in rows.get('SceneRef',[])};general_ids={r.get('refId') for r in rows.get('GeneralRef',[])}
    for row in rows.get('TowerLevelRef',[]):
        for mid in row.get('monsterId','').split('#'):
            if mid not in monster_ids:errors.append(f'Tower floor {row.get("refId")}: missing monster {mid}')
    for row in rows.get('RefreshMonsterRef',[]):
        if row.get('type')=='2' and (row.get('monsterId') not in monster_ids or row.get('sceneId') not in scene_ids):errors.append('Map boss has an invalid scene or monster')
    for row in rows.get('NpcRef',[]):
        if row.get('type')=='5' and int(row.get('bossId') or 0)>0 and (row['bossId'] not in monster_ids or row.get('sceneId') not in scene_ids or row.get('data') not in scene_ids):errors.append('Island challenge has an invalid source/destination/monster')
    for row in rows.get('GeneralSkinRef',[]):
        if row.get('generalId') not in general_ids:errors.append('Skin refers to an unknown character: '+str(row.get('skinId')))
    for table,columns in required.items():
        for row in rows.get(table,[]):
            for column in columns:
                if column in {'attrs','monsterId'}:continue
                try:
                    value=int(row[column])
                    if column in {'refId','maxLevel','type','speed'} and value<=0:raise ValueError()
                except (KeyError,TypeError,ValueError):errors.append(f'{table}: invalid integer {column}')
    if not any(r.get('refId')=='1' for r in rows.get('VoyageTitleRef',[])):
        errors.append('VoyageTitleRef: required initial title refId 1 is missing')
    if errors:raise ValueError('\n'.join(errors[:30]))
    startup_smoke(directory)
    if directory == DATA/'tables':validate_metadata(directory.parent)
    print(f'Validated {len(rows)} tables / {sum(map(len,rows.values()))} rows and critical boss/skin joins.')
    return rows

def validate_metadata(data):
    """Protocol metadata is a separate contract from table/startup validation."""
    try:
        catalog=json.loads((data/'catalog.json').read_text(encoding='utf8'))
        schemas=json.loads((data/'schemas.json').read_text(encoding='utf8'))
        if not isinstance(catalog,dict) or not isinstance(catalog.get('commands'),list) or not catalog['commands'] or not isinstance(catalog.get('initCommandIds'),list):
            raise ValueError('catalog.json: expected nonempty commands and initCommandIds')
        ids=[r['id'] for r in catalog['commands']]
        if any(type(i) is not int for i in ids) or len(ids)!=len(set(ids)) or any(type(i) is not int or i not in ids for i in catalog['initCommandIds']):
            raise ValueError('catalog.json: invalid command IDs or initialization references')
        if not isinstance(schemas,dict) or not schemas or any(not isinstance(r,dict) or not isinstance(r.get('fields'),list) for r in schemas.values()):
            raise ValueError('schemas.json: expected named schemas with field lists')
    except (OSError,KeyError,TypeError,json.JSONDecodeError) as error:
        raise ValueError(f'Runtime protocol metadata is missing or invalid: {error}') from error

def startup_smoke(directory):
    """Exercise seed, normalization and reload using disposable local accounts."""
    engine=str(ROOT/'engine')
    if engine not in sys.path:sys.path.insert(0,engine)
    from offline_core import OfflineStore
    try:
        with tempfile.TemporaryDirectory(prefix='pirate-startup-') as folder:
            store=OfflineStore(folder,data_path=directory)
            store.snapshot('pirate01')
            reloaded=OfflineStore(folder,data_path=directory)
            reloaded.snapshot('pirate01')
    except Exception as error:
        raise ValueError(f'Captain startup/load failed for candidate tables: {type(error).__name__}: {error}') from error

def build():
    dist=ROOT/'dist'
    # Explicit workspace-bound target; never follow a directory junction.
    if dist.is_symlink() or dist.resolve().parent!=ROOT:raise ValueError('Unsafe build output')
    if dist.exists():shutil.rmtree(dist)
    if ASSETS.exists():shutil.copytree(ASSETS,dist)
    else:dist.mkdir()
    shutil.copytree(ROOT/'web/public',dist,dirs_exist_ok=True)
    full=(DATA/'tables/GeneralRef.csv').is_file() and (dist/'game/bundle-offline.js').is_file() and (dist/'pyodide/pyodide.js').is_file()
    if full:
        validate()
        with zipfile.ZipFile(dist/'simulation.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for path in sorted((ROOT/'engine').glob('*.py')):z.write(path,path.name)
            for folder in [DATA,ROOT/'engine/public']:
                for path in sorted(folder.rglob('*')):
                    rel=path.relative_to(ROOT/'engine').as_posix()
                    if path.is_file() and safe_name(rel):z.write(path,rel)
        # Keep indexed code current after contributors change simulator modules.
        index=dist/'knowledge/index.json'
        if index.exists():
            knowledge=json.loads(index.read_text(encoding='utf8'));docs=[d for d in knowledge.get('documents',[]) if not d.get('source','').startswith('/knowledge/code/')]
            for path in sorted((ROOT/'engine').glob('offline_*.py')):
                text=path.read_text(encoding='utf8');out=dist/'knowledge/code'/path.name;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text,encoding='utf8')
                lines=text.splitlines()
                for start in range(0,len(lines),24):docs.append({'title':f'Code {path.name} lines {start+1}-{min(start+32,len(lines))}','text':'\n'.join(lines[start:start+32]),'source':'/knowledge/code/'+path.name,'kind':'code','group':path.name})
            knowledge['documents']=docs;write_json(index,knowledge)
    else:
        shutil.copy2(ROOT/'web/contributor.html',dist/'index.html')
    write_json(dist/'build-info.json',{'mode':'full-local-game' if full else 'source-preview','sourceVersion':'v15'})
    print('Built '+('full local game' if full else 'source-only contributor preview')+'.')

def source_files():
    candidates=[ROOT/p for p in ['README.md','LICENSE','ASSETS.md','SECURITY.md','CONTRIBUTING.md','package.json','.env.example','.gitignore']]
    for folder in ['engine','web','cloud','tools','tests','docs','.github','config']:
        for path in (ROOT/folder).rglob('*'):
            rel=path.relative_to(ROOT)
            if path.is_file() and '__pycache__' not in rel.parts and not any(x in {'__pycache__','data','public','runtime'} for x in rel.parts[:2] if folder=='engine'):candidates.append(path)
    return sorted(set(candidates))

def release_check():
    errors=[]
    try:
        tracked=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode().split('\0')
    except (OSError,subprocess.CalledProcessError):tracked=[]
    for name in tracked:
        if name and (not safe_name(name) or name.startswith(('.local/','dist/','engine/data/','engine/public/')) or name.endswith(('.apk','.aab','.zip','.pem','.key'))):errors.append('Forbidden tracked file: '+name)
    patterns=[re.compile(r'gsk_' + r'[A-Za-z0-9]{20,}'),re.compile(r'(?:ghp_|github_pat_)' + r'[A-Za-z0-9_]{20,}'),re.compile(r'-----BEGIN ' + r'(?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
    scan=set(source_files()) | {ROOT/name for name in tracked if name and (ROOT/name).is_file()}
    for path in sorted(scan):
        if not safe_name(path.relative_to(ROOT).as_posix()):errors.append('Forbidden source path: '+str(path.relative_to(ROOT)));continue
        try:text=path.read_text(encoding='utf8')
        except UnicodeDecodeError:errors.append('Unexpected binary source: '+str(path.relative_to(ROOT)));continue
        if any(p.search(text) for p in patterns):errors.append('Possible secret in '+str(path.relative_to(ROOT)))
        if re.search(r'C:[/\\]Users[/\\]',text,re.I):errors.append('Developer-specific path in '+str(path.relative_to(ROOT)))
        if path.suffix=='.py':
            try:ast.parse(text,filename=str(path))
            except SyntaxError as e:errors.append(str(e))
    if errors:raise ValueError('\n'.join(errors))
    print(f'Release source check passed: {len(source_files())} source files; no detected credential formats, runtime records or private paths.')

def integration():
    validate()
    subprocess.run([sys.executable,'-X','utf8','-m','unittest','discover','-s','engine/tests','-p','test_*.py'],cwd=ROOT,check=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['import','validate','build','check','release','integration']);parser.add_argument('--from',dest='source');args=parser.parse_args()
    try:
        if args.command=='import':
            if not args.source:parser.error('--from is required')
            import_pack(args.source)
        elif args.command=='validate':validate()
        elif args.command=='build':build()
        elif args.command=='integration':integration()
        else:release_check()
    except (ValueError,OSError,subprocess.CalledProcessError,zipfile.BadZipFile) as error:print(str(error),file=sys.stderr);sys.exit(1)
