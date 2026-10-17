"""场景背景。

每个生物群系预渲染一张静态底图并缓存，逐帧只补画会动的部分（火把跳动、岩浆火星、
沼泽气泡、飘雪、墓穴浮尘）。这样背景开销从每帧上千次绘制降到几十次，
同时每个群系有了自己的地貌：地牢石砖、冰晶洞穴、熔岩洞窟、腐沼、亡灵墓穴。
"""


# === IMPORTS ===
import math
import pygame
import random
from ..data.biomes import (BIOME_CHURCH, BIOME_GREAT_TOMB, BIOME_ICE,
                           BIOME_LAVA, BIOME_NORMAL, BIOME_POISON, BIOME_SNOW,
                           BIOME_TEMPLE, BIOME_TOMB)
from ..settings import BLIZZARD_VEIL_ALPHA
from ..settings import SCREEN_HEIGHT, SCREEN_WIDTH, screen
from ..utils import draw_glow, gradient_fill
# === /IMPORTS ===

FLOOR_Y = SCREEN_HEIGHT - 30      # 与地面平台顶面对齐
WATER_Y = 534                     # 沼泽水面 / 岩浆液面

_BACKDROP_CACHE = {}
_SPRITE_CACHE = {}
_TORCHES = {}                     # 群系 -> 火光坐标，供逐帧闪烁使用


# ============================================================
# 缓存与入口
# ============================================================
def draw_background(scene_type, is_boss, frame, weather=None):
    """画一帧背景：先贴缓存底图，再补动态元素；weather="blizzard" 时加飞雪遮挡。"""
    screen.blit(backdrop(scene_type, is_boss), (0, 0))
    _animate(scene_type, frame)
    if weather == "blizzard":
        _blizzard_veil(frame)


def backdrop(scene_type, is_boss):
    """取该群系的静态底图，没有就构建并缓存。"""
    key = (scene_type, bool(is_boss))
    surf = _BACKDROP_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        builder = _BUILDERS.get(scene_type, _build_dungeon)
        builder(surf)
        if is_boss:
            _boss_overlay(surf)
        _vignette(surf)
        _hud_wash(surf)
        _BACKDROP_CACHE[key] = surf
    return surf


def _sprite(key, size, painter):
    """取一张构建一次、之后反复复用的小贴图。"""
    surf = _SPRITE_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        painter(surf)
        _SPRITE_CACHE[key] = surf
    return surf


# ============================================================
# 通用工具
# ============================================================
def _gradient(surf, stops):
    """按颜色停靠点铺垂直渐变。"""
    n = len(stops) - 1
    band = SCREEN_HEIGHT // n
    for i in range(n):
        y0 = i * band
        h = SCREEN_HEIGHT - y0 if i == n - 1 else band
        gradient_fill(surf, (0, y0, SCREEN_WIDTH, h), stops[i], stops[i + 1])


def _shade(color, delta):
    return tuple(max(0, min(255, c + delta)) for c in color)


