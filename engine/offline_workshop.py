"""Native artifact crafting and equipment forge response/state contracts."""
import secrets


class OfflineWorkshop:
    handled_ids = {1356, 1357, 1358, 1750, 1751, 1752}

    def __init__(self, store):
        self.store = store
        self.recipes = {int(r['refId']): r for r in store.table('EquipCompoundRef')}
        self.levels = sorted(int(r['level']) for r in store.table('EquipWorkshopLevelRef'))
        self.lucky = sorted(store.table('EquipWorkshopLuckyRef'), key=lambda r: int(r['refId']))

    def fail(self, code, message):
        from offline_core import SimulationError
        raise SimulationError(code, message)

    @staticmethod
    def pick(rows):
        total = sum(int(r['weight']) for r in rows)
        value = secrets.randbelow(total)
        for row in rows:
            value -= int(row['weight'])
            if value < 0:return row

    def dispatch(self, s, cid, p):
        st = self.store
        info = s.setdefault('workshop', {'level': self.levels[0], 'round': int(self.lucky[0]['refId']), 'score': 0})
        if info['level'] not in self.levels:info['level'] = self.levels[0]
        if not any(int(r['refId']) == info['round'] for r in self.lucky):info['round'] = int(self.lucky[0]['refId'])
        fails = s.setdefault('artifactCraftFails', {})
        if cid in (1356, 1358):
            counts=fails if cid==1356 else s.get('suitCraftFails',{})
            return {'vos': [{'refId': int(k), 'failCount': v} for k, v in counts.items()]}, False, 'reference-driven'
        if cid == 1357:
            rid, count = int(p.get('refId', 0)), int(p.get('count', 1))
            row = self.recipes.get(rid)
            if not row or not 1 <= count <= 1000:self.fail('INVALID_CRAFT', 'Choose a captured artifact recipe and 1–1,000 attempts.')
            st._spend(s, row['reqGoods'], count)
            rewards = []; fail = int(fails.get(str(rid), 0))
            for _ in range(count):
                chance = min(10000, int(row['successRate']) + fail * int(row['addRate']))
                if secrets.randbelow(10000) < chance:
                    rewards += st._grant(s, row['targetGoods']); fail = 0
                else:fail += 1
            fails[str(rid)] = fail
            return {'rewards': rewards, 'failCount': fail}, True, 'reference-driven'
        if cid == 1750:return {'info': info}, False, 'reference-driven'
        if cid == 1752:
            level = int(p.get('level', 0))
            if level not in self.levels:self.fail('INVALID_FORGE_LEVEL', 'Choose a captured forge level.')
            info['level'] = level
            return {'info': info}, True, 'simulated'
        item, count = int(p.get('itemId', 0)), int(p.get('count', 0))
        cost = next((r for r in st.table('EquipWorkshopCostRef') if int(r['refId']) == item and int(r['level']) == info['level']), None)
        if not cost or not 1 <= count <= 1000:self.fail('INVALID_FORGE', 'Choose a forge material and 1–1,000 attempts.')
        rows = [r for r in st.table('EquipWorkshopOrderRef') if int(r['refId']) == item and int(r['level']) == info['level'] and int(r['weight']) > 0]
        points = next((int(r['score']) for r in st.table('EquipWorkshopItemRef') if int(r['refId']) == item), 0)
        if not rows:self.fail('MISSING_FORGE_POOL', 'No captured equipment pool for this material/level.')
        st._spend(s, f'1_{item}_{int(cost["num"]) * count}')
        s.setdefault('progression',{})['gearForged']=int(s.get('progression',{}).get('gearForged',0))+count
        equips = []
        for _ in range(count):
            lucky = next(r for r in self.lucky if int(r['refId']) == info['round'])
            info['score'] += points
            eligible = rows
            if info['score'] >= int(lucky['score']):
                guaranteed = [r for r in rows if int(st.equips[int(r['equipRefId'])]['order']) == int(lucky['assignOrder'])]
                if guaranteed:eligible = guaranteed
                info['score'] = 0
                index = self.lucky.index(lucky)
                info['round'] = int(self.lucky[(index + 1) % len(self.lucky)]['refId'])
            row = self.pick(eligible)
            sequence = max([int(e['equipId']) - 8800000000000 for e in s['equipment']] + [0]) + 1
            equip = st._equip_vo(int(row['equipRefId']), sequence)
            s['equipment'].append(equip); equips.append(equip)
        return {'info': info, 'equips': equips}, True, 'simulated'
