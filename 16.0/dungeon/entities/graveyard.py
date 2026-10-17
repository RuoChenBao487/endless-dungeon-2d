"""古代大墓地物件：会周期性唤醒僵尸的墓碑。"""

import pygame

from ..settings import (GRAVESTONE_HP_BASE, GRAVESTONE_HP_SCALE,
                        GRAVESTONE_INTERVAL, OUTLINE, get_font)
from ..utils import draw_glow


class Gravestone(pygame.sprite.Sprite):
    def __init__(self, x, ground_y, depth, initial_timer):
        super().__init__()
        self.depth = depth
        self.spawn_y = ground_y
        self.max_health = int(GRAVESTONE_HP_BASE
                              + depth * GRAVESTONE_HP_SCALE)
        self.health = self.max_health
        self.timer = max(1, initial_timer)
        self.image = pygame.Surface((48, 66), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (0, 0, 0, 100), (6, 60, 36, 6))
        pygame.draw.rect(self.image, (72, 84, 68), (10, 14, 28, 50), border_radius=8)
        pygame.draw.rect(self.image, (126, 140, 112), (13, 17, 22, 45), border_radius=7)
        pygame.draw.rect(self.image, (94, 118, 82), (8, 56, 32, 8), border_radius=3)
        pygame.draw.line(self.image, (52, 64, 48), (18, 26), (27, 43), 2)
        pygame.draw.line(self.image, (52, 64, 48), (27, 43), (21, 55), 2)
        pygame.draw.line(self.image, (70, 112, 72), (31, 18), (29, 38), 2)
        pygame.draw.rect(self.image, OUTLINE, (10, 14, 28, 50), 2, border_radius=8)
        draw_glow(self.image, (82, 214, 120), (24, 34), 14, 25)
        self.rect = self.image.get_rect(midbottom=(x, ground_y + 3))

    def update_gravestone(self, game):
        if self.health <= 0:
            return
        self.timer -= 1
        if self.timer > 0:
            return
        self.timer = GRAVESTONE_INTERVAL
        game.spawn_zombie_at(self.rect.centerx, self.spawn_y, giant=False)

    def apply_damage(self, damage):
        if self.health <= 0:
            return 0
        before = self.health
        self.health = max(0, self.health - damage)
        return before - self.health

    def draw_health_bar(self, surface):
        if self.health <= 0:
            return
        bar_w = 46
        x = self.rect.centerx - bar_w // 2
        y = self.rect.top - 8
        pygame.draw.rect(surface, (18, 22, 18), (x - 1, y - 1, bar_w + 2, 5))
        ratio = max(0.0, self.health / self.max_health)
        pygame.draw.rect(surface, (118, 204, 126), (x, y, int(bar_w * ratio), 3))
        pygame.draw.rect(surface, (210, 230, 210), (x, y, bar_w, 3), 1)
        font = get_font(11)
        text = font.render("墓碑", True, (172, 220, 180))
        surface.blit(text, (self.rect.centerx - text.get_width() // 2, y - 14))

