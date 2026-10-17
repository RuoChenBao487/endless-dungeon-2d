"""普通敌人配置、群系敌人池与精英数值。"""


# === IMPORTS ===
from .biomes import (BIOME_CHURCH, BIOME_GREAT_TOMB, BIOME_ICE, BIOME_LAVA,
                     BIOME_NORMAL, BIOME_POISON, BIOME_SNOW, BIOME_TEMPLE,
                     BIOME_TOMB)
from ..settings import BONE_WHITE, CYAN, DARK_BLUE, FIRE_ORANGE, GHOST_PURPLE, GREEN, POISON_GREEN, PURPLE, RED, WHITE, YELLOW
# === /IMPORTS ===

ENEMY_CONFIG = {
    0: {"name": "红色士兵", "speed": 2.0, "hp_base": 30, "hp_scale": 5, "color": RED, "size": (32, 50)},
    1: {"name": "跳跃者", "speed": 3.0, "hp_base": 30, "hp_scale": 4, "color": GREEN, "size": (32, 50), "jump": True},
    2: {"name": "强化兵", "speed": 4.0, "hp_base": 60, "hp_scale": 8, "color": PURPLE, "size": (32, 50), "dr": 0.3},
    3: {"name": "坦克", "speed": 1.0, "hp_base": 90, "hp_scale": 12, "color": YELLOW, "size": (38, 58), "dr": 0.2},
    4: {"name": "冰漫步者", "speed": 2.5, "hp_base": 45, "hp_scale": 6, "color": CYAN, "size": (32, 50), "ice_trail": True},
    5: {"name": "冰甲守卫", "speed": 1.5, "hp_base": 120, "hp_scale": 12, "color": DARK_BLUE, "size": (36, 56), "shield": True},
    6: {"name": "雪团怪", "speed": 3.0, "hp_base": 30, "hp_scale": 4, "color": WHITE, "size": (42, 42), "splits": True},
    7: {"name": "火蝠", "speed": 3.5, "hp_base": 25, "hp_scale": 4, "color": FIRE_ORANGE, "size": (32, 26), "flying": True},
    8: {"name": "熔岩史莱姆", "speed": 1.3, "hp_base": 55, "hp_scale": 7, "color": (180, 50, 20), "size": (38, 32)},
    9: {"name": "毒蘑菇", "speed": 0.6, "hp_base": 45, "hp_scale": 6, "color": POISON_GREEN, "size": (36, 44)},
    10: {"name": "沼泽蛙", "speed": 2.8, "hp_base": 55, "hp_scale": 6, "color": (70, 140, 50), "size": (38, 38), "jump": True},
    11: {"name": "骷髅兵", "speed": 2.2, "hp_base": 45, "hp_scale": 6, "color": BONE_WHITE, "size": (34, 52), "revive": True, "undead": True},
    12: {"name": "幽灵", "speed": 1.8, "hp_base": 35, "hp_scale": 4, "color": GHOST_PURPLE, "size": (34, 44), "flying": True, "undead": True},
    13: {"name": "魔魂亡骨", "speed": 1.6, "hp_base": 130, "hp_scale": 15, "color": (150, 130, 215), "size": (42, 64), "undead": True},
    # 风灵不造成伤害，只会把玩家和敌人往外推，风雪天里最难缠
    14: {"name": "风灵", "speed": 2.4, "hp_base": 28, "hp_scale": 4,
         "color": (186, 226, 246), "size": (32, 32), "flying": True, "wind": True},
    # 血类敌人全部属于亡灵；血仆与血蝠是吸血鬼唯一能抽取血液的单位
    15: {"name": "血仆", "speed": 3.2, "hp_base": 48, "hp_scale": 7,
         "color": (180, 54, 72), "size": (34, 52), "undead": True,
         "blood": True},
    16: {"name": "血蝙蝠", "speed": 3.8, "hp_base": 32, "hp_scale": 4,
         "color": (150, 34, 58), "size": (36, 28), "flying": True,
         "undead": True, "blood": True},
    18: {"name": "僵尸", "speed": 0.55, "hp_base": 145, "hp_scale": 14,
         "color": (96, 132, 86), "size": (40, 56), "undead": True,
         "zombie": True},
}

