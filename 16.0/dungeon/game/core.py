"""对局主体：初始化、地牢生成、主循环。"""


# === IMPORTS ===
import pygame
import random
from .. import gallery
from .. import savegame
from ..bosses import create_boss, pick_boss_for_scene
from ..bosses.roster import StitchedBoss
from ..data.biomes import (BIOME_CHURCH, BIOME_GREAT_TOMB, BIOME_ICE,
                           BIOME_NORMAL, BIOME_POISON, BIOME_SNOW, BIOME_TEMPLE)
from ..data.enemies import BIOME_ENEMY_POOL
from ..data.modes import MODES, MODE_ALL_ELITE, MODE_CLASSIC, MODE_ELITE_HELL, MODE_ENEMY_CAP, MODE_SUMMONER
from ..data.skills import SKILL_DATA
from ..entities.affix import AFFIX_TABLE, draw_affix_shield
from ..entities.enemies import EliteEnemy, Enemy
from ..entities.player import Player
from ..entities.projectiles import LavaPool
from ..entities.props import Barrier, Crystal, IceTrap, Platform
from ..entities.units import FloatingText
from ..settings import FPS, POISON_GREEN, SCREEN_HEIGHT, SCREEN_WIDTH, SETTINGS, SHOP_PAGES, clock, screen
from ..timing import advance_frame, frame_count, ms
from ..stats import RunStats
from ..utils import back_hit, present, reward_cat_at, window_to_screen
from ..world.background import draw_background
# === /IMPORTS ===

