"""领主基类：阶段、硬直条、通用状态机。"""


# === IMPORTS ===
import math
import pygame
import random
from ..entities.projectiles import WarningCircle
from ..settings import (GRAVITY, SCREEN_HEIGHT, SCREEN_WIDTH, TROLL_BUFF_DAMAGE,
                        TROLL_BUFF_SPEED, get_font)
from ..timing import frame_count
# === /IMPORTS ===

class BaseBoss(pygame.sprite.Sprite):
    PHASE_HP = (0.7, 0.4)
    BASE_HEALTH = 800
    HEALTH_SCALE = 80
    BASE_SPEED = 0.5
    SHIELD_COLOR = (120, 200, 255)
    BOSS_NAME = "未知领主"
    HP_COLORS = ((120, 200, 255), (80, 130, 220), (220, 80, 220))
    PHASE_NOVA_COLOR = None
    IS_FLYING = False

    def __init__(self, x, y, depth, scene_type):
        super().__init__()
        self.scene_type = scene_type
        self.depth = depth
        self.max_health = self.BASE_HEALTH + depth * self.HEALTH_SCALE + int(1.2 * depth ** 2)
        self.health = self.max_health
        self.phase = 1
        self.phase_triggered = set()
        self.state = "IDLE"
        self.state_timer = 0
        self.action_cooldown = 90
        self.invincible = False
        self.invincible_timer = 0
        self.facing = -1
        self.on_ground = False
        self.velocity_x = 0; self.velocity_y = 0
        self.shield_active = False
        self.shield_hp = 0
        self.shield_timer = 0
        self.base_speed = self.BASE_SPEED
        self._cd = {}
        self.anim_timer = 0
        # 破防槽（可打断的蓄力技能）
        self.break_gauge_max = 0
        self.break_gauge = 0
        self.break_broken = False
        self.buff_timer = 0          # 被巨魔狂呼者增幅的剩余帧数
        self._setup()
        self.image = self.create_boss_image()
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y

    @property
    def dmg_mult(self):
        """伤害倍率；被巨魔狂呼者增幅期间额外 +50%。"""
        base = 1.0 + self.depth * 0.05
        if getattr(self, 'buff_timer', 0) > 0:
            base *= 1.0 + TROLL_BUFF_DAMAGE
        return base

    def _setup(self): pass
    def get_hp_color(self): return self.HP_COLORS[min(self.phase - 1, len(self.HP_COLORS) - 1)]

    def tick_cd(self, names):
        for n in names:
            if n in self._cd and self._cd[n] > 0: self._cd[n] -= 1
        if self.action_cooldown > 0: self.action_cooldown -= 1
        if self.buff_timer > 0: self.buff_timer -= 1

    def apply_gravity(self, platforms):
        if self.IS_FLYING:
            self.on_ground = True
            return
        self.velocity_y += GRAVITY
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

    def create_boss_image(self): raise NotImplementedError
    def refresh_image(self): self.image = self.create_boss_image()

    def enter_phase_transition(self, game):
        self.invincible = True
        self.invincible_timer = 90
        self.state = "PHASE_TRANSITION"
        self.state_timer = 90
        self.phase += 1
        self.refresh_image()
        # 不再使用 nova，改用数个可躲预警
        for i in range(5):
            wx = random.randint(70, SCREEN_WIDTH - 70)
            w = WarningCircle(wx, SCREEN_HEIGHT - 40, delay=50, radius=45, spawn_type="spike")
            game.warnings.add(w); game.all_sprites.add(w)
        if self.phase == 3:
            for k in self._cd: self._cd[k] = max(60, self._cd[k] // 2)
            self.base_speed *= 1.5

    def start_break_gauge(self, amount):
        self.break_gauge_max = amount
        self.break_gauge = amount
        self.break_broken = False

    def apply_break_damage(self, dmg):
        if self.break_gauge_max > 0 and not self.break_broken:
            self.break_gauge -= dmg
            if self.break_gauge <= 0:
                self.break_broken = True
                return True
        return False

    def update(self, player, platforms, barriers, game):
        self.anim_timer += 1
        self.tick_cd(list(self._cd.keys()))
        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0: self.shield_active = False
        hp_ratio = self.health / self.max_health
        if self.phase == 1 and hp_ratio <= self.PHASE_HP[0] and 2 not in self.phase_triggered:
            self.phase_triggered.add(2); self.enter_phase_transition(game)
        elif self.phase == 2 and hp_ratio <= self.PHASE_HP[1] and 3 not in self.phase_triggered:
            self.phase_triggered.add(3); self.enter_phase_transition(game)
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0: self.invincible = False
            if self.state == "PHASE_TRANSITION":
                self.state_timer -= 1
                if self.state_timer <= 0:
                    self.state = "IDLE"; self.action_cooldown = 30
            self.apply_gravity(platforms)
            return
        if self.state != "IDLE":
            handled = self.state_update(player, platforms, barriers, game)
            if not handled:
                self.state_timer -= 1
                self.velocity_x = 0
                self.apply_gravity(platforms)
                if self.state_timer <= 0:
                    self.state = "IDLE"; self.action_cooldown = 30
            return
        self.idle_action(player, platforms, barriers, game)

    def state_update(self, player, platforms, barriers, game): return False

    def idle_action(self, player, platforms, barriers, game):
        dx = player.rect.centerx - self.rect.centerx
        if dx > 0: self.facing = 1
        elif dx < 0: self.facing = -1
        dist = abs(dx)
        if self.action_cooldown > 0:
            self.apply_gravity(platforms); return
        if self.try_cast(player, game, dist): return
        if self.IS_FLYING:
            self._flying_idle(player)
        else:
            speed = self.base_speed if self.phase == 1 else (0.7 if self.phase == 2 else 0.95)
            if self.buff_timer > 0:
                speed *= 1.0 + TROLL_BUFF_SPEED
            if self.phase == 3: speed = 0.95
            if dist > 150: self.velocity_x = self.facing * speed
            else: self.velocity_x = 0
            self.rect.x += self.velocity_x
            if self.rect.left < 25: self.rect.left = 25
            if self.rect.right > SCREEN_WIDTH - 25: self.rect.right = SCREEN_WIDTH - 25
            self.apply_gravity(platforms)
        if pygame.sprite.collide_rect(self, player):
            player.take_damage(1.2 * self.dmg_mult, source='boss')

    def _flying_idle(self, player):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        speed = 1.5 if self.phase == 1 else (2.0 if self.phase == 2 else 2.4)
        if abs(dx) > 60:
            self.rect.x += (1 if dx > 0 else -1) * speed
        if abs(dy) > 40:
            self.rect.y += (1 if dy > 0 else -1) * speed * 0.7
        self.rect.x = max(40, min(self.rect.x, SCREEN_WIDTH - self.rect.width - 40))
        self.rect.y = max(60, min(self.rect.y, SCREEN_HEIGHT - self.rect.height - 60))

    def try_cast(self, player, game, dist): return False

    def draw_shield(self, surface):
        if self.shield_active:
            cx = self.rect.centerx; cy = self.rect.centery
            r = max(self.rect.width, self.rect.height) // 2 + 10
            alpha = 100 + int(60 * math.sin(frame_count() / 12))
            s = pygame.Surface((r * 2 + 12, r * 2 + 12), pygame.SRCALPHA)
            c = self.SHIELD_COLOR
            pygame.draw.circle(s, (*c, alpha), (r + 6, r + 6), r, 3)
            pygame.draw.circle(s, (*c, alpha // 2), (r + 6, r + 6), r - 6, 1)
            pts = []
            for i in range(6):
                a = math.pi / 3 * i + frame_count() / 120
                pts.append((r + 6 + r * math.cos(a), r + 6 + r * math.sin(a)))
            pygame.draw.polygon(s, (*c, 150), pts, 2)
            surface.blit(s, (cx - r - 6, cy - r - 6))

    def draw_break_gauge(self, surface):
        if self.break_gauge_max > 0 and not self.break_broken and self.break_gauge > 0:
            bar_w = 180
            bar_h = 8
            x = self.rect.centerx - bar_w // 2
            y = self.rect.y - 30
            pygame.draw.rect(surface, (20, 20, 30), (x - 2, y - 2, bar_w + 4, bar_h + 4))
            ratio = max(0, self.break_gauge / self.break_gauge_max)
            pygame.draw.rect(surface, (255, 230, 90), (x, y, bar_w * ratio, bar_h))
            pygame.draw.rect(surface, (255, 255, 255), (x, y, bar_w * ratio, 2))
            pygame.draw.rect(surface, (240, 240, 250), (x, y, bar_w, bar_h), 1)
            f = get_font(12)
            t = f.render("破防！", True, (255, 240, 120))
            surface.blit(t, (self.rect.centerx - t.get_width() // 2, y - 16))
