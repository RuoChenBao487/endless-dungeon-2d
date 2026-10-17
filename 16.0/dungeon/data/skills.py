"""技能常量、数据表、成长数值与 Skill 类。"""


# === IMPORTS ===
import pygame
from ..settings import FPS
# === /IMPORTS ===

SKILL_SHIELD = "shield"
SKILL_DASH = "dash"
SKILL_FIREBALL = "fireball"
SKILL_ICE_NOVA = "ice_nova"
SKILL_METEOR = "meteor"
SKILL_BLACK_HOLE = "black_hole"
SKILL_TIME_REWIND = "time_rewind"
SKILL_SOUL_CHAIN = "soul_chain"
SKILL_PACT = "pact"

SKILL_ORDER = [
    SKILL_SHIELD, SKILL_DASH, SKILL_FIREBALL, SKILL_ICE_NOVA, SKILL_METEOR,
    SKILL_BLACK_HOLE, SKILL_TIME_REWIND, SKILL_SOUL_CHAIN, SKILL_PACT,
]
SLOT_KEYS = [pygame.K_u, pygame.K_i, pygame.K_o]
SLOT_KEY_NAMES = ["U", "I", "O"]
SLOT_KEY_NAMES_CN = ["U键", "I键", "O键"]

# 召唤师模式：召唤 / 收回的冷却
SUMMON_COOLDOWN = 60
# 友军受到的接触伤害倍率（敌人对玩家的那套数值对召唤物太温和）
ALLY_INCOMING_DAMAGE = 3.0
# 友军攻击力 = 最大生命 × 该系数（商店显示与实际伤害共用同一个数）
ALLY_ATTACK_RATIO = 0.15
# 复制给友军的词缀里排除这些：它们只在死亡/光环时生效，对友军没有意义
ALLY_BAD_AFFIXES = {"leader_aura", "split", "summon", "death_explosion"}
# 商店「赋予随机词条」的候选池：只给对友军有实际作用的词缀
ALLY_AFFIX_POOL = ["berserk", "shield", "freezing", "lifesteal",
                   "regeneration", "swift", "armor", "mirror"]
# 亡者契约：唤起的临时友军存活时间与同屏上限
PACT_ALLY_LIFETIME = 18 * FPS
PACT_ALLY_CAP = 6


SKILL_DATA = {
    SKILL_SHIELD: {
        "name": "护盾", "icon": "盾", "color": (110, 210, 230),
        "base_cost": 10, "cost_growth": 0.14,
        "desc": "生成护盾，短时间免疫伤害",
        "evolutions": [
            {"key": "shockwave", "name": "震荡", "desc": "护盾被击时释放圆形冲击波"},
            {"key": "bulwark", "name": "防战", "desc": "护盾持续时，攻击力+50%"},
        ],
    },
    SKILL_DASH: {
        "name": "闪电冲刺", "icon": "闪", "color": (150, 220, 255),
        "base_cost": 8, "cost_growth": 0.12,
        "desc": "向前直线冲刺，无视障碍并无敌",
        "evolutions": [
            {"key": "paralyze", "name": "麻痹", "desc": "冲刺命中的敌人眩晕（随等级提升时长）"},
            {"key": "slide", "name": "滑动", "desc": "按住技能键持续冲刺，可用ADW控制方向"},
        ],
    },
    SKILL_FIREBALL: {
        "name": "爆烈火球", "icon": "火", "color": (255, 140, 60),
        "base_cost": 14, "cost_growth": 0.10,
        "desc": "发射爆裂火球，命中后范围爆炸",
        "evolutions": [
            {"key": "sweep", "name": "扫荡", "desc": "一次性向前方发射三发火球"},
            {"key": "snipe", "name": "狙击", "desc": "火球自动瞄准最近敌人"},
        ],
    },
    SKILL_ICE_NOVA: {
        "name": "寒冰新星", "icon": "冰", "color": (150, 220, 255),
        "base_cost": 12, "cost_growth": 0.12,
        "desc": "发射冰锥，造成普攻伤害并冻结+减速敌人",
        "evolutions": [
            {"key": "shatter", "name": "霜爆", "desc": "冰锥命中冻结敌人时额外伤害"},
            {"key": "frost_path", "name": "霜径", "desc": "冰锥留下冰面轨迹，减速经过的敌人"},
        ],
    },
    SKILL_METEOR: {
        "name": "天降陨火", "icon": "陨", "color": (255, 130, 50),
        "base_cost": 16, "cost_growth": 0.12,
        "desc": "进入吟唱，天降火球轰炸；吟唱期间无法移动，再按一次结束",
        "evolutions": [
            {"key": "nimble", "name": "灵巧", "desc": "吟唱期间可自由移动"},
            {"key": "scorch", "name": "灼烧", "desc": "火球落地留下燃烧区域，随等级延长"},
        ],
    },
    SKILL_BLACK_HOLE: {
        "name": "暗影黑洞", "icon": "洞", "color": (145, 95, 225),
        "base_cost": 16, "cost_growth": 0.12,
        "desc": "发射黑暗子弹，命中后生成黑洞，持续吸附聚集敌人10秒",
        "evolutions": [
            {"key": "devour", "name": "吞噬", "desc": "黑洞缓慢造成微弱伤害，并将伤害等额恢复为生命"},
            {"key": "warp", "name": "扭曲", "desc": "敌人子弹靠近时被吸附，较远时向黑洞方向扭曲"},
        ],
    },
    SKILL_TIME_REWIND: {
        "name": "时间回溯", "icon": "溯", "color": (105, 205, 220),
        "base_cost": 18, "cost_growth": 0.10,
        "desc": "记录当前位置并开始倒计时，时间到后自动回到记录位置",
        "evolutions": [
            {"key": "self_guard", "name": "自守", "desc": "记录生命与能量，回溯后恢复到记录值（更高值不降低）"},
            {"key": "persistence", "name": "持恒", "desc": "持续期间生命最低锁定为1，回溯后解除"},
        ],
    },
    SKILL_SOUL_CHAIN: {
        "name": "灵魂锁链", "icon": "链", "color": (185, 105, 225),
        "base_cost": 15, "cost_growth": 0.12,
        "desc": "链接最近的敌人，锁链持续8秒；升级增加链接数量",
        "evolutions": [
            {"key": "shared_pain", "name": "共苦", "desc": "任一被链接敌人受伤时，其他链接目标失去等量生命"},
            {"key": "soul_drain", "name": "灵魂汲取", "desc": "击杀被链接敌人获得少量临时生命，受伤时优先消耗"},
        ],
    },
    SKILL_PACT: {
        "name": "亡者契约", "icon": "契", "color": (140, 235, 190),
        "base_cost": 20, "cost_growth": 0.12,
        "desc": "展开契约领域，期间击杀的敌人会作为临时友军站起来",
        "evolutions": [
            {"key": "long_pact", "name": "长契", "desc": "契约领域的持续时间延长 60%"},
            {"key": "soul_tax", "name": "魂税", "desc": "每唤起一名友军为你恢复 6 点生命"},
        ],
    },
}


