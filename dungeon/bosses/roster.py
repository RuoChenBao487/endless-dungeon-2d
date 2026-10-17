"""七位领主的实现。"""


# === IMPORTS ===
import math
import pygame
import random
from .base import BaseBoss
from ..data.biomes import BIOME_ICE, BIOME_LAVA, BIOME_POISON, BIOME_TOMB
from ..data.enemies import ELITE_STATS
from ..entities.enemies import EliteEnemy, Enemy
from ..data.bosses import BOSS_BONE_DRAGON, BOSS_FALLEN_KNIGHT, BOSS_ICE_TITAN, BOSS_INFERNAL_DEMON, BOSS_MOLTEN_GIANT, BOSS_NAMES, BOSS_POISON_QUEEN, BOSS_STITCHED
from ..entities.enemies import EmberMinion
from ..entities.projectiles import Fireball, FlameWall, GroundWave, LavaPool, NovaWave, SummonCircle, WarningCircle
from ..entities.props import IceTrap
from ..settings import (BLIZZARD_DURATION, BONE_WHITE, DARK_KNIGHT, FIRE_ORANGE, FIRE_RED,
                        FIRE_YELLOW, FPS, GHOST_PURPLE, GOLD, OUTLINE, POISON_BRIGHT,
                        POISON_GREEN, SCREEN_HEIGHT, SCREEN_WIDTH, STEEL, STEEL_DARK,
                        TROLL_BUFF_DAMAGE, TROLL_BUFF_DURATION, TROLL_BUFF_RANGE,
                        TROLL_BUFF_SPEED)
from ..utils import draw_glow
# === /IMPORTS ===

class FallenKnightBoss(BaseBoss):
    BOSS_NAME = BOSS_NAMES[BOSS_FALLEN_KNIGHT]
    BASE_HEALTH = 700; HEALTH_SCALE = 70; BASE_SPEED = 0.8
    SHIELD_COLOR = (200, 210, 230)
    HP_COLORS = ((200, 210, 230), (170, 60, 60), (120, 20, 20))
    PHASE_NOVA_COLOR = (200, 80, 80)

    def _setup(self):
        self._cd = {"slash": 180, "charge": 300, "jump": 360, "summon": 480, "sword_rain": 540}
        self.shield_broken = False
        self.shield_active = False
        self.shield_hp = 0
        self.charge_dir = 0
        self.rage_charges = 0

    def create_boss_image(self):
        W, H = 110, 140
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 120), (10, H - 8, W - 20, 8))
        pygame.draw.polygon(surf, (40, 20, 30), [(26, 40), (6, H - 4), (W - 6, H - 4), (W - 26, 40)])
        pygame.draw.polygon(surf, (90, 30, 40), [(30, 44), (18, H - 10), (W - 18, H - 10), (W - 30, 44)])
        pygame.draw.rect(surf, STEEL_DARK, (32, 88, 18, 42))
        pygame.draw.rect(surf, STEEL_DARK, (60, 88, 18, 42))
        pygame.draw.rect(surf, OUTLINE, (32, 88, 18, 42), 2)
        pygame.draw.rect(surf, OUTLINE, (60, 88, 18, 42), 2)
        pygame.draw.rect(surf, DARK_KNIGHT, (28, 44, 54, 50))
        pygame.draw.rect(surf, STEEL_DARK, (32, 48, 46, 42))
        pygame.draw.rect(surf, OUTLINE, (32, 48, 46, 42), 2)
        crack = (180, 30, 40) if self.phase < 3 else (255, 60, 60)
        pygame.draw.line(surf, crack, (55, 52), (60, 62), 2)
        pygame.draw.line(surf, crack, (60, 62), (52, 78), 2)
        pygame.draw.line(surf, crack, (60, 62), (66, 72), 1)
        pygame.draw.polygon(surf, STEEL, [(20, 46), (34, 40), (38, 60), (22, 64)])
        pygame.draw.polygon(surf, OUTLINE, [(20, 46), (34, 40), (38, 60), (22, 64)], 2)
        pygame.draw.polygon(surf, STEEL, [(W - 20, 46), (W - 34, 40), (W - 38, 60), (W - 22, 64)])
        pygame.draw.polygon(surf, OUTLINE, [(W - 20, 46), (W - 34, 40), (W - 38, 60), (W - 22, 64)], 2)
        shield_col = (160, 170, 190) if not self.shield_broken else (80, 80, 90)
        pygame.draw.polygon(surf, shield_col, [(2, 46), (26, 42), (26, 90), (14, 104), (2, 90)])
        pygame.draw.polygon(surf, OUTLINE, [(2, 46), (26, 42), (26, 90), (14, 104), (2, 90)], 2)
        pygame.draw.line(surf, GOLD, (14, 48), (14, 96), 2)
        pygame.draw.circle(surf, crack if self.phase >= 2 else GOLD, (14, 70), 4)
        pygame.draw.rect(surf, (60, 50, 40), (W - 14, 40, 8, 12))
        pygame.draw.polygon(surf, (200, 200, 220), [(W - 8, 52), (W - 2, 56), (W - 4, 132), (W - 10, 132)])
        pygame.draw.polygon(surf, OUTLINE, [(W - 8, 52), (W - 2, 56), (W - 4, 132), (W - 10, 132)], 2)
        pygame.draw.rect(surf, DARK_KNIGHT, (36, 12, 38, 34))
        pygame.draw.rect(surf, STEEL_DARK, (40, 16, 30, 26))
        pygame.draw.rect(surf, OUTLINE, (40, 16, 30, 26), 2)
        eye = (255, 60, 60) if self.phase < 3 else (255, 130, 130)
        pygame.draw.circle(surf, eye, (49, 28), 3)
        pygame.draw.circle(surf, eye, (61, 28), 3)
        draw_glow(surf, eye, (49, 28), 8, 90)
        draw_glow(surf, eye, (61, 28), 8, 90)
        pygame.draw.polygon(surf, (140, 30, 40), [(48, 12), (56, 0), (64, 12)])
        pygame.draw.polygon(surf, OUTLINE, [(48, 12), (56, 0), (64, 12)], 2)
        core = (180, 60, 60) if self.phase < 3 else (255, 90, 90)
        draw_glow(surf, core, (55, 68), 22, 100)
        return surf

    def apply_damage(self, damage, game=None):
        if self.shield_active and not self.shield_broken and self.phase == 1:
            damage = int(damage * 0.2)
            self.shield_hp -= damage
            if self.shield_hp <= 0:
                self.shield_broken = True
                self.shield_active = False
                self.state = "STUNNED"; self.state_timer = 180
                if game is not None:
                    game.show_message("盾牌被击碎！骑士陷入硬直！", 1500)
        self.health -= damage
        return damage

    def state_update(self, player, platforms, barriers, game):
        if self.state == "STUNNED":
            self.state_timer -= 1
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 20
            return True
        if self.state == "CHARGE":
            self.velocity_x = self.charge_dir * 14
            self.rect.x += self.velocity_x
            hit_wall = False
            if self.rect.left <= 15 or self.rect.right >= SCREEN_WIDTH - 15: hit_wall = True
            for b in barriers:
                if b.visible and pygame.sprite.collide_rect(self, b):
                    hit_wall = True; break
            if hit_wall:
                self.rect.x -= self.velocity_x
                self.velocity_x = 0
                self.state = "STUNNED"
                self.state_timer = 60 if self.phase == 3 else 90
                # 撞墙改为：面向方向的贴地扇形冲击（跳跃躲）
                ground_y = SCREEN_HEIGHT - 30
                facing = -1 if self.charge_dir > 0 else 1
                gw = GroundWave(self.rect.centerx, ground_y, facing,
                                speed=6, width=70, height=28,
                                damage=int(8 * self.dmg_mult),
                                color=(200, 80, 80), lifetime=140)
                game.ground_waves.add(gw); game.all_sprites.add(gw)
                self.apply_gravity(platforms)
                return True
            if pygame.sprite.collide_rect(self, player):
                player.take_damage(14 * self.dmg_mult, source='boss')
                kb = 15 if self.charge_dir > 0 else -15
                player.velocity_x = kb; player.velocity_y = -6
            self.state_timer -= 1
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "SLASH":
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 40
            return True
        if self.state == "JUMP":
            if self.on_ground and self.velocity_y >= 0 and self.state_timer < 40:
                self.state = "JUMP_LAND"; self.state_timer = 20
                # 落地横波，跳跃可躲
                ground_y = SCREEN_HEIGHT - 30
                for d in (-1, 1):
                    gw = GroundWave(self.rect.centerx, ground_y, d,
                                    speed=6, width=70, height=28,
                                    damage=int(10 * self.dmg_mult),
                                    color=(200, 80, 80), lifetime=140)
                    game.ground_waves.add(gw); game.all_sprites.add(gw)
                self.velocity_y = 0
            self.state_timer -= 1
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "JUMP_LAND":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "SWORD_RAIN":
            self.state_timer -= 1
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state_timer % 20 == 0:
                x = random.randint(60, SCREEN_WIDTH - 60)
                w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=30, radius=40, spawn_type="spike")
                game.warnings.add(w); game.all_sprites.add(w)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 60
            return True
        if self.state == "SUMMON":
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 60
            return True
        return False

    def try_cast(self, player, game, dist):
        if self.phase == 1 and not self.shield_broken and not self.shield_active:
            self._do_shield(); return True
        if self.phase == 3 and self.rage_charges > 0:
            self._do_charge(player); self.rage_charges -= 1
            return True
        if dist < 260 and self._cd["charge"] <= 0:
            self._do_charge(player); return True
        if dist < 180 and self._cd["slash"] <= 0:
            self._do_slash(game, player); return True
        if dist < 250 and self._cd["jump"] <= 0:
            self._do_jump(player); return True
        if self.phase >= 3 and self._cd["sword_rain"] <= 0:
            self._do_sword_rain(game); return True
        if self.phase >= 2 and self._cd["summon"] <= 0 and len(game.enemies) < 4:
            self._do_summon(game); return True
        return False

    def _do_shield(self):
        self.shield_active = True
        self.shield_hp = 150
        self.shield_timer = 600

    def _do_slash(self, game, player):
        self.state = "SLASH"; self.state_timer = 40
        self._cd["slash"] = 200
        self.velocity_x = 0
        cx = self.rect.centerx
        cy = self.rect.centery
        dmg = int(10 * self.dmg_mult)
        for i, off in enumerate((-0.4, 0, 0.4)):
            fb = Fireball(cx, cy, math.cos(off) * 7 * self.facing, math.sin(off) * 5,
                          damage=dmg, color=(255, 90, 90))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_charge(self, player):
        self.state = "CHARGE"; self.state_timer = 45
        self._cd["charge"] = 360 if self.phase < 3 else 200
        dx = player.rect.centerx - self.rect.centerx
        self.charge_dir = 1 if dx > 0 else -1
        self.facing = self.charge_dir
        self.velocity_x = 0

    def _do_jump(self, player):
        self.state = "JUMP"; self.state_timer = 60
        self._cd["jump"] = 420 if self.phase < 3 else 280
        self.velocity_y = -16
        self.velocity_x = (1 if player.rect.centerx > self.rect.centerx else -1) * 3

    def _do_sword_rain(self, game):
        self.state = "SWORD_RAIN"; self.state_timer = 90
        self._cd["sword_rain"] = 600

    def _do_summon(self, game):
        self.state = "SUMMON"; self.state_timer = 45
        self._cd["summon"] = 540
        for _ in range(2):
            x = random.randint(80, SCREEN_WIDTH - 80)
            y = SCREEN_HEIGHT - 60
            circle = SummonCircle(x, y - 15, 2, self.scene_type, self.depth, delay=45)
            game.summon_circles.add(circle); game.all_sprites.add(circle)