def _bricks(surf, rng, rect, base, mortar, bw=64, bh=30, spread=12, gap=2):
    """石砖墙：先铺灰浆色，再错缝砌砖，每块砖亮度略有差异。"""
    x0, y0, x1, y1 = rect
    pygame.draw.rect(surf, mortar, (x0, y0, x1 - x0, y1 - y0))
    row = 0
    for y in range(y0, y1, bh):
        offset = -(bw // 2) if row % 2 else 0
        for x in range(x0 + offset, x1, bw):
            bx0, bx1 = max(x0, x), min(x1, x + bw - gap)
            by0, by1 = max(y0, y), min(y1, y + bh - gap)
            if bx1 <= bx0 or by1 <= by0:
                continue
            pygame.draw.rect(surf, _shade(base, rng.randint(-spread, spread)),
                             (bx0, by0, bx1 - bx0, by1 - by0))
            pygame.draw.line(surf, _shade(base, spread + 8), (bx0, by0), (bx1 - 1, by0))
        row += 1


def _soft_band(surf, rect, color, top_alpha, bottom_alpha):
    """一条上下渐隐的柔光带，用来做雾气与辉光。"""
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return
    band = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(h):
        t = i / max(1, h - 1)
        alpha = int(top_alpha * (1 - t) + bottom_alpha * t)
        if alpha <= 0:
            continue
        pygame.draw.line(band, (*color, alpha), (0, i), (w - 1, i))
    surf.blit(band, (x, y))


def _mist_strip(width, height, color, peak_alpha):
    """中间最浓、上下都渐隐的雾带。"""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(height):
        alpha = int(peak_alpha * math.sin(math.pi * i / max(1, height - 1)))
        if alpha <= 0:
            continue
        pygame.draw.line(surf, (*color, alpha), (0, i), (width - 1, i))
    return surf


def _side_band(surf, rect, color, left_alpha, right_alpha):
    """一条左右渐隐的柔光带。"""
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return
    band = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(w):
        t = i / max(1, w - 1)
        alpha = int(left_alpha * (1 - t) + right_alpha * t)
        if alpha <= 0:
            continue
        pygame.draw.line(band, (*color, alpha), (i, 0), (i, h - 1))
    surf.blit(band, (x, y))


def _arch(surf, cx, base_y, width, height, stone, inner):
    """拱门：上半圆加下半矩形，内部填暗色。"""
    r = width // 2
    pygame.draw.rect(surf, stone, (cx - r - 7, base_y - height, width + 14, height + 8))
    pygame.draw.circle(surf, stone, (cx, base_y - height), r + 7)
    pygame.draw.rect(surf, inner, (cx - r, base_y - height, width, height))
    pygame.draw.circle(surf, inner, (cx, base_y - height), r)
    pygame.draw.circle(surf, _shade(stone, 34), (cx, base_y - height), r + 7, 3)


def _crack(surf, rng, x, y, length, color, steps=4):
    """一段锯齿裂纹。"""
    points = [(x, y)]
    for _ in range(steps):
        x += rng.randint(-12, 12)
        y += length // steps
        points.append((x, y))
    pygame.draw.lines(surf, color, False, points, 2)


def _vignette(surf):
    """上下压暗，让画面边缘沉下去。

    注意用 blit 而不是 draw：draw 会直接覆盖像素，把底下的地貌抹成纯黑。
    """
    top_h, bot_h = 120, 170
    _soft_band(surf, (0, 0, SCREEN_WIDTH, top_h), (0, 0, 0), 90, 0)
    _soft_band(surf, (0, SCREEN_HEIGHT - bot_h, SCREEN_WIDTH, bot_h),
               (0, 0, 0), 0, 135)


def _hud_wash(surf):
    """左上角压一层暗色，保证 HUD 文字压在场景上仍然清楚。"""
    _soft_band(surf, (0, 0, SCREEN_WIDTH, 200), (6, 8, 16), 100, 0)
    _side_band(surf, (0, 0, 300, SCREEN_HEIGHT), (6, 8, 16), 70, 0)


def _boss_overlay(surf):
    """领主房：整体再压暗一档，加两根立柱和地面刻线。"""
    dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    dark.fill((6, 4, 16, 96))
    surf.blit(dark, (0, 0))
    for x in (72, SCREEN_WIDTH - 72):
        pygame.draw.rect(surf, (26, 22, 38), (x - 26, 96, 52, FLOOR_Y - 96))
        pygame.draw.rect(surf, (58, 50, 78), (x - 26, 96, 52, FLOOR_Y - 96), 3)
        pygame.draw.rect(surf, (14, 12, 22), (x - 34, 78, 68, 20))
        pygame.draw.rect(surf, (70, 60, 92), (x - 34, 78, 68, 20), 2)
    pygame.draw.line(surf, (150, 130, 190, 90),
                     (150, FLOOR_Y - 3), (SCREEN_WIDTH - 150, FLOOR_Y - 3), 3)


# ============================================================
# 各群系底图
# ============================================================
def _build_dungeon(surf):
    """普通地牢：石砖墙、拱门、墙上火把、碎石地面。"""
    rng = random.Random(1001)
    _gradient(surf, ((16, 13, 22), (28, 22, 32), (20, 15, 24)))
    _bricks(surf, rng, (0, 40, SCREEN_WIDTH, FLOOR_Y - 40),
            base=(74, 62, 58), mortar=(38, 31, 30))

    _arch(surf, 170, FLOOR_Y - 6, 96, 150, (92, 78, 70), (32, 25, 32))
    _arch(surf, SCREEN_WIDTH - 170, FLOOR_Y - 6, 96, 150, (92, 78, 70), (32, 25, 32))
    _arch(surf, SCREEN_WIDTH // 2, FLOOR_Y - 6, 120, 190, (88, 74, 68), (24, 19, 26))

    torches = []
    for x in (70, 300, SCREEN_WIDTH - 300, SCREEN_WIDTH - 70):
        y = 168
        pygame.draw.rect(surf, (58, 44, 36), (x - 5, y, 10, 26))
        pygame.draw.rect(surf, (96, 82, 70), (x - 13, y - 10, 26, 12))
        pygame.draw.circle(surf, (120, 88, 60), (x, y - 13), 8)
        torches.append((x, y - 15))
    _TORCHES[BIOME_NORMAL] = torches

    pygame.draw.rect(surf, (46, 39, 40), (0, FLOOR_Y - 12, SCREEN_WIDTH, 12))
    for _ in range(26):
        x = rng.randint(0, SCREEN_WIDTH)
        pygame.draw.line(surf, (32, 27, 30), (x, FLOOR_Y - 12),
                         (x + rng.randint(-8, 8), FLOOR_Y), 2)
    for _ in range(18):
        x = rng.randint(10, SCREEN_WIDTH - 10)
        pygame.draw.circle(surf, _shade((70, 62, 58), rng.randint(-14, 14)),
                           (x, FLOOR_Y - 8), rng.randint(2, 4))


def _build_ice(surf):
    """冰晶洞穴：冰壁棱面、垂冰、地面冰晶簇。"""
    rng = random.Random(2002)
    _gradient(surf, ((10, 20, 40), (26, 46, 74), (14, 28, 50)))

    for _ in range(90):
        x0 = rng.randint(-60, SCREEN_WIDTH)
        y0 = rng.randint(30, FLOOR_Y)
        w = rng.randint(50, 130)
        h = rng.randint(40, 110)
        tone = rng.choice(((40, 74, 110), (52, 92, 132), (34, 62, 96), (62, 104, 142)))
        pygame.draw.polygon(surf, tone, [(x0, y0), (x0 + w, y0 + rng.randint(-14, 14)),
                                         (x0 + w // 2, y0 + h)])

    for _ in range(30):
        x = rng.randint(0, SCREEN_WIDTH)
        h = rng.randint(24, 70)
        pygame.draw.polygon(surf, (150, 205, 245), [(x - 6, 28), (x + 6, 28), (x, 28 + h)])
        pygame.draw.polygon(surf, (95, 150, 200), [(x - 6, 28), (x + 6, 28), (x, 28 + h)], 2)

    clusters = []
    for i in range(9):
        cx = 40 + i * 86 + rng.randint(-18, 18)
        cy = FLOOR_Y - 6
        for _ in range(rng.randint(3, 5)):
            w = rng.randint(10, 20)
            h = rng.randint(24, 58)
            ox = rng.randint(-22, 22)
            pygame.draw.polygon(surf, (176, 224, 255),
                                [(cx + ox - w, cy), (cx + ox + w, cy), (cx + ox, cy - h)])
            pygame.draw.polygon(surf, (110, 170, 220),
                                [(cx + ox - w, cy), (cx + ox + w, cy), (cx + ox, cy - h)], 2)
            clusters.append((cx + ox, cy - h // 2))
    _TORCHES[BIOME_ICE] = clusters[:14]

    pygame.draw.rect(surf, (108, 150, 190), (0, FLOOR_Y - 10, SCREEN_WIDTH, 10))
    _soft_band(surf, (0, FLOOR_Y - 60, SCREEN_WIDTH, 60), (200, 232, 255), 0, 70)


def _build_lava(surf):
    """熔岩洞窟：玄武岩柱、发光裂缝、底部岩浆。"""
    rng = random.Random(3003)
    _gradient(surf, ((20, 8, 8), (36, 14, 10), (18, 7, 8)))

    for _ in range(26):
        x = rng.randint(-20, SCREEN_WIDTH)
        w = rng.randint(28, 70)
        top = rng.randint(30, 150)
        pygame.draw.rect(surf, _shade((40, 30, 32), rng.randint(-8, 10)),
                         (x, top, w, FLOOR_Y - top))
        pygame.draw.line(surf, (22, 16, 18), (x, top), (x, FLOOR_Y), 2)
        pygame.draw.line(surf, (22, 16, 18), (x + w, top), (x + w, FLOOR_Y), 2)

    for _ in range(22):
        _crack(surf, rng, rng.randint(20, SCREEN_WIDTH - 20),
               rng.randint(120, FLOOR_Y - 60), rng.randint(40, 110), (214, 96, 32))
    for _ in range(9):
        _crack(surf, rng, rng.randint(20, SCREEN_WIDTH - 20),
               rng.randint(200, FLOOR_Y - 40), rng.randint(30, 80), (255, 170, 60))

    for _ in range(14):
        x = rng.randint(0, SCREEN_WIDTH)
        h = rng.randint(20, 56)
        pygame.draw.polygon(surf, (30, 20, 22), [(x - 9, 28), (x + 9, 28), (x, 28 + h)])
        pygame.draw.polygon(surf, (66, 38, 28), [(x - 9, 28), (x + 9, 28), (x, 28 + h)], 2)

    height = FLOOR_Y - WATER_Y
    pygame.draw.rect(surf, (208, 70, 20), (0, WATER_Y, SCREEN_WIDTH, height))
    pygame.draw.rect(surf, (255, 160, 60), (0, WATER_Y, SCREEN_WIDTH, 8))
    pygame.draw.rect(surf, (255, 226, 150), (0, WATER_Y, SCREEN_WIDTH, 3))
    _soft_band(surf, (0, WATER_Y - 70, SCREEN_WIDTH, 70), (255, 130, 50), 0, 90)
    for x in (120, 330, 610):
        draw_glow(surf, (255, 150, 60), (x, WATER_Y + 10), 22, 70)


def _swamp_tree(surf, rng, x, top, trunk_w):
    """一棵枯树：下粗上细的树干、斜出的枝干、顶端一丛枝叶。"""
    body = (16, 24, 16)
    pygame.draw.polygon(surf, body, [
        (x - trunk_w, FLOOR_Y), (x + trunk_w, FLOOR_Y),
        (x + trunk_w // 3, top + 12), (x - trunk_w // 3, top),
    ])
    pygame.draw.line(surf, (34, 46, 28), (x - trunk_w + 4, FLOOR_Y - 12),
                     (x - trunk_w // 3, top + 14), 2)
    for _ in range(rng.randint(3, 4)):
        by = rng.randint(top + 40, FLOOR_Y - 170)
        side = rng.choice((-1, 1))
        bx = x + side * rng.randint(40, 82)
        ty = by - rng.randint(26, 52)
        pygame.draw.line(surf, body, (x, by), (bx, ty), 5)
        pygame.draw.circle(surf, (14, 22, 14), (bx, ty), rng.randint(11, 16))
    for _ in range(3):
        cx = x + rng.randint(-26, 26)
        cy = top + rng.randint(-14, 14)
        pygame.draw.circle(surf, (14, 22, 14), (cx, cy), rng.randint(22, 30))


def _build_poison(surf):
    """腐沼秘境：枯树、垂藤、沼泽水面、芦苇与蘑菇。"""
    rng = random.Random(4004)
    _gradient(surf, ((32, 46, 36), (24, 38, 28), (16, 26, 20)))

    # 远景树影，用来拉开纵深
    for _ in range(16):
        x = rng.randint(-20, SCREEN_WIDTH + 20)
        w = rng.randint(6, 13)
        top = rng.randint(180, 270)
        pygame.draw.rect(surf, (22, 32, 22), (x, top, w, FLOOR_Y - top))

    # 近景枯树
    for i in range(5):
        x = 90 + i * 165 + rng.randint(-28, 28)
        _swamp_tree(surf, rng, x, rng.randint(190, 250), rng.randint(17, 25))

    # 从顶部垂下的藤蔓
    for _ in range(22):
        x = rng.randint(0, SCREEN_WIDTH)
        y = 0
        bottom = rng.randint(90, 210)
        points = [(x, 0)]
        while y < bottom:
            y += rng.randint(18, 32)
            x += rng.randint(-7, 7)
            points.append((x, y))
        pygame.draw.lines(surf, (40, 60, 34), False, points, 3)
        pygame.draw.circle(surf, (62, 94, 46), points[-1], 3)

    # 岸边的芦苇与蘑菇
    for _ in range(12):
        x = rng.randint(20, SCREEN_WIDTH - 20)
        y = FLOOR_Y - 8
        pygame.draw.line(surf, (52, 78, 42), (x, y), (x + rng.randint(-8, 8), y - rng.randint(26, 46)), 2)
    for _ in range(8):
        x = rng.randint(30, SCREEN_WIDTH - 30)
        y = FLOOR_Y - 8
        pygame.draw.rect(surf, (46, 70, 40), (x - 3, y - 34, 6, 34))
        r = rng.randint(5, 8)
        pygame.draw.circle(surf, (120, 190, 90), (x, y - 36), r)
        pygame.draw.circle(surf, (72, 130, 60), (x, y - 36), r, 2)

    # 沼泽水面
    water = pygame.Surface((SCREEN_WIDTH, FLOOR_Y - WATER_Y), pygame.SRCALPHA)
    water.fill((60, 94, 62, 240))
    for x in range(SCREEN_WIDTH):
        w = int(math.sin(x * 0.05) * 3 + math.sin(x * 0.013) * 4)
        pygame.draw.line(water, (92, 130, 84, 210), (x, w), (x, w + 3))
    surf.blit(water, (0, WATER_Y))
    for x in range(0, SCREEN_WIDTH, 6):
        h = 2 + int(2 * abs(math.sin(x * 0.07)))
        pygame.draw.line(surf, (124, 164, 106), (x, WATER_Y + 9), (x + 4, WATER_Y + 9 + h), 1)
    for _ in range(6):
        x = rng.randint(30, SCREEN_WIDTH - 30)
        y = WATER_Y + rng.randint(10, 28)
        r = rng.randint(16, 26)
        pygame.draw.ellipse(surf, (92, 138, 74), (x - r, y - 5, r * 2, 10))
        pygame.draw.ellipse(surf, (52, 92, 52), (x - r, y - 5, r * 2, 10), 2)
        pygame.draw.circle(surf, (168, 222, 130), (x + r // 2, y - 6), 3)
    _soft_band(surf, (0, WATER_Y - 130, SCREEN_WIDTH, 130), (150, 195, 140), 0, 62)


def _build_tomb(surf):
    """亡灵墓穴：石砌墙、壁龛、蛛网、骸骨与石棺。"""
    rng = random.Random(5005)
    _gradient(surf, ((14, 14, 22), (30, 30, 44), (18, 18, 28)))
    _bricks(surf, rng, (0, 40, SCREEN_WIDTH, FLOOR_Y - 40),
            base=(60, 60, 76), mortar=(26, 26, 36), bw=76, bh=34, spread=10)

    for cx in (140, SCREEN_WIDTH // 2, SCREEN_WIDTH - 140):
        y0 = 150
        pygame.draw.rect(surf, (20, 20, 30), (cx - 38, y0, 76, 110))
        pygame.draw.circle(surf, (20, 20, 30), (cx, y0), 38)
        pygame.draw.rect(surf, (84, 84, 104), (cx - 38, y0, 76, 110), 3)
        pygame.draw.circle(surf, (84, 84, 104), (cx, y0), 38, 3)
        pygame.draw.circle(surf, (196, 192, 172), (cx, y0 + 42), 13)
        pygame.draw.circle(surf, (28, 28, 40), (cx - 5, y0 + 40), 3)
        pygame.draw.circle(surf, (28, 28, 40), (cx + 5, y0 + 40), 3)
        for i in range(4):
            pygame.draw.rect(surf, (180, 176, 158), (cx - 9 + i * 5, y0 + 52, 3, 14))

    for sx, direction in ((0, 1), (SCREEN_WIDTH - 1, -1)):
        for i in range(5):
            pygame.draw.line(surf, (150, 150, 170), (sx, 40),
                             (sx + direction * 90, 100 + i * 14), 1)

    for _ in range(9):
        x = rng.randint(20, SCREEN_WIDTH - 20)
        y = FLOOR_Y - 6
        pygame.draw.rect(surf, (210, 206, 186), (x - 2, y - 30, 5, 30), border_radius=2)
        pygame.draw.circle(surf, (210, 206, 186), (x, y - 32), 6)
        if rng.random() < 0.5:
            pygame.draw.line(surf, (210, 206, 186), (x - 12, y - 12), (x + 12, y - 12), 3)

    for i in range(3):
        x = 90 + i * 300 + rng.randint(-20, 20)
        points = [(x - 46, FLOOR_Y - 4), (x + 46, FLOOR_Y - 4),
                  (x + 40, FLOOR_Y - 24), (x - 40, FLOOR_Y - 24)]
        pygame.draw.polygon(surf, (46, 46, 60), points)
        pygame.draw.polygon(surf, (96, 96, 118), points, 2)

    _soft_band(surf, (0, FLOOR_Y - 150, SCREEN_WIDTH, 150), (120, 160, 150), 0, 40)


def _build_snow(surf):
    """暴雪山脉：层层雪山剪影，山顶积雪，山脚下是松林与雪地。"""
    rng = random.Random(7007)
    _gradient(surf, ((38, 52, 76), (66, 84, 112), (96, 114, 142)))

    # 远中近三层山脊，越远越淡
    layers = (
        (0, (126, 146, 176), 120, 210),
        (1, (92, 112, 144), 170, 150),
        (2, (58, 74, 102), 230, 110),
    )
    near_peaks = []
    for idx, (_, color, base, spread) in enumerate(layers):
        points = [(-20, base + rng.randint(-20, 20))]
        x = -20
        while x < SCREEN_WIDTH + 40:
            x += rng.randint(70, 140)
            peak = base - rng.randint(20, spread)
            points.append((x, peak))
            if idx == 2:
                near_peaks.append((x, peak))
            x += rng.randint(20, 50)
            points.append((x, peak + rng.randint(10, 40)))
        points.append((SCREEN_WIDTH + 20, base + 40))
        points.append((SCREEN_WIDTH + 20, FLOOR_Y))
        points.append((-20, FLOOR_Y))
        pygame.draw.polygon(surf, color, points)

    # 山顶积雪：贴着近层山脊的峰顶画帽檐，不悬在半空
    for x, peak in near_peaks:
        w = rng.randint(16, 26)
        pygame.draw.polygon(surf, (232, 242, 252, 220),
                            [(x - w, peak + w), (x + w, peak + w),
                             (x, peak - 2), (x - w // 3, peak + w // 2)])

    # 山脚的松林
    for i in range(14):
        x = 30 + i * 56 + rng.randint(-12, 12)
        h = rng.randint(56, 98)
        base = FLOOR_Y - 10
        pygame.draw.polygon(surf, (28, 44, 46),
                            [(x - 18, base), (x + 18, base), (x, base - h)])
        pygame.draw.polygon(surf, (226, 238, 250),
                            [(x - 11, base - int(h * 0.42)), (x + 11, base - int(h * 0.42)),
                             (x, base - h)])

    # 雪地
    pygame.draw.rect(surf, (222, 234, 246), (0, FLOOR_Y - 14, SCREEN_WIDTH, 14))
    pygame.draw.rect(surf, (196, 214, 232), (0, FLOOR_Y - 14, SCREEN_WIDTH, 3))
    for i in range(40):
        x = rng.randint(0, SCREEN_WIDTH)
        pygame.draw.circle(surf, (238, 246, 255), (x, FLOOR_Y - rng.randint(2, 12)),
                           rng.randint(1, 3))
    _soft_band(surf, (0, FLOOR_Y - 190, SCREEN_WIDTH, 190), (206, 224, 244), 0, 60)


def _build_temple(surf):
    """暴云寺庙：宏伟的静态殿宇，金饰云纹与成排立柱。"""
    rng = random.Random(8008)
    _gradient(surf, ((26, 18, 16), (44, 28, 22), (30, 20, 18)))

    # 后墙板与云纹浮雕
    pygame.draw.rect(surf, (56, 34, 26), (60, 60, SCREEN_WIDTH - 120, FLOOR_Y - 90))
    pygame.draw.rect(surf, (96, 66, 44), (60, 60, SCREEN_WIDTH - 120, FLOOR_Y - 90), 3)
    cx, cy = SCREEN_WIDTH // 2, 200
    for i, r in enumerate((96, 74, 52)):
        pygame.draw.circle(surf, (132, 96, 52), (cx, cy), r, 3)
        pygame.draw.arc(surf, (196, 156, 82), (cx - r, cy - r, r * 2, r * 2),
                        math.pi * 0.15, math.pi * 0.85, 3)
    draw_glow(surf, (255, 206, 120), (cx, cy), 60, 40)

    # 两侧立柱：柱身、柱头、柱基
    for x in (110, 210, SCREEN_WIDTH - 210, SCREEN_WIDTH - 110):
        pygame.draw.rect(surf, (72, 48, 36), (x - 22, 96, 44, FLOOR_Y - 116))
        pygame.draw.rect(surf, (108, 74, 48), (x - 22, 96, 12, FLOOR_Y - 116))
        pygame.draw.rect(surf, (150, 110, 58), (x - 30, 82, 60, 20))
        pygame.draw.rect(surf, (150, 110, 58), (x - 30, FLOOR_Y - 26, 60, 18))
        pygame.draw.rect(surf, (40, 26, 20), (x - 22, 96, 44, FLOOR_Y - 116), 2)

    # 檐下的云纹横梁
    pygame.draw.rect(surf, (86, 56, 38), (30, 50, SCREEN_WIDTH - 60, 30))
    pygame.draw.rect(surf, (164, 122, 62), (30, 50, SCREEN_WIDTH - 60, 30), 2)
    for i in range(9):
        x = 60 + i * 86
        pygame.draw.arc(surf, (206, 164, 86), (x, 54, 46, 22), math.pi, math.pi * 2, 3)
        pygame.draw.circle(surf, (236, 200, 120), (x + 23, 72), 3)

    # 悬着的灯笼与暖光
    for x in (170, SCREEN_WIDTH - 170):
        pygame.draw.line(surf, (60, 44, 32), (x, 80), (x, 118), 2)
        pygame.draw.ellipse(surf, (196, 92, 62), (x - 13, 118, 26, 32))
        pygame.draw.ellipse(surf, (236, 176, 92), (x - 13, 118, 26, 32), 2)
        draw_glow(surf, (255, 178, 96), (x, 136), 28, 70)

    # 红幡
    for x in (255, SCREEN_WIDTH - 255):
        pygame.draw.polygon(surf, (136, 40, 40), [(x - 16, 80), (x + 16, 80),
                                                  (x + 16, 220), (x, 200), (x - 16, 220)])
        pygame.draw.polygon(surf, (196, 78, 66), [(x - 16, 80), (x + 16, 80),
                                                 (x + 16, 220), (x, 200), (x - 16, 220)], 2)

    # 地砖与金线
    pygame.draw.rect(surf, (44, 30, 24), (0, FLOOR_Y - 16, SCREEN_WIDTH, 16))
    pygame.draw.rect(surf, (168, 126, 64), (0, FLOOR_Y - 16, SCREEN_WIDTH, 3))
    for i in range(0, SCREEN_WIDTH, 80):
        pygame.draw.line(surf, (72, 50, 38), (i, FLOOR_Y - 16), (i, FLOOR_Y), 2)
    _soft_band(surf, (0, FLOOR_Y - 210, SCREEN_WIDTH, 210), (255, 196, 120), 0, 46)


def _build_church(surf):
    """破败教堂：塌落的穹顶、残彩窗、长椅与碎石。"""
    rng = random.Random(9009)
    _gradient(surf, ((15, 12, 20), (34, 22, 32), (20, 16, 24)))
    _bricks(surf, rng, (0, 52, SCREEN_WIDTH, FLOOR_Y - 52),
            base=(76, 66, 76), mortar=(28, 22, 30), bw=86, bh=38, spread=12)

    # 中央残破穹顶与裂开的彩窗
    cx = SCREEN_WIDTH // 2
    pygame.draw.arc(surf, (112, 92, 106), (cx - 180, 42, 360, 260),
                    math.pi, math.pi * 2, 7)
    for x in (cx - 106, cx + 106):
        pygame.draw.rect(surf, (36, 24, 36), (x - 34, 118, 68, 142))
        pygame.draw.circle(surf, (36, 24, 36), (x, 118), 34)
        pygame.draw.rect(surf, (118, 90, 104), (x - 34, 118, 68, 142), 3)
        pygame.draw.circle(surf, (118, 90, 104), (x, 118), 34, 3)
        pygame.draw.polygon(surf, (142, 54, 72, 120),
                            [(x - 24, 112), (x - 8, 84), (x + 2, 130),
                             (x + 22, 96), (x + 27, 160), (x - 25, 160)])
        pygame.draw.line(surf, (42, 32, 46), (x, 90), (x, 255), 2)
        pygame.draw.line(surf, (42, 32, 46), (x - 30, 146), (x + 30, 166), 2)

    # 倒塌的立柱
    for x, top in ((92, 84), (SCREEN_WIDTH - 92, 112)):
        pygame.draw.rect(surf, (58, 48, 58), (x - 25, top, 50, FLOOR_Y - top - 12))
        pygame.draw.rect(surf, (102, 84, 96), (x - 25, top, 15, FLOOR_Y - top - 12))
        pygame.draw.rect(surf, (124, 104, 112), (x - 32, top - 16, 64, 18))
        for i in range(3):
            y = top + 30 + i * 52
            pygame.draw.line(surf, (40, 32, 42), (x - 18, y), (x + 19, y + 12), 2)

    # 散落的长椅
    for i in range(5):
        x = 170 + i * 118 + rng.randint(-10, 10)
        y = FLOOR_Y - 38 - rng.randint(0, 26)
        pygame.draw.polygon(surf, (76, 48, 48), [
            (x - 38, y), (x + 34, y - 5), (x + 38, y + 9), (x - 34, y + 14)
        ])
        pygame.draw.line(surf, (42, 28, 34), (x - 28, y + 12), (x - 35, y + 28), 4)
        pygame.draw.line(surf, (42, 28, 34), (x + 26, y + 8), (x + 33, y + 24), 4)

    # 十字架剪影和碎石
    for x, y in ((215, 206), (SCREEN_WIDTH - 224, 188)):
        pygame.draw.rect(surf, (52, 40, 48), (x - 5, y, 10, 92))
        pygame.draw.rect(surf, (52, 40, 48), (x - 30, y + 18, 60, 10))
    for _ in range(24):
        x = rng.randint(20, SCREEN_WIDTH - 20)
        y = FLOOR_Y - rng.randint(2, 18)
        pygame.draw.polygon(surf, (80, 68, 80),
                            [(x, y - 8), (x + 7, y - 2), (x + 2, y + 4), (x - 6, y + 1)])
    _soft_band(surf, (0, FLOOR_Y - 180, SCREEN_WIDTH, 180), (166, 76, 96), 0, 46)


def _build_great_tomb(surf):
    """古代大墓地：宏大的地下墓室、巨柱、石棺与幽绿魂火。"""
    rng = random.Random(11111)
    _gradient(surf, ((12, 22, 18), (28, 44, 34), (15, 26, 21)))
    _bricks(surf, rng, (0, 48, SCREEN_WIDTH, FLOOR_Y - 48),
            base=(66, 84, 70), mortar=(24, 34, 28), bw=92, bh=42, spread=12)

    # 巨大的层叠拱门
    cx = SCREEN_WIDTH // 2
    for half, color in ((250, (42, 58, 48)), (205, (54, 72, 58)),
                        (160, (68, 88, 70))):
        pygame.draw.arc(surf, color,
                        (cx - half, 34, half * 2, 310),
                        math.pi, math.pi * 2, 10)
    for x in (110, SCREEN_WIDTH - 110):
        pygame.draw.rect(surf, (48, 62, 50), (x - 30, 80, 60, FLOOR_Y - 98))
        pygame.draw.rect(surf, (86, 106, 86), (x - 30, 80, 16, FLOOR_Y - 98))
        pygame.draw.rect(surf, (126, 146, 112), (x - 39, 62, 78, 22))
        pygame.draw.rect(surf, (126, 146, 112), (x - 42, FLOOR_Y - 28, 84, 20))
        for y in (126, 214, 302, 390):
            pygame.draw.line(surf, (32, 44, 34), (x - 24, y), (x + 24, y + 8), 2)

    # 后墙壁龛中的石棺
    for i in range(5):
        x = 165 + i * 118
        pygame.draw.rect(surf, (28, 38, 30), (x - 40, 204, 80, 138))
        pygame.draw.circle(surf, (28, 38, 30), (x, 204), 40)
        pygame.draw.rect(surf, (76, 94, 76), (x - 40, 204, 80, 138), 3)
        pygame.draw.circle(surf, (76, 94, 76), (x, 204), 40, 3)
        pygame.draw.rect(surf, (104, 116, 94), (x - 26, 232, 52, 86), border_radius=8)
        pygame.draw.line(surf, (50, 62, 50), (x, 240), (x, 308), 2)

    # 两侧石棺与陪葬石碑
    for x in (210, SCREEN_WIDTH - 210):
        pygame.draw.polygon(surf, (62, 74, 60), [
            (x - 58, FLOOR_Y - 4), (x + 58, FLOOR_Y - 4),
            (x + 48, FLOOR_Y - 34), (x - 48, FLOOR_Y - 34)
        ])
        pygame.draw.polygon(surf, (102, 118, 96), [
            (x - 58, FLOOR_Y - 4), (x + 58, FLOOR_Y - 4),
            (x + 48, FLOOR_Y - 34), (x - 48, FLOOR_Y - 34)
        ], 2)
    for _ in range(12):
        x = rng.randint(30, SCREEN_WIDTH - 30)
        y = FLOOR_Y - rng.randint(4, 26)
        h = rng.randint(18, 38)
        pygame.draw.rect(surf, (74, 88, 72), (x - 7, y - h, 14, h), border_radius=3)
        pygame.draw.line(surf, (42, 56, 44), (x, y - h + 4), (x, y - 3), 1)

    # 绿色魂火灯
    for x in (250, SCREEN_WIDTH - 250):
        pygame.draw.line(surf, (54, 46, 32), (x, 92), (x, 142), 2)
        pygame.draw.ellipse(surf, (34, 54, 40), (x - 14, 142, 28, 34))
        draw_glow(surf, (96, 238, 138), (x, 158), 34, 95)
        pygame.draw.circle(surf, (176, 255, 194), (x, 158), 5)

    _soft_band(surf, (0, FLOOR_Y - 190, SCREEN_WIDTH, 190),
               (86, 184, 112), 0, 42)


_BUILDERS = {
    BIOME_NORMAL: _build_dungeon,
    BIOME_ICE: _build_ice,
    BIOME_LAVA: _build_lava,
    BIOME_POISON: _build_poison,
    BIOME_TOMB: _build_tomb,
    BIOME_SNOW: _build_snow,
    BIOME_TEMPLE: _build_temple,
    BIOME_CHURCH: _build_church,
    BIOME_GREAT_TOMB: _build_great_tomb,
}


# ============================================================
# 逐帧动态部分
# ============================================================
def _animate(scene_type, frame):
    if scene_type == BIOME_ICE:
        _snow(frame)
        _glints(frame, BIOME_ICE)
    elif scene_type == BIOME_SNOW:
        _snowfall(frame)
    elif scene_type == BIOME_TEMPLE:
        _temple_motes(frame)
    elif scene_type == BIOME_CHURCH:
        _motes(frame, (196, 148, 162))
        _wisps(frame)
    elif scene_type == BIOME_GREAT_TOMB:
        _motes(frame, (134, 190, 146))
        _wisps(frame)
    elif scene_type == BIOME_LAVA:
        _embers(frame)
        _lava_surface(frame)
    elif scene_type == BIOME_POISON:
        _bubbles(frame)
        _fog(frame)
        _fireflies(frame)
    elif scene_type == BIOME_TOMB:
        _motes(frame, (176, 176, 206))
        _wisps(frame)
    else:
        _torch_light(frame)
        _motes(frame, (210, 180, 130))


def _torch_light(frame):
    """地牢火把：火苗随帧轻微跳动。"""
    for i, (x, y) in enumerate(_TORCHES.get(BIOME_NORMAL, ())):
        flick = math.sin((frame + i * 11) * 0.3) * 2.5
        pygame.draw.circle(screen, (255, 190, 90), (x, int(y - flick * 0.5)), int(7 + flick))
        pygame.draw.circle(screen, (255, 242, 180), (x, int(y - 3 - flick * 0.4)), 3)
        draw_glow(screen, (255, 150, 60), (x, y), 34, 28)


def _glints(frame, scene_type):
    """冰晶反光。"""
    for i, (x, y) in enumerate(_TORCHES.get(scene_type, ())):
        pulse = 0.5 + 0.5 * math.sin((frame + i * 9) * 0.18)
        if pulse < 0.55:
            continue
        draw_glow(screen, (190, 230, 255), (x, y), int(10 + pulse * 6), 34)


def _snow(frame):
    """冰原飘雪。"""
    for i in range(46):
        x = (i * 131 + (i * i * 7) % 97) % SCREEN_WIDTH
        y = (i * 53 + frame * (1 + (i % 3))) % SCREEN_HEIGHT
        drift = int(math.sin((frame + i * 23) * 0.05) * 6)
        pygame.draw.circle(screen, (226, 242, 255), ((x + drift) % SCREEN_WIDTH, y), 1 + (i % 2))


def _snowfall(frame):
    """雪山常驻的落雪：比冰原更密一些。"""
    for i in range(64):
        x = (i * 149 + (i * i * 11) % 137) % SCREEN_WIDTH
        y = (i * 47 + frame * (1 + (i % 2))) % SCREEN_HEIGHT
        drift = int(math.sin((frame + i * 29) * 0.04) * 9)
        pygame.draw.circle(screen, (236, 246, 255), ((x + drift) % SCREEN_WIDTH, y),
                           1 + (i % 3 == 0))


def _blizzard_veil(frame):
    """暴风雪：一层白雾加上横扫的雪线，把视野压下去。"""
    veil = _sprite("blizzard_veil", (SCREEN_WIDTH, SCREEN_HEIGHT),
                   lambda s: s.fill((238, 246, 255, BLIZZARD_VEIL_ALPHA)))
    screen.blit(veil, (0, 0))
    for i in range(90):
        x = (i * 197 + frame * (9 + (i % 5))) % (SCREEN_WIDTH + 120) - 60
        y = (i * 71 + frame * 2) % SCREEN_HEIGHT
        length = 12 + (i % 4) * 6
        pygame.draw.line(screen, (250, 253, 255), (x, y), (x + length, y + 3), 2)
    for i in range(40):
        x = (i * 233 + frame * 5) % SCREEN_WIDTH
        y = (i * 61 + frame * 3) % SCREEN_HEIGHT
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 2)


def _temple_motes(frame):
    """寺庙里缓缓上升的金色浮尘。"""
    for i in range(26):
        x = (i * 181 + (i * i * 7) % 97) % SCREEN_WIDTH
        y = SCREEN_HEIGHT - (i * 53 + int(frame * 0.6)) % SCREEN_HEIGHT
        sway = int(math.sin((frame + i * 21) * 0.05) * 10)
        pulse = 0.5 + 0.5 * math.sin((frame + i * 13) * 0.06)
        pygame.draw.circle(screen, (255, 226, 150), ((x + sway) % SCREEN_WIDTH, y),
                           int(1 + pulse * 2))


def _embers(frame):
    """熔岩火星上浮。"""
    for i in range(34):
        x = (i * 173 + (i * i * 11) % 151) % SCREEN_WIDTH
        y = SCREEN_HEIGHT - (i * 37 + frame * (2 + (i % 3))) % SCREEN_HEIGHT
        sway = int(math.sin((frame + i * 17) * 0.08) * 10)
        color = (255, 200, 90) if i % 3 else (255, 130, 50)
        pygame.draw.circle(screen, color, ((x + sway) % SCREEN_WIDTH, y), 1 + (i % 2))


def _lava_surface(frame):
    """岩浆液面的呼吸感。"""
    band = _sprite("lava_glow", (SCREEN_WIDTH, 40),
                   lambda s: _soft_band(s, (0, 0, SCREEN_WIDTH, 40), (255, 170, 80), 70, 0))
    screen.blit(band, (0, WATER_Y - 30 + int(4 * math.sin(frame * 0.06))))
    for i in range(6):
        x = (i * 149 + frame * 2) % SCREEN_WIDTH
        pygame.draw.circle(screen, (255, 224, 150), (x, WATER_Y + 4 + (i % 2)), 2)


def _bubbles(frame):
    """沼泽水面冒泡。"""
    span = FLOOR_Y - WATER_Y + 24
    for i in range(26):
        x = (i * 97 + (i * i * 13) % 83) % SCREEN_WIDTH
        y = WATER_Y + span - (i * 11 + frame * (1 + (i % 2))) % span
        r = 1 + (i % 3)
        pygame.draw.circle(screen, (150, 200, 130), (x, y), r)
        pygame.draw.circle(screen, (200, 240, 170), (x - r // 2, y - r // 2), 1)


def _fog(frame):
    """沼泽雾带横向漂移。"""
    strip = _SPRITE_CACHE.get("swamp_fog")
    if strip is None:
        strip = _mist_strip(SCREEN_WIDTH + 240, 110, (152, 196, 148), 20)
        _SPRITE_CACHE["swamp_fog"] = strip
    for i in range(2):
        offset = int((frame * (0.3 + i * 0.16) + i * 320) % (SCREEN_WIDTH + 240)) - 240
        screen.blit(strip, (offset, 330 + i * 96))


def _fireflies(frame):
    """沼泽萤火。"""
    for i in range(16):
        x = (i * 211 + (i * i * 5) % 173) % SCREEN_WIDTH
        y = 150 + (i * 67) % 380
        blink = 0.5 + 0.5 * math.sin((frame + i * 31) * 0.07)
        if blink < 0.45:
            continue
        wobble = int(math.sin((frame + i * 13) * 0.03) * 12)
        draw_glow(screen, (190, 250, 140), ((x + wobble) % SCREEN_WIDTH, y),
                  int(4 + blink * 4), 60)


def _motes(frame, color):
    """空气中缓慢下沉的浮尘。"""
    for i in range(40):
        x = (i * 149 + (i * i * 3) % 71) % SCREEN_WIDTH
        y = (i * 91 + int(frame * 0.4)) % SCREEN_HEIGHT
        drift = int(math.sin((frame + i * 19) * 0.04) * 8)
        pygame.draw.circle(screen, color, ((x + drift) % SCREEN_WIDTH, y), 1)


def _wisps(frame):
    """墓穴里的幽绿鬼火。"""
    for i in range(4):
        phase = (frame * (0.004 + i * 0.001) + i * 0.3) % 1.0
        x = int(120 + i * 180 + math.sin((frame + i * 40) * 0.02) * 40)
        y = int(470 - phase * 320)
        alpha = int(28 + 22 * math.sin(frame * 0.05 + i))
        draw_glow(screen, (140, 220, 180), (x, y), 18, max(14, alpha))
