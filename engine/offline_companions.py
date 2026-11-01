"""Reference-bounded companion progression and repair of older sandbox saves."""
from copy import deepcopy


class OfflineCompanions:
    handled_ids = set(range(2600, 2607)) | set(range(2700, 2708)) | {2709}

    def __init__(self, store):
        self.store = store
        self.pet_rows = {(int(r['refId']), int(r['order'])): r for r in store.table('PetStageRef')}
        self.star_rows = {(int(r['refId']), int(r['star'])): r for r in store.table('MountStarRef')}
        self.level_rows = {(int(r['refId']), int(r['level'])): r for r in store.table('MountLevelRef')}
        self.book_rows = {int(r['order']): r for r in store.table('PetBookStageRef')}
        self.rein_rows = sorted(store.table('MountStageRef'), key=lambda r: int(r['startExp']))
        self.rein_items = {int(r['refId']): int(r['exp']) for r in store.table('MountStageItemRef')}

    def fail(self, code, message):
        from offline_core import SimulationError
        raise SimulationError(code, message)

    @staticmethod
    def bounded(value, keys):
        keys = sorted(keys)
        value = int(value or 0)
        return max((key for key in keys if key <= value), default=keys[0])

    def repair(self, s):
        # Repair once and persist through the store read path. Valid progression
        # is retained; invalid former over-cap values map to the last real row.
        before = deepcopy((s.get('pets'), s.get('mounts'), s.get('companion'),s.get('inventory',{}).get('113')))
        seen = set()
        for pet in s.get('pets', []):
            keys = [stage for rid, stage in self.pet_rows if rid == int(pet['refId'])]
            if keys:
                pet['stage'] = self.bounded(pet.get('stage'), keys)
        s['pets'] = [p for p in s.get('pets', []) if int(p['refId']) in self.store.pets]
        s['mounts'] = [m for m in s.get('mounts', []) if int(m['refId']) in self.store.mounts]
        for mount in s['mounts']:
            rid = int(mount['refId']); row = self.store.mounts[rid]
            mount['star'] = self.bounded(mount.get('star'), [v for k, v in self.star_rows if k == rid])
            mount['level'] = self.bounded(mount.get('level'), [v for k, v in self.level_rows if k == int(row['order'])])
            gid = int(mount.get('generalId', 0))
            if not gid or str(gid) not in s['generals'] or gid in seen:
                mount.update(generalId=0, use=False)
            else:
                seen.add(gid)
                mount['use'] = bool(mount.get('use', False))
        c = s.setdefault('companion', {})
        c.setdefault('bookStage', 0); c.setdefault('bookGroupPetIds', []); c.setdefault('petSkills', [])
        c.setdefault('activeRewardIds', []); c.setdefault('mountStage', int(self.rein_rows[0]['refId']))
        c['mountStage']=self.bounded(c['mountStage'],[int(r['refId']) for r in self.rein_rows])
        current=next(r for r in self.rein_rows if int(r['refId'])==c['mountStage'])
        exp=min(int(self.rein_rows[-1]['startExp']),max(int(c.get('reinExp',0)),int(s['inventory'].get('113',0)),int(current['startExp'])))
        c['reinExp']=exp;s['inventory']['113']=exp
        c['mountStage']=int(max((r for r in self.rein_rows if int(r['startExp'])<=exp),key=lambda r:int(r['startExp']))['refId'])
        return before != (s.get('pets'), s.get('mounts'), s.get('companion'),s.get('inventory',{}).get('113'))

    def dispatch(self, s, cid, p):
        self.repair(s)
        c = s['companion']; store = self.store
        if cid == 2600:
            return {'pets': s['pets'], 'bookStage': c['bookStage'], 'bookGroupPetIds': c['bookGroupPetIds'], 'petSkills': c['petSkills'], 'appearId': s['settings'].get('petAppearId', 0)}, False, 'reference-driven'
        if cid == 2601:
            rid = int(p.get('refId', 0))
            if rid not in store.pets:self.fail('UNKNOWN_PET', 'Select a captured pet.')
            pet = next((r for r in s['pets'] if r['refId'] == rid), None)
            stage = int(pet['stage']) + 1 if pet else 1
            row = self.pet_rows.get((rid, stage))
            if not row:self.fail('MAX_PET_STAGE', 'This pet is at its maximum captured star level.')
            store._spend(s, row['cost'])
            if pet:pet['stage'] = stage
            else:
                pet = {'refId': rid, 'stage': stage}; s['pets'].append(pet)
            return {'pets': pet}, True, 'reference-driven'
        if cid == 2602:
            row = self.book_rows.get(int(c['bookStage']) + 1)
            if not row:self.fail('MAX_PET_BOOK', 'Pet book is at its captured maximum.')
            store._spend(s, row['cost']); c['bookStage'] += 1
            return {'bookStage': c['bookStage']}, True, 'reference-driven'
        if cid == 2603:
            rid = int(p.get('petId', 0))
            if rid not in {r['refId'] for r in s['pets']}:self.fail('PET_NOT_OWNED', 'Activate the pet first.')
            if rid in c['bookGroupPetIds']:self.fail('ALREADY_ACTIVE', 'Pet book entry is already active.')
            c['bookGroupPetIds'].append(rid)
            return {'bookGroupPetIds': c['bookGroupPetIds']}, True, 'reference-driven'
        if cid in (2604, 2605):
            index = int(p.get('index', 0))
            if not 1 <= index <= 5:self.fail('INVALID_PET_SLOT', 'Select pet skill slot 1–5.')
            skills = [r for r in c['petSkills'] if r['index'] != index]
            if cid == 2604:
                required=[1,50,100,150,200][index-1]
                if int(c['bookStage'])<required:self.fail('PET_BOOK_STAGE_REQUIRED',f'This skill slot requires Pet Book stage {required}.')
                skill = int(p.get('skillId', 0))
                pet = next((r for r in s['pets'] if int(store.pets[r['refId']]['skillRefId']) == skill), None)
                if not pet:self.fail('PET_SKILL_LOCKED', 'Activate the pet for this skill first.')
                if any(r['skillId'] == skill for r in skills):self.fail('DUPLICATE_PET_SKILL', 'This skill is already equipped.')
                skills.append({'index': index, 'skillId': skill})
            c['petSkills'] = skills
            return {'petSkills': skills}, True, 'reference-driven'
        if cid == 2606:
            rid = int(p.get('refId', 0))
            if rid and rid not in {r['refId'] for r in s['pets']}:self.fail('PET_NOT_OWNED', 'Activate the pet before selecting its appearance.')
            s['settings']['petAppearId'] = rid
            return {'appearId': rid}, True, 'reference-driven'
        if cid == 2700:
            return {'mounts': s['mounts'], 'mountStage': c['mountStage'], 'activeRewardIds': c['activeRewardIds']}, False, 'reference-driven'
        if cid == 2704:
            item = int(p.get('itemId', 0)); count = int(p.get('itemCount', 0))
            if item not in self.rein_items or not 1 <= count <= 1000000:self.fail('INVALID_REIN_ITEM', 'Choose a valid rein material and quantity.')
            current = next(r for r in self.rein_rows if int(r['refId']) == c['mountStage'])
            if c['mountStage'] == int(self.rein_rows[-1]['refId']):self.fail('MAX_MOUNT_REIN', 'Mount reins are at the captured maximum.')
            exp = max(int(c.get('reinExp', 0)), int(current['startExp']))
            remaining = max(0, int(self.rein_rows[-1]['startExp']) - exp)
            count = min(count, max(1, (remaining + self.rein_items[item] - 1) // self.rein_items[item]))
            store._spend(s, f'1_{item}_{count}'); exp = min(int(self.rein_rows[-1]['startExp']),exp+count*self.rein_items[item])
            c['reinExp'] = exp
            c['mountStage'] = int(max((r for r in self.rein_rows if int(r['startExp']) <= exp), key=lambda r: int(r['startExp']))['refId'])
            # The original rein UI reads the exp item; this is a progress counter.
            exp_id = self.rein_exp_id()
            if exp_id:s['inventory'][str(exp_id)] = exp
            return {'mountStage': c['mountStage']}, True, 'reference-driven'
        rid = int(p.get('refId', 0)); gid = int(p.get('generalId', 0))
        mount = next((m for m in s['mounts'] if m['refId'] == rid), None)
        if cid in (2707, 2709):mount = next((m for m in s['mounts'] if m['generalId'] == gid and gid), None)
        if cid == 2701:
            if mount:self.fail('ALREADY_ACTIVE', 'This mount is already active.')
            row = store.mounts.get(rid)
            if not row:self.fail('UNKNOWN_MOUNT', 'Select a captured mount.')
            store._spend(s, row['cost'])
            mount = {'refId': rid, 'level': int(row['initLevel']), 'star': int(row['initStar']), 'generalId': 0, 'use': False}
            s['mounts'].append(mount)
        elif cid == 2705:
            if not mount:self.fail('MOUNT_NOT_OWNED', 'Activate the mount first.')
            if rid in c['activeRewardIds']:self.fail('ALREADY_CLAIMED', 'Activation reward is already claimed.')
            reward = store._grant(s, store.mounts[rid]['activeReward']); c['activeRewardIds'].append(rid)
            return {'activeRewardIds': c['activeRewardIds'], 'reward': reward}, True, 'reference-driven'
        elif not mount:self.fail('MOUNT_NOT_OWNED', 'Activate and assign this mount first.')
        elif cid in (2702, 2703):
            field = 'level' if cid == 2702 else 'star'; nxt = int(mount[field]) + 1
            row = self.level_rows.get((int(store.mounts[rid]['order']), nxt)) if cid == 2702 else self.star_rows.get((rid, nxt))
            if not row:self.fail('MAX_MOUNT_LEVEL' if cid == 2702 else 'MAX_MOUNT_STAR', 'This mount is at its captured maximum.')
            store._spend(s, row['cost']); mount[field] = nxt
        elif cid == 2706:
            if str(gid) not in s['generals']:self.fail('GENERAL_NOT_OWNED', 'Select an owned character.')
            changed = []
            for other in s['mounts']:
                if other is not mount and other['generalId'] == gid:
                    other.update(generalId=0, use=False); changed.append(other)
            mount.update(generalId=gid, use=True); changed.append(mount)
            return {'mounts': changed}, True, 'reference-driven'
        elif cid == 2707:mount.update(generalId=0, use=False)
        elif cid == 2709:mount['use'] = not mount['use']
        return {'mount': mount}, True, 'reference-driven'

    def rein_exp_id(self):
        return 113  # EItemRefId.MountReinExp; consumable rein materials use fnType 5.