class IceTitanBoss(BaseBoss):
    BOSS_NAME = BOSS_NAMES[BOSS_ICE_TITAN]
    BASE_HEALTH = 850; HEALTH_SCALE = 85; BASE_SPEED = 0.4
    SHIELD_COLOR = (120, 200, 255)
    HP_COLORS = ((160, 220, 255), (80, 150, 230), (200, 90, 240))
    PHASE_NOVA_COLOR = (150, 220, 255)

    def _setup(self):
        self._cd = {"icicle": 300, "breath": 240, "wall": 360, "charge": 300,
                    "crack": 420, "ice_field": 600, "shield": 900}
        self.core_exposed = False
        self.charge_dir = 0

    def create_boss_image(self):
        W, H = 150, 170
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 120), (10, H - 8, W - 20, 8))
        pygame.draw.polygon(surf, (100, 170, 220), [(28, 100), (48, 100), (52, H - 8), (24, H - 8)])
        pygame.draw.polygon(surf, (100, 170, 220), [(W - 48, 100), (W - 28, 100), (W - 24, H - 8), (W - 52, H - 8)])
        pygame.draw.polygon(surf, OUTLINE, [(28, 100), (48, 100), (52, H - 8), (24, H - 8)], 2)
        pygame.draw.polygon(surf, OUTLINE, [(W - 48, 100), (W - 28, 100), (W - 24, H - 8), (W - 52, H - 8)], 2)
        pygame.draw.polygon(surf, (130, 200, 240), [(22, 44), (W - 22, 44), (W - 18, 108), (18, 108)])
        pygame.draw.polygon(surf, OUTLINE, [(22, 44), (W - 22, 44), (W - 18, 108), (18, 108)], 2)
        for i in range(6):
            y = 50 + i * 10
            pygame.draw.line(surf, (200, 240, 255), (26, y), (W - 26, y), 1)
        for i in range(4):
            x = 30 + i * 22
            pygame.draw.polygon(surf, (180, 230, 255), [(x, 46), (x + 8, 10), (x + 16, 46)])
            pygame.draw.polygon(surf, OUTLINE, [(x, 46), (x + 8, 10), (x + 16, 46)], 2)
        core_visible = (self.phase >= 2) or self.core_exposed
        if core_visible:
            core_col = (120, 220, 255) if self.phase < 3 else (220, 120, 255)
            draw_glow(surf, core_col, (W // 2, 76), 26, 150)
            pygame.draw.circle(surf, core_col, (W // 2, 76), 16)
            pygame.draw.circle(surf, (255, 255, 255), (W // 2, 76), 6)
            pygame.draw.circle(surf, OUTLINE, (W // 2, 76), 16, 2)
        else:
            pygame.draw.circle(surf, (80, 140, 190), (W // 2, 76), 16)
            pygame.draw.circle(surf, OUTLINE, (W // 2, 76), 16, 2)
        pygame.draw.polygon(surf, (110, 180, 220), [(18, 50), (2, 54), (4, 96), (22, 92)])
        pygame.draw.polygon(surf, (110, 180, 220), [(W - 18, 50), (W - 2, 54), (W - 4, 96), (W - 22, 92)])
        pygame.draw.polygon(surf, OUTLINE, [(18, 50), (2, 54), (4, 96), (22, 92)], 2)
        pygame.draw.polygon(surf, OUTLINE, [(W - 18, 50), (W - 2, 54), (W - 4, 96), (W - 22, 92)], 2)
        pygame.draw.polygon(surf, (130, 200, 240), [(W // 2 - 22, 12), (W // 2 + 22, 12), (W // 2 + 18, 46), (W // 2 - 18, 46)])
        pygame.draw.polygon(surf, OUTLINE, [(W // 2 - 22, 12), (W // 2 + 22, 12), (W // 2 + 18, 46), (W // 2 - 18, 46)], 2)
        eye = (180, 240, 255) if self.phase < 3 else (255, 180, 255)
        pygame.draw.circle(surf, eye, (W // 2 - 10, 28), 3)
        pygame.draw.circle(surf, eye, (W // 2 + 10, 28), 3)
        draw_glow(surf, eye, (W // 2 - 10, 28), 8, 100)
        draw_glow(surf, eye, (W // 2 + 10, 28), 8, 100)
        for i in range(3):
            x = W // 2 - 14 + i * 14
            pygame.draw.polygon(surf, (200, 240, 255), [(x, 12), (x + 4, -8), (x + 8, 12)])
            pygame.draw.polygon(surf, OUTLINE, [(x, 12), (x + 4, -8), (x + 8, 12)], 2)
        return surf

    def apply_damage(self, damage, game=None):
        if self.phase >= 2:
            damage = int(damage * 1.5)
        self.health -= damage
        return damage

    def state_update(self, player, platforms, barriers, game):
        if self.state == "STUNNED":
            self.state_timer -= 1
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 20
            return True
        if self.state == "CHARGE":
            self.velocity_x = self.charge_dir * 11
            self.rect.x += self.velocity_x
            hit_wall = False
            if self.rect.left <= 15 or self.rect.right >= SCREEN_WIDTH - 15: hit_wall = True
            for b in barriers:
                if b.visible and pygame.sprite.collide_rect(self, b):
                    hit_wall = True; break
            if hit_wall:
                self.rect.x -= self.velocity_x
                self.state = "STUNNED"; self.state_timer = 120
                ground_y = SCREEN_HEIGHT - 30
                facing = -1 if self.charge_dir > 0 else 1
                gw = GroundWave(self.rect.centerx, ground_y, facing,
                                speed=6, width=70, height=28,
                                damage=int(8 * self.dmg_mult),
                                color=(150, 220, 255), lifetime=140)
                game.ground_waves.add(gw); game.all_sprites.add(gw)
                self.apply_gravity(platforms)
                return True
            if pygame.sprite.collide_rect(self, player):
                player.take_damage(18 * self.dmg_mult, source='boss')
                kb = 15 if self.charge_dir > 0 else -15
                player.velocity_x = kb; player.velocity_y = -8
                player.slow_timer = max(player.slow_timer, 180)
            self.state_timer -= 1
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state in ("ICICLE", "BREATH", "WALL", "CRACK", "ICE_FIELD", "SHIELD", "ICE_LOCK"):
            self.state_timer -= 1
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state == "SHIELD" and not self.shield_active:
                self.state = "IDLE"; self.action_cooldown = 30
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        return False

    def try_cast(self, player, game, dist):
        if dist < 220 and self._cd["charge"] <= 0:
            self._do_charge(player); return True
        if self.phase >= 2 and self._cd["crack"] <= 0:
            self._do_crack(game); return True
        if dist < 260 and self._cd["breath"] <= 0:
            self._do_breath(game, player); return True
        if self._cd["icicle"] <= 0:
            self._do_icicle(game); return True
        if self._cd["wall"] <= 0:
            self._do_wall(game, player); return True
        if self.phase >= 3 and self._cd["ice_field"] <= 0:
            self._do_ice_field(game); return True
        if self.phase >= 2 and self._cd["shield"] <= 0 and self.health < self.max_health * 0.65:
            self._do_shield(); return True
        return False

    def _do_icicle(self, game):
        self.state = "ICICLE"; self.state_timer = 60
        self._cd["icicle"] = 480 if self.phase < 3 else 300
        count = 5 if self.phase == 1 else (6 if self.phase == 2 else 7)
        for _ in range(count):
            x = random.randint(60, SCREEN_WIDTH - 60)
            w = WarningCircle(x, SCREEN_HEIGHT - 45, delay=45, radius=50, spawn_type="spike")
            game.warnings.add(w); game.all_sprites.add(w)

    def _do_breath(self, game, player):
        self.state = "BREATH"; self.state_timer = 60
        self._cd["breath"] = 320 if self.phase < 3 else 200
        self.velocity_x = 0
        dx = player.rect.centerx - self.rect.centerx
        base = math.atan2(player.rect.centery - self.rect.centery, dx)
        count = 3 if self.phase == 1 else (5 if self.phase == 2 else 7)
        dmg = int(9 * self.dmg_mult)
        for i in range(count):
            a = base + (i - (count - 1) / 2) * 0.18
            fb = Fireball(self.rect.centerx, self.rect.centery - 10,
                          math.cos(a) * 6, math.sin(a) * 6, damage=dmg,
                          color=(150, 220, 255))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_wall(self, game, player):
        self.state = "WALL"; self.state_timer = 40
        self._cd["wall"] = 420
        self.velocity_x = 0
        direction = 1 if player.rect.centerx > self.rect.centerx else -1
        ground_y = SCREEN_HEIGHT - 30
        for i in range(2):
            x = self.rect.centerx + direction * (60 + i * 80)
            x = max(60, min(x, SCREEN_WIDTH - 60))
            fb = Fireball(x, ground_y - 60, 0, 6, damage=int(10 * self.dmg_mult),
                          color=(170, 230, 255))
            fb.lifetime = 90
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_charge(self, player):
        self.state = "CHARGE"; self.state_timer = 45
        self._cd["charge"] = 400 if self.phase < 3 else 280
        dx = player.rect.centerx - self.rect.centerx
        self.charge_dir = 1 if dx > 0 else -1
        self.facing = self.charge_dir
        self.velocity_x = 0

    def _do_crack(self, game):
        self.state = "CRACK"; self.state_timer = 50
        self._cd["crack"] = 480 if self.phase < 3 else 320
        for _ in range(3):
            x = random.randint(80, SCREEN_WIDTH - 80)
            w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=40, radius=45, spawn_type="spike")
            game.warnings.add(w); game.all_sprites.add(w)

    def _do_ice_field(self, game):
        self.state = "ICE_FIELD"; self.state_timer = 480
        self._cd["ice_field"] = 840
        game.ice_field_timer = 480
        for _ in range(2):
            x = random.randint(80, SCREEN_WIDTH - 80)
            trap = IceTrap(x, SCREEN_HEIGHT - 40)
            game.traps.add(trap); game.all_sprites.add(trap)
        if len(game.enemies) < 5:
            for _ in range(3):
                x = random.randint(100, SCREEN_WIDTH - 100)
                circle = SummonCircle(x, SCREEN_HEIGHT - 45, 5, BIOME_ICE, self.depth, delay=60)
                game.summon_circles.add(circle); game.all_sprites.add(circle)

    def _do_shield(self):
        self.state = "SHIELD"; self.state_timer = 300
        self._cd["shield"] = 1200
        self.shield_active = True
        self.shield_hp = 150
        self.shield_timer = 300


class MoltenGiantBoss(BaseBoss):
    BOSS_NAME = BOSS_NAMES[BOSS_MOLTEN_GIANT]
    BASE_HEALTH = 1000; HEALTH_SCALE = 100; BASE_SPEED = 0.3
    SHIELD_COLOR = (255, 140, 60)
    HP_COLORS = (FIRE_ORANGE, (255, 90, 20), (255, 240, 120))
    PHASE_NOVA_COLOR = FIRE_ORANGE

    def _setup(self):
        self._cd = {"slam": 240, "erupt": 300, "boulder": 360, "lava_wall": 480,
                    "shield": 900, "summon": 420}
        self.core_exposed = False
        self.explode_timer = -1
        self.lava_step_timer = 0
        self.safe_zone_timer = 0

    def create_boss_image(self):
        W, H = 150, 170
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 130), (8, H - 8, W - 16, 8))
        pygame.draw.polygon(surf, (30, 20, 20), [(28, 100), (54, 100), (58, H - 8), (22, H - 8)])
        pygame.draw.polygon(surf, (30, 20, 20), [(W - 54, 100), (W - 28, 100), (W - 22, H - 8), (W - 58, H - 8)])
        pygame.draw.polygon(surf, OUTLINE, [(28, 100), (54, 100), (58, H - 8), (22, H - 8)], 2)
        pygame.draw.polygon(surf, OUTLINE, [(W - 54, 100), (W - 28, 100), (W - 22, H - 8), (W - 58, H - 8)], 2)
        pygame.draw.polygon(surf, (45, 30, 25), [(22, 44), (W - 22, 44), (W - 18, 108), (18, 108)])
        pygame.draw.polygon(surf, OUTLINE, [(22, 44), (W - 22, 44), (W - 18, 108), (18, 108)], 2)
        for i in range(5):
            y = 52 + i * 12
            pygame.draw.line(surf, FIRE_ORANGE, (28, y), (W - 28, y - 3), 2)
            pygame.draw.line(surf, FIRE_YELLOW, (28, y), (W - 28, y - 3), 1)
        pygame.draw.polygon(surf, (35, 22, 18), [(18, 46), (36, 40), (40, 60), (22, 66)])
        pygame.draw.polygon(surf, OUTLINE, [(18, 46), (36, 40), (40, 60), (22, 66)], 2)
        pygame.draw.polygon(surf, (35, 22, 18), [(W - 18, 46), (W - 36, 40), (W - 40, 60), (W - 22, 66)])
        pygame.draw.polygon(surf, OUTLINE, [(W - 18, 46), (W - 36, 40), (W - 40, 60), (W - 22, 66)], 2)
        pygame.draw.polygon(surf, (50, 32, 25), [(16, 52), (2, 58), (4, 100), (22, 96)])
        pygame.draw.polygon(surf, (50, 32, 25), [(W - 16, 52), (W - 2, 58), (W - 4, 100), (W - 22, 96)])
        pygame.draw.polygon(surf, OUTLINE, [(16, 52), (2, 58), (4, 100), (22, 96)], 2)
        pygame.draw.polygon(surf, OUTLINE, [(W - 16, 52), (W - 2, 58), (W - 4, 100), (W - 22, 96)], 2)
        pygame.draw.circle(surf, (35, 22, 18), (10, 100), 10)
        pygame.draw.circle(surf, (35, 22, 18), (W - 10, 100), 10)
        pygame.draw.circle(surf, OUTLINE, (10, 100), 10, 2)
        pygame.draw.circle(surf, OUTLINE, (W - 10, 100), 10, 2)
        core_visible = (self.phase >= 2) or self.core_exposed
        if core_visible:
            core_col = FIRE_YELLOW if self.phase < 3 else (255, 240, 120)
            draw_glow(surf, core_col, (W // 2, 76), 30, 180)
            pygame.draw.circle(surf, FIRE_RED, (W // 2, 76), 20)
            pygame.draw.circle(surf, FIRE_ORANGE, (W // 2, 76), 14)
            pygame.draw.circle(surf, FIRE_YELLOW, (W // 2, 76), 8)
            pygame.draw.circle(surf, (255, 255, 240), (W // 2, 76), 3)
            pygame.draw.circle(surf, OUTLINE, (W // 2, 76), 20, 2)
        else:
            pygame.draw.circle(surf, (50, 20, 15), (W // 2, 76), 20)
            pygame.draw.circle(surf, OUTLINE, (W // 2, 76), 20, 2)
            pygame.draw.line(surf, FIRE_ORANGE, (W // 2 - 12, 62), (W // 2, 76), 2)
            pygame.draw.line(surf, FIRE_ORANGE, (W // 2, 76), (W // 2 + 10, 90), 2)
        pygame.draw.polygon(surf, (40, 25, 20), [(W // 2 - 22, 12), (W // 2 + 22, 12), (W // 2 + 18, 46), (W // 2 - 18, 46)])
        pygame.draw.polygon(surf, OUTLINE, [(W // 2 - 22, 12), (W // 2 + 22, 12), (W // 2 + 18, 46), (W // 2 - 18, 46)], 2)
        eye = FIRE_YELLOW if self.phase < 3 else (255, 255, 200)
        pygame.draw.circle(surf, eye, (W // 2 - 10, 28), 4)
        pygame.draw.circle(surf, eye, (W // 2 + 10, 28), 4)
        draw_glow(surf, FIRE_ORANGE, (W // 2 - 10, 28), 10, 120)
        draw_glow(surf, FIRE_ORANGE, (W // 2 + 10, 28), 10, 120)
        for i in range(3):
            x = W // 2 - 14 + i * 14
            h = 12 + (i % 2) * 6
            pygame.draw.polygon(surf, FIRE_ORANGE, [(x, 12), (x + 4, 12 - h), (x + 8, 12)])
            pygame.draw.polygon(surf, FIRE_YELLOW, [(x + 2, 12), (x + 4, 12 - h + 4), (x + 6, 12)])
        return surf

    def apply_damage(self, damage, game=None):
        if self.phase >= 2:
            damage = int(damage * 1.5)
        # 自爆蓄力期间受伤翻倍
        if self.phase == 3 and self.explode_timer > 0:
            damage = int(damage * 2)
        self.health -= damage
        return damage

    def update(self, player, platforms, barriers, game):
        if self.phase == 3 and self.explode_timer < 0:
            self.explode_timer = 15 * FPS
            game.show_message("熔岩巨人即将自爆！快击杀它！(伤害翻倍)", 2500)
        if self.phase == 3 and self.explode_timer >= 0:
            self.explode_timer -= 1
            if self.explode_timer <= 0:
                # 改为贴地全屏横波：跳跃躲避。地面横波只覆盖地面高度
                ground_y = SCREEN_HEIGHT - 30
                for d in (-1, 1):
                    gw = GroundWave(SCREEN_WIDTH // 2, ground_y, d,
                                    speed=10, width=80, height=32,
                                    damage=int(40 * self.dmg_mult),
                                    color=FIRE_ORANGE, lifetime=200)
                    game.ground_waves.add(gw); game.all_sprites.add(gw)
                # 地面上也生成岩浆池但位置靠边
                for _ in range(5):
                    x = random.choice([80, 160, SCREEN_WIDTH - 80, SCREEN_WIDTH - 160])
                    pool = LavaPool(x, SCREEN_HEIGHT - 25, duration=300, damage=6)
                    game.lava_pools.add(pool); game.all_sprites.add(pool)
                game.kill_boss()
                return
        if self.phase >= 2:
            self.lava_step_timer += 1
            if self.lava_step_timer >= 90:
                self.lava_step_timer = 0
                pool = LavaPool(self.rect.centerx, SCREEN_HEIGHT - 25, duration=180, damage=4)
                game.lava_pools.add(pool); game.all_sprites.add(pool)
        super().update(player, platforms, barriers, game)

    def state_update(self, player, platforms, barriers, game):
        if self.state in ("SLAM", "ERUPT", "BOULDER", "LAVA_WALL", "SUMMON", "SHIELD"):
            self.state_timer -= 1
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state == "SHIELD" and not self.shield_active:
                self.state = "IDLE"; self.action_cooldown = 30
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        return False

    def try_cast(self, player, game, dist):
        if self.phase >= 3 and self.explode_timer > 0 and self.explode_timer < 300:
            if self._cd["summon"] <= 0 and len(game.enemies) < 6:
                self._do_summon(game); return True
        if dist < 220 and self._cd["slam"] <= 0:
            self._do_slam(game); return True
        if self._cd["erupt"] <= 0:
            self._do_erupt(game, player); return True
        if self._cd["boulder"] <= 0:
            self._do_boulder(game, player); return True
        if self.phase >= 2 and self._cd["lava_wall"] <= 0:
            self._do_lava_wall(game, player); return True
        if self.phase >= 2 and self._cd["shield"] <= 0 and self.health < self.max_health * 0.65:
            self._do_shield(); return True
        if self._cd["summon"] <= 0 and len(game.enemies) < 4:
            self._do_summon(game); return True
        return False

    def _do_slam(self, game):
        self.state = "SLAM"; self.state_timer = 40
        self._cd["slam"] = 320 if self.phase < 3 else 220
        cx = self.rect.centerx
        cy = self.rect.centery
        dmg = int(10 * self.dmg_mult)
        for off in (-0.3, 0, 0.3):
            fb = Fireball(cx, cy + 20, math.cos(off) * 8 * self.facing, math.sin(off) * 4,
                          damage=dmg, color=FIRE_ORANGE)
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_erupt(self, game, player):
        self.state = "ERUPT"; self.state_timer = 60
        self._cd["erupt"] = 400 if self.phase < 3 else 260
        count = 3 if self.phase == 1 else (4 if self.phase == 2 else 5)
        for _ in range(count):
            x = random.randint(60, SCREEN_WIDTH - 60)
            w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=40, radius=50, spawn_type="spike")
            game.warnings.add(w); game.all_sprites.add(w)

    def _do_boulder(self, game, player):
        self.state = "BOULDER"; self.state_timer = 40
        self._cd["boulder"] = 420
        cx = self.rect.centerx; cy = self.rect.centery - 20
        px = player.rect.centerx; py = player.rect.centery
        base = math.atan2(py - cy, px - cx)
        for off in (-0.15, 0.15):
            a = base + off
            fb = Fireball(cx, cy, math.cos(a) * 8, math.sin(a) * 8,
                          damage=int(12 * self.dmg_mult), color=(120, 60, 40))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_lava_wall(self, game, player):
        self.state = "LAVA_WALL"; self.state_timer = 50
        self._cd["lava_wall"] = 600
        direction = 1 if player.rect.centerx > self.rect.centerx else -1
        ground_y = SCREEN_HEIGHT - 30
        speed = 2.4 if self.phase == 2 else 3.0
        wall = FlameWall(self.rect.centerx, ground_y, direction, speed=speed,
                         damage=int(9 * self.dmg_mult))
        game.flame_walls.add(wall); game.all_sprites.add(wall)

    def _do_summon(self, game):
        self.state = "SUMMON"; self.state_timer = 45
        self._cd["summon"] = 480 if self.phase < 3 else 240
        count = 2 if self.phase == 1 else (3 if self.phase == 2 else 4)
        for _ in range(count):
            x = random.randint(80, SCREEN_WIDTH - 80)
            y = SCREEN_HEIGHT - 30
            circle = SummonCircle(x, y - 15, 8, BIOME_LAVA, self.depth, delay=45)
            game.summon_circles.add(circle); game.all_sprites.add(circle)

    def _do_shield(self):
        self.state = "SHIELD"; self.state_timer = 300
        self._cd["shield"] = 1200
        self.shield_active = True
        self.shield_hp = 150
        self.shield_timer = 300


class InfernalDemonBoss(BaseBoss):
    BOSS_NAME = BOSS_NAMES[BOSS_INFERNAL_DEMON]
    BASE_HEALTH = 750; HEALTH_SCALE = 75; BASE_SPEED = 1.2
    SHIELD_COLOR = (255, 90, 60)
    HP_COLORS = ((255, 130, 60), (220, 60, 30), (255, 200, 80))
    PHASE_NOVA_COLOR = FIRE_RED
    IS_FLYING = True

    def _setup(self):
        self._cd = {"tri_fireball": 180, "dive": 240, "wall": 360, "clone": 540,
                    "rain": 480, "chain": 600, "ring": 420}
        self.dive_target_y = 0
        self.chain_active = False

    def create_boss_image(self):
        W, H = 120, 130
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (90, 20, 20), [(10, 40), (0, 10), (22, 22), (30, 45), (22, 70), (10, 90)])
        pygame.draw.polygon(surf, (90, 20, 20), [(W - 10, 40), (W, 10), (W - 22, 22), (W - 30, 45), (W - 22, 70), (W - 10, 90)])
        pygame.draw.polygon(surf, OUTLINE, [(10, 40), (0, 10), (22, 22), (30, 45), (22, 70), (10, 90)], 2)
        pygame.draw.polygon(surf, OUTLINE, [(W - 10, 40), (W, 10), (W - 22, 22), (W - 30, 45), (W - 22, 70), (W - 10, 90)], 2)
        pygame.draw.polygon(surf, (130, 30, 20), [(30, 40), (W - 30, 40), (W - 26, 100), (26, 100)])
        pygame.draw.polygon(surf, OUTLINE, [(30, 40), (W - 30, 40), (W - 26, 100), (26, 100)], 2)
        for i in range(4):
            y = 50 + i * 12
            pygame.draw.line(surf, FIRE_ORANGE, (32, y), (W - 32, y), 2)
            pygame.draw.line(surf, FIRE_YELLOW, (32, y), (W - 32, y), 1)
        core = FIRE_YELLOW if self.phase < 3 else (255, 200, 60)
        draw_glow(surf, core, (W // 2, 70), 22, 150)
        pygame.draw.circle(surf, FIRE_RED, (W // 2, 70), 14)
        pygame.draw.circle(surf, FIRE_ORANGE, (W // 2, 70), 9)
        pygame.draw.circle(surf, (255, 240, 200), (W // 2, 70), 4)
        pygame.draw.circle(surf, OUTLINE, (W // 2, 70), 14, 2)
        pygame.draw.circle(surf, (140, 40, 25), (W // 2, 28), 22)
        pygame.draw.circle(surf, OUTLINE, (W // 2, 28), 22, 2)
        pygame.draw.polygon(surf, (60, 20, 15), [(W // 2 - 14, 12), (W // 2 - 22, -4), (W // 2 - 8, 10)])
        pygame.draw.polygon(surf, (60, 20, 15), [(W // 2 + 14, 12), (W // 2 + 22, -4), (W // 2 + 8, 10)])
        pygame.draw.polygon(surf, OUTLINE, [(W // 2 - 14, 12), (W // 2 - 22, -4), (W // 2 - 8, 10)], 2)
        pygame.draw.polygon(surf, OUTLINE, [(W // 2 + 14, 12), (W // 2 + 22, -4), (W // 2 + 8, 10)], 2)
        eye = FIRE_YELLOW if self.phase < 3 else (255, 255, 200)
        pygame.draw.circle(surf, eye, (W // 2 - 7, 26), 3)
        pygame.draw.circle(surf, eye, (W // 2 + 7, 26), 3)
        draw_glow(surf, FIRE_ORANGE, (W // 2 - 7, 26), 9, 120)
        draw_glow(surf, FIRE_ORANGE, (W // 2 + 7, 26), 9, 120)
        pygame.draw.line(surf, (80, 50, 25), (W - 6, 50), (W - 6, 110), 4)
        pygame.draw.polygon(surf, (200, 200, 220), [(W - 12, 40), (W - 6, 30), (W, 40), (W - 6, 50), (W - 12, 40)])
        pygame.draw.polygon(surf, OUTLINE, [(W - 12, 40), (W - 6, 30), (W, 40), (W - 6, 50), (W - 12, 40)], 2)
        return surf

    def state_update(self, player, platforms, barriers, game):
        if self.state == "DIVE":
            self.rect.y += 14
            if pygame.sprite.collide_rect(self, player):
                player.take_damage(12 * self.dmg_mult, source='boss')
                player.velocity_y = -8
            if self.rect.bottom >= SCREEN_HEIGHT - 30:
                self.rect.bottom = SCREEN_HEIGHT - 30
                # 落地改为左右两道贴地横波（跳跃躲）
                ground_y = SCREEN_HEIGHT - 30
                for d in (-1, 1):
                    gw = GroundWave(self.rect.centerx, ground_y, d,
                                    speed=7, width=64, height=28,
                                    damage=int(8 * self.dmg_mult),
                                    color=FIRE_RED, lifetime=140)
                    game.ground_waves.add(gw); game.all_sprites.add(gw)
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "CHAIN":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state in ("TRI_FIREBALL", "WALL", "CLONE", "RAIN", "RING"):
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        return False

    def try_cast(self, player, game, dist):
        if self._cd["dive"] <= 0 and dist < 300:
            self._do_dive(player); return True
        if self.phase >= 3 and self._cd["chain"] <= 0:
            self._do_chain(player, game); return True
        if self.phase >= 3 and self._cd["ring"] <= 0:
            self._do_ring(game); return True
        if self.phase >= 2 and self._cd["rain"] <= 0:
            self._do_rain(game); return True
        if self.phase >= 2 and self._cd["clone"] <= 0:
            self._do_clone(game); return True
        if self._cd["wall"] <= 0:
            self._do_wall(game, player); return True
        if self._cd["tri_fireball"] <= 0:
            self._do_tri_fireball(game, player); return True
        return False

    def _do_tri_fireball(self, game, player):
        self.state = "TRI_FIREBALL"; self.state_timer = 30
        self._cd["tri_fireball"] = 200 if self.phase == 1 else (150 if self.phase == 2 else 100)
        cx = self.rect.centerx; cy = self.rect.centery
        px = player.rect.centerx; py = player.rect.centery
        base = math.atan2(py - cy, px - cx)
        count = 3 if self.phase == 1 else (5 if self.phase == 2 else 7)
        spread = 0.18 if self.phase == 1 else (0.22 if self.phase == 2 else 0.26)
        dmg = int(9 * self.dmg_mult)
        for i in range(count):
            a = base + (i - (count - 1) / 2) * spread
            fb = Fireball(cx, cy, math.cos(a) * 7, math.sin(a) * 7,
                          damage=dmg, color=FIRE_ORANGE)
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_dive(self, player):
        self.state = "DIVE"; self.state_timer = 60
        self._cd["dive"] = 300 if self.phase < 3 else 200
        self.rect.y -= 20

    def _do_wall(self, game, player):
        self.state = "WALL"; self.state_timer = 40
        self._cd["wall"] = 420
        direction = 1 if player.rect.centerx > self.rect.centerx else -1
        ground_y = SCREEN_HEIGHT - 30
        wall = FlameWall(self.rect.centerx, ground_y, direction, speed=2.6,
                         damage=int(8 * self.dmg_mult))
        game.flame_walls.add(wall); game.all_sprites.add(wall)

    def _do_clone(self, game):
        self.state = "CLONE"; self.state_timer = 40
        self._cd["clone"] = 600
        for _ in range(3):
            x = random.randint(80, SCREEN_WIDTH - 80)
            y = random.randint(100, SCREEN_HEIGHT - 200)
            ember = EmberMinion(x, y, self.depth)
            game.embers.add(ember); game.all_sprites.add(ember); game.enemies.add(ember)

    def _do_rain(self, game):
        self.state = "RAIN"; self.state_timer = 50
        self._cd["rain"] = 540
        count = 5 if self.phase == 2 else 7
        for _ in range(count):
            x = random.randint(60, SCREEN_WIDTH - 60)
            w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=40, radius=45, spawn_type="meteor")
            game.warnings.add(w); game.all_sprites.add(w)

    def _do_chain(self, player, game):
        self.state = "CHAIN"; self.state_timer = 40
        self._cd["chain"] = 600
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        d = math.hypot(dx, dy) or 1
        fb = Fireball(self.rect.centerx, self.rect.centery,
                      dx / d * 10, dy / d * 10, damage=int(6 * self.dmg_mult),
                      color=(200, 200, 240))
        fb.lifetime = 60
        game.fireballs.add(fb); game.all_sprites.add(fb)
        if abs(dx) < 200 and abs(dy) < 200:
            player.slow_timer = max(player.slow_timer, 120)

    def _do_ring(self, game):
        """改为双层火环：上下各一圈环波，中间有安全缝隙。"""
        self.state = "RING"; self.state_timer = 40
        self._cd["ring"] = 480
        cx, cy = self.rect.centerx, self.rect.centery
        dmg = int(10 * self.dmg_mult)
        # 上方波
        w1 = NovaWave(cx, cy - 60, max_radius=240, delay=30, damage=dmg, speed=7,
                      small=True, color=FIRE_RED)
        game.nova_waves.add(w1); game.all_sprites.add(w1)
        # 下方波
        w2 = NovaWave(cx, cy + 60, max_radius=240, delay=30, damage=dmg, speed=7,
                      small=True, color=FIRE_RED)
        game.nova_waves.add(w2); game.all_sprites.add(w2)


class PoisonQueenBoss(BaseBoss):
    BOSS_NAME = BOSS_NAMES[BOSS_POISON_QUEEN]
    BASE_HEALTH = 850; HEALTH_SCALE = 85; BASE_SPEED = 0.9
    SHIELD_COLOR = POISON_BRIGHT
    HP_COLORS = ((140, 220, 100), (100, 180, 60), (200, 255, 120))
    PHASE_NOVA_COLOR = POISON_BRIGHT

    def _setup(self):
        self._cd = {"summon": 320, "spore": 180, "pool": 300, "cloud": 240,
                    "nova": 400, "shield": 900}

    def create_boss_image(self):
        W, H = 124, 152
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 120), (10, H - 8, W - 20, 8))
        pygame.draw.polygon(surf, (25, 40, 20), [(28, 45), (8, H - 4), (W - 8, H - 4), (W - 28, 45)])
        pygame.draw.polygon(surf, (50, 90, 40), [(34, 50), (18, H - 8), (W - 18, H - 8), (W - 34, 50)])
        for i in range(3):
            x = 26 + i * 30
            pygame.draw.line(surf, POISON_GREEN, (x, H - 40), (x - 8, H - 4), 3)
            pygame.draw.line(surf, POISON_GREEN, (x, H - 40), (x + 8, H - 4), 3)
        for i in range(4):
            y = 62 + i * 18
            draw_glow(surf, POISON_BRIGHT, (44 + i * 12, y), 8, 100)
            pygame.draw.circle(surf, POISON_GREEN, (44 + i * 12, y), 6)
            pygame.draw.circle(surf, (220, 255, 180), (44 + i * 12, y), 3)
            pygame.draw.circle(surf, OUTLINE, (44 + i * 12, y), 6, 1)
        pygame.draw.rect(surf, (35, 60, 30), (30, 42, 64, 66))
        pygame.draw.rect(surf, OUTLINE, (30, 42, 64, 66), 2)
        pygame.draw.rect(surf, (40, 70, 30), (32, 5, 60, 46))
        pygame.draw.rect(surf, OUTLINE, (32, 5, 60, 46), 2)
        pygame.draw.rect(surf, (20, 35, 15), (38, 15, 48, 26))
        pygame.draw.rect(surf, OUTLINE, (38, 15, 48, 26), 2)
        eye = (200, 255, 100) if self.phase < 3 else (255, 255, 120)
        pygame.draw.circle(surf, eye, (48, 28), 5)
        pygame.draw.circle(surf, eye, (76, 28), 5)
        pygame.draw.circle(surf, (20, 30, 10), (48, 28), 2)
        pygame.draw.circle(surf, (20, 30, 10), (76, 28), 2)
        draw_glow(surf, eye, (48, 28), 10, 80)
        draw_glow(surf, eye, (76, 28), 10, 80)
        if self.phase == 1: core = (120, 220, 80)
        elif self.phase == 2: core = (80, 180, 40)
        else: core = (200, 255, 100)
        draw_glow(surf, core, (62, 76), 22, 120)
        pygame.draw.circle(surf, core, (62, 76), 15)
        pygame.draw.circle(surf, (240, 255, 200), (62, 76), 6)
        pygame.draw.circle(surf, OUTLINE, (62, 76), 15, 2)
        pygame.draw.ellipse(surf, (80, 140, 60), (20, -6, 84, 26))
        pygame.draw.ellipse(surf, (120, 190, 90), (22, -4, 80, 22))
        pygame.draw.ellipse(surf, OUTLINE, (20, -6, 84, 26), 2)
        for i in range(5):
            x = 32 + i * 14
            pygame.draw.circle(surf, POISON_BRIGHT, (x, 6), 3)
            pygame.draw.circle(surf, OUTLINE, (x, 6), 3, 1)
        return surf

    def state_update(self, player, platforms, barriers, game):
        if self.state in ("NOVA", "CAST", "SUMMON", "SHIELD"):
            self.state_timer -= 1
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state == "SHIELD" and not self.shield_active:
                self.state = "IDLE"; self.action_cooldown = 30
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        return False

    def try_cast(self, player, game, dist):
        if self._cd["nova"] <= 0: self._do_nova(game); return True
        if self.phase >= 2 and self._cd["pool"] <= 0: self._do_pool(game, player); return True
        if self._cd["spore"] <= 0: self._do_spore(game, player); return True
        if self.phase >= 2 and self._cd["cloud"] <= 0: self._do_cloud(game); return True
        if self.phase >= 2 and self._cd["shield"] <= 0 and self.health < self.max_health * 0.6:
            self._do_shield(); return True
        if self._cd["summon"] <= 0 and len(game.enemies) < 6: self._do_summon(game); return True
        return False

    def _do_nova(self, game):
        """改为 3 个缓慢扩大的毒圈。"""
        self.state = "NOVA"; self.state_timer = 50
        self._cd["nova"] = 460 if self.phase < 3 else 260
        cx, cy = self.rect.centerx, self.rect.centery
        dmg = int(4 * self.dmg_mult)
        count = 3 if self.phase == 1 else (4 if self.phase == 2 else 5)
        for i in range(count):
            offset_x = (i - (count - 1) / 2) * 140
            px = cx + offset_x
            px = max(60, min(px, SCREEN_WIDTH - 60))
            pool = LavaPool(px, SCREEN_HEIGHT - 25, duration=400, damage=dmg, color=POISON_GREEN)
            game.lava_pools.add(pool); game.all_sprites.add(pool)

    def _do_spore(self, game, player):
        self.state = "CAST"; self.state_timer = 40
        self._cd["spore"] = 220 if self.phase < 3 else 120
        cx = self.rect.centerx; cy = self.rect.centery - 20
        px = player.rect.centerx; py = player.rect.centery
        base_angle = math.atan2(py - cy, px - cx)
        count = 3 if self.phase == 1 else (5 if self.phase == 2 else 7)
        dmg = int(10 * self.dmg_mult)
        for i in range(count):
            a = base_angle + (i - (count - 1) / 2) * 0.22
            fb = Fireball(cx, cy, math.cos(a) * 6, math.sin(a) * 6, damage=dmg, color=POISON_BRIGHT)
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_pool(self, game, player):
        self.state = "CAST"; self.state_timer = 50
        self._cd["pool"] = 480 if self.phase < 3 else 300
        count = 2 if self.phase == 2 else 3
        dmg = int(5 * self.dmg_mult)
        for _ in range(count):
            x = random.randint(60, SCREEN_WIDTH - 60)
            pool = LavaPool(x, SCREEN_HEIGHT - 25, duration=300, damage=dmg, color=POISON_GREEN)
            game.lava_pools.add(pool); game.all_sprites.add(pool)

    def _do_cloud(self, game):
        self.state = "CAST"; self.state_timer = 60
        self._cd["cloud"] = 420
        dmg = int(6 * self.dmg_mult)
        for _ in range(6):
            x = random.randint(60, SCREEN_WIDTH - 60)
            y = random.randint(100, SCREEN_HEIGHT - 150)
            fb = Fireball(x, y, random.uniform(-2, 2), random.uniform(0.5, 2),
                          damage=dmg, color=POISON_BRIGHT)
            fb.lifetime = 300
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_summon(self, game):
        self.state = "SUMMON"; self.state_timer = 50
        self._cd["summon"] = 400 if self.phase < 3 else 240
        count = 2 if self.phase == 1 else (3 if self.phase == 2 else 4)
        for _ in range(count):
            x = random.randint(80, SCREEN_WIDTH - 80)
            y = SCREEN_HEIGHT - 30
            etype = random.choice([9, 10, 8])
            circle = SummonCircle(x, y - 15, etype, BIOME_POISON, self.depth, delay=60)
            game.summon_circles.add(circle); game.all_sprites.add(circle)

    def _do_shield(self):
        self.state = "SHIELD"; self.state_timer = 300
        self._cd["shield"] = 1200
        self.shield_active = True
        self.shield_hp = 150
        self.shield_timer = 300


class BoneDragonBoss(BaseBoss):
    BOSS_NAME = BOSS_NAMES[BOSS_BONE_DRAGON]
    BASE_HEALTH = 950; HEALTH_SCALE = 95; BASE_SPEED = 0.9
    SHIELD_COLOR = BONE_WHITE
    HP_COLORS = (BONE_WHITE, (200, 180, 220), GHOST_PURPLE)
    PHASE_NOVA_COLOR = GHOST_PURPLE
    IS_FLYING = True

    def _setup(self):
        self._cd = {"breath": 240, "tail_sweep": 300, "wing_spike": 220, "summon": 360,
                    "bone_spear": 480, "bone_burst": 300, "bone_rain": 540, "death_breath": 600}
        self.soul_energy = 0
        self.death_breath_charging = False

    def create_boss_image(self):
        W, H = 200, 140
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        wing_col = (220, 215, 200, 220)
        pygame.draw.polygon(surf, wing_col, [(20, 40), (0, 10), (30, 30), (60, 40), (30, 70), (10, 90)])
        pygame.draw.polygon(surf, wing_col, [(W - 20, 40), (W, 10), (W - 30, 30), (W - 60, 40), (W - 30, 70), (W - 10, 90)])
        pygame.draw.polygon(surf, OUTLINE, [(20, 40), (0, 10), (30, 30), (60, 40), (30, 70), (10, 90)], 2)
        pygame.draw.polygon(surf, OUTLINE, [(W - 20, 40), (W, 10), (W - 30, 30), (W - 60, 40), (W - 30, 70), (W - 10, 90)], 2)
        for i in range(4):
            offset = i * 12
            pygame.draw.line(surf, (200, 195, 180), (30 + offset, 40), (10 + offset, 80), 2)
            pygame.draw.line(surf, (200, 195, 180), (W - 30 - offset, 40), (W - 10 - offset, 80), 2)
        pygame.draw.polygon(surf, (230, 225, 205), [(60, 55), (W - 60, 55), (W - 50, 95), (50, 95)])
        pygame.draw.polygon(surf, OUTLINE, [(60, 55), (W - 60, 55), (W - 50, 95), (50, 95)], 2)
        for i in range(6):
            x = 70 + i * 12
            pygame.draw.line(surf, (180, 175, 160), (x, 58), (x - 2, 92), 2)
        core = GHOST_PURPLE if self.phase < 3 else (255, 120, 240)
        draw_glow(surf, core, (W // 2, 76), 22, 150)
        pygame.draw.circle(surf, core, (W // 2, 76), 14)
        pygame.draw.circle(surf, (255, 255, 255), (W // 2, 76), 5)
        pygame.draw.circle(surf, OUTLINE, (W // 2, 76), 14, 2)
        head_cx = W // 2
        pygame.draw.polygon(surf, (230, 225, 205), [
            (head_cx - 30, 30), (head_cx + 30, 30), (head_cx + 26, 60), (head_cx - 26, 60)])
        pygame.draw.polygon(surf, OUTLINE, [
            (head_cx - 30, 30), (head_cx + 30, 30), (head_cx + 26, 60), (head_cx - 26, 60)], 2)
        pygame.draw.polygon(surf, (200, 195, 180), [
            (head_cx + 26, 44), (head_cx + 40, 48), (head_cx + 38, 56), (head_cx + 24, 56)])
        pygame.draw.polygon(surf, OUTLINE, [
            (head_cx + 26, 44), (head_cx + 40, 48), (head_cx + 38, 56), (head_cx + 24, 56)], 2)
        eye = (255, 60, 60) if self.phase < 3 else GHOST_PURPLE
        pygame.draw.ellipse(surf, (15, 10, 20), (head_cx - 18, 38, 12, 10))
        pygame.draw.ellipse(surf, (15, 10, 20), (head_cx + 6, 38, 12, 10))
        pygame.draw.circle(surf, eye, (head_cx - 12, 43), 3)
        pygame.draw.circle(surf, eye, (head_cx + 12, 43), 3)
        draw_glow(surf, eye, (head_cx - 12, 43), 10, 100)
        draw_glow(surf, eye, (head_cx + 12, 43), 10, 100)
        pygame.draw.polygon(surf, (220, 215, 200), [(head_cx - 22, 30), (head_cx - 30, 8), (head_cx - 12, 28)])
        pygame.draw.polygon(surf, (220, 215, 200), [(head_cx + 22, 30), (head_cx + 30, 8), (head_cx + 12, 28)])
        pygame.draw.polygon(surf, OUTLINE, [(head_cx - 22, 30), (head_cx - 30, 8), (head_cx - 12, 28)], 2)
        pygame.draw.polygon(surf, OUTLINE, [(head_cx + 22, 30), (head_cx + 30, 8), (head_cx + 12, 28)], 2)
        for i in range(5):
            x = 60 - i * 10
            pygame.draw.circle(surf, (200, 195, 180), (x, 80 + i * 2), 4 - i // 2)
            pygame.draw.circle(surf, OUTLINE, (x, 80 + i * 2), 4 - i // 2, 1)
        return surf

    def apply_damage(self, damage, game=None):
        self.health -= damage
        return damage

    def on_minion_death(self):
        self.soul_energy += 1
        if self.soul_energy >= 5:
            self.soul_energy = 0
            heal = int(self.max_health * 0.03)
            self.health = min(self.health + heal, self.max_health)

    def state_update(self, player, platforms, barriers, game):
        if self.state == "DEATH_BREATH":
            self.state_timer -= 1
            if self.death_breath_charging:
                # 破防槽逻辑
                if self.break_broken:
                    # 被打破
                    self.death_breath_charging = False
                    self.break_gauge_max = 0
                    self.state = "STUNNED"; self.state_timer = 180
                    game.show_message("死亡龙息被打断！骨龙陷入硬直！", 1800)
                    # 额外奖励强化
                    game.reward_points += 1
                    return True
            if self.state_timer <= 0:
                # 释放贯穿龙息
                dmg = int(40 * self.dmg_mult)
                if not game.player.shield_active:
                    dx = game.player.rect.centerx - self.rect.centerx
                    dy = game.player.rect.centery - self.rect.centery
                    if abs(dx) < 300 and abs(dy) < 200:
                        game.player.take_damage(dmg, source='boss')
                for i in range(10):
                    x = self.rect.centerx + (i - 5) * 40
                    fb = Fireball(x, self.rect.centery, 0, 10, damage=0, color=(180, 120, 240))
                    fb.lifetime = 30
                    game.fireballs.add(fb); game.all_sprites.add(fb)
                w = NovaWave(self.rect.centerx, self.rect.centery, max_radius=400,
                             delay=0, damage=0, speed=10, color=GHOST_PURPLE)
                game.nova_waves.add(w); game.all_sprites.add(w)
                self.death_breath_charging = False
                self.break_gauge_max = 0
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "STUNNED":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state in ("BREATH", "TAIL", "WING", "SUMMON", "SPEAR", "BURST", "RAIN"):
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        return False

    def try_cast(self, player, game, dist):
        if self.phase >= 3 and self._cd["death_breath"] <= 0:
            self._do_death_breath(game); return True
        if self.phase >= 3 and self._cd["bone_rain"] <= 0:
            self._do_bone_rain(game); return True
        if self.phase >= 2 and self._cd["bone_burst"] <= 0:
            self._do_bone_burst(game); return True
        if self.phase >= 2 and self._cd["bone_spear"] <= 0:
            self._do_bone_spear(game, player); return True
        if self.phase >= 2 and self._cd["summon"] <= 0 and len(game.enemies) < 5:
            self._do_summon(game); return True
        if self._cd["wing_spike"] <= 0:
            self._do_wing_spike(game, player); return True
        if dist < 220 and self._cd["tail_sweep"] <= 0:
            self._do_tail_sweep(game); return True
        if self._cd["breath"] <= 0:
            self._do_breath(game, player); return True
        return False

    def _do_breath(self, game, player):
        self.state = "BREATH"; self.state_timer = 40
        self._cd["breath"] = 280 if self.phase < 3 else 180
        cx = self.rect.centerx; cy = self.rect.centery
        px = player.rect.centerx; py = player.rect.centery
        base = math.atan2(py - cy, px - cx)
        count = 3 if self.phase == 1 else 5
        dmg = int(9 * self.dmg_mult)
        for i in range(count):
            a = base + (i - (count - 1) / 2) * 0.2
            fb = Fireball(cx, cy, math.cos(a) * 7, math.sin(a) * 7,
                          damage=dmg, color=(180, 120, 240))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_tail_sweep(self, game):
        self.state = "TAIL"; self.state_timer = 40
        self._cd["tail_sweep"] = 360
        cx = self.rect.centerx; cy = self.rect.centery
        dmg = int(10 * self.dmg_mult)
        for off in (-0.5, 0, 0.5):
            fb = Fireball(cx, cy, math.cos(off) * 7 * (-self.facing), math.sin(off) * 4,
                          damage=dmg, color=(200, 190, 220))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_wing_spike(self, game, player):
        self.state = "WING"; self.state_timer = 30
        self._cd["wing_spike"] = 260
        cx = self.rect.centerx; cy = self.rect.centery
        px = player.rect.centerx; py = player.rect.centery
        base = math.atan2(py - cy, px - cx)
        dmg = int(8 * self.dmg_mult)
        for i in range(5):
            a = base + (i - 2) * 0.18
            fb = Fireball(cx, cy, math.cos(a) * 9, math.sin(a) * 9,
                          damage=dmg, color=(220, 210, 240))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_summon(self, game):
        self.state = "SUMMON"; self.state_timer = 50
        self._cd["summon"] = 420
        for _ in range(3):
            x = random.randint(80, SCREEN_WIDTH - 80)
            y = SCREEN_HEIGHT - 60
            etype = random.choice([11, 12])
            circle = SummonCircle(x, y - 15, etype, BIOME_TOMB, self.depth, delay=50)
            game.summon_circles.add(circle); game.all_sprites.add(circle)

    def _do_bone_spear(self, game, player):
        self.state = "SPEAR"; self.state_timer = 40
        self._cd["bone_spear"] = 540
        count = 4 if self.phase == 2 else 6
        for _ in range(count):
            x = random.randint(60, SCREEN_WIDTH - 60)
            w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=40, radius=50, spawn_type="bone")
            game.warnings.add(w); game.all_sprites.add(w)

    def _do_bone_burst(self, game):
        self.state = "BURST"; self.state_timer = 30
        self._cd["bone_burst"] = 360
        cx = self.rect.centerx; cy = self.rect.centery
        dmg = int(8 * self.dmg_mult)
        for i in range(8):
            a = math.pi * 2 * i / 8
            fb = Fireball(cx, cy, math.cos(a) * 7, math.sin(a) * 7,
                          damage=dmg, color=(220, 210, 240))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_bone_rain(self, game):
        self.state = "RAIN"; self.state_timer = 50
        self._cd["bone_rain"] = 600
        for _ in range(10):
            x = random.randint(50, SCREEN_WIDTH - 50)
            w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=40, radius=40, spawn_type="bone")
            game.warnings.add(w); game.all_sprites.add(w)

    def _do_death_breath(self, game):
        self.state = "DEATH_BREATH"; self.state_timer = 240  # 4 秒蓄力
        self._cd["death_breath"] = 720
        self.death_breath_charging = True
        self.start_break_gauge(max(120, self.max_health * 0.12))
        game.show_message("骷髅骨龙蓄力死亡龙息！打满破防槽可打断！", 2200)


class StitchedBoss(BaseBoss):
    """由本局死掉的敌人部件拼成的领主：杀得越多，它拼得越大、越硬。"""

    BOSS_NAME = BOSS_NAMES[BOSS_STITCHED]
    BASE_HEALTH = 820; HEALTH_SCALE = 82; BASE_SPEED = 0.7
    SHIELD_COLOR = (175, 150, 225)
    HP_COLORS = ((205, 180, 240), (152, 110, 205), (118, 58, 160))
    PHASE_NOVA_COLOR = (165, 125, 205)

    PATCH_COLORS = [(158, 62, 62), (72, 152, 92), (176, 142, 92), (92, 112, 184)]

    def _setup(self):
        self._cd = {"slam": 320, "parts": 260, "summon": 430, "spikes": 470}
        self.stitch_bonus = 0

    def apply_kill_power(self, kills):
        """血量随本局累计击杀数膨胀（每杀 1 个 +7，最多 +1050）。"""
        self.stitch_bonus = min(150, max(0, int(kills))) * 7
        self.max_health += self.stitch_bonus
        self.health = self.max_health
        self.refresh_image()

    def create_boss_image(self):
        W, H = 128, 154
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 120), (14, H - 10, W - 28, 10))
        # 腿：一条骨架腿 + 一条粗腿
        pygame.draw.rect(surf, (120, 116, 140), (40, 104, 18, 44), border_radius=6)
        pygame.draw.rect(surf, OUTLINE, (40, 104, 18, 44), 2, border_radius=6)
        pygame.draw.rect(surf, (86, 64, 108), (72, 104, 22, 44), border_radius=6)
        pygame.draw.rect(surf, OUTLINE, (72, 104, 22, 44), 2, border_radius=6)
        # 躯干
        pygame.draw.rect(surf, (72, 54, 96), (26, 44, 76, 68), border_radius=12)
        pygame.draw.rect(surf, (100, 76, 126), (31, 48, 66, 60), border_radius=10)
        # 来自不同敌人的补丁块
        patch_count = 4 if self.stitch_bonus < 400 else (6 if self.stitch_bonus < 900 else 7)
        spots = [(-4, 54, 28, 22), (22, 82, 30, 20), (0, 96, 26, 18),
                 (34, 58, 22, 16), (8, 74, 20, 14), (30, 100, 20, 14), (46, 76, 18, 16)]
        for i in range(min(patch_count, len(spots))):
            px, py, pw, ph = spots[i]
            color = self.PATCH_COLORS[i % len(self.PATCH_COLORS)]
            box = (34 + px, py, pw, ph)
            pygame.draw.rect(surf, color, box, border_radius=5)
            pygame.draw.rect(surf, OUTLINE, box, 2, border_radius=5)
        # 缝合线
        seam = (238, 214, 126)
        for i in range(4):
            y = 60 + i * 15
            pygame.draw.line(surf, seam, (38, y), (88, y), 2)
            pygame.draw.line(surf, seam, (42, y - 4), (42, y + 4), 2)
            pygame.draw.line(surf, seam, (84, y - 4), (84, y + 4), 2)
        # 手臂
        pygame.draw.rect(surf, (86, 150, 96), (10, 50, 18, 40), border_radius=7)
        pygame.draw.rect(surf, OUTLINE, (10, 50, 18, 40), 2, border_radius=7)
        pygame.draw.rect(surf, (150, 60, 60), (100, 48, 20, 44), border_radius=7)
        pygame.draw.rect(surf, OUTLINE, (100, 48, 20, 44), 2, border_radius=7)
        pygame.draw.circle(surf, (200, 90, 90), (110, 96), 11)
        pygame.draw.circle(surf, OUTLINE, (110, 96), 11, 2)
        pygame.draw.circle(surf, (200, 90, 90), (10, 94), 11)
        pygame.draw.circle(surf, OUTLINE, (10, 94), 11, 2)
        # 头：半张骷髅半张人脸
        pygame.draw.circle(surf, (206, 200, 178), (48, 28), 22)
        pygame.draw.circle(surf, OUTLINE, (48, 28), 22, 2)
        pygame.draw.rect(surf, (150, 60, 60), (48, 10, 24, 18), border_radius=6)
        pygame.draw.rect(surf, OUTLINE, (48, 10, 24, 18), 2, border_radius=6)
        pygame.draw.circle(surf, (40, 20, 30), (40, 26), 5)
        pygame.draw.circle(surf, (40, 20, 30), (58, 26), 5)
        eye = (255, 90, 110) if self.phase < 3 else (255, 160, 170)
        pygame.draw.circle(surf, eye, (40, 26), 2)
        pygame.draw.circle(surf, eye, (58, 26), 2)
        draw_glow(surf, eye, (49, 26), 16, 90)
        for i in range(4):
            x = 40 + i * 6
            pygame.draw.line(surf, OUTLINE, (x, 34), (x, 40), 2)
        # 胸口缝合的核
        core = (190, 110, 235) if self.phase < 3 else (235, 150, 255)
        draw_glow(surf, core, (64, 76), 22, 110)
        pygame.draw.circle(surf, core, (64, 76), 9)
        pygame.draw.circle(surf, OUTLINE, (64, 76), 9, 2)
        return surf

    def state_update(self, player, platforms, barriers, game):
        if self.state == "SLAM":
            was_air = not self.on_ground
            self.rect.x += self.velocity_x
            self.rect.x = max(25, min(self.rect.x, SCREEN_WIDTH - self.rect.width - 25))
            self.apply_gravity(platforms)
            self.state_timer -= 1
            if was_air and self.on_ground:
                self._slam_impact(game)
                self.state = "IDLE"; self.action_cooldown = 45
                return True
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "PARTS":
            self.velocity_x = 0
            self.apply_gravity(platforms)
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 40
            return True
        if self.state == "SUMMON":
            self.velocity_x = 0
            self.apply_gravity(platforms)
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 50
            return True
        if self.state == "SPIKES":
            self.velocity_x = 0
            self.apply_gravity(platforms)
            self.state_timer -= 1
            if self.state_timer % 18 == 0:
                x = random.randint(60, SCREEN_WIDTH - 60)
                w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=30, radius=42,
                                  spawn_type="spike")
                game.warnings.add(w); game.all_sprites.add(w)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 55
            return True
        return False

    def try_cast(self, player, game, dist):
        if self.phase >= 2 and self._cd["spikes"] <= 0:
            self._do_spikes(); return True
        if dist < 240 and self._cd["slam"] <= 0:
            self._do_slam(player); return True
        if self._cd["parts"] <= 0:
            self._do_parts(game, player); return True
        if self.phase >= 2 and self._cd["summon"] <= 0 and len(game.enemies) < 5:
            self._do_summon(game); return True
        return False

    def _do_slam(self, player):
        self.state = "SLAM"; self.state_timer = 70
        self._cd["slam"] = 380 if self.phase < 3 else 260
        self.velocity_y = -17
        self.velocity_x = (1 if player.rect.centerx > self.rect.centerx else -1) * 2.6

    def _slam_impact(self, game):
        dmg = int(9 * self.dmg_mult)
        for d in (-1, 1):
            gw = GroundWave(self.rect.centerx + d * 34, SCREEN_HEIGHT - 30, d,
                            speed=6, width=64, height=26, damage=dmg,
                            color=(178, 140, 232), lifetime=130)
            game.ground_waves.add(gw); game.all_sprites.add(gw)

    def _do_parts(self, game, player):
        self.state = "PARTS"; self.state_timer = 34
        self._cd["parts"] = 300 if self.phase < 3 else 210
        cx, cy = self.rect.centerx, self.rect.centery - 10
        dmg = int(7 * self.dmg_mult)
        base_ang = math.atan2(player.rect.centery - cy, player.rect.centerx - cx)
        for i, off in enumerate((-0.30, 0.0, 0.30)):
            ang = base_ang + off
            color = self.PATCH_COLORS[i % len(self.PATCH_COLORS)]
            fb = Fireball(cx, cy, math.cos(ang) * 8, math.sin(ang) * 8,
                          damage=dmg, color=color)
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _do_summon(self, game):
        self.state = "SUMMON"; self.state_timer = 45
        self._cd["summon"] = 470
        for _ in range(2):
            x = random.randint(90, SCREEN_WIDTH - 90)
            circle = SummonCircle(x, SCREEN_HEIGHT - 75, 0, self.scene_type,
                                  self.depth, delay=45)
            game.summon_circles.add(circle); game.all_sprites.add(circle)

    def _do_spikes(self):
        self.state = "SPIKES"; self.state_timer = 90
        self._cd["spikes"] = 540


FIRE_SOURCES = ("skill_fireball_explosion", "skill_fireball_direct", "scorch",
                "explosion", "lava", "burning")


class GiantYetiBoss(BaseBoss):
    """巨雪怪·霜牙：雪山的巨兽，能掀起暴风雪；风雪里它是"结霜"状态，
    此时火焰伤害翻倍——带火系技能进雪山就有额外收益。"""

    BOSS_NAME = "巨雪怪·霜牙"
    BASE_HEALTH = 900; HEALTH_SCALE = 90; BASE_SPEED = 0.55
    SHIELD_COLOR = (200, 232, 255)
    HP_COLORS = ((210, 236, 255), (150, 190, 235), (110, 150, 210))
    PHASE_NOVA_COLOR = (200, 230, 255)
    FROSTED_DR = 2.0                 # 结霜期间受到火焰伤害的倍数

    def _setup(self):
        self._cd = {"roll": 300, "slam": 360, "summon": 600, "blizzard": 900}
        self.roll_dir = 0
        self.frosted = False

    def create_boss_image(self):
        W, H = 132, 118
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 110), (16, H - 12, W - 32, 12))
        fur = (206, 224, 240)
        fur_dark = (150, 176, 204)
        pygame.draw.ellipse(surf, fur_dark, (16, 36, W - 32, H - 46))
        pygame.draw.ellipse(surf, fur, (22, 42, W - 44, H - 60))
        pygame.draw.polygon(surf, fur_dark, [(34, 44), (26, 6), (58, 30)])
        pygame.draw.polygon(surf, fur_dark, [(W - 34, 44), (W - 26, 6), (W - 58, 30)])
        pygame.draw.circle(surf, fur, (W // 2, 42), 30)
        pygame.draw.circle(surf, (28, 34, 46), (W // 2 - 12, 38), 6)
        pygame.draw.circle(surf, (28, 34, 46), (W // 2 + 12, 38), 6)
        pygame.draw.circle(surf, (150, 240, 255), (W // 2 - 12, 37), 3)
        pygame.draw.circle(surf, (150, 240, 255), (W // 2 + 12, 37), 3)
        pygame.draw.polygon(surf, (36, 30, 40), [(W // 2 - 16, 54), (W // 2 + 16, 54),
                                                 (W // 2 + 10, 64), (W // 2 - 10, 64)])
        for sx in (-1, 1):
            pygame.draw.polygon(surf, (240, 246, 252),
                                [(W // 2 + sx * 12, 54), (W // 2 + sx * 16, 68),
                                 (W // 2 + sx * 8, 54)])
        for i in range(5):
            pygame.draw.line(surf, (240, 248, 255),
                             (30 + i * 8, H - 30), (26 + i * 8, H - 18), 3)
            pygame.draw.line(surf, (240, 248, 255),
                             (W - 30 - i * 8, H - 30), (W - 26 - i * 8, H - 18), 3)
        pygame.draw.rect(surf, (255, 214, 130, 200), (0, 0, W, H), 3, border_radius=10)
        draw_glow(surf, (190, 226, 255), (W // 2, 40), 26, 70)
        return surf

    def adjust_incoming(self, damage, source):
        """结霜期间吃火焰伤害翻倍（由 damage_boss 调用）。"""
        if self.frosted and source in FIRE_SOURCES:
            damage = int(damage * self.FROSTED_DR)
        return damage

    def state_update(self, player, platforms, barriers, game):
        if self.state == "ROLL":
            self.velocity_x = self.roll_dir * (11 if self.phase < 3 else 14)
            self.rect.x += self.velocity_x
            hit_wall = self.rect.left <= 15 or self.rect.right >= SCREEN_WIDTH - 15
            for b in barriers:
                if b.visible and pygame.sprite.collide_rect(self, b):
                    hit_wall = True; break
            if hit_wall:
                self.rect.x -= self.velocity_x
                self.velocity_x = 0
                self.state = "STUNNED"; self.state_timer = 70
                facing = -1 if self.roll_dir > 0 else 1
                gw = GroundWave(self.rect.centerx, SCREEN_HEIGHT - 30, facing,
                                speed=6, width=70, height=28,
                                damage=int(9 * self.dmg_mult), color=(190, 226, 255),
                                lifetime=150)
                game.ground_waves.add(gw); game.all_sprites.add(gw)
                self.apply_gravity(platforms)
                return True
            if pygame.sprite.collide_rect(self, player):
                player.take_damage(16 * self.dmg_mult, source='boss')
                player.velocity_x = 16 if self.roll_dir > 0 else -16
            self.state_timer -= 1
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "STUNNED":
            self.state_timer -= 1
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 20
            return True
        if self.state == "SLAM":
            if self.on_ground and self.velocity_y >= 0 and self.state_timer < 45:
                for d in (-1, 1):
                    gw = GroundWave(self.rect.centerx, SCREEN_HEIGHT - 30, d,
                                    speed=6, width=72, height=28,
                                    damage=int(11 * self.dmg_mult),
                                    color=(190, 226, 255), lifetime=150)
                    game.ground_waves.add(gw); game.all_sprites.add(gw)
                for i in range(3):
                    x = random.randint(80, SCREEN_WIDTH - 80)
                    w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=40, radius=40,
                                      spawn_type="spike")
                    game.warnings.add(w); game.all_sprites.add(w)
                self.state = "SLAM_LAND"; self.state_timer = 20
                self.velocity_y = 0
            self.state_timer -= 1
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "SLAM_LAND":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "BLIZZARD":
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state_timer % 24 == 0:
                x = random.randint(70, SCREEN_WIDTH - 70)
                w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=34, radius=42,
                                  spawn_type="spike")
                game.warnings.add(w); game.all_sprites.add(w)
            self.frosted = self.state_timer > 0
            if self.state_timer <= 0:
                self.frosted = False
                self.state = "IDLE"; self.action_cooldown = 60
            return True
        if self.state == "SUMMON":
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 60
            return True
        return False

    def try_cast(self, player, game, dist):
        if self._cd["blizzard"] <= 0 and self.phase >= 2:
            self._do_blizzard(game); return True
        if dist < 300 and self._cd["roll"] <= 0:
            self._do_roll(player); return True
        if self._cd["slam"] <= 0 and dist < 220:
            self._do_slam(player); return True
        if self.phase >= 2 and self._cd["summon"] <= 0 and len(game.enemies) < 4:
            self._do_summon(game); return True
        return False

    def _do_roll(self, player):
        self.state = "ROLL"; self.state_timer = 70
        self._cd["roll"] = 360 if self.phase < 3 else 240
        dx = player.rect.centerx - self.rect.centerx
        self.roll_dir = 1 if dx > 0 else -1
        self.facing = self.roll_dir

    def _do_slam(self, player):
        self.state = "SLAM"; self.state_timer = 80
        self._cd["slam"] = 420
        self.velocity_y = -17
        self.on_ground = False
        dx = player.rect.centerx - self.rect.centerx
        self.velocity_x = 4 if dx > 0 else -4

    def _do_blizzard(self, game):
        """掀暴风雪：视野被雪挡住，同时它自己进入"结霜"状态，火焰能重伤它。"""
        self.state = "BLIZZARD"; self.state_timer = BLIZZARD_DURATION * 2
        self._cd["blizzard"] = 1200
        self.frosted = True
        game.blizzard_timer = max(game.blizzard_timer, BLIZZARD_DURATION * 2)
        game.show_message("巨雪怪掀起了暴风雪！结霜状态下火焰伤害翻倍", 2600)

    def _do_summon(self, game):
        self.state = "SUMMON"; self.state_timer = 60
        self._cd["summon"] = 720
        for i in range(2):
            x = random.randint(120, SCREEN_WIDTH - 120)
            circle = SummonCircle(x, SCREEN_HEIGHT - 75, 6, self.scene_type,
                                  self.depth, delay=45)
            game.summon_circles.add(circle); game.all_sprites.add(circle)


class TrollChieftainBoss(BaseBoss):
    """巨魔酋长·格罗姆：更大的巨魔，牙更长；横扫与跳砸都躲得开，
    但它会狂呼给全场（含自己）增幅，那段时间要格外小心。"""

    BOSS_NAME = "巨魔酋长·格罗姆"
    BASE_HEALTH = 1000; HEALTH_SCALE = 95; BASE_SPEED = 0.7
    SHIELD_COLOR = (236, 230, 232)
    HP_COLORS = ((120, 202, 190), (180, 120, 60), (200, 70, 60))
    PHASE_NOVA_COLOR = (226, 62, 62)

    def _setup(self):
        self._cd = {"sweep": 260, "leap": 340, "howl": 900, "call": 780, "rock": 460}

    def create_boss_image(self):
        W, H = 128, 132
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 110), (12, H - 12, W - 24, 12))
        skin = (118, 202, 190)
        skin_dark = (74, 148, 140)
        cloth = (176, 58, 54)
        cloth_torn = (120, 36, 34)
        cx = W // 2
        pygame.draw.rect(surf, skin_dark, (cx - 30, H - 34, 22, 30), border_radius=6)
        pygame.draw.rect(surf, skin_dark, (cx + 8, H - 34, 22, 30), border_radius=6)
        pygame.draw.polygon(surf, cloth, [(cx - 36, 52), (cx + 36, 52),
                                          (cx + 40, H - 30), (cx - 40, H - 30)])
        pygame.draw.polygon(surf, cloth_torn, [(cx - 40, H - 30), (cx - 18, H - 42),
                                               (cx - 4, H - 28), (cx + 12, H - 44),
                                               (cx + 40, H - 30)])
        pygame.draw.line(surf, cloth_torn, (cx - 10, 60), (cx + 6, H - 36), 3)
        pygame.draw.rect(surf, skin, (cx - 50, 58, 18, 46), border_radius=8)
        pygame.draw.rect(surf, skin, (cx + 32, 58, 18, 46), border_radius=8)
        pygame.draw.circle(surf, skin, (cx, 34), 28)
        pygame.draw.polygon(surf, skin, [(cx - 28, 30), (cx - 50, 16), (cx - 26, 50)])
        pygame.draw.polygon(surf, skin, [(cx + 28, 30), (cx + 50, 16), (cx + 26, 50)])
        pygame.draw.circle(surf, (52, 26, 26), (cx - 11, 30), 6)
        pygame.draw.circle(surf, (52, 26, 26), (cx + 11, 30), 6)
        pygame.draw.circle(surf, (255, 210, 120), (cx - 11, 28), 3)
        pygame.draw.circle(surf, (255, 210, 120), (cx + 11, 28), 3)
        pygame.draw.line(surf, (34, 24, 26), (cx - 14, 46), (cx + 14, 46), 3)
        for sx in (-1, 1):
            pygame.draw.polygon(surf, (232, 236, 242),
                                [(cx + sx * 10, 46), (cx + sx * 16, 66), (cx + sx * 18, 46)])
        pygame.draw.rect(surf, (255, 214, 130, 200), (0, 0, W, H), 3, border_radius=10)
        return surf

    def state_update(self, player, platforms, barriers, game):
        if self.state == "SWEEP":
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state_timer == 24:
                for d in (-1, 1):
                    gw = GroundWave(self.rect.centerx, SCREEN_HEIGHT - 30, d,
                                    speed=7, width=74, height=30,
                                    damage=int(12 * self.dmg_mult), color=(226, 92, 62),
                                    lifetime=150)
                    game.ground_waves.add(gw); game.all_sprites.add(gw)
                if abs(player.rect.centerx - self.rect.centerx) < 90:
                    player.take_damage(10 * self.dmg_mult, source='boss')
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "LEAP":
            if self.on_ground and self.velocity_y >= 0 and self.state_timer < 50:
                for d in (-1, 1):
                    gw = GroundWave(self.rect.centerx, SCREEN_HEIGHT - 30, d,
                                    speed=6, width=74, height=30,
                                    damage=int(10 * self.dmg_mult), color=(226, 92, 62),
                                    lifetime=150)
                    game.ground_waves.add(gw); game.all_sprites.add(gw)
                for i in range(3):
                    x = max(60, min(self.rect.centerx + (i - 1) * 130, SCREEN_WIDTH - 60))
                    w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=38, radius=44,
                                      spawn_type="bone")
                    game.warnings.add(w); game.all_sprites.add(w)
                self.state = "LEAP_LAND"; self.state_timer = 20
                self.velocity_y = 0
            self.state_timer -= 1
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state == "LEAP_LAND":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 30
            return True
        if self.state in ("HOWL", "CALL"):
            self.velocity_x = 0
            self.apply_gravity(platforms)
            if self.state_timer <= 0:
                self.state = "IDLE"; self.action_cooldown = 45
            return True
        return False

    def try_cast(self, player, game, dist):
        if self._cd["howl"] <= 0:
            self._do_howl(game); return True
        if dist < 300 and self._cd["sweep"] <= 0:
            self._do_sweep(game, player); return True
        if self._cd["leap"] <= 0 and dist < 260:
            self._do_leap(player); return True
        if self.phase >= 2 and self._cd["call"] <= 0 and len(game.enemies) < 5:
            self._do_call(game); return True
        if self.phase >= 3 and self._cd["rock"] <= 0:
            self._do_rock(game); return True
        return False

    def _do_sweep(self, game, player):
        self.state = "SWEEP"; self.state_timer = 48
        self._cd["sweep"] = 320 if self.phase == 1 else 240
        self.velocity_x = 0
        self.facing = 1 if player.rect.centerx >= self.rect.centerx else -1

    def _do_leap(self, player):
        self.state = "LEAP"; self.state_timer = 90
        self._cd["leap"] = 400
        self.velocity_y = -18
        self.on_ground = False
        dx = player.rect.centerx - self.rect.centerx
        self.velocity_x = 5 if dx > 0 else -5

    def _do_howl(self, game):
        """狂呼：半个屏幕内的敌人连同自己一起增幅。"""
        self.state = "HOWL"; self.state_timer = 60
        self._cd["howl"] = 900
        cx, cy = self.rect.centerx, self.rect.centery
        count = 0
        for enemy in list(game.enemies):
            if getattr(enemy, 'health', 0) <= 0:
                continue
            if (abs(enemy.rect.centerx - cx) <= TROLL_BUFF_RANGE
                    and abs(enemy.rect.centery - cy) <= TROLL_BUFF_RANGE):
                enemy.buff_timer = TROLL_BUFF_DURATION
                count += 1
        self.buff_timer = TROLL_BUFF_DURATION
        game.show_message(f"酋长怒吼！{count} 个敌人被增幅（移速与攻击 +50%）", 2400)

    def _do_call(self, game):
        self.state = "CALL"; self.state_timer = 60
        self._cd["call"] = 900
        for i in range(2):
            x = random.randint(110, SCREEN_WIDTH - 110)
            circle = SummonCircle(x, SCREEN_HEIGHT - 75, 0, self.scene_type,
                                  self.depth, delay=45, elite_kind="troll_soldier")
            game.summon_circles.add(circle); game.all_sprites.add(circle)

    def _do_rock(self, game):
        self.state = "SWEEP"; self.state_timer = 40
        self._cd["rock"] = 520
        for i in range(3):
            x = max(70, min(self.rect.centerx + (i - 1) * 150, SCREEN_WIDTH - 70))
            w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=36, radius=44, spawn_type="bone")
            game.warnings.add(w); game.all_sprites.add(w)
