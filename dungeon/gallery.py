"""敌人图鉴：条目表、形象预览与统计数据。

形象是拿现有的敌人工厂现场生成一次、放大后缓存下来的，所以敌人画法一改，
图鉴里的样子跟着变，不需要额外维护一套图。菜单与暂停界面共用同一份条目表。
"""

import random

import pygame

from .bosses import create_boss
from .data.biomes import (BIOME_ICE, BIOME_LAVA, BIOME_NORMAL, BIOME_NAMES, BIOME_POISON,
                          BIOME_TOMB)
from .data.bosses import (BOSS_BONE_DRAGON, BOSS_FALLEN_KNIGHT, BOSS_ICE_TITAN,
                          BOSS_INFERNAL_DEMON, BOSS_MOLTEN_GIANT, BOSS_POISON_QUEEN,
                          BOSS_STITCHED)
from .data.enemies import BIOME_ENEMY_POOL, CODEX_ELITE_NAME, ELITE_STATS, ENEMY_WRAITHBONE
from .entities.church import BloodCross, HolyCross
from .entities.enemies import BoneCarrierEnemy, EliteEnemy, Enemy
from .save import profile
from .settings import (GOLD, OUTLINE, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE, get_font, screen)
from .utils import back_hit, draw_back_button, draw_panel as draw_box

PREVIEW_BOX = 100            # 单个形象放大后的最大边长
PREVIEW_GAP = 16
SPRITE_DEPTH = 1             # 生成样本时的深度，取低值避免刷出词缀
LIST_RECT = (42, 146, 280, SCREEN_HEIGHT - 198)
ROW_H = 20

CATEGORY_FILTERS = (
    ("all", "全部"),
    ("normal", "普通敌人"),
    ("elite", "精英敌人"),
    ("boss", "BOSS"),
    ("other", "特殊"),
)

PLACE_FILTERS = (
    ("all", "全部"),
    ("universal", "通用"),
    ("normal", "普通地牢"),
    ("ice", "冰晶"),
    ("lava", "熔岩"),
    ("poison", "腐沼"),
    ("tomb", "墓穴"),
    ("snow", "雪山"),
    ("temple", "寺庙"),
    ("church", "教堂"),
    ("great_tomb", "大墓地"),
)

PLACE_LABELS = {
    "universal": "通用",
    "normal": "普通地牢",
    "ice": "冰晶洞穴",
    "lava": "熔岩洞窟",
    "poison": "腐沼秘境",
    "tomb": "亡灵墓穴",
    "snow": "暴雪山脉",
    "temple": "暴云寺庙",
    "church": "破败教堂",
    "great_tomb": "古代大墓地",
}


