import unittest,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import test_tester_fixes as fixture

class FeatureRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.TesterRegressionTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):self.store.reset('pirate01');self.store.prepare_test_sandbox('pirate01')
    def state(self):return self.store.snapshot('pirate01')
    def cmd(self,cid,**p):return self.store.command('pirate01',cid,p)
    def good(self,result):self.assertTrue(result['ok'],result.get('error'));return result['reply']
    def power(self,gid=2000001):return self.store.stats.evaluate(self.state())[str(gid)]['power']
    def train(self):
        s=self.state()
        for g in s['generals'].values():g['level']=115
        self.store._write('pirate01',s)
    def kill_all(self):
        while True:
            s=self.state();a=s['activeInstance']
            if a.get('settled'):return
            actor=next(r for r in a['data']['sprites'] if r['type']==1)
            enemies=[r for r in a['data']['sprites'] if r['type']==2 and r['labile']['hp']['cur']>0]
            self.assertTrue(enemies)
            self.good(self.cmd(50010,vo=[{'atkSpriteId':actor['uid'],'tarSpriteId':r['uid'],'damage':r['labile']['hp']['cur']} for r in enemies]))
    def test_fruit_unlock_equip_transfer_remove_and_combat_skill(self):
        fruit=7000001;gids=[2000003,2000004];s=self.state()
        for gid in gids:s['generals'][str(gid)]=self.store._general_vo(gid,95,21)
        self.store._write('pirate01',s)
        self.assertFalse(self.cmd(1308,generalId=gids[0],devilFruit=fruit)['ok'])
        before=self.state()['inventory'][str(fruit)];self.good(self.cmd(1311,refId=fruit))
        self.assertEqual(self.state()['inventory'][str(fruit)],before-1)
        self.assertIn(fruit,self.good(self.cmd(1310))['refIds'])
        self.good(self.cmd(1308,generalId=gids[0],devilFruit=fruit))
        row=next(g for g in self.good(self.cmd(1300))['generals'] if g['generalId']==gids[0])
        self.assertIn(500101,row['skillIds'])
        reply=self.good(self.cmd(1308,generalId=gids[1],devilFruit=fruit));self.assertEqual(len(reply['generals']),2)
        self.assertEqual(self.state()['generals'][str(gids[0])]['devilFruit'],0)
        row=self.good(self.cmd(1309,generalId=gids[1]))['general'];self.assertNotIn(500101,row['skillIds'])
    def test_skin_starts_at_one_and_passive_bonus_does_not_require_wearing(self):
        rid=16003001;gid=2000003;s=self.state();s['generals'][str(gid)]=self.store._general_vo(gid,95,21);self.store._write('pirate01',s)
        before=self.power(gid);self.assertEqual(self.good(self.cmd(1314,skinId=rid))['vo']['star'],1)
        self.assertGreater(self.power(gid),before);self.assertEqual(self.state()['generals'][str(gid)]['skinId'],0)
        self.assertEqual(self.good(self.cmd(1315,skinId=rid))['vo']['star'],2)
        s=self.state();s['generalSkins'][str(rid)]['star']=0;self.store._write('pirate01',s)
        self.assertEqual(self.state()['generalSkins'][str(rid)]['star'],1)
    def test_pet_collection_adds_new_power_at_activation(self):
        self.good(self.cmd(2601,refId=4000001));before=self.power()
        result=self.cmd(2603,petId=4000001);self.good(result)
        self.assertGreater(self.power(),before);self.assertTrue(any(b['id']==1302 for b in result['broadcasts']))
    def test_pink_gear_requires_appraisal_and_real_stats_apply(self):
        self.train();s=self.state();typ=int(self.store.generals[2000001]['type'])
        e=next(e for e in s['equipment'] if int(self.store.equips[e['equipRefId']]['needAuth']) and int(self.store.equips[e['equipRefId']]['generalType'])==typ and int(self.store.equips[e['equipRefId']]['needLevel'])<=115)
        self.assertEqual(self.cmd(1351,generalId=2000001,equipId=e['equipId'])['error']['code'],'GEAR_NOT_IDENTIFIED')
        self.good(self.cmd(1360,equipId=e['equipId']));before=self.power();self.good(self.cmd(1351,generalId=2000001,equipId=e['equipId']))
        self.assertGreater(self.power(),before)
        values=self.store.stats.evaluate(self.state())['2000001']['values'];self.assertGreater(values[1],0)
    def test_preloads_have_no_phantom_equipment_stacks_and_normal_rolls(self):
        s=self.state();self.assertFalse(set(map(int,s['inventory']))&set(self.store.equips))
        e=next(e for e in s['equipment'] if not int(self.store.equips[e['equipRefId']]['needAuth']) and int(self.store.equips[e['equipRefId']]['randomAttrNum'])>0)
        self.assertTrue(e['randomAttrRefIds']);old=list(e['randomAttrRefIds']);self.assertEqual(next(x for x in self.state()['equipment'] if x['equipId']==e['equipId'])['randomAttrRefIds'],old)
    def test_gear_rewards_create_real_instances(self):
        s=self.state();rid=next(iter(self.store.equips));before=len(s['equipment']);self.store._grant(s,f'1_{rid}_2');self.store._write('pirate01',s)
        self.assertEqual(len(self.state()['equipment']),before+2);self.assertNotIn(str(rid),self.state()['inventory'])
    def test_ship_star_material_chart_dock_cabin(self):
        before=self.power();self.good(self.cmd(3403,refId=11000001));self.assertGreater(self.power(),before)
        self.good(self.cmd(3404,refId=11000001,addNum={'refId':1143,'count':2}))
        self.assertEqual(self.good(self.cmd(3401))['ships'][0]['materials'][0]['count'],2)
        self.assertFalse(self.cmd(3404,refId=11000001,addNum={'refId':1143,'count':10000})['ok'])
        self.assertEqual(self.good(self.cmd(3405))['dockLv'],1);self.assertEqual(self.good(self.cmd(3414))['cabin'],1)
        self.assertEqual(self.good(self.cmd(3406,chartId=14010011))['chart']['star'],1)
        self.assertEqual(self.good(self.cmd(3407,chartId=14010011))['chart']['star'],2)
        info=self.good(self.cmd(3400));self.assertIn('onHookInfo',info);self.assertIsInstance(info['rooms'],list)
    def test_haki_path_and_poster_activation_add_bonuses(self):
        before=self.power();self.good(self.cmd(1551,refId=1,part=1));self.assertGreater(self.power(),before)
        before=self.power();self.good(self.cmd(1318,refId=1001));self.assertGreater(self.power(),before)
        self.assertTrue(self.good(self.cmd(1300))['foorprints'])
        rid=101;s=self.state();gid=2000024;s['generals'][str(gid)]=self.store._general_vo(gid,95,1);self.store._write('pirate01',s)
        before=self.power(gid);self.good(self.cmd(10151,refId=rid));self.assertGreater(self.power(gid),before)
    def test_ship_collect_is_well_shaped_empty_and_idempotent(self):
        before=self.state()['inventory'];r=self.good(self.cmd(3410));self.assertEqual(r['rewards'],[]);self.assertIn('lastSettlementTime',r['onHook']);self.good(self.cmd(3417));self.assertEqual(self.state()['inventory'],before)
    def test_tower_completion_rewards_once_and_advances_voyage_floor(self):
        self.assertEqual(self.good(self.cmd(2000))['info']['refId'],0)
        self.good(self.cmd(51002,refId=201,lv=1));self.good(self.cmd(2002));self.kill_all()
        result=self.good(self.cmd(2003,isWin=True));self.assertTrue(result['reward']);self.assertEqual(result['info']['refId'],1);self.assertEqual(self.state()['towerFloor'],2)
        inv=self.state()['inventory'];self.assertEqual(self.good(self.cmd(2003,isWin=True))['reward'],[]);self.assertEqual(self.state()['inventory'],inv)
    def test_zero_position_dungeon_markers_spawn_near_scene_entrance(self):
        for ref in [101,111]:
            self.store.reset('pirate01');self.store.prepare_test_sandbox('pirate01');r=self.good(self.cmd(51002,refId=ref,lv=1));data=r['data'];hero=next(s for s in data['sprites'] if s['type']==1)
            enemies=[s for s in data['sprites'] if s['type']==2];self.assertTrue(enemies)
            for enemy in enemies:self.assertLess(abs(enemy['labile']['pos']['x']-hero['labile']['pos']['x']),1000)
    def test_local_solo_practice_has_enemies_stage_payload_and_final_rewards(self):
        result=self.cmd(51002,refId=27001,lv=1);self.good(result);self.assertTrue(any(b['id']==51009 for b in result['broadcasts']))
        self.kill_all();s=self.state();self.assertTrue(s['activeInstance']['success']);self.assertTrue(s['activeInstance']['data']['rewards'])
    def test_fleet_squad_create_survive_reload_and_follow_up_queries(self):
        r=self.good(self.cmd(2902,name='Test Fleet',declaration='Offline testers',autoApply=True,badgeRefId=1,baseMapRefId=1));self.assertEqual(r['guildInfo']['guild']['guild']['memberCount'],1)
        self.assertTrue(self.good(self.cmd(2908))['memberInfos']);self.good(self.cmd(2916));self.assertEqual(self.good(self.cmd(2904))['guildInfo']['type'],1)
        self.good(self.cmd(30003,name='Test Squad',avatarRefId=20101));self.assertTrue(self.good(self.cmd(30001))['team']['members']);self.good(self.cmd(30006));self.good(self.cmd(30016))
    def test_rare_hunt_and_world_chests_collect_once(self):
        self.good(self.cmd(10160));r=self.good(self.cmd(10161,rareType=1,buyType=1));self.assertTrue(r['reward']);self.assertEqual(r['rareInfo']['continueCount'],1)
        boxes=self.good(self.cmd(50201,sceneId=2))['vos'];self.assertTrue(boxes);r=self.good(self.cmd(50202,sceneId=2,uid=boxes[0]['uid'],rate=1));self.assertTrue(r['rewards'])
        inv=self.state()['inventory'];self.assertFalse(self.cmd(50202,sceneId=2,uid=boxes[0]['uid'],rate=1)['ok']);self.assertEqual(self.state()['inventory'],inv)
    def test_secret_chamber_bosses_and_safe_leave(self):
        r=self.good(self.cmd(54002,subActivityId='brawlSub_1'));self.assertTrue(any(x['type']==2 for x in r['data']['sprites']));self.assertEqual(r['type'],3)
        self.good(self.cmd(54003,subActivityId='brawlSub_1'));self.assertTrue(self.state()['activeInstance']['left'])
    def test_cosmetics_permanent_expiry_correct_types_and_space_default(self):
        s=self.state();self.assertEqual(s['player']['personality']['mainRoleSkin'],60001)
        self.assertGreater(s['personalities']['60001']['endTime'],self.store.systems.now())
        for typ,field in [(3,'avatarFrameRefId'),(4,'chatFrameRefId'),(5,'title'),(6,'mainRoleSkin')]:
            row=next(r for r in self.store.table('PersonalityRef') if int(r['type'])==typ and r.get('cost') and int(r.get('effectSecond') or 0)==0)
            rid=int(row['refId']);self.good(self.cmd(2504,refId=rid));result=self.cmd(2502,type=typ,refId=rid);self.good(result)
            self.assertEqual(self.state()['player']['personality'][field],rid)
            self.assertGreater(self.state()['personalities'][str(rid)]['endTime'],self.store.systems.now())
            self.assertTrue(any(b['id']==2503 for b in result['broadcasts']))
    def test_talent_all_maxes_both_tracks_without_spending(self):
        before=self.state();result=self.store.gm('pirate01','talentAll','');self.good(result);after=self.state()
        self.assertEqual(set(after['talent']['refIds']),set(self.store.progression.talents))
        self.assertEqual(set(after['talent']['advanceIds']),set(self.store.progression.advanced_talents))
        self.assertEqual(before['inventory'],after['inventory']);self.assertGreater(self.power(),self.store.stats.evaluate(before)['2000001']['power'])
        self.good(self.store.gm('pirate01','talentAll',''));self.assertEqual(after['talent'],self.state()['talent'])
    def test_active_crew_resonance_is_captured_id_and_adds_attributes(self):
        self.good(self.store.gm('pirate01','generalMax',''));s=self.state();reply=self.good(self.cmd(1300));echo=reply['echoRefId']
        self.assertIn(echo,{int(r['refId']) for r in self.store.table('GeneralEchoRef')});self.assertGreater(echo,0)
        sources=self.store.stats.evaluate(s)['2000001']['sources'];self.assertTrue(any(r['source']==f'Active crew resonance {echo}' for r in sources))
    def test_mount_reins_clamp_and_persist_progress_at_maximum(self):
        item=next(iter(self.store.companions.rein_items));self.good(self.cmd(2704,itemId=item,itemCount=1000000));s=self.state()
        maximum=int(self.store.companions.rein_rows[-1]['startExp'])
        self.assertEqual(s['inventory']['113'],maximum);self.assertEqual(s['companion']['reinExp'],maximum)
        before=s['inventory'];self.assertEqual(self.cmd(2704,itemId=item,itemCount=1)['error']['code'],'MAX_MOUNT_REIN');self.assertEqual(before,self.state()['inventory'])
    def test_registered_name_has_an_independent_safe_local_save(self):
        from offline_accounts import atomic_json
        username='test_captain';records=self.store.accounts._records();records['users'][username]={'username':username,'displayName':username,'playerId':9000000000021,'salt':'11'*16,'passwordHash':'22'*32,'gm':True};atomic_json(self.store.accounts.path,records)
        self.store._write(username,self.store._seed(username));state=self.store.prepare_test_sandbox(username)
        self.assertEqual(state['playerId'],9000000000021);self.assertNotEqual(state['playerId'],self.state()['playerId'])
        self.assertTrue(self.store._path(username).is_relative_to(self.store.saves))

    def test_movement_reuses_stats_without_full_roster_broadcast(self):
        s=self.state();self.store.stats.evaluate(s)
        with patch.object(self.store.stats,'_evaluate',wraps=self.store.stats._evaluate) as calculate:
            result=self.cmd(50004,centerPos={'x':s['scene']['x']+1,'y':s['scene']['y']})
            self.good(result)
            self.assertEqual(calculate.call_count,0)
            self.assertFalse(any(b['id'] in (1007,1302) for b in result['broadcasts']))

    def test_stat_cache_invalidates_boost_and_emits_one_roster(self):
        s=self.state();self.store.stats.evaluate(s)
        for key in ('talent','treasures','gemSlots','shipyard','personalities','suitStages'):
            changed=dict(s);changed[key]={'cache-test':{'refId':1,'lv':1}}
            if key=='shipyard':changed[key]={'lv':987}
            self.assertNotEqual(self.store.stats.signature(s),self.store.stats.signature(changed))
        result=self.cmd(1301,generalId=2000001);self.good(result)
        self.assertEqual(sum(b['id']==1302 for b in result['broadcasts']),1)
