"""成就系统。

成就不靠事件回调，而是从已经记下来的数据里算出来：跨局数据在存档里
（层数、总击杀、图鉴击杀与阵亡），单局数据在最近一局记录里
（单局击杀、无伤房间、最高单次、精英击杀、伤害构成）。
所以加一条成就通常只要往下面的表里写一行。
"""

from .data.bosses import BOSS_NAMES


def _codex_kill(name):
    return lambda book, run: book.codex_kills(name)


def _codex_kills_any(names):
    return lambda book, run: sum(1 for n in names if book.codex_kills(n) > 0)


def _deaths_by_boss():
    def value(book, run):
        return sum(1 for name in BOSS_NAMES.values() if book.codex_deaths(name) > 0)
    return value


def _mode_best(mode_id):
    return lambda book, run: book.mode_best(mode_id)


def _run_value(key):
    def value(book, run):
        return int(run.get(key, 0) or 0)
    return value


def _share_of(bucket, least):
    """某一类伤害在本局的占比超过阈值（同时要有最低总量，避免刷小数据）。"""
    def value(book, run):
        dealt = run.get("dealt") or {}
        total = sum(dealt.values())
        if total < least:
            return 0
        return int(100 * dealt.get(bucket, 0) / total)
    return value


ACHIEVEMENTS = [
    {"id": "first_run", "name": "初次下潜", "desc": "完成第一局",
     "target": 1, "value": lambda b, r: b.total_runs},
    {"id": "first_blood", "name": "亡者初见", "desc": "累计击杀 1 个敌人",
     "target": 1, "value": lambda b, r: b.total_kills},
    {"id": "kill_100", "name": "小有斩获", "desc": "累计击杀 100 个敌人",
     "target": 100, "value": lambda b, r: b.total_kills},
    {"id": "kill_500", "name": "百战之身", "desc": "累计击杀 500 个敌人",
     "target": 500, "value": lambda b, r: b.total_kills},
    {"id": "depth_10", "name": "深渊行者", "desc": "到达第 10 层",
     "target": 10, "value": lambda b, r: b.best_depth},
    {"id": "depth_20", "name": "隧道尽头", "desc": "到达第 20 层",
     "target": 20, "value": lambda b, r: b.best_depth},
    {"id": "depth_30", "name": "无尽深渊", "desc": "到达第 30 层",
     "target": 30, "value": lambda b, r: b.best_depth},
    {"id": "kill_50_run", "name": "硬骨头", "desc": "单局击杀 50 个敌人",
     "target": 50, "value": lambda b, r: b.best_kills},
    {"id": "kill_100_run", "name": "收割者", "desc": "单局击杀 100 个敌人",
     "target": 100, "value": lambda b, r: b.best_kills},
    {"id": "boss_first", "name": "领主终结者", "desc": "击败任意一位领主",
     "target": 1, "value": _codex_kills_any(list(BOSS_NAMES.values()))},
    {"id": "boss_all", "name": "群魔俯首", "desc": "击败全部 7 位领主",
     "target": len(BOSS_NAMES), "value": _codex_kills_any(list(BOSS_NAMES.values()))},
    {"id": "die_to_boss", "name": "与恶魔同行", "desc": "被任意一位领主打死",
     "target": 1, "value": _deaths_by_boss()},
    {"id": "skeleton_20", "name": "亡灵克星", "desc": "累计击杀 20 只骷髅兵",
     "target": 20, "value": _codex_kill("骷髅兵")},
    {"id": "ghost_20", "name": "幽魂散尽", "desc": "累计击杀 20 只幽灵",
     "target": 20, "value": _codex_kill("幽灵")},
    {"id": "wraithbone_5", "name": "骨与魂", "desc": "累计击杀 5 只魔魂亡骨",
     "target": 5, "value": _codex_kill("魔魂亡骨")},
    {"id": "elite_3_run", "name": "精英猎手", "desc": "单局击杀 3 个精英",
     "target": 3, "value": _run_value("elite_kills")},
    {"id": "clean_3", "name": "毫发无伤", "desc": "单局有 3 个房间没掉血",
     "target": 3, "value": _run_value("clean_rooms")},
    {"id": "clean_8", "name": "滴水不漏", "desc": "单局有 8 个房间没掉血",
     "target": 8, "value": _run_value("clean_rooms")},
    {"id": "best_hit_80", "name": "一击必杀", "desc": "单次造成 80 点伤害",
     "target": 80, "value": _run_value("best_hit")},
    {"id": "low_hp_1", "name": "极限逃生", "desc": "血量只剩 1 点还活了下来",
     "target": 1, "value": lambda b, r: 1 if r.get("lowest_health") == 1 else 0},
    {"id": "bomb_share", "name": "炸弹狂人", "desc": "单局炸弹伤害占比超过 40%（总量 300+）",
     "target": 40, "value": _share_of("炸弹与灼烧", 300)},
    {"id": "skill_1000", "name": "技能大师", "desc": "单局技能伤害超过 1000",
     "target": 1000, "value": lambda b, r: int((r.get("dealt") or {}).get("技能", 0))},
    {"id": "summoner_8", "name": "召唤大师", "desc": "召唤师模式到达第 8 层",
     "target": 8, "value": _mode_best("summoner")},
    {"id": "undead_8", "name": "亡灵潮的幸存者", "desc": "亡灵潮模式到达第 8 层",
     "target": 8, "value": _mode_best("undead_tide")},
    {"id": "elite_hell_8", "name": "精英地狱的幸存者", "desc": "精英地狱模式到达第 8 层",
     "target": 8, "value": _mode_best("elite_hell")},
    {"id": "frenzy_8", "name": "词缀狂欢者", "desc": "词缀狂欢模式到达第 8 层",
     "target": 8, "value": _mode_best("affix_frenzy")},
    {"id": "soul_reaper_shield_death", "name": "护盾谎言",
     "desc": "在护盾开启时被炼魂魔骷的真实伤害杀死",
     "target": 1,
     "value": lambda b, r: 1 if r.get("soul_reaper_shield_death") else 0},
]


def progress(book, run):
    """返回 (成就条目, 当前值, 是否已解锁) 的列表，供界面显示。"""
    unlocked = set(book.achievements())
    rows = []
    for item in ACHIEVEMENTS:
        try:
            value = item["value"](book, run)
        except Exception:
            value = 0
        rows.append((item, min(value, item["target"]), item["id"] in unlocked))
    return rows


def evaluate(book, run):
    """算一遍成就，把新解锁的写进存档并返回。"""
    unlocked = set(book.achievements())
    fresh = []
    for item in ACHIEVEMENTS:
        if item["id"] in unlocked:
            continue
        try:
            value = item["value"](book, run)
        except Exception:
            value = 0
        if value >= item["target"]:
            fresh.append(item)
    if fresh:
        book.unlock([item["id"] for item in fresh])
    return fresh


def unlocked_count(book):
    return len(set(book.achievements()) & {item["id"] for item in ACHIEVEMENTS})
