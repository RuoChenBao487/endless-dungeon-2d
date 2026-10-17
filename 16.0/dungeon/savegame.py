"""暂停存档：把一局的现场原样存下来，之后随时继续。

做法是通用快照而不是逐类手写：遍历所有精灵组，把每个精灵的字段编码成 JSON
（数字、字符串、列表、字典随便存；指向别的精灵的引用存成对方的编号），
贴图单独存成内联 PNG，读档时按编号把引用接回去。
这样以后新增敌人或投射物不用再改存档代码。

和 save_data.json 分工：那份存跨局的纪录与设置，这份只存进行中的那一局。
"""

import base64
import importlib
import io
import json
import random
from pathlib import Path

import pygame

from . import save as _save
from .data.modes import MODES
from .stats import RunStats
from .timing import frame_count

SNAPSHOT_VERSION = 1

# 需要逐帧存下来的精灵组（顺序无关，这里只用来遍历）
GROUPS = (
    "platforms", "enemies", "bullets", "bombs", "barriers", "traps", "ice_trails",
    "crystals", "mirrors", "nova_waves", "ice_spikes", "warnings", "summon_circles",
    "fireballs", "flame_walls", "lava_pools", "embers", "hook_projectiles",
    "skill_fireballs", "black_hole_bullets", "black_holes", "ice_shards", "meteors",
    "ground_waves", "floating_texts", "event_goals", "allies",
    "snow_drifts", "storm_crystals", "church_crosses", "gravestones",
    "soul_shocks",
)

# Game 上不进存档的字段：要么是静态表，要么带着函数或界面状态
SKIP_GAME_FIELDS = {
    "enemy_descriptions", "reward_descriptions", "game_rules", "enhancements",
    "shop_items", "stats", "all_sprites",
}

# 这些字段存的是绝对帧号，改存成“距存档那一刻过了多少帧”，读档时再换算回来
STAMP_FIELDS = {"last_shot_time", "shield_end_time", "message_start_frame"}

# 老存档兜底：这些字段是后来才加到类上的，旧存档里没有；
# 以后给精灵新增字段时，记得往这里补一条默认值。
SPRITE_FIELD_DEFAULTS = {
    "buff_timer": 0,
    "is_wind": False,
    "is_wraithbone": False,
    "is_giant": False,
    "is_ally": False,
    "is_ember": False,
    "is_undead": False,
    "is_blood_minion": False,
    "is_church_cross": False,
    "contact_harmful": True,
    "cross_buff_timer": 0,
    "is_zombie": False,
    "is_giant_zombie": False,
    "is_bone_carrier": False,
    "slow_immune": False,
    "damage_multiplier": 1.0,
    "aura_speed_bonus": 0.0,
    "aura_damage_reduction": 0.0,
}


class _Skip(Exception):
    """编码不了的值，直接跳过这个字段。"""


# ============================================================
# 路径
# ============================================================
def save_path(path=None):
    if path is not None:
        return Path(path)
    return _save.default_path().with_name("run_save.json")


def has_save(path=None):
    return save_path(path).exists()


def header(path=None):
    """给主菜单显示用的摘要；读不出来就返回 None。"""
    data = _read(path)
    if not data:
        return None
    if not _classes_ok(data):
        # 存档是旧代码写的，类已经不在了，主菜单就不要把它当成可继续的存档
        return None
    return {
        "mode_name": data.get("mode_name", "未知模式"),
        "depth": data.get("depth", 0),
        "kills": data.get("kills", 0),
        "saved_at": data.get("saved_at", ""),
    }


def _classes_ok(data):
    """检查存档里引用的精灵类是否都还在，避免主菜单点进去才发现读不了。"""
    for entry in data.get("sprites", ()):
        try:
            _cls_of(entry.get("cls", ""))
        except Exception:
            return False
    return True


def clear(path=None):
    try:
        save_path(path).unlink()
        return True
    except OSError:
        return False


