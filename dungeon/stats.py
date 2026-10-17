"""一局的战斗统计。

只保存数字与字符串，不引用任何精灵对象，所以既能直接喂给结算界面，
也能原样写进存档。
"""

# 伤害来源 -> 结算面板上的分类
_CATEGORY = {
    "bullet": "普通攻击",
    "bomb": "炸弹与灼烧",
    "scorch": "炸弹与灼烧",
    "lava": "炸弹与灼烧",
    "ember": "炸弹与灼烧",
    "thorns": "反伤与盟友",
    "ally": "反伤与盟友",
    "temple_beam": "寺庙水晶",
    "holy_cross": "环境与机关",
}

_SKILL_SOURCES = {
    "explosion", "skill_fireball_explosion", "skill_fireball_direct",
    "black_hole_devour", "soul_chain_shared", "shockwave", "dash",
    "ice_shard", "ice_shatter",
}

BURST_WINDOW = 90        # 判定“爆发”的帧窗口
BURST_COUNT = 5
BIG_HIT = 40             # 记进高光的大额单次伤害
LOW_HEALTH = 3           # 记进高光的残血线
HIGHLIGHT_LIMIT = 6

# 承伤来源的显示名：内部标签换成中文，免得结算面板出现 'burn' 这种字样
SOURCE_LABELS = {
    "burn": "燃烧", "trap": "地刺", "lava": "岩浆", "hunter": "猎魂幽灵",
    "ice_spike": "冰刺", "nova": "冲击波", "ground_wave": "贴地横波",
    "fireball": "火球", "flame_wall": "火墙", "ember": "余烬自爆",
    "hook": "铁钩", "death_explosion": "死亡爆炸", "ice_shard": "冰锥",
    "boss": "领主", "enemy": "敌人",
    "soul_shock": "灵魂冲击", "soul_burn": "燃魂",
    "soul_burn_self": "自身燃魂",
}


def source_label(source):
    return SOURCE_LABELS.get(source, source or "未知")


def categorize(source):
    """把伤害来源归到结算面板的四个分类里。"""
    if not source:
        return "其他"
    if source in _CATEGORY:
        return _CATEGORY[source]
    if source in _SKILL_SOURCES or source.startswith("skill"):
        return "技能"
    return "其他"


class RunStats:
    """记录一局的输出、承伤与高光。"""

    def __init__(self):
        self.dealt = {}              # 分类 -> 伤害
        self.taken = {}              # 来源 -> 伤害
        self.shots = 0               # 普攻出手次数
        self.kills = 0
        self.elite_kills = 0
        self.boss_kills = []         # [(名称, 层数)]
        self.best_hit = 0.0
        self.best_hit_from = ""
        self.best_hit_target = ""
        self.lowest_health = None
        self.clean_rooms = 0         # 无伤通过的房间数
        self.room_dirty = False      # 当前房间是否已经挨过打
        self.highlights = []
        self._recent_kills = []      # 最近的击杀帧号，用来判断爆发
        self._burst_done = False

    # ---- 记录 ------------------------------------------------------
    def record_shot(self):
        self.shots += 1

    def record_dealt(self, source, damage, target=""):
        damage = float(damage)
        if damage <= 0:
            return
        bucket = categorize(source)
        self.dealt[bucket] = self.dealt.get(bucket, 0.0) + damage
        if damage > self.best_hit:
            self.best_hit = damage
            self.best_hit_from = bucket
            self.best_hit_target = target

    def record_taken(self, source, damage):
        damage = float(damage)
        if damage <= 0:
            return
        self.taken[source] = self.taken.get(source, 0.0) + damage
        self.room_dirty = True

    def note_health(self, health):
        if health > 0 and (self.lowest_health is None or health < self.lowest_health):
            self.lowest_health = health

    def record_kill(self, is_elite=False, frame=0):
        self.kills += 1
        if is_elite:
            self.elite_kills += 1
        self._recent_kills = [f for f in self._recent_kills if frame - f <= BURST_WINDOW]
        self._recent_kills.append(frame)
        if not self._burst_done and len(self._recent_kills) >= BURST_COUNT:
            self._burst_done = True
            self.add_highlight(f"爆发：1.5 秒内放倒 {len(self._recent_kills)} 个敌人")

    def record_boss_kill(self, name, depth):
        self.boss_kills.append((name, depth))
        self.add_highlight(f"终结领主：{name}（第 {depth} 层）")

    def note_room_cleared(self, depth):
        if not self.room_dirty:
            self.clean_rooms += 1
        self.room_dirty = False

    # ---- 高光与汇总 ------------------------------------------------
    def add_highlight(self, text):
        if text and text not in self.highlights:
            self.highlights.append(text)

    def build_highlights(self, died=False):
        """结算时补齐那些只能事后判断的高光。"""
        if self.best_hit >= BIG_HIT:
            self.add_highlight(f"致命一击：单次 {int(self.best_hit)} 点伤害（{self.best_hit_from}）")
        if self.lowest_health is not None and self.lowest_health <= LOW_HEALTH:
            self.add_highlight(f"残血逃生：血量一度只剩 {int(self.lowest_health)} 点")
        if self.clean_rooms >= 3:
            self.add_highlight(f"滴水不漏：{self.clean_rooms} 个房间没掉血")
        return self.highlights[:HIGHLIGHT_LIMIT]

    def dealt_rows(self, limit=4):
        return _rows(self.dealt, limit)

    def taken_rows(self, limit=3):
        return _rows(self.taken, limit)

    def total_dealt(self):
        return sum(self.dealt.values())

    def total_taken(self):
        return sum(self.taken.values())

    def to_dict(self, highlights=None):
        return {
            "dealt": {k: round(v, 1) for k, v in self.dealt.items()},
            "taken": {k: round(v, 1) for k, v in self.taken.items()},
            "shots": self.shots,
            "kills": self.kills,
            "elite_kills": self.elite_kills,
            "boss_kills": [list(x) for x in self.boss_kills],
            "best_hit": round(self.best_hit, 1),
            "best_hit_from": self.best_hit_from,
            "lowest_health": self.lowest_health,
            "clean_rooms": self.clean_rooms,
            "total_dealt": round(self.total_dealt(), 1),
            "total_taken": round(self.total_taken(), 1),
            "highlights": list(self.highlights if highlights is None else highlights),
        }

    @classmethod
    def from_dict(cls, data):
        stats = cls()
        for key in ("dealt", "taken", "shots", "kills", "elite_kills", "best_hit",
                    "best_hit_from", "best_hit_target", "lowest_health", "clean_rooms",
                    "room_dirty", "highlights"):
            if key in data:
                setattr(stats, key, data[key])
        stats.boss_kills = [tuple(item) for item in data.get("boss_kills", [])]
        return stats

def _rows(mapping, limit):
    """转成 (名称, 伤害, 占比) 的降序列表。"""
    total = sum(mapping.values())
    rows = sorted(mapping.items(), key=lambda kv: -kv[1])[:limit]
    return [(name, value, (value / total) if total else 0.0) for name, value in rows]
