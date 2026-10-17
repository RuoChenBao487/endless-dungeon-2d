"""局外存档。

记录跨局保留的数据：最高层数（分模式）、累计击杀、总场次、最近几局成绩，
以及设置项。存档是和 main.py 同级目录下的 save_data.json，
读写失败不会影响游戏运行。
"""


# === IMPORTS ===
from pathlib import Path
import json
from .settings import SETTINGS
# === /IMPORTS ===

SAVE_VERSION = 2
RECENT_LIMIT = 5


def default_path():
    """存档文件放在 15.0 目录下，跟着游戏走。"""
    return Path(__file__).resolve().parents[1] / "save_data.json"


def _defaults():
    return {
        "version": SAVE_VERSION,
        "best_depth": 0,
        "best_depth_mode": "",
        "best_kills": 0,
        "total_kills": 0,
        "total_runs": 0,
        "mode_best": {},
        "mode_runs": {},
        "recent": [],
        "codex": {"kills": {}, "deaths": {}},
        "last_run": {},
        "achievements": [],
        "settings": {"auto_fire": False},
    }


class Profile:
    """存档的读取、修改与落盘。"""

    def __init__(self, path=None):
        self.path = Path(path) if path else default_path()
        self.data = _defaults()
        self.load()

    # ---- 读写 --------------------------------------------------------
    def load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not isinstance(raw, dict):
            return False
        data = _defaults()
        for key, value in raw.items():
            if key in data and isinstance(value, type(data[key])):
                data[key] = value
            elif key in ("mode_best", "mode_runs", "settings", "recent"):
                if isinstance(value, type(data[key])):
                    data[key] = value
        self.data = data
        return True

    def save(self):
        try:
            self.data["version"] = SAVE_VERSION
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8")
            return True
        except OSError:
            return False

    # ---- 记录查询 ----------------------------------------------------
    @property
    def best_depth(self):
        return self.data["best_depth"]

    @property
    def best_depth_mode(self):
        return self.data["best_depth_mode"]

    @property
    def total_kills(self):
        return self.data["total_kills"]

    @property
    def total_runs(self):
        return self.data["total_runs"]

    @property
    def best_kills(self):
        return self.data["best_kills"]

    def mode_best(self, mode_id):
        return self.data["mode_best"].get(mode_id, 0)

    def mode_runs(self, mode_id):
        return self.data["mode_runs"].get(mode_id, 0)

    def recent(self):
        return list(self.data["recent"])

    # ---- 写入接口 ----------------------------------------------------
    def record_run(self, mode_id, mode_name, depth, kills, frames=0):
        """记一局的成绩，返回是否刷新纪录，供结算界面提示。"""
        data = self.data
        prev_best = data["mode_best"].get(mode_id, 0)
        data["total_runs"] += 1
        data["total_kills"] += kills
        data["mode_runs"][mode_id] = data["mode_runs"].get(mode_id, 0) + 1
        broke_mode = depth > prev_best
        if broke_mode:
            data["mode_best"][mode_id] = depth
        broke_overall = depth > data["best_depth"]
        if broke_overall:
            data["best_depth"] = depth
            data["best_depth_mode"] = mode_name
        data["best_kills"] = max(data["best_kills"], kills)
        data["recent"].insert(0, {
            "mode": mode_name, "depth": depth, "kills": kills, "frames": frames,
        })
        del data["recent"][RECENT_LIMIT:]
        self.save()
        return {
            "broke_mode": broke_mode,
            "broke_overall": broke_overall,
            "prev_best": prev_best,
        }

    def set_setting(self, key, value):
        self.data["settings"][key] = value
        self.save()

    def get_setting(self, key, fallback=False):
        return self.data["settings"].get(key, fallback)

    # ---- 图鉴统计 ----------------------------------------------------
    def codex_kills(self, name):
        return self.data["codex"]["kills"].get(name, 0)

    def codex_deaths(self, name):
        return self.data["codex"]["deaths"].get(name, 0)

    def record_codex(self, kills, deaths=()):
        """把一局里攒下的击杀记进图鉴，写盘一次。"""
        if not kills and not deaths:
            return
        book = self.data["codex"]
        for name, count in kills.items():
            if count > 0:
                book["kills"][name] = book["kills"].get(name, 0) + count
        for name, count in deaths.items():
            if count > 0:
                book["deaths"][name] = book["deaths"].get(name, 0) + count
        self.save()

    def record_last_run(self, summary):
        self.data["last_run"] = dict(summary)
        self.save()

    def last_run(self):
        return dict(self.data.get("last_run") or {})

    # ---- 成就 --------------------------------------------------------
    def achievements(self):
        return list(self.data["achievements"])

    def unlock(self, ids):
        """解锁成就，返回真正新增的那些。"""
        owned = set(self.data["achievements"])
        fresh = [i for i in ids if i not in owned]
        if fresh:
            self.data["achievements"].extend(fresh)
            self.save()
        return fresh


_profile = None


def profile():
    """全局单例，第一次访问时才读盘。"""
    global _profile
    if _profile is None:
        _profile = Profile()
    return _profile


def apply_saved_settings():
    """启动时把存档里的设置同步到运行时的 SETTINGS。"""
    for key, value in profile().data["settings"].items():
        if key in SETTINGS:
            SETTINGS[key] = value


def set_setting(key, value):
    """改一个设置项：先落到运行时，再写回存档。"""
    SETTINGS[key] = value
    profile().set_setting(key, value)


def set_auto_fire(value):
    """切换自动射击。"""
    set_setting("auto_fire", value)