def _read(path=None):
    try:
        raw = json.loads(save_path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or raw.get("version") != SNAPSHOT_VERSION:
        return None
    return raw


# ============================================================
# 编码
# ============================================================
def _cls_name(obj):
    return f"{type(obj).__module__}:{type(obj).__name__}"


def _cls_of(name):
    module, _, cls = name.partition(":")
    return getattr(importlib.import_module(module), cls)


def _encode(value, frame):
    if value is None or isinstance(value, (bool, int, str, float)):
        return value
    if isinstance(value, pygame.Rect):
        return {"@rect": [value.x, value.y, value.width, value.height]}
    if isinstance(value, pygame.sprite.Sprite):
        return {"@ref": id(value)}
    if isinstance(value, pygame.Surface):
        # 玩家还额外握着 left_image / right_image 这类贴图，一并带上
        return {"@png": _encode_image(value)}
    if isinstance(value, (list, tuple)):
        return {"@list": [_encode(v, frame) for v in value]}
    if isinstance(value, set):
        return {"@set": [_encode(v, frame) for v in value]}
    if isinstance(value, dict):
        return {"@dict": [[_encode(k, frame), _encode(v, frame)] for k, v in value.items()]}
    if isinstance(value, (pygame.font.Font, pygame.time.Clock, pygame.sprite.Group)):
        raise _Skip
    if callable(value):
        raise _Skip
    if hasattr(value, "to_dict") and hasattr(value, "from_dict"):
        return {"@obj": {"cls": _cls_name(value), "data": value.to_dict()}}
    if hasattr(value, "__dict__") and vars(value):
        # 词缀实例这类小对象：字段照存，指向别人的引用照样接回去
        return {"@new": {"cls": _cls_name(value),
                         "fields": _encode_fields(value, frame)}}
    raise _Skip


def _encode_fields(obj, frame):
    fields = {}
    for key, value in vars(obj).items():
        if key in ("image", "rect"):
            continue
        try:
            encoded = _encode(value, frame)
        except _Skip:
            continue
        if key in STAMP_FIELDS and isinstance(encoded, int):
            encoded = {"@stamp": encoded - frame}
        fields[key] = encoded
    return fields


def _encode_image(surface):
    buffer = io.BytesIO()
    try:
        pygame.image.save(surface, buffer, "png")
    except Exception:
        return None
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _decode_image(blob):
    """把内联 PNG 还原成贴图；坏了就返回 None。"""
    if not blob:
        return None
    try:
        surface = pygame.image.load(io.BytesIO(base64.b64decode(blob)))
        try:
            surface = surface.convert_alpha()
        except Exception:
            pass
        return surface
    except Exception:
        return None


def snapshot(game):
    """把一局的现场编码成可以写盘的结构。"""
    frame = frame_count()
    sprites = []
    seen = set()
    # 遍历时带上 all_sprites，免得只挂在总组里的精灵（比如玩家）漏掉
    for group_name in GROUPS + ("all_sprites",):
        group = getattr(game, group_name, None)
        if group is None:
            continue
        for sprite in group:
            if id(sprite) in seen:
                continue
            seen.add(id(sprite))
            entry = {
                "id": id(sprite),
                "cls": _cls_name(sprite),
                "groups": [],
                "in_all": game.all_sprites.has(sprite),
                "x": sprite.rect.x,
                "y": sprite.rect.y,
                "fields": _encode_fields(sprite, frame),
            }
            if sprite.image is not None:
                entry["image"] = _encode_image(sprite.image)
            for other in GROUPS:
                target = getattr(game, other, None)
                if target is not None and target.has(sprite):
                    entry["groups"].append(other)
            sprites.append(entry)

    fields = {}
    for key, value in vars(game).items():
        if key in SKIP_GAME_FIELDS:
            continue
        if isinstance(value, pygame.sprite.Group):
            continue
        try:
            fields[key] = _encode(value, frame)
        except _Skip:
            continue

    return {
        "version": SNAPSHOT_VERSION,
        "mode": game.mode,
        "mode_name": game.mode_name,
        "depth": game.current_depth,
        "kills": game.player.kills,
        "saved_at": _now_text(),
        "frame": frame,
        "fields": fields,
        "stats": game.stats.to_dict(),
        "sprites": sprites,
    }


def _now_text():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def write(game, path=None):
    """写盘；先写临时文件再替换，避免写一半崩掉把存档写坏。"""
    data = snapshot(game)
    target = save_path(path)
    tmp = target.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(target)
        return True
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


# ============================================================
# 解码
# ============================================================
def _decode(value, resolve, frame):
    if isinstance(value, dict):
        if "@ref" in value:
            return resolve(value["@ref"])
        if "@rect" in value:
            return pygame.Rect(*value["@rect"])
        if "@png" in value:
            surface = _decode_image(value["@png"])
            return surface if surface is not None else pygame.Surface((1, 1), pygame.SRCALPHA)
        if "@list" in value:
            return [_decode(v, resolve, frame) for v in value["@list"]]
        if "@set" in value:
            return {_decode(v, resolve, frame) for v in value["@set"]
                    if not isinstance(v, dict) or "@ref" not in v
                    or resolve(v["@ref"]) is not None}
        if "@dict" in value:
            return {_decode(k, resolve, frame): _decode(v, resolve, frame)
                    for k, v in value["@dict"]}
        if "@stamp" in value:
            return frame + value["@stamp"]
        if "@obj" in value:
            cls = _cls_of(value["@obj"]["cls"])
            return cls.from_dict(value["@obj"]["data"])
        if "@new" in value:
            cls = _cls_of(value["@new"]["cls"])
            obj = cls.__new__(cls)
            for key, item in value["@new"]["fields"].items():
                setattr(obj, key, _decode(item, resolve, frame))
            return obj
    return value


def _decode_fields(game, entry, resolve, frame):
    fields = {}
    for key, value in entry["fields"].items():
        fields[key] = _decode(value, resolve, frame)
    return fields


def _build_sprite(entry):
    """先建一个空壳，贴图从内联 PNG 还原，字段稍后再填。"""
    cls = _cls_of(entry["cls"])
    sprite = cls.__new__(cls)
    pygame.sprite.Sprite.__init__(sprite)
    surface = _decode_image(entry.get("image"))
    sprite.image = surface if surface is not None else pygame.Surface((16, 16), pygame.SRCALPHA)
    sprite.rect = sprite.image.get_rect(topleft=(entry.get("x", 0), entry.get("y", 0)))
    return sprite


def load(path=None):
    """读档并还原成一局。

    存档不存在、版本对不上、类已经不在、或者数据被改坏了，一律返回 None
    交给调用方当作"没有存档"处理——绝不让一份坏档把游戏卡在启动阶段。
    """
    try:
        game = _load(path)
    except Exception:
        return None
    if game is None:
        return None
    if not _is_playable(game):
        return None
    _repair(game)
    return game


def _is_playable(game):
    """必要的现场元素齐不齐：玩家必须在，且带 rect。"""
    player = getattr(game, "player", None)
    if not isinstance(player, pygame.sprite.Sprite):
        return False
    return isinstance(getattr(player, "rect", None), pygame.Rect)


def _load(path=None):
    from .game import Game      # 延迟导入，避免和 game 包互相引用

    data = _read(path)
    if not data:
        return None
    # 模式对不上（比如以后删掉了某个模式）就当这份档不能用，别静默换成经典模式
    if data.get("mode") not in MODES:
        return None
    # 玩家必须在存档字段里；缺了它只能用新建的默认玩家顶上，现场就串了
    if "player" not in (data.get("fields") or {}):
        return None
    frame = frame_count()

    game = Game(data["mode"])
    for group_name in GROUPS:
        group = getattr(game, group_name, None)
        if group is not None:
            group.empty()
    game.all_sprites.empty()

    sprites = {}
    for entry in data["sprites"]:
        sprites[entry["id"]] = _build_sprite(entry)

    def resolve(sprite_id):
        return sprites.get(sprite_id)

    for entry in data["sprites"]:
        sprite = sprites[entry["id"]]
        for key, value in _decode_fields(game, entry, resolve, frame).items():
            setattr(sprite, key, value)
        for group_name in entry.get("groups", ()):
            group = getattr(game, group_name, None)
            if group is not None and not group.has(sprite):
                group.add(sprite)
        # 原样还原它是否在总组里，免得把本来不画的精灵画出来
        if entry.get("in_all", True) and not game.all_sprites.has(sprite):
            game.all_sprites.add(sprite)

    for key, value in data.get("fields", {}).items():
        setattr(game, key, _decode(value, resolve, frame))

    game.stats = RunStats.from_dict(data.get("stats", {}))
    game.shop_items = []
    game.show_shop = False
    game.paused = False
    game.message_text = ""
    game.message_duration = 0
    game.message_start_frame = frame
    return game


def _repair(game):
    """补齐老存档缺的贴图属性。

    早期版本只存了 sprite.image，玩家身上那对左右图（left_image / right_image）
    没被写下来，读回来一转向就会崩；能重新生成的就地补上。
    """
    player = getattr(game, "player", None)
    if player is None:
        return
    # 老存档缺的新字段用默认值补齐，免得读档后第一帧就 AttributeError
    for sprite in game.all_sprites:
        # 只补敌人 / 精英 / 盟友（它们都有 is_elite），平台与投射物没有这些字段
        if hasattr(sprite, "is_elite"):
            for key, value in SPRITE_FIELD_DEFAULTS.items():
                if not hasattr(sprite, key):
                    setattr(sprite, key, value)
            from .data.enemies import UNDEAD_ENEMY_TYPES
            if getattr(sprite, "enemy_type", None) in UNDEAD_ENEMY_TYPES:
                sprite.is_undead = True
            if (getattr(sprite, "kind", None) == "vampire"
                    or getattr(sprite, "kind", None) == "blood"):
                sprite.is_undead = True
            continue
        # 领主（有 _cd）只需要增幅计时，别的一概不塞
        if hasattr(sprite, "_cd") and not hasattr(sprite, "buff_timer"):
            sprite.buff_timer = 0
    # 回调不能进存档（函数没法序列化），读档后要重新挂上，否则承伤统计会失效
    if getattr(player, "damage_reporter", None) is None:
        player.damage_reporter = getattr(game, "note_player_damage", None)
    if not isinstance(getattr(player, "left_image", None), pygame.Surface) \
            or not isinstance(getattr(player, "right_image", None), pygame.Surface):
        build = getattr(player, "create_player_images", None)
        if callable(build):
            build()
    player_defaults = {
        "soul_burn_timer": 0,
        "soul_burn_tick": 0,
        "soul_burn_damage": 2,
        "soul_burn_source": "",
        "last_damage_codex": None,
    }
    for key, value in player_defaults.items():
        if not hasattr(player, key):
            setattr(player, key, value)
        # 补完之后按原先朝向重新选一张
        if getattr(player, "facing_right", True):
            player.image = player.right_image
        else:
            player.image = player.left_image