ENEMY_WIND_SPIRIT = 14

# 幽灵与骷髅相撞会合体成魔魂亡骨（巨型骷髅不参与）
ENEMY_SKELETON = 11
ENEMY_GHOST = 12
ENEMY_WRAITHBONE = 13
ENEMY_BLOOD_SERVANT = 15
ENEMY_BLOOD_BAT = 16
ENEMY_BLOOD_CROSS = 17
ENEMY_ZOMBIE = 18
FUSION_TYPES = (ENEMY_SKELETON, ENEMY_GHOST)
FUSION_HEALTH_RATIO = 0.85     # 合体后的血量 = 两者之和 × 该系数
FUSION_HEAL_RADIUS = 170       # 附近有亡灵倒下时的回血判定半径
FUSION_HEAL_RATIO = 0.09       # 每次回血占自身最大生命的比例
FUSION_HEAL_MIN = 5            # 回血下限，避免后期数值太小

BLOOD_MINION_TYPES = (ENEMY_BLOOD_SERVANT, ENEMY_BLOOD_BAT)
UNDEAD_ENEMY_TYPES = (ENEMY_SKELETON, ENEMY_GHOST, ENEMY_WRAITHBONE,
                      ENEMY_BLOOD_SERVANT, ENEMY_BLOOD_BAT)
UNDEAD_SUMMON_TYPES = (ENEMY_SKELETON, ENEMY_GHOST, ENEMY_WRAITHBONE,
                       ENEMY_BLOOD_SERVANT, ENEMY_BLOOD_BAT)

# 魔魂亡骨对玩家的普通攻击与技能攻击各减伤一半，炸弹与灼烧不在其列
WRAITHBONE_DR = 0.5
WRAITHBONE_RESIST_SOURCES = (
    "bullet", "explosion", "skill_fireball_explosion", "skill_fireball_direct",
    "black_hole_devour", "soul_chain_shared", "shockwave", "dash",
    "ice_shard", "ice_shatter",
)

CODEX_ELITE_NAME = "精英怪"      # 图鉴里所有精英共用这一条

BIOME_ENEMY_POOL = {
    BIOME_NORMAL: [0, 0, 1, 1, 2, 3],
    BIOME_ICE:    [4, 4, 6, 6, 5, 2, 3, 0],
    BIOME_LAVA:   [7, 7, 8, 8, 9, 2, 3, 0],
    BIOME_POISON: [9, 9, 10, 10, 8, 2, 3, 0],
    BIOME_TOMB:   [11, 11, 12, 12, 18, 18, 5, 2, 3, 0],
    BIOME_GREAT_TOMB: [18, 18, 18, 11, 11, 12, 5, 2],
    BIOME_SNOW:   [14, 14, 6, 6, 4, 5, 2, 3],
    BIOME_TEMPLE: [14, 14, 4, 5, 2, 3, 0],
    BIOME_CHURCH: [15, 15, 16, 16, 11, 12, 2, 3],
}


