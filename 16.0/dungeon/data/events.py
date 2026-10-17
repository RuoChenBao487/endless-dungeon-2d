"""事件房、诅咒、核心防守与轮盘的数据表。"""


# === IMPORTS ===
from ..settings import FPS
# === /IMPORTS ===

MIRROR_SKILLS = ["fireball", "ice_nova", "dash", "shield", "summon", "nova", "meteor"]
MIRROR_SKILL_NAMES = {
    "fireball": "火球术", "ice_nova": "寒冰新星", "dash": "疾风冲刺",
    "shield": "守护护盾", "summon": "亡者召唤", "nova": "能量新星",
    "meteor": "天降陨火",
}


CURSE_ROOMS = 3
CURSE_TABLE = [
    {"name": "虚弱", "desc": "最大生命 -15", "attr": "max_health", "delta": -15, "floor": 30},
    {"name": "迟缓", "desc": "移动速度 -8%", "attr": "speed_multiplier", "delta": -0.08, "floor": 0.5},
    {"name": "枯竭", "desc": "能量恢复 -0.3/秒", "attr": "energy_regen", "delta": -0.3, "floor": 0.5},
    {"name": "钝刃", "desc": "攻击力 -4", "attr": "attack_bonus", "delta": -4, "floor": 0},
    {"name": "迟滞", "desc": "攻击速度 -10%", "attr": "attack_speed_multiplier",
     "delta": -0.10, "floor": 0.5},
]


CORE_DEFENSE_SECONDS = 30
CORE_BASE_HEALTH = 160
CORE_WAVE_INTERVAL = 5 * FPS


ROULETTE_SECTORS = [
    {"label": "晶体 ×25", "color": (110, 190, 250), "kind": "crystals", "value": 25},
    {"label": "强化 ×3", "color": (250, 205, 110), "kind": "rewards", "value": 3},
    {"label": "空白", "color": (105, 105, 125), "kind": "blank", "value": 0},
    {"label": "生命全恢复", "color": (115, 225, 140), "kind": "heal", "value": 0},
    {"label": "诅咒", "color": (210, 85, 120), "kind": "curse", "value": 0},
    {"label": "炸弹×3", "color": (240, 150, 90), "kind": "bombs", "value": 3},
]
