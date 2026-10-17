"""子弹、技能投射物与地面效果。"""


# === IMPORTS ===
import math
import pygame
import random
from ..data.biomes import BIOME_ICE
from ..data.skills import Skill
from .props import IceTrail
from ..settings import BOMB_RADIUS, FIRE_ORANGE, FIRE_YELLOW, LAVA_RED, OUTLINE, POISON_GREEN, SCREEN_HEIGHT, SCREEN_WIDTH
from ..utils import draw_glow
# === /IMPORTS ===

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, damage, pierce=0, explosive=False, color=None):
        super().__init__()
        if color is None: color = (110, 240, 180)
        self.base_color = color[:3]
        size = 20 if explosive else 14
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        for r, a in [(size // 2, 60), (size // 2 - 2, 100), (4, 220)]:
            if r <= 0: continue
            pygame.draw.circle(self.image, (*self.base_color, a), (cx, cy), r)
        pygame.draw.circle(self.image, (240, 255, 240), (cx, cy), 2)
        if explosive: pygame.draw.circle(self.image, (255, 180, 80, 220), (cx, cy), 5)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = vx; self.vy = vy
        self.damage = damage
        self.pierce_max = pierce
        self.hit_enemies = set()
        self.pierce_count = 0
        self.explosive = explosive
        self.lifetime = 300
        self.is_crit = False

    def update(self, barriers, enemies):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0: self.kill(); return
        if (self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or
                self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT):
            self.kill()


class BlackHoleBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, skill):
        super().__init__()
        self.skill = skill
        self.vx = vx
        self.vy = vy
        self.lifetime = 150
        size = 22
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        draw_glow(self.image, (125, 70, 220), (cx, cy), 13, 150)
        pygame.draw.circle(self.image, (25, 10, 45), (cx, cy), 9)
        pygame.draw.circle(self.image, (145, 95, 225), (cx, cy), 7, 2)
        pygame.draw.circle(self.image, (225, 205, 255), (cx, cy), 2)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, barriers):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
            return
        if (self.rect.right < -40 or self.rect.left > SCREEN_WIDTH + 40 or
                self.rect.bottom < -40 or self.rect.top > SCREEN_HEIGHT + 40):
            self.kill()
            return
        for barrier in barriers:
            if barrier.visible and pygame.sprite.collide_rect(self, barrier):
                self.kill()
                return