ELITE_STATS = {
    "hook_warden": {"name": "狱卒·铁钩", "hp_base": 240, "hp_scale": 25,
        "speed": 1.3, "size": (46, 70), "color": (130, 75, 40),
        "skill_cd": 240, "fixed_affixes": ["berserk"], "scene": "normal", "shape": "warden"},
    "shadow_blade": {"name": "暗影刺客·夜刃", "hp_base": 200, "hp_scale": 20,
        "speed": 2.6, "size": (38, 62), "color": (60, 45, 100),
        "skill_cd": 260, "fixed_affixes": ["mirror"], "scene": "tomb", "shape": "assassin"},
    "bone_caller": {"name": "亡灵召唤师·墓语者", "hp_base": 180, "hp_scale": 22,
        "speed": 1.2, "size": (40, 66), "color": (130, 80, 180),
        "skill_cd": 300, "fixed_affixes": ["summon"], "scene": "tomb", "shape": "necromancer"},
    "frost_claw": {"name": "霜噬者·冰爪", "hp_base": 260, "hp_scale": 28,
        "speed": 2.8, "size": (58, 44), "color": (150, 215, 255),
        "skill_cd": 220, "fixed_affixes": ["freezing"], "scene": "ice", "shape": "beast"},
    "ice_witch": {"name": "冰晶女巫·霜织", "hp_base": 220, "hp_scale": 24,
        "speed": 1.4, "size": (42, 68), "color": (180, 230, 255),
        "skill_cd": 260, "fixed_affixes": ["freezing"], "scene": "ice", "shape": "witch"},
    "ember_mage": {"name": "灰烬法师·烬火", "hp_base": 240, "hp_scale": 26,
        "speed": 1.5, "size": (42, 68), "color": (210, 110, 45),
        "skill_cd": 240, "fixed_affixes": ["burning"], "scene": "lava", "shape": "mage"},
    "plague_priest": {"name": "腐沼祭司·瘴", "hp_base": 220, "hp_scale": 24,
        "speed": 1.4, "size": (42, 68), "color": (130, 190, 90),
        "skill_cd": 260, "fixed_affixes": ["burning"], "scene": "poison", "shape": "priest"},
    # ---- 暴雪山脉 ----
    # 冰爪狼会瞄准玩家起跳，起跳后无视平台；跳得到低处，跳不上太高的平台
    "frost_wolf": {"name": "冰爪狼", "hp_base": 210, "hp_scale": 22,
        "speed": 2.4, "size": (56, 40), "color": (176, 228, 252),
        "skill_cd": 190, "fixed_affixes": ["freezing"], "scene": "snow", "shape": "wolf"},
    # 巨魔一律是精英，并且必定带"再生"；士兵只会追，猎手点射，狂呼者给全场增幅
    "troll_soldier": {"name": "巨魔士兵", "hp_base": 430, "hp_scale": 42,
        "speed": 1.1, "size": (50, 76), "color": (118, 202, 190), "giant": True,
        "skill_cd": 99999, "fixed_affixes": ["regeneration"], "scene": "snow",
        "shape": "troll"},
    "troll_hunter": {"name": "巨魔猎手", "hp_base": 240, "hp_scale": 24,
        "speed": 1.6, "size": (40, 64), "color": (118, 202, 190),
        "skill_cd": 165, "fixed_affixes": ["regeneration"], "scene": "snow",
        "shape": "troll"},
    "troll_howler": {"name": "巨魔狂呼者", "hp_base": 400, "hp_scale": 40,
        "speed": 1.0, "size": (50, 76), "color": (118, 202, 190), "giant": True,
        "skill_cd": 900, "fixed_affixes": ["regeneration"], "scene": "snow",
        "shape": "troll"},
    # ---- 破败教堂 ----
    "vampire": {"name": "吸血鬼", "hp_base": 250, "hp_scale": 26,
        "speed": 2.0, "size": (42, 68), "color": (176, 46, 66),
        "skill_cd": 99999, "fixed_affixes": ["lifesteal"], "scene": "church",
        "shape": "vampire"},
    "gargoyle": {"name": "石像鬼", "hp_base": 230, "hp_scale": 25,
        "speed": 1.8, "size": (48, 66), "color": (104, 210, 202),
        "skill_cd": 99999, "fixed_affixes": [], "scene": "church",
        "shape": "gargoyle"},
    "bone_carrier": {"name": "载骨机", "hp_base": 280, "hp_scale": 28,
        "speed": 1.2, "size": (52, 76), "color": (222, 218, 198),
        "skill_cd": 99999, "fixed_affixes": [], "scene": "great_tomb",
        "shape": "bone_carrier"},
    "soul_reaper": {"name": "炼魂魔骷", "hp_base": 360, "hp_scale": 32,
        "speed": 1.4, "size": (70, 96), "color": (174, 238, 184),
        "skill_cd": 99999, "fixed_affixes": [], "scene": "__preview__",
        "shape": "soul_reaper"},
}
