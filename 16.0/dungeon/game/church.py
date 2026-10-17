"""破败教堂：亡灵墓穴的嵌套房流程与场地机制。"""

import math
import random

import pygame

from ..data.biomes import BIOME_CHURCH
from ..data.enemies import ENEMY_BLOOD_BAT, ENEMY_BLOOD_SERVANT, ENEMY_GHOST, ENEMY_SKELETON
from ..entities.church import BloodCross, HolyCross
from ..entities.enemies import Enemy, GargoyleEnemy, VampireEnemy
from ..entities.props import Platform
from ..settings import (CHURCH_CROSS_RANGE, SCREEN_HEIGHT, SCREEN_WIDTH, screen)
from ..utils import draw_glow


class GameChurchMixin:
    def _setup_church_room(self):
        ground_top = SCREEN_HEIGHT - 30
        ground = Platform(0, ground_top, SCREEN_WIDTH, 30, BIOME_CHURCH)
        self.platforms.add(ground)
        self.all_sprites.add(ground)

        platforms = [
            (48, SCREEN_HEIGHT - 210, 172, 18),
            (SCREEN_WIDTH - 220, SCREEN_HEIGHT - 210, 172, 18),
            (SCREEN_WIDTH // 2 - 92, SCREEN_HEIGHT - 150, 184, 18),
            (SCREEN_WIDTH // 2 - 126, 258, 252, 18),
        ]
        for x, y, w, h in platforms:
            p = Platform(x, y, w, h, BIOME_CHURCH)
            self.platforms.add(p)
            self.all_sprites.add(p)

        kinds = ["blood", "holy"]
        random.shuffle(kinds)
        for kind, x in zip(kinds, (135, SCREEN_WIDTH - 135)):
            if kind == "blood":
                cross = BloodCross(x, ground_top, self.current_depth)
            else:
                cross = HolyCross(x, ground_top, self.current_depth)
            self.church_crosses.add(cross)
            self.all_sprites.add(cross)

        spawn_xs = [230, 320, SCREEN_WIDTH // 2, SCREEN_WIDTH - 320, SCREEN_WIDTH - 230]
        random.shuffle(spawn_xs)
        for i, enemy_type in enumerate((ENEMY_BLOOD_SERVANT, ENEMY_BLOOD_SERVANT,
                                        ENEMY_BLOOD_BAT, ENEMY_BLOOD_BAT,
                                        ENEMY_SKELETON, ENEMY_GHOST)):
            x = spawn_xs[i % len(spawn_xs)]
            enemy = Enemy(x, 80, self.current_depth, enemy_type, BIOME_CHURCH)
            if enemy.is_flying:
                enemy.rect.center = (x, random.randint(120, ground_top - 120))
            else:
                enemy.rect.bottom = ground_top
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)

        vampire_x = random.choice((265, SCREEN_WIDTH - 265))
        vampire = VampireEnemy(vampire_x, ground_top - 68,
                               self.current_depth, BIOME_CHURCH)
        vampire.rect.bottom = ground_top
        self.enemies.add(vampire)
        self.all_sprites.add(vampire)

        gargoyle_x = SCREEN_WIDTH // 2
        gargoyle = GargoyleEnemy(gargoyle_x, ground_top - 66,
                                 self.current_depth, BIOME_CHURCH)
        gargoyle.rect.bottom = ground_top
        self.enemies.add(gargoyle)
        self.all_sprites.add(gargoyle)

        self.initial_enemy_count = len(self.enemies)
        self.show_message("破败教堂的钟声在墓穴深处回响", 2400)

    def interactive_church_cross(self):
        best, best_d = None, CHURCH_CROSS_RANGE
        for cross in self.church_crosses:
            if cross.active:
                continue
            dx = cross.rect.centerx - self.player.rect.centerx
            dy = cross.rect.centery - self.player.rect.centery
            dist = math.hypot(dx, dy)
            if dist <= best_d:
                best, best_d = cross, dist
        return best

    def use_church_cross(self):
        cross = self.interactive_church_cross()
        if cross is None:
            return False
        cross.activate()
        if cross.kind == "blood":
            self.enemies.add(cross)
            self.show_message("血腥十字架苏醒，开始召唤亡者！", 2200)
        else:
            self.show_message("圣光十字架亮起", 1500)
        return True

    def update_church_crosses(self):
        for cross in list(self.church_crosses):
            if cross.active and cross.health > 0:
                cross.update_cross(self)

    def damage_church_cross(self, cross, damage, source="cross_hit"):
        if cross is None or not cross.active or cross.health <= 0:
            return 0
        if getattr(cross, "kind", "") == "blood" and self.enemies.has(cross):
            return self.damage_enemy(cross, damage, source=source)
        dealt = cross.apply_damage(damage, self)
        if cross.health <= 0:
            name = "血腥十字架" if cross.kind == "blood" else "圣光十字架"
            self.add_floating_text(cross.rect.centerx, cross.rect.top,
                                   "十字架破碎", (235, 225, 210), 18)
            cross.kill()
            self.show_message(f"{name}被摧毁了", 1300)
        return dealt

    def draw_church_effects(self):
        for cross in self.church_crosses:
            if not cross.active or cross.health <= 0:
                continue
            cx, cy = cross.rect.center
            if cross.kind == "blood":
                pulse = int(24 + 6 * math.sin(self.frame * 0.09))
                draw_glow(screen, (220, 42, 64), (cx, cy - 12), pulse, 36)
                pygame.draw.circle(screen, (176, 38, 58),
                                   (cx, cross.rect.bottom - 4), 58, 2)
            else:
                pulse = int(20 + 5 * math.sin(self.frame * 0.07))
                draw_glow(screen, (255, 238, 162), (cx, cy - 12), pulse, 42)
                pygame.draw.circle(screen, (242, 222, 138),
                                   (cx, cross.rect.bottom - 4), 38, 2)

        for enemy in self.enemies:
            if not isinstance(enemy, VampireEnemy) or enemy.drain_fx_timer <= 0:
                continue
            target = enemy.drain_target
            if target is None or not target.alive() or target.health <= 0:
                continue
            start = (enemy.rect.centerx, enemy.rect.centery)
            end = (target.rect.centerx, target.rect.centery)
            wobble = math.sin(self.frame * 0.4) * 3
            pygame.draw.line(screen, (185, 35, 58), start,
                             (end[0], end[1] + wobble), 5)
            pygame.draw.line(screen, (255, 152, 164), start,
                             (end[0], end[1] + wobble), 2)