ENTRIES = [
    {"name": "红色士兵", "enemy_type": 0, "desc": ["基础敌人", "生命值随深度增加"]},
    {"name": "跳跃者", "enemy_type": 1, "desc": ["擅长跳跃接近玩家"]},
    {"name": "强化兵", "enemy_type": 2, "desc": ["减免30%子弹伤害"]},
    {"name": "坦克", "enemy_type": 3, "desc": ["高血量，减免20%伤害"]},
    {"name": "冰漫步者", "enemy_type": 4, "desc": ["冰晶场景特有", "留下冰痕减速"]},
    {"name": "冰甲守卫", "enemy_type": 5, "desc": ["初始有护盾"]},
    {"name": "雪团怪", "enemy_type": 6, "desc": ["死亡后分裂"]},
    {"name": "火蝠", "enemy_type": 7, "desc": ["熔岩场景飞行敌人"]},
    {"name": "熔岩史莱姆", "enemy_type": 8, "desc": ["熔岩场景，死亡留岩浆"]},
    {"name": "毒蘑菇", "enemy_type": 9, "desc": ["腐沼场景，远程吐毒"]},
    {"name": "沼泽蛙", "enemy_type": 10, "desc": ["腐沼场景，跳跃扑击"]},
    {"name": "骷髅兵", "enemy_type": 11, "desc": ["墓穴场景，死亡后复活一次", "与幽灵相撞会合体"]},
    {"name": "幽灵", "enemy_type": 12, "desc": ["墓穴场景，穿墙漂浮", "与骷髅相撞会合体"]},
    {"name": "僵尸", "enemy_type": 18, "desc": [
        "移动极慢、血量厚，接触攻击伤害较低",
        "附近有非亡灵死亡时，会额外唤醒僵尸",
        "若附近有巨型僵尸，额外唤醒的也是巨型僵尸",
        "墓碑每 10 秒唤醒一只僵尸；僵尸死亡后产生幽魂",
    ]},
    {"name": "巨型僵尸", "enemy_type": 18, "giant": True, "desc": [
        "巨型僵尸属于精英，行动比普通僵尸更慢",
        "附近有非亡灵死亡时，会额外生成巨型僵尸",
        "死亡后同样会产生幽魂",
    ]},
    {"name": "巨型骷髅", "enemy_type": 11, "giant": True, "desc": [
        "巨型骷髅属于精英",
        "由死亡气息爆发产生",
        "不会与幽灵合体",
        "被载骨机吸收时视为 3 道幽火",
    ]},
    {"name": "魔魂亡骨", "enemy_type": 13, "fused": True, "desc": [
        "幽灵与骷髅相撞时合体而成",
        "继承两者的全部词缀",
        "普攻与技能伤害减半，炸弹与灼烧不受影响",
        "附近有亡灵倒下时回复生命",
        "巨型骷髅不会参与合体",
    ]},
    {"name": "风灵", "enemy_type": 14, "desc": [
        "暴雪山脉的飞行单位，不造成任何伤害",
        "只会按暴风雪的强度把玩家往外推",
        "风雪天里最容易被它吹下平台或吹进危险区",
    ]},
    {"name": "血仆", "enemy_type": 15, "desc": [
        "破败教堂的血族仆从，自带吸血词缀",
        "吸血鬼可以从它身上抽血回复自己",
        "属于亡灵，死亡后不会按墓穴规则生成骷髅",
    ]},
    {"name": "血蝙蝠", "enemy_type": 16, "desc": [
        "破败教堂的飞行血族，自带吸血词缀",
        "吸血鬼可以从它身上抽血回复自己",
        "属于亡灵，死亡后不会按墓穴规则生成骷髅",
    ]},
    {"name": "吸血鬼", "elite_kinds": ("vampire",), "place_key": "church",
     "place": "亡灵墓穴 · 破败教堂", "desc": [
        "自带吸血词缀的精英",
        "受伤时会抽取附近血仆与血蝠的生命",
        "被抽干的血族会转化为新的血仆",
        "每隔一段时间随机召唤血仆或血蝙蝠",
    ]},
    {"name": "石像鬼", "elite_kinds": ("gargoyle",), "place_key": "church",
     "place": "亡灵墓穴 · 破败教堂", "desc": [
        "教堂必定出现一只，初始为灰色石像",
        "第一阶段血条打空后转为青色，落地追击",
        "第二阶段血条打空后再次石化，从零开始回血",
        "回血期间可以彻底击杀，回满后进入飞行阶段",
    ]},
    {"name": "血腥十字架", "cross_kind": "blood", "place_key": "church",
     "place": "亡灵墓穴 · 破败教堂", "desc": [
        "调查前与普通石十字架没有区别",
        "苏醒后持续随机召唤亡灵",
        "强化半屏内所有敌人，离开范围后增幅消失",
        "本体不会直接攻击，但拥有精英级血量",
        "只能被玩家攻击，敌人无法伤害它",
    ]},
    {"name": "圣光十字架", "cross_kind": "holy", "place_key": "church",
     "place": "亡灵墓穴 · 破败教堂", "desc": [
        "调查前与普通石十字架没有区别",
        "缓慢恢复玩家生命",
        "持续灼烧范围内所有敌人",
        "只能被敌人攻击，玩家子弹与炸弹会直接穿过",
    ]},
    {"name": "载骨机", "elite_kinds": ("bone_carrier",), "place_key": "great_tomb",
     "desc": [
        "高壮骷髅精英，附近任何敌人死亡都会为其回血",
        "幽魂与普通骷髅碰到它会被吸收，各留下 1 道幽火",
        "巨型骷髅被吸收时留下 3 道幽火",
        "累计 5 道幽火后进化为炼魂魔骷，保留已有全部词缀",
    ]},
    {"name": "炼魂魔骷", "elite_kinds": ("soul_reaper",), "place_key": "great_tomb",
     "desc": [
        "载骨机累计吸收 5 道幽火后的进化形态",
        "获得专属词条「燃魂」；自身极慢扣血",
        "发射高速幽绿灵魂冲击，直接扣血并绕过护盾",
        "玩家触碰后会持续受到无视护盾的燃魂伤害",
    ]},
    {"name": CODEX_ELITE_NAME, "elite_kinds": ("hook_warden", "frost_claw"),
     "place_key": "universal",
     "desc": ["带词条与专属技能", "50%血量时进入狂暴，触发地面预警爆点"]},
    {"name": "堕落骑士·瓦尔德", "boss": BOSS_FALLEN_KNIGHT, "boss_scene": BIOME_NORMAL,
     "desc": ["普通地牢 Boss", "盾可击碎进入硬直", "撞墙/落地释放贴地横波，跳跃可躲"]},
    {"name": "冰泰坦·尤弥尔", "boss": BOSS_ICE_TITAN, "boss_scene": BIOME_ICE,
     "desc": ["冰晶洞穴 Boss", "核心暴露时受伤 +50%", "撞墙冲击改为贴地横波"]},
    {"name": "熔岩巨人·苏尔特", "boss": BOSS_MOLTEN_GIANT, "boss_scene": BIOME_LAVA,
     "desc": ["熔岩洞窟 Boss", "阶段三自爆时受伤翻倍", "自爆改为贴地横波，跳跃躲"]},
    {"name": "炼狱恶魔·巴洛斯", "boss": BOSS_INFERNAL_DEMON, "boss_scene": BIOME_LAVA,
     "desc": ["熔岩洞窟 Boss", "飞行，机动强", "落地/大招改为贴地横波或双层火环"]},
    {"name": "腐沼女王·莫尔加娜", "boss": BOSS_POISON_QUEEN, "boss_scene": BIOME_POISON,
     "desc": ["腐沼秘境 Boss", "毒圈扩散与召唤"]},
    {"name": "骷髅骨龙·纳克萨", "boss": BOSS_BONE_DRAGON, "boss_scene": BIOME_TOMB,
     "desc": ["亡灵墓穴 Boss", "召唤物死亡为其回血", "死亡龙息可被破防打断"]},
    {"name": "缝合怪·残躯", "boss": BOSS_STITCHED, "boss_scene": BIOME_NORMAL,
     "desc": ["普通地牢 Boss（深层轮换出现）", "血量随本局累计击杀数膨胀",
              "贴地横波、残骸飞弹、召唤残兵"]},
    {"name": "词缀颜色对照", "legend": True, "desc": [], "legend_items": [
        ("狂", "狂暴", (255, 90, 90)),
        ("盾", "护盾", (120, 200, 255)),
        ("裂", "分裂", (150, 255, 150)),
        ("召", "召唤", (200, 150, 255)),
        ("燃", "燃烧", (255, 120, 30)),
        ("冻", "冰冻", (180, 220, 255)),
        ("吸", "吸血", (220, 60, 90)),
        ("爆", "死亡爆炸", (255, 180, 60)),
        ("镜", "镜像", (200, 200, 220)),
        ("环", "首领光环", (255, 215, 80)),
        ("生", "再生", (100, 240, 140)),
        ("疾", "疾行", (110, 245, 210)),
        ("铁", "铁壁", (150, 165, 200)),
        ("魂", "燃魂", (104, 238, 142)),
    ]},
]


