"""非敌非弹的特殊单位：镜像、祭坛、核心、幽灵、决斗者、飘字。"""


# === IMPORTS ===
import math
import pygame
import random
from ..data.events import MIRROR_SKILL_NAMES
from .projectiles import Fireball, IceShard, MeteorFireball, SummonCircle, WarningCircle
from ..settings import GOLD, GRAVITY, OUTLINE, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE, get_font, screen
from ..utils import draw_glow
# === /IMPORTS ===

class MirrorImage(pygame.sprite.Sprite):
    def __init__(self, x, y, image, lifetime):
        super().__init__()
        self.image = image.copy()
        self.image.set_alpha(120)
        tint = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        tint.fill((120, 80, 200, 60))
        self.image.blit(tint, (0, 0), special_flags=pygame.BLEND_ADD)
        self.rect = self.image.get_rect(center=(x, y))
        self.lifetime = lifetime
    def update(self):
        self.lifetime -= 1
        if self.lifetime <= 0: self.kill()


class EventAltar(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        W, H = 64, 88
        self.image = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (0, 0, 0, 100), (6, H - 8, W - 12, 8))
        pygame.draw.rect(self.image, (60, 40, 25), (8, H - 20, W - 16, 16))
        pygame.draw.rect(self.image, OUTLINE, (8, H - 20, W - 16, 16), 2)
        pygame.draw.rect(self.image, (90, 70, 45), (14, H - 58, 36, 42))
        pygame.draw.rect(self.image, OUTLINE, (14, H - 58, 36, 42), 2)
        pygame.draw.rect(self.image, (140, 100, 60), (18, H - 52, 28, 6))
        cx, cy = W // 2, 22
        draw_glow(self.image, (255, 210, 120), (cx, cy), 20, 150)
        pygame.draw.circle(self.image, (255, 220, 130), (cx, cy), 15)
        pygame.draw.circle(self.image, (255, 255, 210), (cx, cy), 8)
        pygame.draw.circle(self.image, OUTLINE, (cx, cy), 15, 2)
        self.rect = self.image.get_rect()
        self.rect.centerx = x; self.rect.bottom = y
    def update(self): pass


