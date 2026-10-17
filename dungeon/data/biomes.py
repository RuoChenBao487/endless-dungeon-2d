"""生物群系常量、名称、配色与背景色板。"""


# === IMPORTS ===
from ..settings import BONE_WHITE, FIRE_ORANGE, ICE_WHITE, LIGHT_BROWN, POISON_BRIGHT
# === /IMPORTS ===

BIOME_NORMAL = "normal"
BIOME_ICE = "ice"
BIOME_LAVA = "lava"
BIOME_POISON = "poison"
BIOME_TOMB = "tomb"
BIOME_GREAT_TOMB = "great_tomb"
BIOME_SNOW = "snow"
# 暴云寺庙不是独立生态：它只会作为雪山里的一种房间出现，所以不进 SPECIAL_BIOMES
BIOME_TEMPLE = "temple"
# 破败教堂同样不是独立生态，它是亡灵墓穴区域里的一种嵌套房
BIOME_CHURCH = "church"
SPECIAL_BIOMES = [BIOME_ICE, BIOME_LAVA, BIOME_POISON, BIOME_TOMB, BIOME_SNOW]
ALL_BIOMES = [BIOME_NORMAL] + SPECIAL_BIOMES

BIOME_NAMES = {
    BIOME_NORMAL: "普通地牢",
    BIOME_ICE: "冰晶洞穴",
    BIOME_LAVA: "熔岩洞窟",
    BIOME_POISON: "腐沼秘境",
    BIOME_TOMB: "亡灵墓穴",
    BIOME_GREAT_TOMB: "古代大墓地",
    BIOME_SNOW: "暴雪山脉",
    BIOME_TEMPLE: "暴云寺庙",
    BIOME_CHURCH: "破败教堂",
}

BIOME_COLORS = {
    BIOME_NORMAL: LIGHT_BROWN,
    BIOME_ICE: ICE_WHITE,
    BIOME_LAVA: FIRE_ORANGE,
    BIOME_POISON: POISON_BRIGHT,
    BIOME_TOMB: BONE_WHITE,
    BIOME_GREAT_TOMB: (170, 214, 184),
    BIOME_SNOW: (215, 232, 250),
    BIOME_TEMPLE: (245, 205, 110),
    BIOME_CHURCH: (210, 120, 135),
}

BIOME_AMBIENT = {
    BIOME_NORMAL: ((30, 22, 30), (44, 32, 40), (210, 180, 130)),
    BIOME_ICE:    ((18, 26, 44), (30, 44, 66), (170, 220, 255)),
    BIOME_LAVA:   ((32, 12, 8), (54, 20, 12), (255, 120, 60)),
    BIOME_POISON: ((18, 28, 20), (30, 46, 30), (150, 220, 120)),
    BIOME_TOMB:   ((20, 20, 30), (34, 34, 48), (170, 170, 200)),
    BIOME_GREAT_TOMB: ((14, 24, 20), (28, 46, 38), (150, 236, 178)),
    BIOME_SNOW:   ((26, 36, 56), (58, 74, 100), (235, 245, 255)),
    BIOME_TEMPLE: ((26, 18, 16), (52, 34, 26), (255, 214, 130)),
    BIOME_CHURCH: ((22, 14, 22), (38, 22, 34), (222, 118, 132)),
}