def entry_of(index):
    if 0 <= index < len(ENTRIES):
        return ENTRIES[index]
    return None


def biome_of(enemy_type):
    """这个敌人出没在哪个群系；查不到就按普通地牢算。"""
    if enemy_type == ENEMY_WRAITHBONE:
        return BIOME_TOMB
    for biome, pool in BIOME_ENEMY_POOL.items():
        if enemy_type in pool:
            return biome
    return BIOME_NORMAL


# ============================================================
# 形象预览
# ============================================================
_PREVIEWS = {}


def preview(index):
    """取一条图鉴条目的形象（已放大合成）；没有形象的条目返回 None。"""
    if index not in _PREVIEWS:
        _PREVIEWS[index] = _build_preview(entry_of(index))
    return _PREVIEWS[index]


def _build_preview(entry):
    if not entry:
        return None
    images = _entry_images(entry)
    if not images:
        return None
    return _compose([img for img in images if img is not None])


def _entry_images(entry):
    """按需生成样本精灵，顺手把随机数状态还原，避免影响对局里的随机。"""
    state = random.getstate()
    images = []
    try:
        if "enemy_type" in entry:
            image = Enemy(0, 0, SPRITE_DEPTH, entry["enemy_type"],
                          biome_of(entry["enemy_type"])).image
            if entry.get("giant"):
                image = pygame.transform.scale(
                    image, (int(image.get_width() * 2.2),
                            int(image.get_height() * 2.2)))
            images.append(image)
        elif "cross_kind" in entry:
            cls = BloodCross if entry["cross_kind"] == "blood" else HolyCross
            cross = cls(0, 70, SPRITE_DEPTH)
            cross.activate()
            images.append(cross.image)
        elif "elite_kinds" in entry:
            for kind in entry["elite_kinds"]:
                if kind in ELITE_STATS:
                    if kind == "bone_carrier":
                        images.append(BoneCarrierEnemy(
                            0, 80, SPRITE_DEPTH, "great_tomb").image)
                        continue
                    if kind == "soul_reaper":
                        carrier = BoneCarrierEnemy(
                            0, 100, SPRITE_DEPTH, "great_tomb")
                        carrier.evolved = True
                        carrier.absorbed_ghosts = 5
                        carrier.elite_name = "炼魂魔骷"
                        carrier._rebuild_image()
                        images.append(carrier.image)
                        continue
                    scene = ELITE_STATS[kind].get("scene", BIOME_NORMAL)
                    images.append(EliteEnemy(0, 0, SPRITE_DEPTH, scene, kind).image)
        elif "boss" in entry:
            scene = entry.get("boss_scene", BIOME_NORMAL)
            owner = create_boss(entry["boss"], 0, 0, 8, scene)
            images.append(owner.image)
    except Exception:
        images = [img for img in images if img is not None]
    finally:
        random.setstate(state)
    return images