class BlackHole(pygame.sprite.Sprite):
    def __init__(self, x, y, skill, duration):
        super().__init__()
        self.skill = skill
        self.duration = duration
        self.timer = duration
        self.radius = 105
        self.pull_radius = 250
        self.damage_timer = 0
        self.anim = 0
        self.image = pygame.Surface((self.radius * 2 + 30, self.radius * 2 + 30), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self._redraw()

    def _redraw(self):
        self.image.fill((0, 0, 0, 0))
        cx = cy = self.rect.width // 2
        pulse = 4 + int(3 * math.sin(self.anim / 9))
        draw_glow(self.image, (115, 60, 210), (cx, cy), self.radius + pulse, 115)
        pygame.draw.circle(self.image, (8, 4, 18, 235), (cx, cy), self.radius - 16)
        pygame.draw.circle(self.image, (95, 45, 175, 210), (cx, cy), self.radius - 10, 4)
        for i, scale in enumerate((0.42, 0.66, 0.9)):
            r = int((self.radius - 12) * scale + 5 * math.sin(self.anim / (7 + i)))
            if r > 3:
                pygame.draw.circle(self.image, (185, 135, 255, 160 - i * 35), (cx, cy), r, 2)
        pygame.draw.circle(self.image, (240, 225, 255, 220), (cx, cy), 4)

    def update(self):
        self.timer -= 1
        self.anim += 1
        if self.timer <= 0:
            self.kill()
            return
        self._redraw()


class IceShard(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, damage, pierce, is_crit, freeze_dur, slow_dur,
                 owner=None, hostile=False, color=(150, 220, 255)):
        super().__init__()
        self.base_color = color
        self.hostile = hostile
        size = 22
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        draw_glow(self.image, color, (cx, cy), 10, 110)
        pygame.draw.polygon(self.image, color, [
            (cx, 1), (size - 3, cy), (cx, size - 2), (3, cy)
        ])
        pygame.draw.polygon(self.image, (240, 250, 255), [
            (cx, 4), (size - 7, cy), (cx, size - 5), (7, cy)
        ])
        pygame.draw.polygon(self.image, OUTLINE, [
            (cx, 1), (size - 3, cy), (cx, size - 2), (3, cy)
        ], 2)
        if is_crit:
            pygame.draw.circle(self.image, (255, 130, 130), (cx, cy), 3, 1)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = vx; self.vy = vy
        self.damage = damage
        self.pierce_max = pierce
        self.pierce_count = 0
        self.hit_enemies = set()
        self.is_crit = is_crit
        self.freeze_dur = freeze_dur
        self.slow_dur = slow_dur
        self.lifetime = 120
        self.owner = owner
        self.hit_player = False
        self.frost_path_timer = 0
        self.has_frost_path = False
        if owner is not None and isinstance(owner, Skill):
            self.has_frost_path = owner.has_evolution("frost_path")
        elif owner is not None:
            self.has_frost_path = getattr(owner, 'has_evolution', lambda x: False)("frost_path")

    def update(self, barriers, platforms=None, ice_trails=None, all_sprites=None):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0: self.kill(); return
        if (self.rect.right < -40 or self.rect.left > SCREEN_WIDTH + 40 or
                self.rect.bottom < -40 or self.rect.top > SCREEN_HEIGHT + 40):
            self.kill(); return
        if self.has_frost_path and not self.hostile:
            self.frost_path_timer += 1
            if self.frost_path_timer % 12 == 0 and ice_trails is not None:
                trail = IceTrail(self.rect.centerx,
                                 self.rect.bottom if self.rect.bottom < SCREEN_HEIGHT - 20 else SCREEN_HEIGHT - 35)
                ice_trails.add(trail)
                if all_sprites is not None: all_sprites.add(trail)


class SkillFireball(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, direct_damage, explosion_damage, radius, skill, is_crit=False, target=None):
        super().__init__()
        self.direct_damage = direct_damage
        self.explosion_damage = explosion_damage
        self.radius = radius
        self.vx = vx; self.vy = vy
        self.lifetime = 120
        self.skill = skill
        self.is_crit = is_crit
        self.target = target
        self.homing = (skill.has_evolution("snipe"))
        size = 26
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        draw_glow(self.image, (255, 140, 60), (cx, cy), 13, 150)
        pygame.draw.circle(self.image, (150, 40, 15), (cx, cy), 10)
        pygame.draw.circle(self.image, (255, 140, 60), (cx, cy), 7)
        pygame.draw.circle(self.image, (255, 235, 170), (cx, cy), 3)
        pygame.draw.circle(self.image, OUTLINE, (cx, cy), 10, 2)
        self.rect = self.image.get_rect(center=(x, y))


class MeteorFireball(pygame.sprite.Sprite):
    def __init__(self, x, y, vy, damage, radius, scorch=False, scorch_dur=300):
        super().__init__()
        self.damage = damage
        self.radius = radius
        self.scorch = scorch
        self.scorch_dur = scorch_dur
        self.is_crit = False
        self.lifetime = 300
        size = 36
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        draw_glow(self.image, (255, 140, 60), (cx, cy), 17, 170)
        pygame.draw.polygon(self.image, (255, 200, 80), [
            (cx, 0), (cx - 5, 8), (cx - 3, size - 4), (cx + 3, size - 4), (cx + 5, 8)
        ])
        pygame.draw.circle(self.image, (150, 40, 15), (cx, cy + 4), 12)
        pygame.draw.circle(self.image, (255, 130, 50), (cx, cy + 4), 9)
        pygame.draw.circle(self.image, (255, 240, 180), (cx, cy + 4), 5)
        pygame.draw.circle(self.image, OUTLINE, (cx, cy + 4), 12, 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.vy = vy


class Bomb(pygame.sprite.Sprite):
    def __init__(self, x, y, scene_type, upgrade_level=0):
        super().__init__()
        self.scene_type = scene_type
        self.upgrade_level = upgrade_level
        if upgrade_level > 0:
            self.radius = int(BOMB_RADIUS * (1.3 + 0.15 * upgrade_level))
        else:
            self.radius = BOMB_RADIUS
        size = self.radius * 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        base = (255, 170, 80) if scene_type != BIOME_ICE else (140, 220, 255)
        for i in range(8, 0, -1):
            r = int(self.radius * (i / 8))
            a = int(60 + (8 - i) * 22)
            pygame.draw.circle(self.image, (*base, min(220, a)), (self.radius, self.radius), r, 2)
        pygame.draw.circle(self.image, (*base, 90), (self.radius, self.radius), self.radius // 3)
        pygame.draw.circle(self.image, (255, 240, 210, 200), (self.radius, self.radius), self.radius // 6)
        self.rect = self.image.get_rect(center=(x, y))
        self.exploded = True
        self.area_timer = -1
        if upgrade_level > 0:
            self.duration = 60 + 15 * upgrade_level
            self.tick_damage = 8 + 5 * upgrade_level
        else:
            self.duration = 0
            self.tick_damage = 0

    def update(self):
        self.area_timer += 1
        if self.area_timer > self.duration: self.kill()

    def check_explosion_damage(self, targets):
        if not self.exploded: return []
        if self.area_timer == 0:
            damage = 100 + self.upgrade_level * 25
        elif self.tick_damage > 0 and self.area_timer > 0 and self.area_timer % 20 == 0:
            damage = self.tick_damage
        else:
            damage = 0
        if damage <= 0: return []
        bomb_center = (self.rect.centerx, self.rect.centery)
        damaged = []
        for target in targets:
            c = (target.rect.centerx, target.rect.centery)
            distance = math.sqrt((bomb_center[0] - c[0]) ** 2 + (bomb_center[1] - c[1]) ** 2)
            if distance <= self.radius:
                factor = 1 - (distance / self.radius)
                total = int(damage * factor)
                if total > 0: damaged.append((target, total))
        return damaged


class HookProjectile(pygame.sprite.Sprite):
    SPEED = 13
    MAX_DIST = 360

    def __init__(self, x, y, angle, owner, damage=10):
        super().__init__()
        self.owner = owner
        self.damage = damage
        self.angle = angle
        self.vx = math.cos(angle) * self.SPEED
        self.vy = math.sin(angle) * self.SPEED
        self.travelled = 0.0
        size = 30
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        for a in (-0.75, 0.0, 0.75):
            ex = cx + math.cos(angle + a) * 12
            ey = cy + math.sin(angle + a) * 12
            pygame.draw.line(self.image, (35, 25, 20), (cx, cy), (ex, ey), 5)
            pygame.draw.line(self.image, (200, 200, 215), (cx, cy), (ex, ey), 3)
            pygame.draw.line(self.image, (250, 250, 255), (cx, cy), (ex, ey), 1)
        pygame.draw.circle(self.image, (35, 25, 20), (cx, cy), 8)
        pygame.draw.circle(self.image, (150, 110, 70), (cx, cy), 6)
        pygame.draw.circle(self.image, (220, 190, 130), (cx, cy), 3)
        pygame.draw.circle(self.image, OUTLINE, (cx, cy), 8, 2)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, barriers, platforms):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.travelled += self.SPEED
        if self.travelled >= self.MAX_DIST: self.kill(); return
        for b in barriers:
            if b.visible and pygame.sprite.collide_rect(self, b):
                self.kill(); return
        if (self.rect.right < -20 or self.rect.left > SCREEN_WIDTH + 20 or
                self.rect.bottom < -20 or self.rect.top > SCREEN_HEIGHT + 20):
            self.kill()


class WarningCircle(pygame.sprite.Sprite):
    def __init__(self, x, y, delay=60, radius=60, spawn_type="spike"):
        super().__init__()
        self.x = x; self.y = y
        self.radius = radius
        self.timer = 0
        self.delay = delay
        self.spawn_type = spawn_type
        self.triggered = False
        self.image = pygame.Surface((radius * 2, radius), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.timer += 1
        self.image.fill((0, 0, 0, 0))
        progress = min(1.0, self.timer / self.delay)
        blink = (self.timer // 8) % 2 == 0
        if self.spawn_type == "meteor":
            color = (255, 90, 40) if blink else (255, 190, 80)
        elif self.spawn_type == "bomb":
            color = (180, 180, 200) if blink else (255, 100, 100)
        elif self.spawn_type == "bone":
            color = (220, 200, 240) if blink else (255, 255, 255)
        else:
            color = (255, 110, 90) if blink else (255, 200, 90)
        pygame.draw.ellipse(self.image, (*color, 220), (0, 0, self.radius * 2, self.radius), 2)
        inner_w = int(self.radius * progress)
        inner_h = max(1, int(self.radius * progress / 2))
        pygame.draw.ellipse(self.image, (*color, 90),
                            (self.radius - inner_w, self.radius // 2 - inner_h,
                             inner_w * 2, inner_h * 2))
        if self.timer >= self.delay and not self.triggered:
            self.triggered = True
            return True
        return False


class IceSpike(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((30, 60), pygame.SRCALPHA)
        pts = [(15, 0), (28, 45), (20, 60), (10, 60), (2, 45)]
        pygame.draw.polygon(self.image, (150, 220, 250), pts)
        pygame.draw.polygon(self.image, (220, 245, 255), [(15, 5), (22, 45), (15, 55), (10, 45)], 2)
        pygame.draw.polygon(self.image, OUTLINE, pts, 2)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y - 300
        self.target_y = y
        self.speed = 18
        self.damage = 18
        self.hit_player = False
        self.landed = False
        self.ground_timer = 0

    def update(self):
        if not self.landed:
            self.rect.y += self.speed
            if self.rect.bottom >= self.target_y:
                self.rect.bottom = self.target_y
                self.landed = True
                self.ground_timer = 0

    def check_player_hit(self, player):
        if self.hit_player or self.landed: return False
        if pygame.sprite.collide_rect(self, player):
            self.hit_player = True
            return True
        return False


class NovaWave(pygame.sprite.Sprite):
    """用于视觉呈现的波（不带伤害或极低伤害）。"""
    def __init__(self, x, y, max_radius=340, delay=0, damage=12, speed=6,
                 small=False, color=None):
        super().__init__()
        self.x = x; self.y = y
        self.radius = 0
        self.max_radius = max_radius
        self.delay = delay
        self.damage = damage
        self.speed = speed
        self.small = small
        if color is None:
            color = (255, 150, 150) if small else (150, 220, 255)
        self.color = color
        self.image = pygame.Surface((max_radius * 2, max_radius * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.hit_player = False

    def update(self):
        if self.delay > 0:
            self.delay -= 1
            return
        self.radius += self.speed
        self.image.fill((0, 0, 0, 0))
        if self.radius < self.max_radius:
            c = self.color
            pygame.draw.circle(self.image, (*c, 220), (self.max_radius, self.max_radius), int(self.radius), 6)
            pygame.draw.circle(self.image, (*c, 100), (self.max_radius, self.max_radius), int(self.radius), 2)
            pygame.draw.circle(self.image, (255, 255, 255, 180), (self.max_radius, self.max_radius), int(self.radius), 1)
        else:
            self.kill()

    def check_player_hit(self, player):
        """对视觉 nova 不再造成伤害（伤害为 0 时也直接返回）。"""
        if self.damage <= 0: return False
        if self.delay > 0 or self.hit_player: return False
        dx = player.rect.centerx - self.x
        dy = player.rect.centery - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if abs(dist - self.radius) < 28:
            self.hit_player = True
            return True
        return False


class SummonCircle(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type, scene_type, depth, delay=60, elite_kind=None):
        super().__init__()
        self.x = x; self.y = y
        self.enemy_type = enemy_type
        self.scene_type = scene_type
        self.depth = depth
        self.elite_kind = elite_kind
        self.timer = 0
        self.delay = delay
        self.triggered = False
        self.image = pygame.Surface((70, 30), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.timer += 1
        self.image.fill((0, 0, 0, 0))
        progress = min(1.0, self.timer / self.delay)
        color = (120, 210, 255)
        pygame.draw.ellipse(self.image, (*color, 220), (0, 0, 70, 30), 3)
        inner_w = int(35 * progress); inner_h = max(1, int(15 * progress))
        pygame.draw.ellipse(self.image, (*color, 120), (35 - inner_w, 15 - inner_h, inner_w * 2, inner_h * 2))
        if self.timer >= self.delay and not self.triggered:
            self.triggered = True
            return True
        return False


class Fireball(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, damage=10, color=None):
        super().__init__()
        self.base_color = color if color else FIRE_ORANGE
        size = 26
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        draw_glow(self.image, self.base_color, (cx, cy), 12, 140)
        dark = (max(0, self.base_color[0] - 80), max(0, self.base_color[1] - 80), max(0, self.base_color[2] - 80))
        pygame.draw.circle(self.image, dark, (cx, cy), 11)
        pygame.draw.circle(self.image, self.base_color, (cx, cy), 8)
        pygame.draw.circle(self.image, (255, 240, 200), (cx, cy), 3)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = vx; self.vy = vy
        self.damage = damage
        self.lifetime = 400

    def update(self, barriers):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0: self.kill(); return
        if (self.rect.right < -60 or self.rect.left > SCREEN_WIDTH + 60 or
                self.rect.bottom < -60 or self.rect.top > SCREEN_HEIGHT + 60):
            self.kill(); return
        for barrier in barriers:
            if barrier.visible and pygame.sprite.collide_rect(self, barrier):
                self.kill(); return


class SoulShock(pygame.sprite.Sprite):
    """炼魂魔骷的灵魂冲击：速度很快，命中后造成无视护盾的真实伤害。"""

    def __init__(self, x, y, vx, vy, damage=8, owner=None):
        super().__init__()
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.owner = owner
        self.lifetime = 180
        size = 30
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        draw_glow(self.image, (86, 238, 132), (cx, cy), 14, 180)
        pygame.draw.circle(self.image, (24, 92, 44), (cx, cy), 10)
        pygame.draw.circle(self.image, (88, 244, 140), (cx, cy), 7)
        pygame.draw.circle(self.image, (213, 255, 220), (cx, cy), 3)
        pygame.draw.polygon(self.image, (150, 255, 178), [
            (cx + 9, cy), (cx - 6, cy - 7), (cx - 2, cy),
            (cx - 6, cy + 7),
        ])
        pygame.draw.circle(self.image, OUTLINE, (cx, cy), 10, 2)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, barriers):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
            return
        if (self.rect.right < -50 or self.rect.left > SCREEN_WIDTH + 50 or
                self.rect.bottom < -50 or self.rect.top > SCREEN_HEIGHT + 50):
            self.kill()
            return
        for barrier in barriers:
            if barrier.visible and pygame.sprite.collide_rect(self, barrier):
                self.kill()
                return


class GroundWave(pygame.sprite.Sprite):
    """贴地横波：只覆盖地面上方一小段高度，跳跃可躲。"""
    def __init__(self, x, ground_y, direction, speed=6, width=60, height=30,
                 damage=10, color=None, lifetime=180):
        super().__init__()
        self.width = width
        self.height = height
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = ground_y
        self.direction = direction
        self.speed = speed
        self.damage = damage
        self.color = color if color else (255, 120, 60)
        self.lifetime = lifetime
        self.anim = random.randint(0, 100)
        self.hit_timer = 0

    def update(self):
        self.rect.x += self.speed * self.direction
        self.anim += 1
        self.image.fill((0, 0, 0, 0))
        c = self.color
        dark = (max(0, c[0] - 80), max(0, c[1] - 80), max(0, c[2] - 80))
        for i in range(0, self.width, 6):
            h = self.height - int(6 * abs(math.sin((self.anim + i) / 6)))
            h = max(6, h)
            pygame.draw.rect(self.image, (*dark, 200), (i, self.height - h, 6, h))
            pygame.draw.rect(self.image, (*c, 220), (i + 1, self.height - h + 2, 4, h - 4))
            pygame.draw.rect(self.image, (255, 240, 200, 180), (i + 2, self.height - h + 2, 2, 3))
        draw_glow(self.image, c, (self.width // 2, self.height // 2), self.width // 2 + 6, 60)
        if self.hit_timer > 0: self.hit_timer -= 1
        self.lifetime -= 1
        if self.lifetime <= 0 or self.rect.right < -120 or self.rect.left > SCREEN_WIDTH + 120:
            self.kill()


class FlameWall(pygame.sprite.Sprite):
    def __init__(self, x, ground_y, direction, speed=2.5, height=90, width=44, damage=8):
        super().__init__()
        self.width = width; self.height = height
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = ground_y
        self.direction = direction
        self.speed = speed
        self.damage = damage
        self.hit_timer = 0
        self.anim = random.randint(0, 100)

    def update(self):
        self.rect.x += self.speed * self.direction
        self.anim += 1
        self.image.fill((0, 0, 0, 0))
        pygame.draw.rect(self.image, (180, 55, 20, 180), (0, 0, self.width, self.height))
        pygame.draw.rect(self.image, (250, 130, 50, 220), (4, 6, self.width - 8, self.height - 6))
        for i in range(0, self.height, 8):
            offset = int(6 * math.sin((self.anim + i) / 5))
            cx = self.width // 2 + offset
            r = 5 + int(2 * math.sin((self.anim + i * 2) / 4))
            pygame.draw.circle(self.image, FIRE_YELLOW, (cx, i + 4), r)
            pygame.draw.circle(self.image, (255, 240, 180), (cx, i + 4), max(1, r - 3))
        draw_glow(self.image, FIRE_ORANGE, (self.width // 2, self.height // 2), self.width // 2 + 6, 60)
        if self.rect.right < -120 or self.rect.left > SCREEN_WIDTH + 120:
            self.kill()


class LavaPool(pygame.sprite.Sprite):
    def __init__(self, x, y, duration=300, damage=5, color=None, width=None, team="enemy"):
        super().__init__()
        self.width = width if width else 96
        self.image = pygame.Surface((self.width, 20), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.duration = duration
        self.damage = damage
        self.hit_timer = 0
        self.tick_timer = 0          # 新增：给玩家方使用的对敌伤害间隔计时
        self.team = team             # "enemy"（伤玩家）/ "player"（伤敌人）
        self.anim = random.randint(0, 60)
        self.color = color if color else LAVA_RED
        self.max_duration = duration

    def update(self):
        self.duration -= 1
        self.anim += 1
        self.image.fill((0, 0, 0, 0))
        if self.color == POISON_GREEN:
            base = (30, 70, 25, 220); mid = (110, 190, 70, 240); top = (200, 255, 140, 220)
        else:
            base = (140, 35, 10, 220); mid = (240, 110, 30, 240); top = (255, 230, 140, 220)
        pygame.draw.ellipse(self.image, base, (0, 0, self.width, 20))
        w2 = self.width - 16 + int(6 * math.sin(self.anim / 10))
        pygame.draw.ellipse(self.image, mid, (8, 3, w2, 12))
        pygame.draw.ellipse(self.image, top, (20, 6, w2 - 22, 6))
        if self.duration <= 0: self.kill()
