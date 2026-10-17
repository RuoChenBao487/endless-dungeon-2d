"""古代大墓地：墓碑、僵尸与载骨机。"""

import random

import pygame

from ..data.biomes import BIOME_GREAT_TOMB
from ..data.enemies import ENEMY_GHOST, ENEMY_SKELETON, ENEMY_ZOMBIE
from ..data.modes import MODE_UNDEAD_TIDE
from ..entities.affix import roll_affixes
from ..entities.enemies import BoneCarrierEnemy, Enemy
from ..entities.graveyard import Gravestone
from ..entities.props import Platform
from ..settings import (BONE_CARRIER_HEAL_RADIUS, GRAVESTONE_INTERVAL,
                        GRAVESTONE_MAX, GRAVESTONE_MIN, SCREEN_HEIGHT,
                        SCREEN_WIDTH, ZOMBIE_CORPSE_RADIUS)


class GameGraveyardMixin:
    def _setup_great_tomb_room(self):
        ground_top = SCREEN_HEIGHT - 30
        ground = Platform(0, ground_top, SCREEN_WIDTH, 30, BIOME_GREAT_TOMB)
        self.platforms.add(ground)
        self.all_sprites.add(ground)

        platforms = [
            (74, SCREEN_HEIGHT - 190, 190, 18),
            (SCREEN_WIDTH - 264, SCREEN_HEIGHT - 190, 190, 18),
            (SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT - 132, 260, 18),
            (110, 278, 180, 18),
            (SCREEN_WIDTH - 290, 278, 180, 18),
        ]
        for x, y, w, h in platforms:
            p = Platform(x, y, w, h, BIOME_GREAT_TOMB)
            self.platforms.add(p)
            self.all_sprites.add(p)

        count = random.randint(GRAVESTONE_MIN, GRAVESTONE_MAX)
        margin = 62
        usable = SCREEN_WIDTH - margin * 2
        for i in range(count):
            slot = usable / max(1, count)
            x = int(margin + slot * (i + 0.5)
                    + random.uniform(-slot * 0.18, slot * 0.18))
            x = max(45, min(SCREEN_WIDTH - 45, x))
            initial = random.randint(GRAVESTONE_INTERVAL // 3, GRAVESTONE_INTERVAL)
            grave = Gravestone(x, ground_top, self.current_depth, initial)
            self.gravestones.add(grave)
            self.all_sprites.add(grave)

        for i in range(random.randint(4, 6)):
            x = 220 + (i % 4) * 118 + random.randint(-30, 30)
            zombie = Enemy(x, ground_top - 56, self.current_depth,
                           ENEMY_ZOMBIE, BIOME_GREAT_TOMB)
            zombie.rect.bottom = ground_top
            self.enemies.add(zombie)
            self.all_sprites.add(zombie)
        for i in range(2):
            x = 300 + i * 210
            skeleton = Enemy(x, ground_top - 52, self.current_depth,
                             ENEMY_SKELETON, BIOME_GREAT_TOMB)
            skeleton.rect.bottom = ground_top
            self.enemies.add(skeleton)
            self.all_sprites.add(skeleton)
        ghost = Enemy(SCREEN_WIDTH // 2, 250, self.current_depth,
                      ENEMY_GHOST, BIOME_GREAT_TOMB)
        ghost.rect.center = (SCREEN_WIDTH // 2, 250)
        self.enemies.add(ghost)
        self.all_sprites.add(ghost)

        carrier = BoneCarrierEnemy(SCREEN_WIDTH // 2, ground_top - 76,
                                   self.current_depth, BIOME_GREAT_TOMB)
        carrier.rect.bottom = ground_top
        self.enemies.add(carrier)
        self.all_sprites.add(carrier)

        giant_zombie = self.spawn_zombie_at(
            SCREEN_WIDTH - 230, ground_top, giant=True)
        if giant_zombie is not None:
            self.elite_banner_timer = 160
            self.elite_banner_name = "巨型僵尸"

        self.initial_enemy_count = len(self.enemies)
        self.show_message("古代大墓地的墓碑正在苏醒", 2400)

    def spawn_zombie_at(self, x, ground_y, giant=False):
        if giant:
            if sum(1 for e in self.enemies
                   if getattr(e, "is_giant_zombie", False)) >= 3:
                return None
        if len(self.enemies) >= self.enemy_cap:
            return None
        x = max(35, min(int(x), SCREEN_WIDTH - 35))
        zombie = Enemy(x, ground_y - 56, self.current_depth,
                       ENEMY_ZOMBIE, BIOME_GREAT_TOMB)
        zombie.rect.bottom = ground_y
        if giant:
            zombie.image = pygame.transform.scale(
                zombie.image,
                (int(zombie.image.get_width() * 2.2),
                 int(zombie.image.get_height() * 2.2)))
            zombie.rect = zombie.image.get_rect(midbottom=(x, ground_y))
            zombie.is_giant = True
            zombie.is_giant_zombie = True
            zombie.is_elite = True
            zombie.elite_name = "巨型僵尸"
            zombie.base_health = int(zombie.base_health * 4.2)
            zombie.max_health = zombie.base_health
            zombie.health = zombie.max_health
            zombie.base_speed *= 0.7
            affix_count = min(3, 1 + self.current_depth // 7)
            zombie.affix_names = []
            zombie.affix_instances = []
            self._attach_affixes(
                zombie, roll_affixes(self.current_depth, affix_count))
        self.enemies.add(zombie)
        self.all_sprites.add(zombie)
        return zombie

    def update_gravestones(self):
        for grave in list(self.gravestones):
            if getattr(grave, "health", 0) > 0:
                grave.update_gravestone(self)

    def damage_gravestone(self, grave, damage, source="player"):
        if grave is None or getattr(grave, "health", 0) <= 0:
            return 0
        dealt = grave.apply_damage(damage)
        if grave.health <= 0:
            self.add_floating_text(grave.rect.centerx, grave.rect.top,
                                   "墓碑破碎", (170, 222, 174), 17)
            grave.kill()
        return dealt

    def heal_bone_carriers_on_death(self, dead):
        if dead is None or getattr(dead, "health", 0) > 0:
            return
        cx, cy = dead.rect.center
        for carrier in list(self.enemies):
            if not isinstance(carrier, BoneCarrierEnemy) or carrier is dead:
                continue
            if carrier.health <= 0:
                continue
            dx = carrier.rect.centerx - cx
            dy = carrier.rect.centery - cy
            if dx * dx + dy * dy > BONE_CARRIER_HEAL_RADIUS ** 2:
                continue
            heal = max(1, int(carrier.max_health * 0.04))
            before = carrier.health
            carrier.health = min(carrier.max_health, carrier.health + heal)
            if carrier.health > before:
                self.add_floating_text(carrier.rect.centerx, carrier.rect.top - 8,
                                       f"+{int(carrier.health - before)}",
                                       (126, 240, 154), 16)

    def spawn_zombie_from_death(self, dead):
        if dead is None or getattr(dead, "is_undead", False):
            return None
        if getattr(dead, "is_mirror_duelist", False):
            return None
        cx, cy = dead.rect.center
        giant_nearby = False
        zombie_nearby = False
        for enemy in self.enemies:
            if enemy is dead or not getattr(enemy, "is_zombie", False):
                continue
            if getattr(enemy, "health", 0) <= 0:
                continue
            dx = enemy.rect.centerx - cx
            dy = enemy.rect.centery - cy
            if dx * dx + dy * dy > ZOMBIE_CORPSE_RADIUS ** 2:
                continue
            zombie_nearby = True
            if getattr(enemy, "is_giant_zombie", False):
                giant_nearby = True
                break
        if not zombie_nearby:
            return None
        return self.spawn_zombie_at(cx, dead.rect.bottom, giant=giant_nearby)

    def spawn_ghost_from_zombie(self, zombie):
        if zombie is None or self.mode == MODE_UNDEAD_TIDE:
            return None
        if len(self.enemies) >= self.enemy_cap:
            return None
        x = max(30, min(zombie.rect.centerx, SCREEN_WIDTH - 30))
        ghost = Enemy(x, zombie.rect.bottom - 44, self.current_depth,
                      ENEMY_GHOST, self.scene_type)
        ghost.rect.bottom = zombie.rect.bottom
        self.enemies.add(ghost)
        self.all_sprites.add(ghost)
        return ghost

