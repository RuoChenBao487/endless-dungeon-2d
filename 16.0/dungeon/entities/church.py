"""破败教堂的十字架与专属场景物件。"""

import math
import random

import pygame

from ..data.biomes import BIOME_CHURCH
from ..data.enemies import ENEMY_BLOOD_CROSS, UNDEAD_SUMMON_TYPES
from ..settings import (CHURCH_CROSS_AURA_RANGE, CHURCH_CROSS_AURA_TICKS,
                        CHURCH_CROSS_HOLY_HEAL, CHURCH_CROSS_HOLY_RADIUS,
                        CHURCH_CROSS_HOLY_TICK, CHURCH_CROSS_HP_BASE,
                        CHURCH_CROSS_HP_SCALE, CHURCH_CROSS_SUMMON_INTERVAL,
                        SCREEN_HEIGHT, SCREEN_WIDTH, get_font)
from ..utils import draw_glow


class ChurchCross(pygame.sprite.Sprite):
    """未调查时外观完全一致；按 F 后才显露血光或圣光。"""

    def __init__(self, x, ground_y, depth, kind):
        super().__init__()
        self.kind = kind
        self.depth = depth
        self.scene_type = BIOME_CHURCH
        self.active = False
        self.health = 0.0
        self.max_health = float(CHURCH_CROSS_HP_BASE
                                + depth * CHURCH_CROSS_HP_SCALE + depth * depth)
        self.base_health = self.max_health
        self.enemy_hit_timer = 0
        self.pulse = random.uniform(0, math.pi * 2)
        self.image = self._make_image("hidden")
        self.rect = self.image.get_rect(midbottom=(x, ground_y + 5))

    def _make_image(self, mode):
        w, h = 44, 74
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2
        if mode == "hidden":
            stone = (126, 124, 132)
            edge = (66, 64, 74)
            glow = (130, 122, 140)
        elif mode == "blood":
            stone = (136, 30, 46)
            edge = (54, 10, 20)
            glow = (242, 54, 76)
        else:
            stone = (244, 234, 188)
            edge = (146, 120, 58)
            glow = (255, 244, 190)
        if mode != "hidden":
            draw_glow(surf, glow, (cx, h // 2), 22, 90)
        pygame.draw.rect(surf, (0, 0, 0, 90), (9, h - 5, w - 18, 5))
        pygame.draw.rect(surf, edge, (cx - 8, 5, 16, h - 10), border_radius=2)
        pygame.draw.rect(surf, stone, (cx - 6, 7, 12, h - 14), border_radius=2)
        pygame.draw.rect(surf, edge, (cx - 20, 18, w - 8, 14), border_radius=2)
        pygame.draw.rect(surf, stone, (cx - 18, 20, w - 12, 10), border_radius=2)
        pygame.draw.line(surf, (255, 255, 255, 100), (cx - 2, 10), (cx - 2, h - 12), 1)
        pygame.draw.line(surf, (255, 255, 255, 80), (cx - 16, 22), (cx + 16, 22), 1)
        return surf

    def activate(self):
        if self.active:
            return
        self.active = True
        self.health = self.max_health
        self.image = self._make_image("blood" if self.kind == "blood" else "holy")

    def apply_damage(self, damage, game=None):
        if not self.active or self.health <= 0:
            return 0
        before = self.health
        self.health = max(0.0, self.health - damage)
        return before - self.health

    def update_cross(self, game):
        if self.enemy_hit_timer > 0:
            self.enemy_hit_timer -= 1

    def draw_health_bar(self, surface):
        if not self.active or self.health <= 0:
            return
        bar_w = max(self.rect.width, 58)
        bar_h = 5
        x = self.rect.centerx - bar_w // 2
        y = self.rect.top - 10
        pygame.draw.rect(surface, (28, 18, 22), (x - 1, y - 1, bar_w + 2, bar_h + 2))
        ratio = max(0.0, self.health / max(1.0, self.max_health))
        color = (226, 54, 72) if self.kind == "blood" else (246, 232, 154)
        pygame.draw.rect(surface, color, (x, y, int(bar_w * ratio), bar_h))
        pygame.draw.rect(surface, (245, 240, 235), (x, y, bar_w, bar_h), 1)
        font = get_font(12)
        name = "血腥十字架" if self.kind == "blood" else "圣光十字架"
        text = font.render(name, True, color)
        surface.blit(text, (self.rect.centerx - text.get_width() // 2, y - 16))

    def draw_affix_icons(self, surface):
        pass


class BloodCross(ChurchCross):
    """血腥十字架：本体重型精英，持续召唤亡者并强化附近敌人。"""

    def __init__(self, x, ground_y, depth):
        super().__init__(x, ground_y, depth, "blood")
        self.enemy_type = ENEMY_BLOOD_CROSS
        self.is_elite = True
        self.is_ember = False
        self.is_church_cross = True
        self.is_blood_minion = False
        self.is_undead = True
        self.is_flying = False
        self.is_giant = False
        self.contact_harmful = False
        self.cfg = {"name": "血腥十字架"}
        self.damage_multiplier = 1.0
        self.aura_speed_bonus = 0.0
        self.aura_damage_reduction = 0.0
        self.buff_timer = 0
        self.cross_buff_timer = 0
        self.slow_timer = 0
        self.freeze_timer = 0
        self.stun_timer = 0
        self.black_hole_lock = 0
        self.black_hole_angle = None
        self.split_done = True
        self.affix_names = []
        self.affix_instances = []
        self.summon_timer = CHURCH_CROSS_SUMMON_INTERVAL

    def activate(self):
        super().activate()
        if self.active and self.health > 0:
            self.summon_timer = CHURCH_CROSS_SUMMON_INTERVAL // 2

    def update_cross(self, game):
        super().update_cross(game)
        if not self.active or self.health <= 0 or game is None:
            return
        self._update_aura(game)
        self.summon_timer -= 1
        if self.summon_timer <= 0:
            self.summon_timer = CHURCH_CROSS_SUMMON_INTERVAL
            self._summon_undead(game)

    def _update_aura(self, game):
        cx, cy = self.rect.center
        for other in list(game.enemies):
            if other is self or getattr(other, 'health', 0) <= 0:
                continue
            dx = other.rect.centerx - cx
            dy = other.rect.centery - cy
            if dx * dx + dy * dy <= CHURCH_CROSS_AURA_RANGE ** 2:
                other.cross_buff_timer = max(
                    getattr(other, 'cross_buff_timer', 0),
                    CHURCH_CROSS_AURA_TICKS)

    def _summon_undead(self, game):
        if len(game.enemies) >= game.enemy_cap + 6:
            return
        from .enemies import Enemy
        from .projectiles import SummonCircle

        kind = random.choice(UNDEAD_SUMMON_TYPES)
        side = random.choice((-1, 1))
        x = max(45, min(self.rect.centerx + side * random.randint(70, 150),
                        SCREEN_WIDTH - 45))
        y = min(self.rect.bottom + 4, SCREEN_HEIGHT - 35)
        circle = SummonCircle(x, y, kind, BIOME_CHURCH, self.depth, delay=50)
        game.summon_circles.add(circle)
        game.all_sprites.add(circle)


class HolyCross(ChurchCross):
    """圣光十字架：缓慢治疗玩家，并灼烧附近敌人。"""

    def __init__(self, x, ground_y, depth):
        super().__init__(x, ground_y, depth, "holy")
        self.is_elite = False
        self.is_church_cross = True
        self.is_undead = False
        self.contact_harmful = False
        self.holy_tick = 0

    def update_cross(self, game):
        super().update_cross(game)
        if not self.active or self.health <= 0 or game is None:
            return
        player = game.player
        if player.health < player.max_health:
            player.health = min(player.max_health,
                                player.health + CHURCH_CROSS_HOLY_HEAL)
        self.holy_tick += 1
        if self.holy_tick < CHURCH_CROSS_HOLY_TICK:
            return
        self.holy_tick = 0
        cx, cy = self.rect.center
        radius = CHURCH_CROSS_HOLY_RADIUS
        damage = max(3, int(3 + self.depth * 0.55))
        for enemy in list(game.enemies):
            if getattr(enemy, 'health', 0) <= 0:
                continue
            if getattr(enemy, 'is_church_cross', False):
                continue
            dx = enemy.rect.centerx - cx
            dy = enemy.rect.centery - cy
            if dx * dx + dy * dy <= radius * radius:
                game.damage_enemy(enemy, damage, source='holy_cross')
