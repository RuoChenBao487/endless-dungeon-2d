"""无状态绘图与几何小工具。"""


# === IMPORTS ===
import math
import pygame
from .settings import (GOLD, OUTLINE, SCREEN_HEIGHT, WHITE, WINDOW_HEIGHT, WINDOW_SCALE,
                       WINDOW_WIDTH, _scaled_buffer, get_font, screen, window)
# === /IMPORTS ===

def present():
    pygame.transform.smoothscale(screen, (WINDOW_WIDTH, WINDOW_HEIGHT), _scaled_buffer)
    window.blit(_scaled_buffer, (0, 0))
    pygame.display.flip()


def window_to_screen(pos):
    return (int(pos[0] / WINDOW_SCALE), int(pos[1] / WINDOW_SCALE))


# 子界面左上角的返回按钮：绘制与点击判定共用这个矩形
BACK_RECT = pygame.Rect(18, 16, 104, 36)


def back_hit(pos):
    return pos is not None and BACK_RECT.collidepoint(pos)


def draw_back_button(mouse=None):
    """画左上角的返回按钮，悬停时高亮；返回它的矩形。"""
    hover = back_hit(mouse)
    fill = (52, 42, 30) if hover else (22, 24, 34)
    border = GOLD if hover else (120, 120, 145)
    pygame.draw.rect(screen, fill, BACK_RECT, border_radius=6)
    pygame.draw.rect(screen, border, BACK_RECT, 2, border_radius=6)
    # 左向箭头
    cx, cy = BACK_RECT.x + 22, BACK_RECT.centery
    pygame.draw.polygon(screen, border, [(cx + 5, cy - 7), (cx + 5, cy + 7), (cx - 5, cy)])
    pygame.draw.rect(screen, border, (cx - 1, cy - 2, 12, 4))
    font = get_font(20)
    text = font.render("返回", True, WHITE if not hover else GOLD)
    screen.blit(text, (BACK_RECT.x + 44, BACK_RECT.centery - text.get_height() // 2))
    return BACK_RECT


# 「奖励说明」页左边的分类列表：菜单与暂停界面共用这一套坐标
REWARD_CAT_RECT = (50, 110, 200, SCREEN_HEIGHT - 180)


def reward_cat_rect(i):
    x, y, w, _h = REWARD_CAT_RECT
    row_y = y + 40 + i * 55
    return pygame.Rect(x + 4, row_y - 22, w - 8, 48)


def reward_cat_at(pos, count):
    if pos is None:
        return None
    for i in range(count):
        if reward_cat_rect(i).collidepoint(pos):
            return i
    return None


def try_step_up(sprite, platform, max_step=8):
    """上坡辅助：平台顶面只比脚下高一点点时，把人抬上去而不是挡住。

    雪山的缓坡是由很细的碰撞段拼的，没有这一步，横向撞到下一段就会被当墙挡住。
    返回 True 表示已经抬上去了，调用方应当保留这次横向移动。
    """
    if not getattr(sprite, "on_ground", False):
        return False
    rise = sprite.rect.bottom - platform.rect.top
    if rise <= 0 or rise > max_step:
        return False
    sprite.rect.bottom = platform.rect.top
    sprite.velocity_y = 0
    sprite.on_ground = True
    return True


def draw_glow(surface, color, center, radius, max_alpha=110):
    if radius <= 0:
        return
    tmp = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(radius, 0, -1):
        a = int(max_alpha * (1 - i / radius))
        if a <= 0:
            continue
        pygame.draw.circle(tmp, (color[0], color[1], color[2], a), (radius, radius), i)
    surface.blit(tmp, (center[0] - radius, center[1] - radius), special_flags=pygame.BLEND_ADD)


def gradient_fill(surface, rect, top_color, bottom_color):
    x, y, w, h = rect
    if h <= 0 or w <= 0:
        return
    for i in range(h):
        t = i / max(1, h - 1)
        c = (
            int(top_color[0] * (1 - t) + bottom_color[0] * t),
            int(top_color[1] * (1 - t) + bottom_color[1] * t),
            int(top_color[2] * (1 - t) + bottom_color[2] * t),
        )
        pygame.draw.line(surface, c, (x, y + i), (x + w - 1, y + i))


def outlined_circle(surf, color, center, radius, ow=2, oc=OUTLINE):
    pygame.draw.circle(surf, color, center, radius)
    if ow > 0:
        pygame.draw.circle(surf, oc, center, radius, ow)


def outlined_rect(surf, color, rect, ow=2, oc=OUTLINE):
    pygame.draw.rect(surf, color, rect)
    if ow > 0:
        pygame.draw.rect(surf, oc, rect, ow)


def outlined_polygon(surf, color, points, ow=2, oc=OUTLINE):
    pygame.draw.polygon(surf, color, points)
    if ow > 0:
        pygame.draw.polygon(surf, oc, points, ow)


def resolve_platform_overlap(sprite, platforms):
    if getattr(sprite, 'is_flying', False):
        return
    for platform in platforms:
        if not pygame.sprite.collide_rect(sprite, platform):
            continue
        rect = sprite.rect
        p = platform.rect
        left = rect.right - p.left
        right = p.right - rect.left
        top = rect.bottom - p.top
        bottom = p.bottom - rect.top
        edge = min(left, right, top, bottom)
        if edge == top:
            rect.bottom = p.top
        elif edge == bottom:
            rect.top = p.bottom
        elif edge == left:
            rect.right = p.left
        else:
            rect.left = p.right
        sprite.velocity_x = 0
        sprite.velocity_y = 0
        return


def draw_panel(surface, rect, border_color=GOLD, fill_alpha=180):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    s.fill((10, 12, 22, fill_alpha))
    surface.blit(s, (rect[0], rect[1]))
    pygame.draw.rect(surface, border_color, rect, 2, border_radius=6)


def draw_pie_slice(surface, color, center, radius, start_deg, end_deg):
    """画一个扇形，深渊轮盘用。"""
    steps = max(4, int(abs(end_deg - start_deg) / 6))
    pts = [center]
    for i in range(steps + 1):
        a = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        pts.append((center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)))
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.polygon(surface, OUTLINE, pts, 2)
