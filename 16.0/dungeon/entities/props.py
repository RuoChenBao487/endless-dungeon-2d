"""场景物件：平台、屏障、晶体、冰陷阱与冰痕。"""


# === IMPORTS ===
import pygame
import random
from ..data.biomes import (BIOME_CHURCH, BIOME_GREAT_TOMB, BIOME_LAVA,
                           BIOME_NORMAL, BIOME_POISON, BIOME_TOMB)
from ..settings import (CRYSTAL_BEAM_DURATION, CRYSTAL_COOLDOWN, ICE_TRAP_COOLDOWN,
                        OUTLINE, WHITE)
from ..utils import draw_glow, gradient_fill
# === /IMPORTS ===

class Crystal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = 20
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        draw_glow(self.image, (140, 220, 255), (cx, cy), 9, 120)
        pts = [(cx, 0), (size - 3, cy), (cx, size - 1), (3, cy)]
        pygame.draw.polygon(self.image, (170, 220, 250), pts)
        pygame.draw.polygon(self.image, (230, 245, 255), [(cx, 3), (size - 6, cy), (cx, size - 4), (6, cy)])
        pygame.draw.polygon(self.image, OUTLINE, pts, 2)
        pygame.draw.line(self.image, WHITE, (cx, 4), (cx, size - 5), 1)
        self.rect = self.image.get_rect(center=(x, y))
        self.pulse_timer = 0

    def update(self):
        self.pulse_timer = (self.pulse_timer + 1) % 60


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, scene_type=BIOME_NORMAL, fragile=False):
        super().__init__()
        self.scene_type = scene_type
        self.fragile = fragile
        self.hit_count = 0
        self.create_platform_image(width, height)
        self.rect = self.image.get_rect()
        self.rect.x = x; self.rect.y = y

    def create_platform_image(self, width, height):
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        if self.scene_type == BIOME_NORMAL:
            gradient_fill(self.image, (0, 0, width, height), (95, 70, 50), (55, 38, 26))
            for i in range(0, width, 22):
                pygame.draw.line(self.image, (40, 26, 18), (i, 0), (i, height), 1)
            pygame.draw.line(self.image, (140, 100, 70), (0, 1), (width, 1), 2)
            pygame.draw.line(self.image, (30, 20, 12), (0, height - 1), (width, height - 1), 1)
        elif self.scene_type == BIOME_LAVA:
            gradient_fill(self.image, (0, 0, width, height), (60, 22, 12), (30, 10, 5))
            for i in range(0, width, 26):
                pygame.draw.line(self.image, (80, 30, 15), (i, 0), (i, height), 1)
            pygame.draw.line(self.image, (255, 130, 40), (0, 1), (width, 1), 3)
            pygame.draw.line(self.image, (255, 220, 120), (0, 1), (width, 1), 1)
            for x in range(0, width, 8):
                if (x // 8) % 3 == 0:
                    pygame.draw.circle(self.image, (255, 200, 90), (x, 3), 1)
        elif self.scene_type == BIOME_POISON:
            gradient_fill(self.image, (0, 0, width, height), (45, 70, 40), (25, 40, 22))
            for i in range(0, width, 20):
                pygame.draw.line(self.image, (60, 100, 55), (i, 0), (i, height), 1)
            pygame.draw.line(self.image, (160, 220, 110), (0, 1), (width, 1), 2)
            for x in range(0, width, 15):
                if (x // 15) % 2 == 0:
                    pygame.draw.circle(self.image, (180, 230, 130), (x + 4, 4), 1)
        elif self.scene_type == BIOME_TOMB:
            gradient_fill(self.image, (0, 0, width, height), (60, 60, 75), (35, 35, 48))
            for i in range(0, width, 24):
                pygame.draw.line(self.image, (30, 30, 42), (i, 0), (i, height), 1)
            pygame.draw.line(self.image, (170, 170, 190), (0, 1), (width, 1), 2)
        elif self.scene_type == BIOME_CHURCH:
            gradient_fill(self.image, (0, 0, width, height), (74, 48, 56), (38, 27, 35))
            for i in range(0, width, 20):
                pygame.draw.line(self.image, (40, 28, 36), (i, 0), (i, height), 1)
            pygame.draw.line(self.image, (164, 108, 116), (0, 1), (width, 1), 2)
            for x in range(0, width, 34):
                pygame.draw.circle(self.image, (192, 74, 88), (x + 5, 4), 1)
        elif self.scene_type == BIOME_GREAT_TOMB:
            gradient_fill(self.image, (0, 0, width, height), (54, 72, 60), (26, 38, 31))
            for i in range(0, width, 24):
                pygame.draw.line(self.image, (28, 42, 32), (i, 0), (i, height), 1)
            pygame.draw.line(self.image, (124, 174, 132), (0, 1), (width, 1), 2)
            for x in range(0, width, 31):
                pygame.draw.circle(self.image, (74, 128, 84), (x + 7, 4), 1)
        else:
            gradient_fill(self.image, (0, 0, width, height), (190, 230, 250), (140, 190, 225))
            for i in range(0, width, 28):
                pygame.draw.line(self.image, (110, 170, 210), (i, 0), (i, height), 1)
            pygame.draw.line(self.image, WHITE, (0, 1), (width, 1), 3)
            for i in range(0, width, 12):
                pygame.draw.line(self.image, (240, 250, 255), (i, 2), (i + 6, 5), 1)
        if self.fragile:
            for i in range(0, width, 16):
                pygame.draw.line(self.image, (255, 80, 80), (i, height // 2),
                                 (min(i + 8, width), height // 2), 2)
        pygame.draw.line(self.image, OUTLINE, (0, height - 1), (width, height - 1), 2)


class Barrier(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, direction, scene_type=BIOME_NORMAL):
        super().__init__()
        self.scene_type = scene_type
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self._fill_color()
        self.rect = self.image.get_rect()
        self.rect.x = x; self.rect.y = y
        self.direction = direction
        self.visible = True

    def _fill_color(self):
        if self.scene_type == BIOME_NORMAL: base = (80, 100, 140)
        elif self.scene_type == BIOME_LAVA: base = (200, 80, 30)
        elif self.scene_type == BIOME_POISON: base = (120, 200, 90)
        elif self.scene_type == BIOME_TOMB: base = (150, 140, 180)
        elif self.scene_type == BIOME_CHURCH: base = (190, 82, 96)
        elif self.scene_type == BIOME_GREAT_TOMB: base = (92, 172, 112)
        else: base = (140, 210, 250)
        for y in range(0, self.image.get_height(), 8):
            c = (base[0] // 3, base[1] // 3, base[2] // 3)
            pygame.draw.rect(self.image, c, (0, y, self.image.get_width(), 4))
        pygame.draw.rect(self.image, base, (0, 0, self.image.get_width(), self.image.get_height()), 2)

    def set_visible(self, visible):
        self.visible = visible
        self.image.set_alpha(255 if visible else 0)


class IceTrap(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 10), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.x = x; self.rect.y = y
        self.active = False
        self.timer = 0
        self.cycle = [False] * (ICE_TRAP_COOLDOWN - 60) + [True] * 60

    def update(self):
        self.timer = (self.timer + 1) % len(self.cycle)
        self.active = self.cycle[self.timer]
        self.image.fill((0, 0, 0, 0))
        if self.active:
            for i in range(3):
                pts = [(i * 15 + 2, 10), (i * 15 + 8, 0), (i * 15 + 14, 10)]
                pygame.draw.polygon(self.image, (140, 220, 250), pts)
                pygame.draw.polygon(self.image, (200, 240, 255), pts, 1)
                pygame.draw.polygon(self.image, OUTLINE, pts, 2)


class IceTrail(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((30, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (170, 220, 245, 130), (0, 0, 30, 6))
        pygame.draw.ellipse(self.image, (220, 240, 255, 180), (4, 1, 22, 3))
        self.rect = self.image.get_rect(center=(x, y))
        self.lifetime = 300

    def update(self):
        self.lifetime -= 1
        self.image.set_alpha(int(130 * max(0, self.lifetime) / 300))
        if self.lifetime <= 0: self.kill()


class SnowDrift(pygame.sprite.Sprite):
    """暴风雪过后堆在地上的疏雪层：不完全遮挡，只是把视线搅乱。

    玩家走过去或者任何爆炸波及都会把它铲掉，所以它只挡一会儿。
    """

    def __init__(self, x, ground_top, width):
        super().__init__()
        height = 38
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        rng = random.Random((x * 31 + width) & 0xffff)
        # 一簇一簇的雪堆，中间留缝，看着像灌木而不是墙
        count = max(5, width // 11)
        for i in range(count):
            cx = int(width * (i + 0.5) / count) + rng.randint(-4, 4)
            r = rng.randint(13, 21)
            top = height - r
            pygame.draw.ellipse(self.image, (238, 246, 255, 232),
                                (cx - r, top, r * 2, r * 2))
            pygame.draw.ellipse(self.image, (206, 222, 240, 210),
                                (cx - r, top, r * 2, r * 2), 2)
        self.rect = self.image.get_rect(midbottom=(x + width // 2, ground_top + 4))

    def update(self):
        pass


class StormCrystal(pygame.sprite.Sprite):
    """暴云寺庙的金色菱形水晶：按 F 让它朝最近的敌人射一束金光。

    光束持续几秒，之后水晶暗淡，冷却结束才会重新亮起。
    """

    def __init__(self, x, ground_top):
        super().__init__()
        w, h = 22, 52
        self.image = pygame.Surface((w + 20, h + 16), pygame.SRCALPHA)
        cx, top = (w + 20) // 2, 8
        points = [(cx, top), (cx + w // 2, top + h // 2),
                  (cx, top + h), (cx - w // 2, top + h // 2)]
        pygame.draw.polygon(self.image, (255, 232, 150), points)
        pygame.draw.polygon(self.image, (246, 196, 74), points, 2)
        pygame.draw.line(self.image, (255, 250, 220), (cx, top + 6), (cx, top + h - 6), 2)
        draw_glow(self.image, (255, 214, 110), (cx, top + h // 2), 20, 90)
        self.rect = self.image.get_rect(midbottom=(x, ground_top + 6))
        self.ready = True
        self.cooldown = 0
        self.beam_timer = 0
        self.target = None
        self.tick = 0
        self.glow_timer = 0

    def activate(self, target):
        """点亮：锁定目标并开始计时。"""
        self.ready = False
        self.beam_timer = CRYSTAL_BEAM_DURATION
        self.target = target
        self.tick = 0
        self.glow_timer = CRYSTAL_BEAM_DURATION

    def tick_timers(self):
        if self.beam_timer > 0:
            self.beam_timer -= 1
            if self.beam_timer == 0:
                self.target = None
                self.cooldown = CRYSTAL_COOLDOWN
            return
        if self.cooldown > 0:
            self.cooldown -= 1
            if self.cooldown == 0:
                self.ready = True

    def update(self):
        self.tick_timers()