class GameCoreMixin:
    def __init__(self, mode=MODE_CLASSIC):
        self.mode = mode if mode in MODES else MODE_CLASSIC
        mode_cfg = MODES[self.mode]
        self.mode_name = mode_cfg["name"]
        self.start_crystals = mode_cfg.get("start_crystals", 0)
        self.free_shop = mode_cfg.get("free_shop", False)
        self.all_elite_mode = self.mode in MODE_ALL_ELITE
        self.enemy_cap = MODE_ENEMY_CAP.get(self.mode, 20)
        self.current_depth = 0
        self.all_sprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.bombs = pygame.sprite.Group()
        self.barriers = pygame.sprite.Group()
        self.traps = pygame.sprite.Group()
        self.ice_trails = pygame.sprite.Group()
        self.crystals = pygame.sprite.Group()
        self.mirrors = pygame.sprite.Group()
        self.boss = None
        self.boss_type = None
        self.nova_waves = pygame.sprite.Group()
        self.ice_spikes = pygame.sprite.Group()
        self.warnings = pygame.sprite.Group()
        self.summon_circles = pygame.sprite.Group()
        self.fireballs = pygame.sprite.Group()
        self.flame_walls = pygame.sprite.Group()
        self.lava_pools = pygame.sprite.Group()
        self.embers = pygame.sprite.Group()
        self.hook_projectiles = pygame.sprite.Group()
        self.skill_fireballs = pygame.sprite.Group()
        self.black_hole_bullets = pygame.sprite.Group()
        self.black_holes = pygame.sprite.Group()
        self.ice_shards = pygame.sprite.Group()
        self.meteors = pygame.sprite.Group()
        self.ground_waves = pygame.sprite.Group()
        self.floating_texts = pygame.sprite.Group()
        self.event_goals = pygame.sprite.Group()
        self.allies = pygame.sprite.Group()
        self.snow_drifts = pygame.sprite.Group()      # 雪山：暴风雪留下的疏雪层
        self.storm_crystals = pygame.sprite.Group()   # 寺庙：金色水晶
        self.church_crosses = pygame.sprite.Group()   # 教堂：尚未/已经调查的十字架
        self.gravestones = pygame.sprite.Group()      # 古代大墓地：会唤醒僵尸的墓碑
        self.soul_shocks = pygame.sprite.Group()      # 炼魂魔骷：无视护盾的灵魂冲击

        self.initial_enemy_count = 0
        self.left_barrier = None
        self.right_barrier = None
        self.transitioning = False
        self.scene_cleared = False
        self.last_kill_count = 0
        self.reward_points = 0
        self.scene_type = BIOME_NORMAL
        self.paused = False
        self.show_rules = False
        self.show_enemy_info = False
        self.show_reward_info = False
        self.show_shop = False
        self.shop_items = []
        self.shop_page = 0
        self.selected_enemy_idx = 0
        self.gallery_category = "all"
        self.gallery_place = "all"
        self.selected_reward_cat = 0
        self.is_boss_room = False
        self.boss_defeated = False
        self.ice_field_timer = 0
        self.elite_banner_timer = 0
        self.elite_banner_name = ""
        self.frame = 0
        self.mouse = None          # 这一帧的鼠标位置（已换算到逻辑坐标）
        self.message_text = ""
        self.message_start_frame = 0
        self.message_duration = 0
        self.auto_fire_active = False

        # 战斗统计、图鉴记账与死亡归因
        self.stats = RunStats()
        self.codex_kills = {}
        self.codex_deaths = {}
        self.lethal_source = None
        self.soul_reaper_shield_death = False
        self.enhance_counts = {}      # 各强化已拿次数，用于给移速/跳跃封顶
        self.achievements_unlocked = []

        # 生态区域与天气
        self.region_biome = None          # 当前区域是什么生态；None 表示在普通地牢的空档里
        self.region_rooms_left = 0        # 区域还剩几间（含当前这间）
        self.normal_gap_chance = 1.0      # 继续是普通地牢的概率，按 0.9/0.8…递减
        self.temple_seen = False          # 本个雪山区域是否已经出过寺庙
        self.nested_seen = set()          # 本个连续生态里已经出现过的嵌套房
        self.blizzard_timer = 0           # 暴风雪剩余帧数
        self.blizzard_cooldown = 0
        self.blizzard_dir = 1
        self.blizzard_drift = 0.0         # 风力的像素余量（推力小于 1 像素/帧）

        self.is_event_room = False
        self.event_done = False
        self.event_kind = None
        self.event_title = ""
        self.event_choices = []
        self.event_altar = None
        self.pending_elite_reward = False
        self.pending_event_rewards = 0
        self.event_running = False
        self.event_timer = 0
        self.event_data = {}
        self.event_goal = None
        self.hunter_ghost = None
        self.core = None
        self.last_room_was_event = False
        self.soul_chain_targets = []
        self.soul_chain_timer = 0
        self.soul_chain_skill = None

        self.death_essence = 0
        self.active_curses = []      # 限时诅咒：[{name, attr, applied, rooms}]
        self.pending_room_affixes = []   # 词缀熔炉：下一房间要挂给敌人的词缀

        self.player = Player()
        self.player.damage_reporter = self.note_player_damage
        self.all_sprites.add(self.player)

        # 模式差异化的开局配置
        if self.start_crystals:
            self.player.crystals = self.start_crystals
        if self.mode == MODE_SUMMONER:
            # 三个槽位开局可用，但装的是捕捉来的召唤物而不是技能
            self.player.skill_slots = 3
        self.capture_slot = -1      # 正在捕捉的槽位，-1 表示没有
        self.captured = [None, None, None]   # 每个槽位记录被捕获敌人的模板
        self.summon_cd = [0, 0, 0]
        self.summoned = [None, None, None]   # 每个槽位绑定一只召唤物
        self.ally_out = [False, False, False]   # 它当前是否在场上

        self.enemy_descriptions = self._build_enemy_descriptions()
        self.reward_descriptions = self._build_reward_descriptions()
        self.game_rules = self._build_game_rules()
        self.rules_scroll = 0
        self.max_visible_rules = 14
        self.enhancements = self._build_enhancements()

        self.generate_dungeon()


    def _build_enemy_descriptions(self):
        return gallery.ENTRIES


    def _build_reward_descriptions(self):
        return [
            {"category": "基础资源", "items": [
                {"name": "生命值恢复", "desc": "恢复20点生命值"},
                {"name": "晶体", "desc": "在商店购买强化（E键打开）"},
                {"name": "炸弹", "desc": "鼠标左键引爆范围伤害"}
            ]},
            {"category": "属性强化", "items": [
                {"name": "跳跃高度", "desc": "+15%跳跃力度"},
                {"name": "攻击速度", "desc": "+20%攻击速度（间隔下限8帧）"},
                {"name": "移动速度", "desc": "+15%移动速度"},
                {"name": "最大生命值", "desc": "+5最大生命值（高权重）"},
                {"name": "攻击力", "desc": "固定+4基础攻击力（高权重）"},
                {"name": "精准射击", "desc": "穿透+1，攻击+10%"},
                {"name": "暴击伤害增加", "desc": "暴击时：(伤害+加成)×2倍"}
            ]},
            {"category": "技能相关", "items": [
                {"name": "学习新技能", "desc": "随机获得一个新技能（含天降陨火）"},
                {"name": "解锁技能槽 II", "desc": "开启 I 键技能槽"},
                {"name": "解锁技能槽 III", "desc": "开启 O 键技能槽（需先解锁II）"},
                {"name": "能量上限 +20", "desc": "提高最大能量值（高权重）"},
                {"name": "能量恢复 +0.5/秒", "desc": "加快能量回复速度"},
                {"name": "技能升级", "desc": "在商店第2页升级技能，无等级上限"},
                {"name": "技能进化", "desc": "在商店第2页选择进化分支（每个技能仅能选一个方向）"},
                {"name": "护盾·防战", "desc": "护盾期间攻击力+50%"},
                {"name": "冲刺·麻痹", "desc": "升级时眩晕时长同步提升"},
                {"name": "陨火·灵巧/灼烧", "desc": "吟唱可移动 / 火球留燃烧区"},
            ]},
            {"category": "特殊能力", "items": [
                {"name": "二段跳", "desc": "空中可再次跳跃"},
                {"name": "暴击", "desc": "先提升概率至60%，溢出转为暴击伤害"},
                {"name": "噬血·概率", "desc": "提升击杀回血触发概率（最高80%）"},
                {"name": "噬血·回血", "desc": "提升每次触发回血量"},
                {"name": "反伤", "desc": "受击时周围敌人掉5点血"},
                {"name": "防滑靴", "desc": "消除冰面滑行"},
                {"name": "爆破专家", "desc": "炸弹范围与持续伤害提升"},
                {"name": "应急护盾", "desc": "低血量自动激活"}
            ]},
            {"category": "事件房", "items": [
                {"name": "献祭祭坛", "desc": "以最大生命换取攻击/攻速/暴击"},
                {"name": "陷阱宝箱", "desc": "获得奖励后召唤敌人，深度越高名额越多"},
                {"name": "许愿井", "desc": "投晶体得强化/进化，投0晶体得诅咒"},
                {"name": "精英挑战", "desc": "召唤2精英，击败后获得强化与晶体"},
                {"name": "坠落炸弹挑战", "desc": "躲避20秒轰炸，奖励2次强化+5晶体"},
                {"name": "无尽追猎", "desc": "撑过20秒幽灵追猎，奖励3次强化"},
                {"name": "脆弱之路", "desc": "踩脆弱平台到达顶部水晶，成功得20晶体"},
                {"name": "精英车轮战", "desc": "连杀3精英，奖励5次强化+10晶体"},
                {"name": "镜像对决", "desc": "复制自己（含3个随机技能），胜利后可选择：晶体×20 或 为任意技能叠加进化"},
                {"name": "词缀熔炉", "desc": "给下个房间的敌人注入一条词缀，换1次强化+8晶体"},
                {"name": "属性交易所", "desc": "互换两项属性（生命↔能量 / 移速↔攻速 / 暴击↔噬血）"},
                {"name": "护核防守", "desc": "守住左侧核心30秒，敌人从右侧来袭且只攻击核心"},
                {"name": "深渊轮盘", "desc": "押生命或晶体转轮盘，6格：4奖励/1空白/1诅咒"}
            ]}
        ]


    def _build_game_rules(self):
        return [
            "游戏规则", "",
            "1. 基本操作:",
            "   A/D 移动    K 跳跃    J 射击",
            "   （可在主菜单设置页切换为自动射击模式）",
            "   U/I/O 释放技能    E 商店（消耗3晶体）",
            "   F 与事件祭坛、寺庙水晶或教堂十字架交互",
            "   鼠标左键放置炸弹",
            "   ESC 暂停 / 继续，暂停时按空格结束本局", "",
            "2. 生物群系:",
            "   普通地牢 / 冰晶洞穴 / 熔岩洞窟",
            "   腐沼秘境 / 亡灵墓穴", "",
            "3. 技能与能量:",
            "   初始只有 1 个技能槽（U键）且无技能",
            "   需通过强化/商店/事件获取技能",
            "   能量上限100，每秒恢复1.5点",
            "   技能升级无等级上限，威力线性成长", "",
            "4. 技能进化:",
            "   每个技能只能选择一个进化方向",
            "   选择后商店不再提供另一方向",
            "   镜像对决胜利可为技能叠加第二个进化", "",
            "5. 天降陨火:",
            "   按技能键进入吟唱，无法移动",
            "   再按一次退出吟唱",
            "   火球威力=普攻+技能附加",
            "   灵巧：吟唱中可移动",
            "   灼烧：火球落地留燃烧区（升级延长）", "",
            "6. Boss 反制机制:",
            "   已移除所有赖皮大范围震荡波",
            "   改为贴地横波（跳跃躲）/双层火环",
            "   骷髅骨龙死亡龙息可被破防打断",
            "   熔岩巨人自爆期间受伤×2", "",
            "7. 事件房:",
            "   非Boss层，深度≥2时有概率出现",
        "   靠近祭坛按 F 交互，做出选择",
        "   选择离开/放弃/什么都不做后解除边界",
        "   脆弱之路限时20秒", "",
            "   词缀熔炉：给下个房间敌人注入词缀换1次强化+8晶体",
            "   属性交易所：互换两项属性，也可以什么都不做",
            "   护核防守：敌人在右侧、核心在左侧，敌人只打核心",
            "   深渊轮盘：押生命或晶体，6格里4奖励1空白1诅咒", "",
            "8. 亡灵墓穴:",
            "   非亡灵单位死亡后原地生成骷髅；亡灵死亡不再转化",
            "   非亡灵死亡累积死亡气息，每10点生成巨型骷髅", "",
            "   僵尸移动极慢、血量厚、攻击低；死亡后生成幽魂",
            "   僵尸附近有非亡灵死亡时额外生成僵尸，巨型僵尸附近则生成巨型僵尸", "",
            "9. 生态区域:",
            "   一个生态持续 3~5 间房（往左回走也算），结束后必接一间普通地牢",
            "   之后每间继续是普通地牢的概率按 0.9 / 0.8 / 0.7… 递减，直到新区域开始",
            "   领主房沿用当前区域的生态（第一位于第10层，仍是普通地牢）", "",
            "10. 暴雪山脉:",
            "   每30秒刮一次暴风雪，持续6秒，期间有横向推风与飞雪挡视野",
            "   地面高低起伏但连续；风雪停后地上会留下疏雪层挡视线",
            "   疏雪层被玩家走过或任何爆炸波及都会消失",
            "   冰爪狼会瞄准玩家扑击，起跳后无视平台，跳得上低处、跳不上太高处",
            "   风灵不造成伤害，只会按风雪强度把人往外吹",
            "   巨魔一律是精英且自带再生：士兵体型大、猎手远程点射",
            "   巨魔狂呼者每15秒给半屏内的敌人增幅5秒（移速与攻击+50%，脚下红环）",
            "   巨雪怪结霜期间怕火：火焰类伤害翻倍", "",
            "11. 暴云寺庙:",
            "   它不是独立生态，而是雪山深处的一种房间（进入雪山房时20%概率出现）",
            "   出现寺庙会让雪山区域再延长3间；寺庙里没有风雪与落雪",
            "   最低的平台上会刷金色菱形水晶，靠近按 F 即可点亮",
            "   水晶朝最近的敌人射出金色光束，每秒伤害为当前攻击力的两倍，持续4秒",
            "   用完冷却20秒（水晶会暗淡并显示进度环），敌人打它会打断并进入冷却", "",
            "12. 古代大墓地:",
            "   亡灵墓穴的嵌套房，每段生态每种嵌套房最多出现一次",
            "   墓碑随机分布并每10秒唤醒僵尸，必须由玩家摧毁",
            "   载骨机吸收幽魂/骷髅，普通目标1道幽火，巨型骷髅3道",
            "   附近有敌人死亡时回血；累计5道幽火后进化为炼魂魔骷",
            "   炼魂魔骷的灵魂冲击与燃魂都会直接扣血，无视护盾", "",
            "13. 破败教堂:",
            "   亡灵墓穴里的嵌套房，每段生态最多出现一次，出现后区域延长2间",
            "   教堂必定有一只吸血鬼与一只三阶段石像鬼",
            "   血仆与血蝙蝠属于亡灵并自带吸血；吸血鬼只能抽这两种单位的血",
            "   吸血鬼受伤时会快速抽血，血族被抽干后会变成新的血仆",
            "   血腥十字架会召唤亡灵并强化半屏内敌人；圣光十字架回血并灼烧敌人",
            "   十字架调查前外观相同，靠近按 F 才会显露；两类都有实体与血量",
            "   血腥十字架只能被玩家攻击，圣光十字架只能被敌人攻击", "",
            "14. 强化:",
            "   每消灭10个敌人获得1次强化", "",
            "15. 特殊模式（主菜单 - 更多模式）:",
            "   词缀狂欢：开局30晶体，敌人至少1条词缀，数量无上限",
            "   亡灵潮：开局30晶体，非幽魂亡灵死亡化作幽灵，幽灵不再连锁",
            "   亡灵潮：精英与领主死亡降下巨大骷髅",
            "   亡灵潮：死亡气息常驻累积，满10点爆发",
            "   精英地狱：开局50晶体，商店免入场费",
            "   精英地狱：普通敌人全部变成精英，数量与血量不变",
            "   精英地狱：精英种类无视环境随机抽取",
            "   召唤师：U/I/O 开局可用，但装的是召唤物",
            "   召唤师：按技能键进入捕捉，击败敌人即收进该槽位",
            "   召唤师：再按一次放出盟友（复制其词缀）",
            "   召唤师：盟友出战期间再按一次即可收回，血量保留",
            "   召唤师：盟友阵亡后槽位直接清空，需要重新捕捉",
            "   召唤师：商店第2页可提升盟友生命/攻击/随机词缀",
            "   召唤师：普通盟友扫荡，精英盟友索敌最近的敌人",
            "   召唤师：盟友会被敌人攻击，飞行敌人优先缠住盟友",
        ]


    def _build_enhancements(self):
        return [
            {"name": "恢复20点生命值", "func": self.enhance_heal, "weight": 3},
            {"name": "增加跳跃高度", "func": self.enhance_jump, "weight": 2, "key": "jump"},
            {"name": "增加攻击速度", "func": self.enhance_attack_speed, "weight": 2},
            {"name": "增加移动速度", "func": self.enhance_move_speed, "weight": 2,
             "key": "move_speed"},
            {"name": "增加5点最大生命值", "func": self.enhance_max_health, "weight": 8},
            {"name": "增加攻击力(+4固定)", "func": self.enhance_attack_damage, "weight": 8},
            {"name": "能量上限 +20", "func": self.enhance_max_energy, "weight": 6},
            {"name": "获得3个炸弹", "func": self.enhance_bombs, "weight": 2},
            {"name": "精准射击（穿透+1，伤害+10%）", "func": self.enhance_piercing_bullets, "weight": 2},
            {"name": "二段跳", "func": self.enhance_double_jump, "weight": 2,
             "once": True, "check": lambda: self.player.double_jump},
            {"name": "防滑靴", "func": self.enhance_anti_slide, "weight": 1,
             "once": True, "check": lambda: self.player.anti_slide},
            {"name": "应急护盾", "func": self.enhance_emergency_shield, "weight": 1,
             "once": True, "check": lambda: self.player.emergency_shield},
            {"name": "暴击（率/倍率）", "func": self.enhance_crit, "weight": 3},
            {"name": "暴击伤害增加", "func": self.enhance_crit_damage, "weight": 4},
            {"name": "噬血·概率 +10%", "func": self.enhance_lifesteal_chance, "weight": 3,
             "check": lambda: self.player.lifesteal_chance >= 0.8},
            {"name": "噬血·回血 +1", "func": self.enhance_lifesteal_amount, "weight": 3},
            {"name": "反伤 (+5)", "func": self.enhance_thorns, "weight": 2},
            {"name": "爆破专家", "func": self.enhance_bomb_upgrade, "weight": 1},
            {"name": "能量恢复 +0.5/秒", "func": self.enhance_energy_regen, "weight": 3},
            {"name": "学习新技能", "func": self.enhance_new_skill, "weight": 4,
             "check": lambda: self._skills_all_known()},
            {"name": "解锁技能槽 II（I键）", "func": self.enhance_unlock_slot_i, "weight": 3,
             "once": True, "check": lambda: self.player.skill_slots >= 2},
            {"name": "解锁技能槽 III（O键）", "func": self.enhance_unlock_slot_o, "weight": 2,
             "once": True,
             "check": lambda: (self.player.skill_slots >= 3 or self.player.skill_slots < 2)},
        ]


    def _skills_all_known(self):
        kinds = set()
        for s in self.player.skills:
            if s: kinds.add(s.kind)
        return len(kinds) >= len(SKILL_DATA)


    def show_message(self, message, duration):
        self.message_text = message
        self.message_start_frame = frame_count()
        self.message_duration = ms(duration)

    def run_summary(self, highlights=None):
        """这一局的完整记录：结算面板与存档共用同一份。"""
        summary = self.stats.to_dict(highlights)
        summary.update({
            "mode": self.mode,
            "mode_name": self.mode_name,
            "depth": self.current_depth,
            "kills": self.player.kills,
            "frames": self.frame,
            "soul_reaper_shield_death": bool(self.soul_reaper_shield_death),
        })
        return summary


    def add_floating_text(self, x, y, text, color, size=20):
        ft = FloatingText(x, y, text, color, size)
        self.floating_texts.add(ft); self.all_sprites.add(ft)


    def clear_scene(self):
        for group in [self.platforms, self.enemies, self.bullets, self.bombs,
                      self.barriers, self.traps, self.ice_trails, self.crystals,
                      self.nova_waves, self.ice_spikes, self.warnings, self.summon_circles,
                      self.fireballs, self.flame_walls, self.lava_pools, self.embers,
                      self.mirrors, self.hook_projectiles, self.skill_fireballs,
                      self.black_hole_bullets, self.black_holes,
                      self.ice_shards, self.meteors, self.ground_waves,
                      self.floating_texts, self.event_goals,
                      self.snow_drifts, self.storm_crystals, self.church_crosses,
                      self.gravestones, self.soul_shocks]:
            # 注意：召唤物不在这里清，它们跟着玩家进下一个房间
            for sprite in list(group): sprite.kill()
        if self.boss is not None:
            self.boss.kill(); self.boss = None
        if self.event_altar is not None:
            self.event_altar.kill(); self.event_altar = None
        if self.hunter_ghost is not None:
            self.hunter_ghost.kill(); self.hunter_ghost = None
        if self.core is not None:
            self.core.kill(); self.core = None
        self.event_goal = None
        self.soul_chain_targets = []
        self.soul_chain_timer = 0
        self.soul_chain_skill = None


    def generate_dungeon(self):
        self.transitioning = True
        self.scene_cleared = False
        self.is_boss_room = (self.current_depth > 0 and self.current_depth % 10 == 0)
        self.boss_defeated = False
        self.ice_field_timer = 0
        self.player.stop_meteor()
        self.clear_scene()
        self.capture_slot = -1    # 换房间时取消未完成的捕捉
        self._tick_curses()

        self.is_event_room = (
            not self.is_boss_room
            and self.current_depth >= 2
            and not self.last_room_was_event
            and random.random() < 0.22
        )
        self.last_room_was_event = self.is_event_room
        self.event_done = False
        self.event_kind = None
        self.event_title = ""
        self.event_choices = []
        self.pending_elite_reward = False
        self.pending_event_rewards = 0
        self.event_running = False
        self.event_timer = 0
        self.event_data = {}

        if self.is_boss_room:
            self.scene_type = self._pick_scene_type()
            self.boss_type = pick_boss_for_scene(self.scene_type, self.current_depth)
        else:
            self.boss_type = None
            # 生态按区域推进：区域 3~5 间，走完必接一间普通地牢
            self.scene_type = self._pick_scene_type()
        self.enter_region_room()
        # 寺庙是战斗房，不该被抽成事件房，否则没有空中平台可以放水晶
        if self.scene_type in (BIOME_TEMPLE, BIOME_CHURCH, BIOME_GREAT_TOMB):
            self.is_event_room = False
            self.last_room_was_event = False

        self.left_barrier = Barrier(0, 0, 10, SCREEN_HEIGHT, 'left', self.scene_type)
        self.right_barrier = Barrier(SCREEN_WIDTH - 10, 0, 10, SCREEN_HEIGHT, 'right', self.scene_type)
        self.barriers.add(self.left_barrier, self.right_barrier)
        self.all_sprites.add(self.left_barrier, self.right_barrier)

        if self.is_boss_room:
            self._setup_boss_room()
        elif self.is_event_room:
            self._setup_event_room()
        else:
            self._setup_normal_room()
        self.spawn_room_props()
        if self.pending_room_affixes:
            # 词缀熔炉的代价：这个房间的敌人全部带上注入的词缀
            for enemy in list(self.enemies):
                self._attach_affixes(enemy, self.pending_room_affixes)
            names = " / ".join(AFFIX_TABLE[k].name for k in self.pending_room_affixes
                               if k in AFFIX_TABLE)
            self.show_message(f"熔炉之约：本层敌人获得「{names}」", 2200)
            self.pending_room_affixes = []
        self._reposition_allies()
        self.update_barriers()
        self.transitioning = False


    def _setup_normal_room(self):
        if self.scene_type == BIOME_CHURCH:
            self._setup_church_room()
            return
        if self.scene_type == BIOME_GREAT_TOMB:
            self._setup_great_tomb_room()
            return
        if self.scene_type == BIOME_SNOW:
            # 雪山：地面高低起伏但连续，最高的那一段用来当生长点
            GROUND_TOP = self.build_snow_ground()
        else:
            ground = Platform(0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30, self.scene_type)
            self.platforms.add(ground); self.all_sprites.add(ground)
            GROUND_TOP = SCREEN_HEIGHT - 30
        PLATFORM_HEIGHT = 20
        MAX_VERTICAL_GAP = 160; MIN_VERTICAL_GAP = 90
        MIN_GROUND_CLEARANCE = 110; EDGE_MARGIN = 60
        H_GAP = 45; V_GAP = 30
        safe_zones = [
            pygame.Rect(0, GROUND_TOP - 240, 180, 240),
            pygame.Rect(SCREEN_WIDTH - 180, GROUND_TOP - 240, 180, 240),
        ]
        target_count = random.randint(3, 6 + min(5, self.current_depth // 3))
        placed_rects = []
        layer_ys = []
        y_cursor = GROUND_TOP
        while True:
            step = random.randint(MIN_VERTICAL_GAP + 10, MAX_VERTICAL_GAP)
            y_cursor -= step
            if y_cursor < 80: break
            layer_ys.append(y_cursor)
        max_attempts = target_count * 40
        attempts = 0
        while len(placed_rects) < target_count and attempts < max_attempts:
            attempts += 1
            width = random.randint(80, 160)
            if layer_ys and random.random() < 0.85: py = random.choice(layer_ys)
            else: py = random.randint(140, GROUND_TOP - MIN_GROUND_CLEARANCE - PLATFORM_HEIGHT)
            if py < 80: continue
            if py + PLATFORM_HEIGHT > GROUND_TOP - MIN_GROUND_CLEARANCE: continue
            px = random.randint(EDGE_MARGIN, SCREEN_WIDTH - width - EDGE_MARGIN)
            candidate = pygame.Rect(px, py, width, PLATFORM_HEIGHT)
            if any(candidate.colliderect(z) for z in safe_zones): continue
            conflict = False
            for r in placed_rects:
                if (candidate.left < r.right + H_GAP and candidate.right + H_GAP > r.left and
                        candidate.top < r.bottom + V_GAP and candidate.bottom + V_GAP > r.top):
                    conflict = True; break
            if conflict: continue
            placed_rects.append(candidate)
            fragile = self.scene_type == BIOME_ICE and random.random() < 0.2
            platform = Platform(px, py, width, PLATFORM_HEIGHT, self.scene_type, fragile)
            self.platforms.add(platform); self.all_sprites.add(platform)

        if self.scene_type != BIOME_NORMAL:
            crystal_count = random.randint(1, 5)
            for _ in range(crystal_count * 12):
                if len(self.crystals) >= crystal_count: break
                fx = random.randint(100, SCREEN_WIDTH - 100)
                fy = random.randint(120, GROUND_TOP - 80)
                test = pygame.Rect(fx - 8, fy - 8, 16, 16)
                if any(test.colliderect(r.inflate(10, 10)) for r in placed_rects): continue
                crystal = Crystal(fx, fy)
                self.crystals.add(crystal); self.all_sprites.add(crystal)

        if self.scene_type == BIOME_ICE:
            trap_count = random.randint(2, 4)
            placed_trap_x = []
            for _ in range(trap_count * 12):
                if len(placed_trap_x) >= trap_count: break
                tx = random.randint(120, SCREEN_WIDTH - 160)
                if any(abs(tx - ox) < 130 for ox in placed_trap_x): continue
                placed_trap_x.append(tx)
                trap = IceTrap(tx, GROUND_TOP - 10)
                self.traps.add(trap); self.all_sprites.add(trap)
        elif self.scene_type == BIOME_POISON:
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, SCREEN_WIDTH - 100)
                pool = LavaPool(x, GROUND_TOP + 5, duration=9999, damage=4, color=POISON_GREEN)
                self.lava_pools.add(pool); self.all_sprites.add(pool)

        max_extra = min(5, self.current_depth // 3)
        enemy_count = random.randint(2, 4 + max_extra)
        enemy_spawn_positions = []
        for _ in range(enemy_count * 30):
            if len(enemy_spawn_positions) >= enemy_count: break
            if random.random() < 0.7:
                ex = random.randint(120, SCREEN_WIDTH - 150)
                ey = GROUND_TOP - 60
            else:
                ex = random.randint(120, SCREEN_WIDTH - 150)
                ey = random.randint(140, GROUND_TOP - 220)
            test_rect = pygame.Rect(ex, ey, 40, 50)
            if test_rect.colliderect(safe_zones[0]): continue
            if any(test_rect.colliderect(r.inflate(10, 10)) for r in placed_rects): continue
            if any(abs(ex - sx) < 70 and abs(ey - sy) < 70 for sx, sy in enemy_spawn_positions): continue
            enemy_spawn_positions.append((ex, ey))
        while len(enemy_spawn_positions) < enemy_count:
            ex = random.randint(120, SCREEN_WIDTH - 150)
            enemy_spawn_positions.append((ex, 60))

        if self.all_elite_mode:
            # 精英地狱：普通敌人全部换成精英，数量与经典一致、血量不削减
            for (ex, ey) in enemy_spawn_positions:
                kind = random.choice(self._elite_kind_pool())
                elite = EliteEnemy(ex, ey - 30, self.current_depth, self.scene_type, kind)
                self.enemies.add(elite); self.all_sprites.add(elite)
        else:
            pool = BIOME_ENEMY_POOL.get(self.scene_type, BIOME_ENEMY_POOL[BIOME_NORMAL])
            for (ex, ey) in enemy_spawn_positions:
                enemy_type = random.choice(pool)
                affix_names = self._roll_enemy_affixes()
                enemy = Enemy(ex, ey, self.current_depth, enemy_type, self.scene_type, affix_names=affix_names)
                self.enemies.add(enemy); self.all_sprites.add(enemy)

        if self.mode != MODE_ELITE_HELL and self.current_depth >= 3 and random.random() < 0.35:
            self._spawn_elite(placed_rects, safe_zones, GROUND_TOP)
        self.initial_enemy_count = len(self.enemies)


    def _setup_boss_room(self):
        ground = Platform(0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30, self.scene_type)
        self.platforms.add(ground); self.all_sprites.add(ground)
        platforms = [
            (30, SCREEN_HEIGHT - 180, 130, 20),
            (SCREEN_WIDTH - 160, SCREEN_HEIGHT - 180, 130, 20),
            (SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 260, 160, 20),
            (150, 100, 100, 20),
            (SCREEN_WIDTH - 250, 100, 100, 20),
        ]
        for (px, py, pw, ph) in platforms:
            p = Platform(px, py, pw, ph, self.scene_type)
            self.platforms.add(p); self.all_sprites.add(p)
        if self.scene_type == BIOME_ICE:
            for _ in range(2):
                x = random.randint(200, SCREEN_WIDTH - 200)
                trap = IceTrap(x, SCREEN_HEIGHT - 40)
                self.traps.add(trap); self.all_sprites.add(trap)
            for _ in range(3):
                x = random.randint(100, SCREEN_WIDTH - 100)
                y = random.randint(150, SCREEN_HEIGHT - 100)
                crystal = Crystal(x, y)
                self.crystals.add(crystal); self.all_sprites.add(crystal)
        else:
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, SCREEN_WIDTH - 100)
                y = random.randint(150, SCREEN_HEIGHT - 100)
                crystal = Crystal(x, y)
                self.crystals.add(crystal); self.all_sprites.add(crystal)
        self.boss = create_boss(self.boss_type, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30,
                                self.current_depth, self.scene_type)
        self.all_sprites.add(self.boss)
        if isinstance(self.boss, StitchedBoss):
            self.boss.apply_kill_power(self.player.kills)
            self.show_message(
                f"{self.boss.BOSS_NAME} 由 {self.player.kills} 具残骸拼成，降临！", 2500)
        else:
            self.show_message(f"{self.boss.BOSS_NAME} 降临！", 2500)
        self.initial_enemy_count = 1


    def update_barriers(self):
        if self.is_boss_room:
            is_cleared = self.boss is None or self.boss.health <= 0
        elif self.is_event_room:
            is_cleared = self.event_done and len(self.enemies) == 0
        else:
            # 召唤圈里还压着敌人不算清场，否则门会刚开就又关上
            # 同时忽略已经被挤到屏幕外、玩家够不着的单位，避免房间永远清不掉
            live = [e for e in self.enemies
                    if getattr(e, 'health', 0) > 0
                    and e.rect.right > 0 and e.rect.left < SCREEN_WIDTH]
            is_cleared = not live and len(self.summon_circles) == 0
            if self.scene_type == BIOME_GREAT_TOMB:
                is_cleared = is_cleared and len(self.gravestones) == 0
            # 普通房间一旦清空就不再关上：后续掉出来的召唤物不该把出口堵回去
            if self.scene_cleared:
                is_cleared = True
        self.left_barrier.set_visible(not is_cleared)
        self.right_barrier.set_visible(not is_cleared)
        if is_cleared and not self.scene_cleared:
            self.scene_cleared = True
            self.stats.note_room_cleared(self.current_depth)
            if self.is_event_room:
                self.show_message("事件结束，可以前进", 1500)
            elif not self.is_boss_room:
                self.show_message("区域已清空！", 2000)
            else:
                self.show_message("领主已被击败！", 2500)
        return is_cleared


    def change_dungeon(self, direction):
        if self.transitioning or self.paused: return
        self.player.stop_meteor()
        self.player.cancel_time_rewind()
        if direction == 'right':
            self.player.rect.x = 50
            self.current_depth += 1
        else:
            self.player.rect.x = SCREEN_WIDTH - 50 - self.player.rect.width
            self.current_depth = max(0, self.current_depth - 1)
        if self.player.rect.bottom > SCREEN_HEIGHT:
            self.player.rect.bottom = SCREEN_HEIGHT - 30
        self.generate_dungeon()


    def run(self):
        running = True
        while running:
            advance_frame()
            clock.tick(FPS)
            self.frame += 1
            self.mouse = window_to_screen(pygame.mouse.get_pos())

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.flush_codex()
                    return False

                if self.show_shop:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.show_shop = False; self.paused = False
                        elif event.key == pygame.K_a:
                            self.shop_page = max(0, self.shop_page - 1); self._gen_shop_items()
                        elif event.key == pygame.K_d:
                            self.shop_page = min(SHOP_PAGES - 1, self.shop_page + 1); self._gen_shop_items()
                        elif pygame.K_1 <= event.key <= pygame.K_9:
                            self.handle_shop_purchase(event.key - pygame.K_1)
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.paused:
                            if self.show_rules: self.show_rules = False
                            elif self.show_enemy_info: self.show_enemy_info = False
                            elif self.show_reward_info: self.show_reward_info = False
                            else: self.paused = False
                        else:
                            self.paused = True
                    elif event.key == pygame.K_SPACE:
                        if (self.paused and not self.show_rules and not self.show_enemy_info
                                and not self.show_reward_info):
                            self.flush_codex()
                            return False
                    elif event.key == pygame.K_s:
                        if (self.paused and not self.show_rules and not self.show_enemy_info
                                and not self.show_reward_info and not self.show_shop):
                            # 先清账再快照：否则存档里留着已记账的击杀，续局时会被记第二次
                            self.flush_codex()
                            if savegame.write(self):
                                return False
                            self.show_message("保存失败，请检查游戏目录是否可写", 2000)
                    elif event.key == pygame.K_e:
                        if not self.paused and not self.transitioning:
                            if self.free_shop:
                                self.open_shop()
                            elif self.player.crystals >= 3:
                                self.player.crystals -= 3
                                self.open_shop()
                            else:
                                self.show_message("需要3个晶体才能打开商店！", 1500)
                        elif self.paused and not self.show_rules and not self.show_reward_info:
                            self.show_enemy_info = not self.show_enemy_info
                            self.selected_enemy_idx = 0
                    elif event.key == pygame.K_f:
                        if (self.is_event_room and not self.event_done
                                and not self.paused and not self.transitioning
                                and not self.show_rules and not self.show_enemy_info
                                and not self.show_reward_info and not self.show_shop
                                and not self.event_running):
                            if self.event_altar is not None:
                                test_rect = self.player.rect.inflate(50, 50)
                                if test_rect.colliderect(self.event_altar.rect):
                                    self.show_event_selection()
                        elif (self.scene_type == BIOME_TEMPLE and not self.paused
                                and not self.transitioning and not self.show_rules
                                and not self.show_enemy_info and not self.show_reward_info):
                            # 暴云寺庙的金色水晶：靠近按 F 就点亮，不给提示文字
                            self.use_storm_crystal()
                        elif (self.scene_type == BIOME_CHURCH and not self.paused
                                and not self.transitioning and not self.show_rules
                                and not self.show_enemy_info and not self.show_reward_info):
                            self.use_church_cross()
                    elif event.key == pygame.K_k:
                        if (self.paused and not self.show_rules and not self.show_enemy_info
                                and not self.show_reward_info):
                            self.paused = False
                        elif not self.paused:
                            self.player.jump()
                    elif event.key == pygame.K_j:
                        if (not self.paused and not self.show_rules
                                and not self.show_enemy_info and not self.show_reward_info):
                            if SETTINGS["auto_fire"]:
                                self.auto_fire_active = not self.auto_fire_active
                                self.show_message(
                                    "自动射击：开启" if self.auto_fire_active else "自动射击：关闭", 900)
                            else:
                                self.shoot()
                    elif event.key in (pygame.K_u, pygame.K_i, pygame.K_o):
                        if (not self.paused and not self.show_rules
                                and not self.show_enemy_info and not self.show_reward_info
                                and not self.transitioning):
                            slot = {pygame.K_u: 0, pygame.K_i: 1, pygame.K_o: 2}[event.key]
                            self.use_skill(slot)
                    elif event.key == pygame.K_p and self.paused and not self.show_enemy_info and not self.show_reward_info:
                        self.show_rules = not self.show_rules
                        if self.show_rules: self.rules_scroll = 0
                    elif event.key == pygame.K_r and self.paused and not self.show_rules and not self.show_enemy_info:
                        self.show_reward_info = not self.show_reward_info
                        self.selected_reward_cat = 0
                    elif event.key == pygame.K_UP:
                        if self.show_rules: self.handle_rules_scroll("up")
                        elif self.show_enemy_info:
                            indices = gallery.filtered_indices(
                                self.gallery_category, self.gallery_place)
                            self.selected_enemy_idx = gallery.scroll_selection(
                                self.selected_enemy_idx, indices, -1)
                        elif self.show_reward_info:
                            self.selected_reward_cat = (self.selected_reward_cat - 1) % len(self.reward_descriptions)
                    elif event.key == pygame.K_DOWN:
                        if self.show_rules: self.handle_rules_scroll("down")
                        elif self.show_enemy_info:
                            indices = gallery.filtered_indices(
                                self.gallery_category, self.gallery_place)
                            self.selected_enemy_idx = gallery.scroll_selection(
                                self.selected_enemy_idx, indices, 1)
                        elif self.show_reward_info:
                            self.selected_reward_cat = (self.selected_reward_cat + 1) % len(self.reward_descriptions)
                elif event.type == pygame.KEYUP and event.key == pygame.K_k:
                    # 松键削顶：轻点小跳、长按高跳
                    if not self.paused:
                        self.player.cut_jump()
                elif event.type == pygame.MOUSEWHEEL:
                    if self.show_rules:
                        self.handle_rules_scroll("up" if event.y > 0 else "down")
                    elif self.show_enemy_info:
                        indices = gallery.filtered_indices(
                            self.gallery_category, self.gallery_place)
                        self.selected_enemy_idx = gallery.scroll_selection(
                            self.selected_enemy_idx, indices,
                            -1 if event.y > 0 else 1)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.paused or self.show_rules or self.show_enemy_info \
                            or self.show_reward_info:
                        self._handle_overlay_click()
                    else:
                        self.place_bomb(*window_to_screen(pygame.mouse.get_pos()))

            if (not self.paused and not self.transitioning and not self.show_rules
                    and not self.show_enemy_info and not self.show_reward_info):
                keys = pygame.key.get_pressed()
                if self.player.dash_timer <= 0:
                    if keys[pygame.K_a]: self.player.move_left()
                    elif keys[pygame.K_d]: self.player.move_right()
                    else: self.player.stop()

            if (not self.transitioning and not self.paused and not self.show_rules
                    and not self.show_enemy_info and not self.show_reward_info):
                if self.ice_field_timer > 0: self.ice_field_timer -= 1
                if SETTINGS["auto_fire"] and self.auto_fire_active:
                    self.shoot()
                self.player.update(self.platforms, self.barriers, self.traps, self.scene_type)
                for enemy in list(self.enemies):
                    if enemy.is_ember: continue
                    if getattr(enemy, 'is_church_cross', False): continue
                    enemy.update(self.platforms, self.barriers, self.ice_trails, self.all_sprites, self)
                for ally in list(self.allies):
                    ally.update(self.platforms, self.barriers, self)
                if self.mode == MODE_SUMMONER:
                    for i in range(len(self.summon_cd)):
                        if self.summon_cd[i] > 0: self.summon_cd[i] -= 1
                if self.player.pact_timer > 0:
                    self.player.pact_timer -= 1
                for bullet in self.bullets: bullet.update(self.barriers, self.enemies)
                self.update_black_hole_bullets()
                for bomb in self.bombs: bomb.update()
                for trap in self.traps: trap.update()
                for trail in self.ice_trails: trail.update()
                for crystal in self.crystals: crystal.update()
                for m in self.mirrors: m.update()
                for ft in self.floating_texts: ft.update()
                for goal in self.event_goals: goal.update()
                self.update_blizzard()          # 雪山：风雪循环与推力
                self.update_snow_drifts()       # 玩家走过会铲掉疏雪层
                self.update_storm_crystals()    # 寺庙：水晶计时与光束伤害
                self.update_church_crosses()    # 教堂：十字架召唤、圣光与计时
                self.update_gravestones()       # 大墓地：墓碑唤醒僵尸
                if self.boss is not None:
                    self.boss.update(self.player, self.platforms, self.barriers, self)
                    if pygame.sprite.collide_rect(self.boss, self.player):
                        self.hurt_player(1.5 * self.boss.dmg_mult, self.boss.BOSS_NAME,
                                         codex=self.boss.BOSS_NAME)
                self.stats.note_health(self.player.health)
                self.update_black_holes()
                self.update_boss_projectiles()
                self.update_skill_effects()
                self.update_meteor_casting()
                self.update_meteors()
                self.check_collisions()
                self.check_crystal_collection()
                self.check_elite_challenge_reward()
                if self.is_boss_room and self.boss is None and not self.scene_cleared:
                    self.update_barriers()
                if self.event_running:
                    self._update_event()

            if self.pending_event_rewards > 0 and not self.paused and not self.transitioning:
                while self.pending_event_rewards > 0:
                    self.pending_event_rewards -= 1
                    self._show_event_enhancement_pick()

            if (self.player.health <= 0 and not self.paused and not self.show_rules
                    and not self.show_enemy_info and not self.show_reward_info and not self.show_shop):
                restart = self.game_over()
                return restart

            draw_background(self.scene_type, self.is_boss_room, self.frame,
                            "blizzard" if self.is_blizzard() else None)

            if self.ice_field_timer > 0:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((120, 180, 240, 40))
                screen.blit(overlay, (0, 0))

            self.black_holes.draw(screen)
            self.draw_snow_ground()            # 雪坡整体绘制，压在角色之下
            self.all_sprites.draw(screen)
            self.snow_drifts.draw(screen)      # 疏雪层压在角色之上，用来挡视线
            self.draw_unit_buffs()             # 巨魔增幅的红环
            self.draw_crystal_beams()          # 寺庙水晶的光束
            self.draw_church_effects()         # 教堂血色连接与十字架光环
            self.draw_soul_chains()

            for enemy in self.enemies:
                if hasattr(enemy, 'draw_health_bar'): enemy.draw_health_bar(screen)
                if hasattr(enemy, 'draw_affix_icons'): enemy.draw_affix_icons(screen)
                draw_affix_shield(screen, enemy)

            for cross in self.church_crosses:
                if not self.enemies.has(cross):
                    cross.draw_health_bar(screen)
            for grave in self.gravestones:
                grave.draw_health_bar(screen)

            for ally in self.allies:
                ally.draw_health_bar(screen)
                ally.draw_affix_icons(screen)
                draw_affix_shield(screen, ally)

            if self.core is not None and self.core.alive():
                self.core.draw_health_bar(screen)

            self.player.draw_shield(screen)
            if self.boss is not None: self.boss.draw_shield(screen)

            self.draw_hud()

            if self.paused:
                if self.show_shop: self.draw_shop()
                elif self.show_rules: self.draw_rules()
                elif self.show_enemy_info: self.draw_enemy_info()
                elif self.show_reward_info: self.draw_reward_info()
                else: self.draw_pause_menu()

            self.draw_message()
            present()

        return False
    def _handle_overlay_click(self):
        """暂停时点界面：角落的返回按钮，以及图鉴与奖励列表的条目。"""
        pos = self.mouse
        if pos is None:
            return
        if back_hit(pos):
            # 关掉当前这一层，和按 ESC 一致
            if self.show_shop:
                self.show_shop = False; self.paused = False
            elif self.show_rules:
                self.show_rules = False
            elif self.show_enemy_info:
                self.show_enemy_info = False
            elif self.show_reward_info:
                self.show_reward_info = False
            else:
                self.paused = False
            return
        if self.show_enemy_info:
            hit = gallery.filter_hit(pos)
            if hit is not None:
                kind, key = hit
                if kind == "category":
                    self.gallery_category = key
                else:
                    self.gallery_place = key
                indices = gallery.filtered_indices(
                    self.gallery_category, self.gallery_place)
                if indices and self.selected_enemy_idx not in indices:
                    self.selected_enemy_idx = indices[0]
                return
            indices = gallery.filtered_indices(
                self.gallery_category, self.gallery_place)
            index = gallery.list_index_at(
                pos, self.selected_enemy_idx, indices)
            if index is not None:
                self.selected_enemy_idx = index
        elif self.show_reward_info:
            index = reward_cat_at(pos, len(self.reward_descriptions))
            if index is not None:
                self.selected_reward_cat = index