def _compose(images):
    if not images:
        return None
    box = PREVIEW_BOX
    scaled = [_fit(img, box) for img in images]
    width = sum(s.get_width() for s in scaled) + PREVIEW_GAP * (len(scaled) - 1)
    height = max(s.get_height() for s in scaled)
    canvas = pygame.Surface((width, height), pygame.SRCALPHA)
    x = 0
    for s in scaled:
        canvas.blit(s, (x, (height - s.get_height()) // 2))
        x += s.get_width() + PREVIEW_GAP
    return canvas


def _fit(image, box):
    """整数倍放大，保持像素画的锐利。"""
    w, h = image.get_size()
    factor = max(1, min(box // max(1, w), box // max(1, h)))
    return pygame.transform.scale(image, (w * factor, h * factor))


# ============================================================
# 统计与整页绘制
# ============================================================
def record_text(index):
    """条目底部那行：出没地点与击杀记录。"""
    entry = entry_of(index)
    if not entry or entry.get("legend"):
        return ""
    parts = []
    place = _entry_place(entry)
    if place:
        parts.append(f"出没：{place}")
    book = profile()
    kills = book.codex_kills(entry["name"])
    deaths = book.codex_deaths(entry["name"])
    if kills or deaths:
        parts.append(f"击杀 {kills}")
        if deaths:
            parts.append(f"被它打死 {deaths} 次")
    else:
        parts.append("尚未遭遇")
    return "　·　".join(parts)


def _entry_place(entry):
    """条目显示用的出没地点。"""
    if entry.get("place"):
        return entry["place"]
    key = entry_place_key(entry)
    return PLACE_LABELS.get(key) or BIOME_NAMES.get(key, "地牢")


def entry_category(entry):
    if entry.get("legend"):
        return "other"
    if "boss" in entry:
        return "boss"
    if "elite_kinds" in entry or entry.get("giant"):
        return "elite"
    if entry.get("cross_kind") == "blood":
        return "elite"
    if "cross_kind" in entry:
        return "other"
    return "normal"


def entry_place_key(entry):
    explicit = entry.get("place_key")
    if explicit:
        return explicit
    if "enemy_type" in entry:
        mapping = {
            0: "universal", 1: "universal", 2: "universal", 3: "universal",
            4: "ice", 5: "ice", 6: "ice", 7: "lava", 8: "lava",
            9: "poison", 10: "poison", 11: "tomb", 12: "tomb", 13: "tomb",
            14: "snow", 15: "church", 16: "church", 18: "tomb",
        }
        return mapping.get(entry["enemy_type"], "all")
    if "boss" in entry:
        return entry.get("boss_scene", "normal")
    if "cross_kind" in entry:
        return "church"
    return "universal"


def filtered_indices(category="all", place="all"):
    result = []
    for i, entry in enumerate(ENTRIES):
        if category != "all" and entry_category(entry) != category:
            continue
        key = entry_place_key(entry)
        if place != "all":
            if place == "tomb" and key not in ("tomb", "church", "great_tomb"):
                continue
            if place == "snow" and key not in ("snow", "temple"):
                continue
            if place not in ("tomb", "snow") and key != place:
                continue
        result.append(i)
    return result


def filter_button_rect(kind, index):
    if kind == "category":
        width, gap, y = 86, 6, 58
        start = SCREEN_WIDTH // 2 - (len(CATEGORY_FILTERS) * width
                                     + (len(CATEGORY_FILTERS) - 1) * gap) // 2
        return pygame.Rect(start + index * (width + gap), y, width, 22)
    width, gap = 76, 5
    row, col = divmod(index, 6)
    per_row = 6 if row == 0 else len(PLACE_FILTERS) - 6
    start = SCREEN_WIDTH // 2 - (per_row * width + (per_row - 1) * gap) // 2
    return pygame.Rect(start + col * (width + gap), 86 + row * 24, width, 20)


def filter_hit(pos):
    if pos is None:
        return None
    for i, (key, _label) in enumerate(CATEGORY_FILTERS):
        if filter_button_rect("category", i).collidepoint(pos):
            return "category", key
    for i, (key, _label) in enumerate(PLACE_FILTERS):
        if filter_button_rect("place", i).collidepoint(pos):
            return "place", key
    return None


def list_layout(selected_index, indices=None):
    """列表的滚动窗口：(可见索引列表中的起始位置, 可见条数)。"""
    indices = list(indices if indices is not None else range(len(ENTRIES)))
    visible = max(1, (LIST_RECT[3] - 16) // ROW_H)
    if len(indices) <= visible:
        return 0, visible, indices
    try:
        selected_pos = indices.index(selected_index)
    except ValueError:
        selected_pos = 0
    first = max(0, min(selected_pos - visible // 2, len(indices) - visible))
    return first, visible, indices


def list_row_rect(row):
    return pygame.Rect(LIST_RECT[0] + 4, LIST_RECT[1] + 7 + row * ROW_H,
                       LIST_RECT[2] - 8, ROW_H)


def list_index_at(pos, selected_index, indices=None):
    if pos is None:
        return None
    first, visible, indices = list_layout(selected_index, indices)
    for row in range(visible):
        pos_in_list = first + row
        if pos_in_list >= len(indices):
            break
        if list_row_rect(row).collidepoint(pos):
            return indices[pos_in_list]
    return None


def scroll_selection(selected_index, indices, delta):
    if not indices:
        return selected_index
    try:
        pos = indices.index(selected_index)
    except ValueError:
        pos = 0
    pos = (pos + delta) % len(indices)
    return indices[pos]


def draw_panel(draw_text, selected_index, mouse=None, category="all", place="all"):
    """整页敌人图鉴：分类筛选、左侧列表、右侧形象与说明。"""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 8, 18, 235))
    screen.blit(overlay, (0, 0))
    draw_text("敌 人 图 鉴", 42, GOLD, SCREEN_WIDTH // 2, 32)

    hovered_filter = filter_hit(mouse)
    for i, (key, label) in enumerate(CATEGORY_FILTERS):
        rect = filter_button_rect("category", i)
        active = category == key
        hover = hovered_filter == ("category", key)
        fill = (58, 68, 100) if active else ((34, 40, 58) if hover else (20, 24, 36))
        pygame.draw.rect(screen, fill, rect, border_radius=5)
        pygame.draw.rect(screen, GOLD if active else (90, 96, 120), rect, 1,
                         border_radius=5)
        draw_text(label, 15, GOLD if active else (190, 194, 214),
                  rect.centerx, rect.centery)
    for i, (key, label) in enumerate(PLACE_FILTERS):
        rect = filter_button_rect("place", i)
        active = place == key
        hover = hovered_filter == ("place", key)
        fill = (50, 70, 58) if active else ((30, 40, 34) if hover else (18, 24, 22))
        pygame.draw.rect(screen, fill, rect, border_radius=5)
        pygame.draw.rect(screen, (144, 224, 164) if active else (80, 92, 86),
                         rect, 1, border_radius=5)
        draw_text(label, 13, (176, 244, 190) if active else (170, 178, 176),
                  rect.centerx, rect.centery)

    indices = filtered_indices(category, place)
    if not indices:
        indices = list(range(len(ENTRIES)))
    index = selected_index if selected_index in indices else indices[0]
    list_rect = LIST_RECT
    info_rect = (340, 146, SCREEN_WIDTH - 390, SCREEN_HEIGHT - 198)
    draw_box(screen, list_rect, (100, 100, 140), 200)
    draw_box(screen, info_rect, GOLD, 200)
    draw_text(f"筛选结果 {len(indices)}", 14, (150, 166, 154),
              list_rect[0] + 8, 136, center=False)
    _draw_entry(draw_text, info_rect, index)

    first, visible, indices = list_layout(index, indices)
    hovered = list_index_at(mouse, index, indices)
    for row in range(visible):
        pos_in_list = first + row
        if pos_in_list >= len(indices):
            break
        i = indices[pos_in_list]
        entry = ENTRIES[i]
        color = GOLD if i == index else (150, 150, 170)
        row_rect = list_row_rect(row)
        y_pos = list_rect[1] + 9 + row * ROW_H
        if i == hovered and i != index:
            pygame.draw.rect(screen, (30, 36, 52, 200), row_rect, border_radius=4)
        if i == index:
            pygame.draw.rect(screen, (40, 50, 80, 200), row_rect, border_radius=4)
        draw_text(entry["name"], 14, color, list_rect[0] + 15, y_pos, center=False)
    draw_text("点击分类筛选 / 滚轮或上下键翻阅 / ESC返回", 18,
              (150, 150, 170), SCREEN_WIDTH // 2, SCREEN_HEIGHT - 24)
    draw_back_button(mouse)


def _draw_entry(draw_text, info_rect, index):
    entry = entry_of(index)
    if not entry:
        return
    cx = info_rect[0] + info_rect[2] // 2
    draw_text(entry["name"], 32, GOLD, cx, info_rect[1] + 40)
    pygame.draw.line(screen, (100, 100, 140),
                     (info_rect[0] + 30, info_rect[1] + 70),
                     (info_rect[0] + info_rect[2] - 30, info_rect[1] + 70), 1)

    if entry.get("legend"):
        _draw_legend(draw_text, info_rect, entry.get("legend_items", []))
    else:
        shape = preview(index)
        top = info_rect[1] + 96
        if shape is not None:
            screen.blit(shape, (cx - shape.get_width() // 2, top))
            top += shape.get_height() + 20
        else:
            top += 60
        max_w = info_rect[2] - 58
        font = get_font(15)
        lines = []
        for raw in entry.get("desc", []):
            parts = _wrap_desc(raw, font, max_w)
            for j, part in enumerate(parts):
                lines.append((part, j > 0))
        for text, continuation in lines[:11]:
            prefix = "  " if continuation else "· "
            draw_text(prefix + text, 15, WHITE,
                      info_rect[0] + 25, top, center=False)
            top += 20
        record = record_text(index)
        if record:
            draw_text(record, 17, (150, 160, 185), cx,
                      info_rect[1] + info_rect[3] - 30)


def _wrap_desc(text, font, max_width):
    """中文说明按标点优先断行，续行不留单字孤行。"""
    punctuation = "，。；：！？、"
    lines = []
    current = ""
    for char in text:
        candidate = current + char
        if current and font.size(candidate)[0] > max_width:
            cut = max((current.rfind(p) for p in punctuation), default=-1)
            if cut >= max(1, len(current) // 2):
                lines.append(current[:cut + 1])
                current = current[cut + 1:] + char
            else:
                lines.append(current)
                current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    for i in range(1, len(lines)):
        if len(lines[i]) <= 2 and len(lines[i - 1]) > 2:
            lines[i] = lines[i - 1][-1] + lines[i]
            lines[i - 1] = lines[i - 1][:-1]
    return lines


def _draw_legend(draw_text, info_rect, items):
    """词缀对照表：两列排布，避免撑出面板。"""
    rows = (len(items) + 1) // 2
    for i, (icon, name, color) in enumerate(items):
        col, row = divmod(i, rows)
        x = info_rect[0] + 35 + col * (info_rect[2] // 2 - 10)
        y = info_rect[1] + 100 + row * 34
        circle = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(circle, (30, 30, 40, 220), (12, 12), 12)
        pygame.draw.circle(circle, color, (12, 12), 10)
        pygame.draw.circle(circle, OUTLINE, (12, 12), 10, 2)
        try:
            text = get_font(12).render(icon, True, OUTLINE)
            circle.blit(text, (12 - text.get_width() // 2, 12 - text.get_height() // 2))
        except Exception:
            pass
        screen.blit(circle, (x, y - 10))
        draw_text(name, 18, color, x + 36, y, center=False)
