"""Compile permitted local reference tables into an on-site guide catalog.

Output is captured data: keep it under .local/assets, never in the source PR.
No network requests; no guessed stats or synthetic artwork.
"""
from pathlib import Path, PurePosixPath
import argparse, csv, json, re

SYSTEMS = {
 'pets': ('PetRef','refId', [('Pet_All_Skill_Levels','pet_id'),('PetStageRef','refId')]),
 'mounts': ('MountRef','refId',[('Mount_Skill_Unlocks','mount_id'),('MountStarRef','refId')]),
 'treasures': ('TreasureRef','refId',[('Treasure_Character_Groups','treasure_id'),('TreasureStarRef','refId')]),
 'gems': ('GemRef','refId',[('Gem_Stats_All_Levels','gem_id')]),
 'gear': ('EquipRef','refId',[]),
 'ships': ('ShipsRef','refId',[('Ship_Character_Groups','ship_id'),('ShipsStarRef','refId')]),
 'posters': ('PirateReportRef','refId',[('Poster_Recipients_and_Levels','poster_id'),('PirateReportLevelRef','refId')]),
 'skins': ('GeneralSkinRef','skinId',[('Skin_All_Stars_and_Skill_Entries','skin_id'),('Skin_Mechanical_Entries_English','skin_id')]),
 'relics': ('UniqueRef','refId',[('Relic_Effects_All_Levels','relic_id'),('UniqueLvRef','refId')]),
 'characters': ('GeneralRef','refId',[('Character_Skill_Timing','character_id')]),
}

def decode_packed(values):
    if not isinstance(values,list) or not values or not isinstance(values[0],int) or values[0]<1:
        raise ValueError('Invalid packed table header')
    width=values[0]; cols=values[1:width+1]; body=values[width+1:]
    if len(cols)!=width or len(set(cols))!=width or len(body)%width:
        raise ValueError('Malformed packed table')
    return [dict(zip(cols,map(lambda v: '' if v is None else str(v),body[i:i+width]))) for i in range(0,len(body),width)]

def load_tables(directory):
    out={}
    for path in sorted(Path(directory).rglob('*.csv')):
        with path.open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream)
            if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames):
                raise ValueError('Invalid CSV header: '+path.name)
            rows=list(reader)
            if any(None in r or any(v is None for v in r.values()) for r in rows): raise ValueError('Malformed CSV: '+path.name)
            out[path.stem]=rows
    return out

def safe_icon(asset, groups, types, manifest):
    group=groups.get(asset.get('group'),{}).get('group','')
    ext=types.get(asset.get('type'),{}).get('type','png')
    name=asset.get('name','')
    logical=f'{group}/{name}.{ext}'
    physical=manifest.get(logical,logical)
    path=PurePosixPath(physical)
    if not name or not group or ext not in ('png','jpg','jpeg','webp') or path.is_absolute() or '..' in path.parts or not re.fullmatch(r'[\w./-]+',physical): return None
    return '/game/'+physical

def index(rows,key='refId'):
    return {str(r.get(key,'')):r for r in rows}

def compile_catalog(tables, manifest=None, build='local import'):
    manifest=manifest or {}
    assets=index(tables.get('AssetsRef',[])); groups=index(tables.get('AssetsGroupRef',[])); types=index(tables.get('AssetsTypeRef',[])); items=index(tables.get('ItemRef',[]))
    catalog={'schemaVersion':1,'build':str(build),'evidence':'Captured client configuration; not live-server verification','systems':{}}
    for system,(table,key,joins) in SYSTEMS.items():
        entities=[]
        joined={}
        for name,jkey in joins:
            grouped={}
            for row in tables.get(name,[]): grouped.setdefault(row.get(jkey,''),[]).append(row)
            joined[name]=grouped
        for row in tables.get(table,[]):
            identity=row.get(key,''); item=items.get(identity,{})
            name=row.get('english_name') or row.get('name') or item.get('english_name') or item.get('name') or f'{table} {identity}'
            icon_id=row.get('icon') or item.get('icon'); icon=safe_icon(assets.get(icon_id,{}),groups,types,manifest)
            fields={k:v for k,v in row.items() if v and k not in ('name','source_name','english_name')}
            related=[{'table':t,'rows':byid.get(identity,[])} for t,byid in joined.items() if byid.get(identity)]
            entities.append({'id':identity,'name':name,'icon':icon,'quality':row.get('quality') or row.get('color') or item.get('quality',''),'fields':fields,'related':related})
        if system=='mounts':
            for entity in entities:
                source=next((r for r in tables.get(table,[]) if r.get(key)==entity['id']),{})
                levels=[r for r in tables.get('MountLevelRef',[]) if r.get('refId')==source.get('order')]
                if levels: entity['related'].append({'table':'MountLevelRef','rows':levels})
        catalog['systems'][system]=entities
    reference_names={
      'pets':['PetBookGroupRef','PetBookStageRef','PetSkillIndexRef'],
      'mounts':['MountStageRef','MountStageItemRef','MountBookGroupRef'],
      'gems':['GemSlotRef','Gem_Stats_All_Levels'],
      'gear':['Gear_Random_Affix_Pools','Gear_Set_Bonuses_English'],
      'ships':['ShipsDockLvRef','ShipsCabinRef','ShipsMaterialRef','ShipsCookbookRef'],
      'treasures':['TreasureMaterialRef'],
      'control':['Buff_Status_Catalog'],
      'damage':['Stat_Keyword_Glossary'],
      'drops':['Weighted_Pool_Shares','Reward_Routes_English_Items'],
    }
    catalog['references']={system:[{'table':name,'rows':tables[name]} for name in names if tables.get(name)] for system,names in reference_names.items()}
    return catalog

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tables',required=True,type=Path);p.add_argument('--packed',type=Path);p.add_argument('--manifest',type=Path);p.add_argument('--build',default='local import');p.add_argument('--out',required=True,type=Path);args=p.parse_args()
    tables=load_tables(args.tables)
    # Current raw values take precedence. Keep only authored/derived English
    # explanations from matching CSV rows; never overwrite current numeric data.
    if args.packed:
        for path in sorted(args.packed.glob('*.json')):
            if not re.fullmatch(r'(?:preRef|ref\d+)\.json',path.name): continue
            for name,packed in json.loads(path.read_text()).items():
                current=decode_packed(packed)
                old=tables.get(name,[])
                if old and current:
                    key=next((k for k in ('refId','skillId','skinId','buffId','skillEffectId') if k in current[0]),None)
                    # Join progression rows on their complete key. A refId-only
                    # join would label every level with the final level's stats.
                    keys=[key]+[k for k in ('level','lv','star','order','stageLv','part','type','lock') if k in current[0]] if key else []
                    row_key=lambda r: tuple(str(r.get(k,'')) for k in keys)
                    old_index={row_key(r):r for r in old} if keys else {}
                    for row in current:
                        prior=old_index.get(row_key(row),{})
                        for k,v in prior.items():
                            if k.endswith('_english'):
                                raw=k[:-8]
                                if raw in row and str(prior.get(raw,''))!=str(row[raw]):continue
                            if k.endswith('_english') or k in ('english_name','source_name'): row[k]=v
                tables[name]=current
    manifest=json.loads(args.manifest.read_text()) if args.manifest else {}
    catalog=compile_catalog(tables,manifest,args.build)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':'))+'\n')
    print('Compiled '+str(sum(map(len,catalog['systems'].values())))+' guide entities to '+str(args.out))

if __name__=='__main__': main()