def skill_shield_duration(level):
    return int(180 + (level - 1) * 12)


def skill_dash_damage(level):
    return int(20 + (level - 1) * 8)


def skill_dash_stun(level):
    return int(60 + (level - 1) * 15)


def skill_fireball_bonus(level):
    return int(30 + (level - 1) * 18)


def skill_fireball_radius(level):
    return min(150, int(70 + (level - 1) * 4))


def skill_ice_nova_freeze(level):
    return int(60 + (level - 1) * 15)


def skill_ice_nova_slow(level):
    return int(300 + (level - 1) * 30)


def skill_meteor_bonus(level):
    return int(16 + (level - 1) * 10)


def skill_meteor_drain(level):
    return 3.0 + (level - 1) * 0.4


def skill_meteor_scorch_duration(level):
    return int(300 + (level - 1) * 45)


def skill_black_hole_duration(level):
    return int((10 + (level - 1) * 2) * FPS)


def skill_black_hole_damage(level):
    return max(1, level)


def skill_time_rewind_duration(level):
    return int((5 + (level - 1)) * FPS)


def skill_soul_chain_targets(level):
    return 1 + level


def skill_soul_chain_duration(level):
    return 8 * FPS


def skill_soul_chain_temp_health(level):
    return 3 + level


def skill_pact_duration(level):
    return int((8 + (level - 1) * 1.5) * FPS)


class Skill:
    def __init__(self, kind, level=1, evolutions=None):
        self.kind = kind
        self.level = level
        self.evolutions = list(evolutions) if evolutions else []

    def to_dict(self):
        return {"kind": self.kind, "level": self.level,
                "evolutions": list(self.evolutions)}

    @classmethod
    def from_dict(cls, data):
        return cls(data["kind"], data.get("level", 1), list(data.get("evolutions", [])))

    @property
    def data(self): return SKILL_DATA[self.kind]
    @property
    def name(self): return self.data["name"]
    @property
    def color(self): return self.data["color"]
    @property
    def icon(self): return self.data["icon"]

    @property
    def evolution(self):
        return self.evolutions[0] if self.evolutions else None

    @property
    def cost(self):
        d = self.data
        return int(d["base_cost"] * (1 + d["cost_growth"] * (self.level - 1)))

    def has_evolution(self, key):
        return key in self.evolutions

    def available_evolutions(self):
        """商店 / 许愿井用：已有进化方向的技能不再提供新方向"""
        if self.evolutions:
            return []
        return list(self.data["evolutions"])

    def unused_evolutions(self):
        """镜像对决用：允许叠加到已有的进化之上"""
        return [e for e in self.data["evolutions"] if e["key"] not in self.evolutions]

    def evolution_name(self):
        if not self.evolutions: return "无"
        names = []
        for e in self.data["evolutions"]:
            if e["key"] in self.evolutions:
                names.append(e["name"])
        return "·".join(names) if names else "无"
