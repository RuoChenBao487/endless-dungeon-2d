"""特殊模式的配置、顺序与同屏敌人上限。"""


# === IMPORTS ===
# === /IMPORTS ===

MODE_CLASSIC = "classic"
MODE_AFFIX_FRENZY = "affix_frenzy"
MODE_UNDEAD_TIDE = "undead_tide"
MODE_ELITE_HELL = "elite_hell"
MODE_SUMMONER = "summoner"

MODE_ORDER = [MODE_CLASSIC, MODE_AFFIX_FRENZY, MODE_UNDEAD_TIDE,
              MODE_ELITE_HELL, MODE_SUMMONER]

# 模式的子菜单只列需要额外选择的模式：经典无尽在主菜单第一项就能直接开，
# 不在这里重复出现；MODE_ORDER 仍然是完整列表（冒险记录按它列出各模式成绩）。
MODE_CHOICES = [m for m in MODE_ORDER if m != MODE_CLASSIC]

MODES = {
    MODE_CLASSIC: {
        "name": "经典无尽",
        "stars": "★☆☆",
        "start_crystals": 0,
        "desc": [
            "标准规则，从零开始的深渊之旅。",
            "敌人随深度成长，每 10 层一位领主。",
            "没有任何额外修饰。",
        ],
    },
    MODE_AFFIX_FRENZY: {
        "name": "词缀狂欢",
        "stars": "★★☆",
        "start_crystals": 30,
        "desc": [
            "开局携带 30 晶体，缓解前期压力。",
            "每个敌人都至少携带 1 条词缀。",
            "词缀数量没有上限，但越多概率越小。",
            "精英与巨型骷髅同样会堆叠更多词缀。",
        ],
    },
    MODE_UNDEAD_TIDE: {
        "name": "亡灵潮",
        "stars": "★★★",
        "start_crystals": 30,
        "desc": [
            "开局携带 30 晶体，缓解前期压力。",
            "非骷髅非幽灵单位死亡后原地站起骷髅。",
            "任何骷髅死亡都会留下幽灵。",
            "精英与领主死亡会降下巨大骷髅。",
            "死亡气息常驻累积，满 10 点爆发一次。",
            "召唤物死亡不会引发连锁。",
        ],
    },
    MODE_ELITE_HELL: {
        "name": "精英地狱",
        "stars": "★★★",
        "start_crystals": 50,
        "free_shop": True,
        "all_elite": True,
        "desc": [
            "开局 50 晶体，打开商店免入场费。",
            "普通敌人全部换成精英，数量不变。",
            "精英血量不做削减，强度照旧。",
            "精英种类无视环境随机抽取。",
        ],
    },
    MODE_SUMMONER: {
        "name": "召唤师",
        "stars": "★★☆",
        "start_crystals": 0,
        "desc": [
            "U/I/O 开局可用，但装的是召唤物。",
            "按键进入捕捉，击杀敌人即收入该槽。",
            "再按一次放出，出战后再按即收回。",
            "普通盟友扫荡，精英盟友主动索敌。",
            "盟友阵亡后槽位清空，需要重新捕捉。",
            "商店第2页可提升盟友生命/攻击/词缀。",
        ],
    },
}

# 每种模式的同屏敌人上限，防止连锁生成拖垮帧数
MODE_ENEMY_CAP = {
    MODE_CLASSIC: 20,
    MODE_AFFIX_FRENZY: 20,
    MODE_UNDEAD_TIDE: 34,
    MODE_ELITE_HELL: 20,
    MODE_SUMMONER: 22,
}

# 这些模式里精英不再受生物群系限制，种类完全随机
MODE_ALL_ELITE = {MODE_ELITE_HELL}