class EventGoal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = 44
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2
        draw_glow(self.image, (255, 220, 100), (cx, cy), 22, 180)
        pygame.draw.circle(self.image, (255, 240, 150), (cx, cy), 16)
        pygame.draw.circle(self.image, (255, 255, 220), (cx, cy), 8)
        pygame.draw.circle(self.image, GOLD, (cx, cy), 16, 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.pulse = 0
    def update(self):
        self.pulse = (self.pulse + 1) % 60


class CoreCrystal(pygame.sprite.Sprite):
    """护核防守事件的目标：敌人只冲着它来，被打破就意味着防守失败。"""

    def __init__(self, x, y, max_health):
        super().__init__()
        W, H = 58, 82
        self.image = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (0, 0, 0, 110), (4, H - 9, W - 8, 8))
        body = [(29, 2), (54, 30), (43, H - 8), (15, H - 8), (4, 30)]
        pygame.draw.polygon(self.image, (58, 38, 88), body)
        pygame.draw.polygon(self.image, (140, 100, 225), [
            (29, 9), (46, 32), (37, H - 14), (21, H - 14), (12, 32)])
        pygame.draw.polygon(self.image, (212, 188, 255), [(29, 14), (39, 33), (29, H - 22), (19, 33)])
        draw_glow(self.image, (170, 130, 255), (29, 44), 30, 130)
        pygame.draw.polygon(self.image, OUTLINE, body, 2)
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)
        self.max_health = max(1, int(max_health))
        self.health = self.max_health
        self.hurt_cd = 0
        self.pulse = 0

    def update(self):
        self.pulse = (self.pulse + 1) % 90
        if self.hurt_cd > 0: self.hurt_cd -= 1

    def take_damage(self, amount):
        if self.hurt_cd > 0: return False
        self.hurt_cd = 30
        self.health = max(0, self.health - amount)
        return True

    def draw_health_bar(self, surface):
        bar_w = 160
        bar_h = 10
        x = self.rect.centerx - bar_w // 2
        y = self.rect.y - 22
        pygame.draw.rect(surface, (20, 16, 30), (x - 2, y - 2, bar_w + 4, bar_h + 4))
        ratio = max(0.0, self.health / self.max_health)
        color = (150, 120, 245) if ratio > 0.4 else (230, 80, 120)
        pygame.draw.rect(surface, color, (x, y, bar_w * ratio, bar_h))
        pygame.draw.rect(surface, (240, 240, 250), (x, y, bar_w, bar_h), 1)
        f = get_font(14)
        t = f.render(f"核心 {int(self.health)}/{self.max_health}", True, (240, 235, 255))
        surface.blit(t, (self.rect.centerx - t.get_width() // 2, y - 20))


class HunterGhost(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        W, H = 52, 62
        self.image = pygame.Surface((W, H), pygame.SRCALPHA)
        body = (210, 50, 80, 235)
        pygame.draw.ellipse(self.image, body, (5, 0, W - 10, H - 14))
        pygame.draw.polygon(self.image, body, [
            (5, H - 20), (W // 2 - 9, H - 4), (W // 2, H - 14),
            (W // 2 + 9, H - 4), (W - 5, H - 20)
        ])
        pygame.draw.circle(self.image, (40, 0, 10), (W // 3, H // 3), 5)
        pygame.draw.circle(self.image, (40, 0, 10), (2 * W // 3, H // 3), 5)
        pygame.draw.circle(self.image, (255, 200, 60), (W // 3, H // 3), 2)
        pygame.draw.circle(self.image, (255, 200, 60), (2 * W // 3, H // 3), 2)
        draw_glow(self.image, (255, 100, 100), (W // 2, H // 2), 22, 110)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 2.0
        self.phase = 0
    def update(self, player):
        self.phase += 1
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        d = math.hypot(dx, dy) or 1
        self.rect.x += dx / d * self.speed
        self.rect.y += dy / d * self.speed
        if self.phase % 10 == 0:
            self.rect.y += random.randint(-2, 2)


class MirrorDuelist(pygame.sprite.Sprite):
    def __init__(self, x, y, depth, scene_type, mirror_skills):
        super().__init__()
        self.scene_type = scene_type
        self.depth = depth
        self.is_elite = True
        self.is_mirror_duelist = True
        self.is_ember = False
        self.enemy_type = -1
        self.is_flying = False
        self.split_done = True
        self.stun_timer = 0
        self.freeze_timer = 0
        self.slow_timer = 0
        self.anim_timer = 0
        self.damage_multiplier = 1.0
        self.aura_speed_bonus = 0.0
        self.aura_damage_reduction = 0.0
        self.affix_names = []
        self.affix_instances = []
        self.base_speed = 2.4
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.facing = -1
        self.max_health = int(220 + depth * 28)
        self.health = self.max_health
        self.elite_name = "暗影镜像"
        self.mirror_skills = list(mirror_skills)
        self.skill_cd = {k: random.randint(90, 180) for k in self.mirror_skills}
        self.shield_active = False
        self.shield_hp = 0
        self.shield_timer = 0
        self.dash_timer = 0
        self.dash_dir = (1, 0)
        W, H = 48, 68
        self.image = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (0, 0, 0, 90), (8, H - 6, 32, 6))
        pygame.draw.polygon(self.image, (60, 25, 70), [(10, 22), (0, 58), (8, 60), (14, 32)])
        pygame.draw.polygon(self.image, (110, 40, 130), [(13, 24), (5, 54), (11, 56), (18, 30)])
        pygame.draw.rect(self.image, (40, 30, 60), (14, 46, 8, 18))
        pygame.draw.rect(self.image, (40, 30, 60), (26, 46, 8, 18))
        pygame.draw.polygon(self.image, (70, 45, 110), [(12, 24), (36, 24), (38, 48), (10, 48)])
        pygame.draw.polygon(self.image, OUTLINE, [(12, 24), (36, 24), (38, 48), (10, 48)], 2)
        pygame.draw.polygon(self.image, (110, 80, 170), [(14, 26), (34, 26), (34, 42), (14, 42)])
        pygame.draw.circle(self.image, (60, 30, 80), (13, 28), 6)
        pygame.draw.circle(self.image, (180, 100, 240), (13, 27), 3)
        pygame.draw.circle(self.image, OUTLINE, (13, 28), 6, 2)
        pygame.draw.circle(self.image, (200, 180, 230), (26, 16), 11)
        pygame.draw.circle(self.image, OUTLINE, (26, 16), 11, 2)
        pygame.draw.circle(self.image, (255, 80, 200), (22, 16), 2)
        pygame.draw.circle(self.image, (255, 80, 200), (30, 16), 2)
        draw_glow(self.image, (200, 80, 240), (24, 34), 20, 80)
        pygame.draw.rect(self.image, (255, 220, 130, 180), (0, 0, W, H), 2, border_radius=6)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y

    def apply_damage(self, damage, game=None):
        if self.shield_active and self.shield_hp > 0:
            absorbed = min(self.shield_hp, damage)
            self.shield_hp -= absorbed
            if self.shield_hp <= 0:
                self.shield_active = False
            damage -= absorbed
        if damage > 0:
            self.health -= damage
        return damage

    def update(self, platforms, barriers, ice_trails, all_sprites=None, game=None):
        self.anim_timer += 1
        frozen = self.freeze_timer > 0
        slowed = self.slow_timer > 0
        if self.freeze_timer > 0: self.freeze_timer -= 1
        if self.slow_timer > 0: self.slow_timer -= 1
        if self.shield_timer > 0:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False
        if self.stun_timer > 0:
            self.stun_timer -= 1
            self.velocity_y += GRAVITY
            self.rect.y += self.velocity_y
            self.on_ground = False
            for platform in platforms:
                if pygame.sprite.collide_rect(self, platform):
                    if self.velocity_y > 0:
                        self.rect.bottom = platform.rect.top
                        self.velocity_y = 0
                        self.on_ground = True
            return
        if frozen:
            self.velocity_y += GRAVITY
            self.rect.y += self.velocity_y
            self.on_ground = False
            for platform in platforms:
                if pygame.sprite.collide_rect(self, platform):
                    if self.velocity_y > 0:
                        self.rect.bottom = platform.rect.top
                        self.velocity_y = 0
                        self.on_ground = True
            return

        if game is not None:
            player = game.player
            dx = player.rect.centerx - self.rect.centerx
            dist = abs(dx)
            if dx > 0: self.facing = 1
            elif dx < 0: self.facing = -1
            for k in list(self.skill_cd.keys()):
                if self.skill_cd[k] > 0:
                    self.skill_cd[k] -= 1
                else:
                    self._cast_skill(k, game, player)
                    self.skill_cd[k] = 240 + random.randint(-60, 120)
            if self.dash_timer > 0:
                self.dash_timer -= 1
                prev_x = self.rect.x
                prev_y = self.rect.y
                self.rect.x += self.dash_dir[0] * 12
                self.rect.y += self.dash_dir[1] * 12
                if self.rect.left < 0:
                    self.rect.left = 0
                    self.dash_timer = 0
                elif self.rect.right > SCREEN_WIDTH:
                    self.rect.right = SCREEN_WIDTH
                    self.dash_timer = 0
                if self.rect.top < 0:
                    self.rect.top = 0
                if self.rect.bottom > SCREEN_HEIGHT - 30:
                    self.rect.bottom = SCREEN_HEIGHT - 30
                for b in barriers:
                    if b.visible and pygame.sprite.collide_rect(self, b):
                        self.rect.x = prev_x
                        self.rect.y = prev_y
                        self.dash_timer = 0
                        break

        self.velocity_y += GRAVITY
        self.rect.x += self.velocity_x
        collision_sprites = list(platforms) + [b for b in barriers if b.visible]
        for sprite in collision_sprites:
            if pygame.sprite.collide_rect(self, sprite):
                if self.velocity_x > 0:
                    self.rect.right = sprite.rect.left; self.velocity_x = 0
                elif self.velocity_x < 0:
                    self.rect.left = sprite.rect.right; self.velocity_x = 0
        self.rect.y += self.velocity_y
        self.on_ground = False
        for platform in platforms:
            if pygame.sprite.collide_rect(self, platform):
                if self.velocity_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.velocity_y = 0; self.on_ground = True
                elif self.velocity_y < 0:
                    self.rect.top = platform.rect.bottom
                    self.velocity_y = 0

    def _cast_skill(self, kind, game, player):
        cx = self.rect.centerx
        cy = self.rect.centery - 10
        px = player.rect.centerx
        py = player.rect.centery
        if kind == "fireball":
            base_angle = math.atan2(py - cy, px - cx)
            for off in (-0.2, 0, 0.2):
                a = base_angle + off
                fb = Fireball(cx, cy, math.cos(a) * 6, math.sin(a) * 6,
                              damage=int(8 + self.depth * 0.8), color=(180, 130, 240))
                game.fireballs.add(fb); game.all_sprites.add(fb)
        elif kind == "ice_nova":
            direction = 1 if px > cx else -1
            shard = IceShard(cx + direction * 20, cy, direction * 12, 0,
                             damage=int(10 + self.depth * 0.8), pierce=0,
                             is_crit=False, freeze_dur=60, slow_dur=360,
                             owner=None, hostile=True, color=(180, 140, 240))
            game.ice_shards.add(shard); game.all_sprites.add(shard)
        elif kind == "dash":
            self.dash_dir = (1 if px > cx else -1, 0)
            self.dash_timer = 20
            self.velocity_x = 0
        elif kind == "shield":
            self.shield_active = True
            self.shield_hp = 60
            self.shield_timer = 240
        elif kind == "summon":
            for _ in range(2):
                x = random.randint(80, SCREEN_WIDTH - 80)
                y = SCREEN_HEIGHT - 60
                circle = SummonCircle(x, y - 15, random.choice([11, 12]),
                                      self.scene_type, self.depth, delay=45)
                game.summon_circles.add(circle); game.all_sprites.add(circle)
        elif kind == "nova":
            # 镜像自己的新星改为预警圈
            for _ in range(2):
                x = random.randint(80, SCREEN_WIDTH - 80)
                w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=35, radius=40, spawn_type="spike")
                game.warnings.add(w); game.all_sprites.add(w)
        elif kind == "meteor":
            for _ in range(2):
                x = random.randint(80, SCREEN_WIDTH - 80)
                m = MeteorFireball(x, -40, 13, int(8 + self.depth * 0.8), 70, scorch=False)
                game.meteors.add(m); game.all_sprites.add(m)

    def draw_health_bar(self, surface):
        bar_w = max(self.rect.width, 80)
        bar_h = 6
        x = self.rect.centerx - bar_w // 2
        y = self.rect.y - 18
        pygame.draw.rect(surface, (30, 10, 40), (x - 1, y - 1, bar_w + 2, bar_h + 2))
        ratio = max(0, self.health / self.max_health)
        pygame.draw.rect(surface, (200, 90, 240), (x, y, bar_w * ratio, bar_h))
        pygame.draw.rect(surface, (255, 200, 255), (x, y, bar_w * ratio, 1))
        pygame.draw.rect(surface, WHITE, (x, y, bar_w, bar_h), 1)
        font = get_font(14)
        text = font.render("暗影镜像", True, (220, 150, 255))
        ts = pygame.Surface((text.get_width() + 12, text.get_height() + 4), pygame.SRCALPHA)
        ts.fill((20, 10, 30, 180))
        ts.blit(text, (6, 2))
        tr = ts.get_rect(center=(self.rect.centerx, y - 12))
        surface.blit(ts, tr)
        skill_names = " / ".join(MIRROR_SKILL_NAMES.get(k, k) for k in self.mirror_skills)
        f2 = get_font(12)
        t2 = f2.render(skill_names, True, (200, 180, 240))
        screen.blit(t2, (self.rect.centerx - t2.get_width() // 2, y - 32))

    def draw_affix_icons(self, surface): pass


class FloatingText(pygame.sprite.Sprite):
    def __init__(self, x, y, text, color, size=20, lifetime=50):
        super().__init__()
        self.lifetime = lifetime; self.max_life = lifetime
        font = get_font(size)
        base = font.render(text, True, color)
        shadow = font.render(text, True, (10, 10, 18))
        self.image = pygame.Surface((base.get_width() + 6, base.get_height() + 6), pygame.SRCALPHA)
        self.image.blit(shadow, (3, 3)); self.image.blit(base, (1, 1))
        self.fy = float(y)
        self.rect = self.image.get_rect(center=(x, y))
    def update(self):
        self.lifetime -= 1
        if self.lifetime <= 0: self.kill(); return
        self.fy -= 1.2
        self.rect.centery = int(self.fy)
        a = int(255 * (self.lifetime / self.max_life))
        self.image.set_alpha(max(0, min(255, a)))
