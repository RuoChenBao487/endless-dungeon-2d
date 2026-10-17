"""普通敌人、精英敌人、盟友召唤物与余烬小兵。"""


# === IMPORTS ===
import math
import pygame
import random
from ..data.biomes import BIOME_ICE, BIOME_NORMAL
from ..data.enemies import (BLOOD_MINION_TYPES, ELITE_STATS, ENEMY_BLOOD_BAT,
                            ENEMY_BLOOD_SERVANT, ENEMY_CONFIG, ENEMY_WIND_SPIRIT,
                            ENEMY_GHOST, ENEMY_SKELETON, ENEMY_WRAITHBONE,
                            ENEMY_ZOMBIE, UNDEAD_SUMMON_TYPES)
from ..data.skills import ALLY_ATTACK_RATIO, ALLY_BAD_AFFIXES
from .affix import AFFIX_TABLE, draw_affix_icons_row, roll_affixes
from .projectiles import (Fireball, HookProjectile, LavaPool, SoulShock,
                          SummonCircle, WarningCircle)
from .props import IceTrail, IceTrap
from ..settings import (BLACK, CYAN, ELITE_PURPLE, ENEMY_JUMP_POWER, FIRE_ORANGE,
                        FIRE_RED, FIRE_YELLOW, FPS, GRAVITY, ICE_TRAP_COOLDOWN,
                        JUMP_POWER_BASE, LAVA_BRIGHT, OUTLINE, POISON_BRIGHT,
                        POISON_GREEN, SCREEN_HEIGHT, SCREEN_WIDTH, SLIDE_FACTOR,
                        TROLL_BUFF_DAMAGE, TROLL_BUFF_DURATION, TROLL_BUFF_RANGE,
                        TROLL_BUFF_SPEED, TROLL_GIANT_SCALE, VAMPIRE_DRAIN_BASE,
                        VAMPIRE_DRAIN_INTERVAL, VAMPIRE_DRAIN_RADIUS,
                        VAMPIRE_SUMMON_INTERVAL, GARGOYLE_RECOVER_FRAMES,
                        LEADER_AURA_MAX_DAMAGE_REDUCTION, SOUL_SHOCK_DAMAGE,
                        SOUL_SHOCK_INTERVAL, SOUL_SHOCK_SPEED, WHITE, get_font)
from ..utils import (draw_glow, outlined_circle, outlined_rect, resolve_platform_overlap,
                     try_step_up)
# === /IMPORTS ===


def _shade_color(color, delta):
    return tuple(max(0, min(255, c + delta)) for c in color)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, depth, enemy_type=0, scene_type=BIOME_NORMAL, affix_names=None):
        super().__init__()
        self.enemy_type = enemy_type
        self.scene_type = scene_type
        self.depth = depth
        self.is_elite = False
        self.is_ember = False
        self.is_wraithbone = enemy_type == ENEMY_WRAITHBONE
        self.is_wind = enemy_type == ENEMY_WIND_SPIRIT
        self.is_blood_minion = enemy_type in BLOOD_MINION_TYPES
        self.is_zombie = enemy_type == ENEMY_ZOMBIE
        self.is_giant_zombie = False
        self.is_bone_carrier = False
        self.is_church_cross = False
        self.contact_harmful = True
        # 召唤师模式里由同一套逻辑驱动的友方单位会把它置为 True
        self.is_ally = False
        self.damage_multiplier = 1.0
        self.aura_speed_bonus = 0.0
        self.aura_damage_reduction = 0.0
        self.buff_timer = 0          # 被巨魔狂呼者增幅的剩余帧数
        self.cross_buff_timer = 0    # 血腥十字架附近的增幅
        self.affix_names = list(affix_names or [])
        self.stun_timer = 0
        self.freeze_timer = 0
        self.slow_timer = 0
        self.is_giant = False
        self.black_hole_lock = 0
        self.black_hole_angle = None
        cfg = ENEMY_CONFIG.get(enemy_type, ENEMY_CONFIG[0])
        self.cfg = cfg
        self.is_undead = bool(cfg.get("undead", False))
        self.base_speed = cfg["speed"]
        self.base_health = int(cfg["hp_base"] + depth * cfg["hp_scale"] + 0.5 * depth ** 2)
        self.is_flying = cfg.get("flying", False)
        self.has_revive = cfg.get("revive", False)
        self.revived = False
        self.anim_timer = 0
        self.create_enemy_image()
        self.rect = self.image.get_rect()
        self.rect.x = x; self.rect.y = y
        self.velocity_x = 0; self.velocity_y = 0
        self.on_ground = False
        self.jump_timer = 0
        self.next_jump_time = random.randint(60, 180)
        self.charge_timer = 0; self.charge_active = False
        self.ice_trail_timer = 0
        self.shield_active = cfg.get("shield", False)
        self.split_done = False
        self.spore_timer = random.randint(60, 180)
        self.target = None
        self.core_target = None   # 护核防守：只冲这个目标
        self.velocity_x = random.choice([-self.base_speed, self.base_speed])
        self.health = self.base_health; self.max_health = self.base_health
        if cfg.get("blood") and "lifesteal" not in self.affix_names:
            self.affix_names.append("lifesteal")
        self.affix_instances = []
        for name in self.affix_names:
            cls = AFFIX_TABLE.get(name)
            if cls:
                inst = cls(self)
                self.affix_instances.append(inst)
                inst.on_spawn(None)

    def create_enemy_image(self):
        color = self.cfg["color"]
        w, h = self.cfg["size"]
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        if not self.is_flying:
            pygame.draw.ellipse(s, (0, 0, 0, 90), (2, h - 4, w - 4, 5))
        t = self.enemy_type
        if t == 0: self._draw_soldier(s, w, h, color)
        elif t == 1: self._draw_jumper(s, w, h, color)
        elif t == 2: self._draw_brute(s, w, h, color)
        elif t == 3: self._draw_tank(s, w, h, color)
        elif t == 4: self._draw_icewalker(s, w, h, color)
        elif t == 5: self._draw_iceguard(s, w, h, color)
        elif t == 6: self._draw_snowball(s, w, h, color)
        elif t == 7: self._draw_bat(s, w, h, color)
        elif t == 8: self._draw_slime(s, w, h, color)
        elif t == 9: self._draw_mushroom(s, w, h, color)
        elif t == 10: self._draw_frog(s, w, h, color)
        elif t == 11: self._draw_skeleton(s, w, h, color)
        elif t == 12: self._draw_ghost(s, w, h, color)
        elif t == 13: self._draw_wraithbone(s, w, h, color)
        elif t == 14: self._draw_wind_spirit(s, w, h, color)
        elif t == ENEMY_BLOOD_SERVANT: self._draw_blood_servant(s, w, h, color)
        elif t == ENEMY_BLOOD_BAT: self._draw_blood_bat(s, w, h, color)
        elif t == ENEMY_ZOMBIE: self._draw_zombie(s, w, h, color)
        else: outlined_rect(s, color, (0, 0, w, h))
        self.image = s

    def _draw_blood_servant(self, s, w, h, color):
        """血仆：弓背、披着破布的血族仆从。"""
        cx = w // 2
        pygame.draw.ellipse(s, (0, 0, 0, 90), (2, h - 5, w - 4, 6))
        pygame.draw.polygon(s, (68, 18, 26), [
            (cx - 12, 22), (cx + 12, 22), (cx + 15, h - 5), (cx - 15, h - 5)
        ])
        outlined_rect(s, color, (cx - 10, 22, 20, 24))
        pygame.draw.line(s, (222, 96, 108), (cx - 9, 30), (cx + 9, 36), 2)
        outlined_circle(s, (222, 190, 176), (cx, 13), 9)
        pygame.draw.polygon(s, (58, 18, 26), [
            (cx - 9, 12), (cx - 4, 2), (cx, 8), (cx + 5, 2), (cx + 9, 12)
        ])
        pygame.draw.circle(s, (255, 92, 92), (cx - 3, 12), 2)
        pygame.draw.circle(s, (255, 92, 92), (cx + 3, 12), 2)
        pygame.draw.polygon(s, WHITE, [(cx - 4, 20), (cx - 2, 24), (cx, 20)])
        pygame.draw.polygon(s, WHITE, [(cx + 1, 20), (cx + 3, 24), (cx + 5, 20)])
        draw_glow(s, (220, 60, 80), (cx, h // 2), 15, 35)

    def _draw_blood_bat(self, s, w, h, color):
        """血蝙蝠：暗红蝠翼与发亮的血色眼睛。"""
        cx, cy = w // 2, h // 2
        wing = (96, 22, 38)
        pygame.draw.polygon(s, wing, [(cx - 3, cy), (0, 2), (2, h - 2), (cx - 4, cy + 4)])
        pygame.draw.polygon(s, wing, [(cx + 3, cy), (w, 2), (w - 2, h - 2), (cx + 4, cy + 4)])
        pygame.draw.polygon(s, OUTLINE, [(cx - 3, cy), (0, 2), (2, h - 2), (cx - 4, cy + 4)], 2)
        pygame.draw.polygon(s, OUTLINE, [(cx + 3, cy), (w, 2), (w - 2, h - 2), (cx + 4, cy + 4)], 2)
        outlined_circle(s, color, (cx, cy), 7)
        pygame.draw.polygon(s, (58, 10, 18), [(cx - 6, cy - 5), (cx - 9, cy - 12), (cx - 2, cy - 7)])
        pygame.draw.polygon(s, (58, 10, 18), [(cx + 6, cy - 5), (cx + 9, cy - 12), (cx + 2, cy - 7)])
        pygame.draw.circle(s, (255, 80, 90), (cx - 3, cy), 2)
        pygame.draw.circle(s, (255, 80, 90), (cx + 3, cy), 2)
        draw_glow(s, (230, 55, 75), (cx, cy), 13, 55)

    def _draw_zombie(self, s, w, h, color):
        """僵尸：佝偻、迟缓，胸口与破损处露出暗绿色腐肉。"""
        cx = w // 2
        pygame.draw.ellipse(s, (0, 0, 0, 100), (3, h - 5, w - 6, 6))
        pygame.draw.polygon(s, (54, 72, 48), [
            (cx - 14, 20), (cx + 14, 20), (cx + 17, h - 5), (cx - 17, h - 5)
        ])
        pygame.draw.polygon(s, color, [
            (cx - 11, 23), (cx + 10, 23), (cx + 13, h - 8), (cx - 13, h - 8)
        ])
        outlined_rect(s, (48, 58, 42), (cx - 15, 30, 7, 23))
        outlined_rect(s, (48, 58, 42), (cx + 8, 30, 7, 23))
        outlined_circle(s, (132, 150, 106), (cx, 13), 10)
        pygame.draw.circle(s, (38, 28, 24), (cx - 4, 12), 2)
        pygame.draw.circle(s, (38, 28, 24), (cx + 4, 12), 2)
        pygame.draw.circle(s, (188, 244, 124), (cx - 4, 11), 1)
        pygame.draw.circle(s, (188, 244, 124), (cx + 4, 11), 1)
        pygame.draw.line(s, (42, 28, 24), (cx - 5, 19), (cx + 5, 18), 2)
        pygame.draw.line(s, (86, 112, 70), (cx - 8, 34), (cx + 7, 41), 2)
        pygame.draw.line(s, (86, 112, 70), (cx - 7, 44), (cx + 8, 50), 2)
        draw_glow(s, (88, 152, 82), (cx, h // 2), 15, 28)

    def _draw_wind_spirit(self, s, w, h, color):
        """风灵：一团打着旋的浅蓝气流，没有实体轮廓。"""
        cx, cy = w // 2, h // 2
        for i, r in enumerate((13, 10, 7)):
            a = 150 - i * 30
            pygame.draw.ellipse(s, (*color, a), (cx - r, cy - r + i * 3, r * 2, r * 2 - 4), 2)
        pygame.draw.arc(s, (*color, 210), (cx - 12, cy - 12, 24, 24), 0.4, 3.2, 2)
        pygame.draw.arc(s, (*color, 170), (cx - 9, cy - 6, 18, 18), 3.4, 6.0, 2)
        pygame.draw.circle(s, (240, 252, 255), (cx + 3, cy - 4), 3)
        draw_glow(s, (150, 210, 245), (cx, cy), 14, 60)

    def _draw_soldier(self, s, w, h, color):
        outlined_rect(s, (60, 30, 40), (6, 12, w - 12, 26))
        outlined_rect(s, color, (8, 14, w - 16, 22))
        pygame.draw.rect(s, (255, 130, 130), (12, 18, 4, 14))
        outlined_rect(s, (40, 20, 28), (8, 38, 8, 10))
        outlined_rect(s, (40, 20, 28), (w - 16, 38, 8, 10))
        outlined_circle(s, (230, 200, 175), (w // 2, 10), 8)
        pygame.draw.polygon(s, (150, 40, 40), [(w // 2 - 8, 6), (w // 2, 0), (w // 2 + 8, 6), (w // 2 + 6, 12), (w // 2 - 6, 12)])
        pygame.draw.polygon(s, OUTLINE, [(w // 2 - 8, 6), (w // 2, 0), (w // 2 + 8, 6), (w // 2 + 6, 12), (w // 2 - 6, 12)], 2)
        pygame.draw.circle(s, (255, 90, 90), (w // 2 - 3, 10), 1)
        pygame.draw.circle(s, (255, 90, 90), (w // 2 + 3, 10), 1)

    def _draw_jumper(self, s, w, h, color):
        outlined_rect(s, (40, 90, 50), (8, 16, w - 16, 24))
        outlined_rect(s, color, (10, 18, w - 20, 20))
        outlined_circle(s, WHITE, (w // 2 - 5, 22), 5)
        outlined_circle(s, WHITE, (w // 2 + 5, 22), 5)
        pygame.draw.circle(s, (20, 20, 20), (w // 2 - 5, 23), 2)
        pygame.draw.circle(s, (20, 20, 20), (w // 2 + 5, 23), 2)
        outlined_rect(s, (40, 90, 50), (10, 40, 5, 8))
        outlined_rect(s, (40, 90, 50), (w - 15, 40, 5, 8))

    def _draw_brute(self, s, w, h, color):
        outlined_rect(s, (60, 30, 80), (4, 12, w - 8, 30))
        outlined_rect(s, color, (6, 14, w - 12, 26))
        pygame.draw.line(s, (220, 160, 240), (8, 20), (w - 8, 20), 2)
        pygame.draw.line(s, (220, 160, 240), (8, 30), (w - 8, 30), 2)
        outlined_rect(s, (90, 50, 130), (w // 2 - 9, 2, 18, 14))
        pygame.draw.rect(s, (255, 200, 255), (w // 2 - 7, 6, 14, 3))
        pygame.draw.circle(s, (255, 200, 255), (w // 2 - 4, 12), 1)
        pygame.draw.circle(s, (255, 200, 255), (w // 2 + 4, 12), 1)
        outlined_rect(s, (60, 30, 80), (6, 40, 8, 8))
        outlined_rect(s, (60, 30, 80), (w - 14, 40, 8, 8))

    def _draw_tank(self, s, w, h, color):
        outlined_rect(s, (140, 110, 40), (2, 14, w - 4, 32))
        outlined_rect(s, color, (4, 16, w - 8, 28))
        pygame.draw.line(s, (255, 230, 130), (6, 22), (w - 6, 22), 2)
        pygame.draw.line(s, (255, 230, 130), (6, 34), (w - 6, 34), 2)
        outlined_circle(s, (140, 110, 40), (4, 20), 6)
        outlined_circle(s, (140, 110, 40), (w - 4, 20), 6)
        outlined_rect(s, (180, 140, 60), (w // 2 - 10, 2, 20, 14))
        pygame.draw.rect(s, (40, 30, 20), (w // 2 - 7, 6, 14, 6))
        pygame.draw.circle(s, (255, 90, 40), (w // 2 - 4, 9), 2)
        pygame.draw.circle(s, (255, 90, 40), (w // 2 + 4, 9), 2)
        outlined_rect(s, (60, 50, 20), (4, 42, w - 8, 12))

    def _draw_icewalker(self, s, w, h, color):
        outlined_rect(s, (80, 140, 190), (6, 14, w - 12, 24))
        outlined_rect(s, color, (8, 16, w - 16, 20))
        pygame.draw.line(s, WHITE, (12, 20), (12, 34), 1)
        pygame.draw.line(s, WHITE, (w - 12, 20), (w - 12, 34), 1)
        pygame.draw.line(s, WHITE, (w // 2, 18), (w // 2, 34), 1)
        outlined_circle(s, (200, 235, 255), (w // 2, 10), 8)
        pygame.draw.polygon(s, (60, 140, 220), [(w // 2 - 6, 10), (w // 2 - 4, 8), (w // 2 - 4, 12)])
        pygame.draw.polygon(s, (60, 140, 220), [(w // 2 + 6, 10), (w // 2 + 4, 8), (w // 2 + 4, 12)])
        pygame.draw.polygon(s, (180, 220, 245), [(w // 2 - 10, 6), (w // 2 - 6, 0), (w // 2 - 4, 6)])
        pygame.draw.polygon(s, (180, 220, 245), [(w // 2 + 10, 6), (w // 2 + 6, 0), (w // 2 + 4, 6)])

    def _draw_iceguard(self, s, w, h, color):
        outlined_rect(s, (30, 45, 85), (2, 12, w - 4, 32))
        outlined_rect(s, (60, 90, 150), (4, 14, w - 8, 28))
        pygame.draw.line(s, (140, 200, 255), (6, 22), (w - 6, 22), 2)
        pygame.draw.line(s, (140, 200, 255), (w // 2, 16), (w // 2, 40), 2)
        outlined_circle(s, (60, 90, 150), (4, 18), 6)
        outlined_circle(s, (60, 90, 150), (w - 4, 18), 6)
        outlined_rect(s, (30, 45, 85), (w // 2 - 10, 2, 20, 14))
        pygame.draw.rect(s, (150, 240, 255), (w // 2 - 7, 8, 14, 3))

    def _draw_snowball(self, s, w, h, color):
        outlined_circle(s, (230, 240, 250), (w // 2, h // 2), w // 2 - 2)
        pygame.draw.circle(s, WHITE, (w // 2 - 4, h // 2 - 4), 4)
        pygame.draw.circle(s, (30, 40, 60), (w // 2 - 4, h // 2), 2)
        pygame.draw.circle(s, (30, 40, 60), (w // 2 + 4, h // 2), 2)
        for (ox, oy, r) in [(-6, 6, 2), (7, 5, 2), (-8, -2, 2), (8, -6, 2)]:
            pygame.draw.circle(s, (190, 210, 235), (w // 2 + ox, h // 2 + oy), r)

    def _draw_bat(self, s, w, h, color):
        cx, cy = w // 2, h // 2
        pygame.draw.polygon(s, (150, 40, 20), [(cx - 3, cy), (0, 2), (2, h - 2), (cx - 3, cy + 4)])
        pygame.draw.polygon(s, (150, 40, 20), [(cx + 3, cy), (w, 2), (w - 2, h - 2), (cx + 3, cy + 4)])
        pygame.draw.polygon(s, OUTLINE, [(cx - 3, cy), (0, 2), (2, h - 2), (cx - 3, cy + 4)], 2)
        pygame.draw.polygon(s, OUTLINE, [(cx + 3, cy), (w, 2), (w - 2, h - 2), (cx + 3, cy + 4)], 2)
        outlined_circle(s, color, (cx, cy), 8)
        pygame.draw.circle(s, (255, 220, 80), (cx - 3, cy - 1), 2)
        pygame.draw.circle(s, (255, 220, 80), (cx + 3, cy - 1), 2)
        draw_glow(s, (255, 140, 60), (cx, cy), 14, 90)

    def _draw_slime(self, s, w, h, color):
        pygame.draw.ellipse(s, (90, 25, 10), (0, 2, w, h))
        pygame.draw.ellipse(s, color, (1, 3, w - 2, h - 2))
        pygame.draw.arc(s, LAVA_BRIGHT, (3, 4, w - 6, h - 6), 0.5, 2.6, 2)
        pygame.draw.circle(s, FIRE_YELLOW, (w // 3, h // 2), 3)
        pygame.draw.circle(s, FIRE_YELLOW, (2 * w // 3, h // 2), 3)
        pygame.draw.circle(s, (40, 10, 5), (w // 3, h // 2), 1)
        pygame.draw.circle(s, (40, 10, 5), (2 * w // 3, h // 2), 1)

    def _draw_mushroom(self, s, w, h, color):
        outlined_rect(s, (200, 180, 140), (w // 2 - 4, h // 2 - 2, 8, h // 2 - 2))
        pygame.draw.ellipse(s, (60, 100, 50), (0, 0, w, h // 2 + 6))
        pygame.draw.ellipse(s, color, (1, 1, w - 2, h // 2 + 2))
        pygame.draw.circle(s, POISON_BRIGHT, (w // 3, h // 4), 3)
        pygame.draw.circle(s, POISON_BRIGHT, (2 * w // 3, h // 4 + 3), 3)
        pygame.draw.circle(s, POISON_BRIGHT, (w // 2, h // 6), 2)
        pygame.draw.circle(s, (30, 50, 20), (w // 3, h // 2 + 3), 2)
        pygame.draw.circle(s, (30, 50, 20), (2 * w // 3, h // 2 + 3), 2)

    def _draw_frog(self, s, w, h, color):
        pygame.draw.ellipse(s, (40, 90, 30), (0, 4, w, h - 4))
        pygame.draw.ellipse(s, color, (1, 5, w - 2, h - 6))
        pygame.draw.ellipse(s, (150, 200, 100), (6, h // 2, w - 12, h // 2 - 4))
        outlined_circle(s, (240, 220, 100), (w // 3, h // 3 - 2), 5)
        outlined_circle(s, (240, 220, 100), (2 * w // 3, h // 3 - 2), 5)
        pygame.draw.circle(s, BLACK, (w // 3, h // 3 - 2), 2)
        pygame.draw.circle(s, BLACK, (2 * w // 3, h // 3 - 2), 2)
        pygame.draw.circle(s, WHITE, (w // 3 - 1, h // 3 - 3), 1)
        pygame.draw.circle(s, WHITE, (2 * w // 3 - 1, h // 3 - 3), 1)

    def _draw_skeleton(self, s, w, h, color):
        pygame.draw.line(s, color, (w // 2 - 5, h - 12), (w // 2 - 5, h - 4), 3)
        pygame.draw.line(s, color, (w // 2 + 5, h - 12), (w // 2 + 5, h - 4), 3)
        pygame.draw.circle(s, color, (w // 2 - 5, h - 3), 2)
        pygame.draw.circle(s, color, (w // 2 + 5, h - 3), 2)
        for i in range(3):
            y = 22 + i * 5
            pygame.draw.line(s, color, (w // 2 - 9, y), (w // 2 + 9, y), 2)
        pygame.draw.line(s, color, (w // 2, 18), (w // 2, 38), 2)
        pygame.draw.circle(s, color, (w // 2 - 10, 20), 3)
        pygame.draw.circle(s, color, (w // 2 + 10, 20), 3)
        outlined_circle(s, color, (w // 2, 10), 9)
        pygame.draw.circle(s, (20, 20, 30), (w // 2 - 3, 10), 3)
        pygame.draw.circle(s, (20, 20, 30), (w // 2 + 3, 10), 3)
        pygame.draw.circle(s, (255, 60, 60), (w // 2 - 3, 10), 1)
        pygame.draw.circle(s, (255, 60, 60), (w // 2 + 3, 10), 1)
        pygame.draw.line(s, (20, 20, 30), (w // 2 - 3, 15), (w // 2 + 3, 15), 2)

    def _draw_ghost(self, s, w, h, color):
        body_color = (color[0], color[1], color[2], 220)
        pygame.draw.ellipse(s, body_color, (2, 0, w - 4, h - 8))
        pygame.draw.polygon(s, body_color, [
            (2, h - 15), (w // 2 - 6, h - 4), (w // 2, h - 12),
            (w // 2 + 6, h - 4), (w - 2, h - 15)
        ])
        pygame.draw.circle(s, (40, 20, 70), (w // 3, h // 3), 3)
        pygame.draw.circle(s, (40, 20, 70), (2 * w // 3, h // 3), 3)
        pygame.draw.circle(s, WHITE, (w // 3, h // 3 - 1), 1)
        pygame.draw.circle(s, WHITE, (2 * w // 3, h // 3 - 1), 1)

    def _draw_wraithbone(self, s, w, h, color):
        """魔魂亡骨：骷髅骨架外面裹着幽灵的魂体。"""
        cx = w // 2
        # 外层魂体
        haze = (color[0], color[1], color[2], 120)
        pygame.draw.ellipse(s, haze, (1, 3, w - 2, h - 12))
        pygame.draw.polygon(s, haze, [
            (1, h - 22), (cx - 10, h - 2), (cx, h - 16),
            (cx + 10, h - 2), (w - 1, h - 22),
        ])
        # 骨架：脊椎、肋骨、四肢
        bone = (238, 234, 214)
        pygame.draw.line(s, bone, (cx, 19), (cx, h - 14), 4)
        for i in range(4):
            y = 25 + i * 7
            pygame.draw.line(s, bone, (cx - 10, y), (cx + 10, y), 3)
        pygame.draw.line(s, bone, (cx - 9, 24), (cx - 15, 40), 3)     # 左臂
        pygame.draw.line(s, bone, (cx + 9, 24), (cx + 15, 13), 3)     # 举起的手臂
        pygame.draw.line(s, (206, 202, 186), (cx + 15, 13), (cx + 17, 38), 2)   # 镰柄
        pygame.draw.polygon(s, (226, 222, 206),
                            [(cx + 17, 6), (cx + 20, 16), (cx + 11, 10)])       # 镰刃
        pygame.draw.line(s, bone, (cx - 6, h - 15), (cx - 9, h - 3), 3)
        pygame.draw.line(s, bone, (cx + 6, h - 15), (cx + 9, h - 3), 3)
        # 头骨与魂火
        outlined_circle(s, bone, (cx, 12), 10)
        pygame.draw.circle(s, (26, 18, 40), (cx - 4, 12), 3)
        pygame.draw.circle(s, (26, 18, 40), (cx + 4, 12), 3)
        pygame.draw.circle(s, (150, 240, 255), (cx - 4, 11), 1)
        pygame.draw.circle(s, (150, 240, 255), (cx + 4, 11), 1)
        pygame.draw.line(s, (26, 18, 40), (cx - 4, 18), (cx + 4, 18), 2)
        draw_glow(s, (140, 110, 230), (cx, h // 2), 18, 80)

    def apply_damage(self, damage, game=None):
        aura_dr = min(LEADER_AURA_MAX_DAMAGE_REDUCTION,
                      max(0.0, getattr(self, 'aura_damage_reduction', 0)))
        if aura_dr > 0:
            damage = int(damage * (1 - aura_dr))
        if self.cfg.get("dr"):
            damage = int(damage * (1 - self.cfg["dr"]))
        if self.enemy_type == 5 and self.shield_active:
            damage = int(damage * 0.3)
        for affix in self.affix_instances:
            damage = affix.on_damaged(damage, game)
        damage = max(1, int(damage))
        self.health -= damage
        if self.enemy_type == 5 and self.shield_active and self.health < self.base_health * 0.7:
            self.shield_active = False
        return damage

    def apply_freeze(self, freeze_dur, slow_dur):
        self.freeze_timer = max(self.freeze_timer, freeze_dur)
        self.slow_timer = max(self.slow_timer, slow_dur)

    def heal_from_undead(self, amount):
        """附近有亡灵倒下时的回血，返回实际回复量。"""
        if self.health <= 0:
            return 0
        healed = min(amount, self.max_health - self.health)
        if healed <= 0:
            return 0
        self.health += healed
        return healed

    def update(self, platforms, barriers, ice_trails, all_sprites=None, game=None):
        self.anim_timer += 1
        if self.black_hole_lock > 0:
            self.black_hole_lock -= 1
            if self.freeze_timer > 0: self.freeze_timer -= 1
            if self.slow_timer > 0: self.slow_timer -= 1
            if self.stun_timer > 0: self.stun_timer -= 1
            if self.black_hole_lock == 0:
                resolve_platform_overlap(self, platforms)
            for affix in self.affix_instances:
                affix.update(game)
            return
        speed_mult = 1.0 + getattr(self, 'aura_speed_bonus', 0.0)
        if self.buff_timer > 0:
            self.buff_timer -= 1
            speed_mult *= 1.0 + TROLL_BUFF_SPEED
        if self.cross_buff_timer > 0:
            self.cross_buff_timer -= 1
            speed_mult *= 1.0 + TROLL_BUFF_SPEED

        frozen = self.freeze_timer > 0
        slowed = self.slow_timer > 0
        if self.freeze_timer > 0: self.freeze_timer -= 1
        if self.slow_timer > 0: self.slow_timer -= 1
        if slowed: speed_mult *= 0.5

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
            for affix in self.affix_instances:
                affix.update(game)
            return

        if self.is_flying:
            speed = self.base_speed * speed_mult
            if self.velocity_x == 0:
                self.velocity_x = random.choice([-1, 1])
            sign = 1 if self.velocity_x > 0 else -1
            target_cy = None
            # 召唤师模式：飞行敌人优先缠住玩家的召唤物，并与它保持同一高度
            chase = game.nearest_ally(self.rect.centerx, self.rect.centery) if game is not None else None
            if chase is not None:
                target_cy = chase.rect.centery
                dx = chase.rect.centerx - self.rect.centerx
                if dx > 1: sign = 1
                elif dx < -1: sign = -1
            self.rect.x += sign * speed
            if self.rect.left < 0:
                self.rect.left = 0; sign = 1
            elif self.rect.right > SCREEN_WIDTH:
                self.rect.right = SCREEN_WIDTH; sign = -1
            self.velocity_x = sign
            if game is not None:
                if target_cy is None:
                    target_cy = game.player.rect.centery
                dy = target_cy - self.rect.centery
                if abs(dy) > 2:
                    vy = 1.6 if dy > 0 else -1.6
                    if abs(dy) < 1.6: vy = dy
                    self.rect.y += vy
            if self.rect.top < 30: self.rect.top = 30
            if self.rect.bottom > SCREEN_HEIGHT - 30: self.rect.bottom = SCREEN_HEIGHT - 30
        else:
            self.velocity_y += GRAVITY
            if self.cfg.get("jump"):
                self.jump_timer += 1
                if self.jump_timer > self.next_jump_time and self.on_ground:
                    self.velocity_y = ENEMY_JUMP_POWER
                    self.on_ground = False
                    self.jump_timer = 0
                    self.next_jump_time = random.randint(60, 180)
            elif self.enemy_type == 4:
                self.ice_trail_timer += 1
                if self.ice_trail_timer >= 15 and self.on_ground:
                    trail = IceTrail(self.rect.centerx, self.rect.bottom)
                    ice_trails.add(trail)
                    if all_sprites is not None:
                        all_sprites.add(trail)
                    self.ice_trail_timer = 0

            if self.enemy_type == 9 and game is not None:
                self.spore_timer -= 1
                if self.spore_timer <= 0:
                    self.spore_timer = random.randint(180, 300)
                    direction = -1 if game.player.rect.centerx < self.rect.centerx else 1
                    fb = Fireball(self.rect.centerx, self.rect.centery - 10,
                                  direction * 4, -3, damage=6, color=(130, 210, 90))
                    game.fireballs.add(fb); game.all_sprites.add(fb)

            if self.core_target is not None and self.core_target.alive():
                # 护核防守：无视巡逻路线，直奔核心
                dx = self.core_target.rect.centerx - self.rect.centerx
                if abs(dx) > 24:
                    self.velocity_x = (1 if dx > 0 else -1) * self.base_speed * speed_mult
                else:
                    self.velocity_x = 0
            elif self.scene_type == BIOME_ICE and self.on_ground:
                self.velocity_x *= SLIDE_FACTOR
                if abs(self.velocity_x) < 0.3:
                    self.velocity_x = random.choice([-self.base_speed, self.base_speed]) * speed_mult
            else:
                self.velocity_x = (1 if self.velocity_x > 0 else -1) * self.base_speed * speed_mult

            self.rect.x += self.velocity_x
            collision_sprites = list(platforms) + [b for b in barriers if b.visible]
            for sprite in collision_sprites:
                if pygame.sprite.collide_rect(self, sprite):
                    if try_step_up(self, sprite):
                        continue
                    if self.velocity_x > 0:
                        self.rect.right = sprite.rect.left
                        self.velocity_x = -abs(self.velocity_x)
                    elif self.velocity_x < 0:
                        self.rect.left = sprite.rect.right
                        self.velocity_x = abs(self.velocity_x)

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

        for affix in self.affix_instances:
            affix.update(game)

    def draw_health_bar(self, surface):
        bar_w = max(self.rect.width, 30)
        bar_h = 4
        x = self.rect.centerx - bar_w // 2
        y = self.rect.y - 9
        pygame.draw.rect(surface, (30, 12, 18), (x - 1, y - 1, bar_w + 2, bar_h + 2))
        ratio = max(0, self.health / self.max_health)
        if ratio > 0.6: c = (120, 220, 130)
        elif ratio > 0.3: c = (250, 210, 90)
        else: c = (230, 80, 80)
        pygame.draw.rect(surface, c, (x, y, bar_w * ratio, bar_h))
        pygame.draw.rect(surface, (240, 240, 250), (x, y, bar_w, bar_h), 1)
        if self.shield_active and self.enemy_type == 5:
            pygame.draw.rect(surface, CYAN, (x, y - 4, bar_w, 2))

    def draw_affix_icons(self, surface):
        draw_affix_icons_row(surface, self)


class AllyUnit(pygame.sprite.Sprite):
    """被捕获敌人的友方版本：贴图与词缀复制自原敌人，行动由本类接管。

    普通单位左右扫荡，精英单位主动追击最近的敌人，飞行单位贴着目标的高度飞行。
    所有友军都会被敌人伤害。
    """

    CONTACT_CD = 30        # 友军攻击间隔（帧）
    HURT_CD = 26           # 友军受击后的无敌时间（帧）
    SEEK_RANGE = 560       # 索敌半径
    STOP_DIST = 44         # 近战贴脸距离

    def __init__(self, x, y, depth, template, scene_type, slot=-1):
        super().__init__()
        self.depth = depth
        self.scene_type = scene_type
        self.slot = slot
        self.template = template
        self.is_ally = True
        self.is_ember = False
        self.is_mirror_duelist = False
        self.is_summoned = True
        self.is_pact = False
        self.lifetime = int(template.get("lifetime", 0) or 0)
        self.is_elite = bool(template.get("is_elite"))
        self.enemy_type = template.get("enemy_type", 0)
        self.elite_kind = template.get("elite_kind")
        self.cfg = template.get("cfg") or {}
        self.is_flying = bool(template.get("is_flying"))
        self.base_speed = float(template.get("base_speed", 2.0))
        self.damage_multiplier = 1.0
        self.aura_speed_bonus = 0.0
        self.buff_timer = 0          # 被巨魔狂呼者增幅的剩余帧数
        self.cross_buff_timer = 0
        self.aura_damage_reduction = 0.0
        self.slow_immune = False
        self.max_health = self._health_of(template)
        self.health = self.max_health
        self.contact_damage = self._attack_of(template, self.max_health)
        self.image = template["image"].copy()
        self._mark_friendly()
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)
        self.velocity_x = random.choice([-1, 1]) * self.base_speed
        self.velocity_y = 0
        self.on_ground = False
        self.facing = 1 if self.velocity_x >= 0 else -1
        self.freeze_timer = 0
        self.slow_timer = 0
        self.stun_timer = 0
        self.black_hole_lock = 0
        self.black_hole_angle = None
        self.anim_timer = 0
        self.attack_cd = 0
        self.hurt_cd = 0
        self.affix_names = list(template.get("affix_names") or [])
        self.affix_instances = []
        self.affix_names = [n for n in self.affix_names
                            if n in AFFIX_TABLE and n not in ALLY_BAD_AFFIXES]
        for name in self.affix_names:
            inst = AFFIX_TABLE[name](self)
            self.affix_instances.append(inst)
            inst.on_spawn(None)

    @staticmethod
    def _health_of(template):
        base = max(1, int(template.get("max_health", 30)))
        return max(1, int(base * template.get("hp_mult", 1.0)))

    @staticmethod
    def _attack_of(template, max_health):
        return (max(8, int(max_health * ALLY_ATTACK_RATIO))
                + int(template.get("atk_bonus", 0)))

    def refresh_from_template(self, template):
        """商店强化后同步到这只已经出场的召唤物，血量按比例保留。"""
        self.template = template
        ratio = (self.health / self.max_health) if self.max_health > 0 else 1.0
        self.max_health = self._health_of(template)
        self.contact_damage = self._attack_of(template, self.max_health)
        self.health = max(1, min(self.max_health, int(self.max_health * ratio)))
        for name in template.get("affix_names") or []:
            if name in self.affix_names or name in ALLY_BAD_AFFIXES:
                continue
            cls = AFFIX_TABLE.get(name)
            if cls is None:
                continue
            self.affix_names.append(name)
            inst = cls(self)
            self.affix_instances.append(inst)
            inst.on_spawn(None)

    def teleport_to(self, x, y):
        """换房间时把召唤物带到玩家身边。"""
        self.rect.midbottom = (x, y)
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        self.velocity_x = 0
        self.velocity_y = 0
        self.attack_cd = 0
        self.hurt_cd = 0

    def _mark_friendly(self):
        """给复制来的贴图描一圈青色边，方便一眼区分敌我。"""
        w, h = self.image.get_size()
        pygame.draw.rect(self.image, (110, 240, 220), (0, 0, w, h), 2, border_radius=6)
        pygame.draw.polygon(self.image, (110, 240, 220),
                            [(w // 2 - 5, 0), (w // 2 + 5, 0), (w // 2, 7)])

    def apply_damage(self, damage, game=None):
        aura_dr = min(LEADER_AURA_MAX_DAMAGE_REDUCTION,
                      max(0.0, self.aura_damage_reduction))
        if aura_dr > 0:
            damage = int(damage * (1 - aura_dr))
        for affix in self.affix_instances:
            damage = affix.on_damaged(damage, game)
        damage = max(1, int(damage))
        self.health -= damage
        return damage

    def apply_freeze(self, freeze_dur, slow_dur):
        if self.is_elite:
            freeze_dur //= 2
        self.freeze_timer = max(self.freeze_timer, freeze_dur)
        self.slow_timer = max(self.slow_timer, slow_dur)

    def take_damage(self, damage, game=None):
        """被敌人命中，返回这次是否真的扣了血。"""
        if self.health <= 0 or self.hurt_cd > 0:
            return False
        self.apply_damage(damage, game)
        self.hurt_cd = self.HURT_CD
        if self.health < 0:
            self.health = 0
        return True

    def update(self, platforms, barriers, game=None):
        self.anim_timer += 1
        if self.lifetime > 0:
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.kill()
                return
        if self.hurt_cd > 0: self.hurt_cd -= 1
        if self.attack_cd > 0: self.attack_cd -= 1
        if self.freeze_timer > 0: self.freeze_timer -= 1
        if self.slow_timer > 0: self.slow_timer -= 1
        speed_mult = 1.0 + self.aura_speed_bonus
        if self.buff_timer > 0:
            self.buff_timer -= 1
            speed_mult *= 1.0 + TROLL_BUFF_SPEED
        if self.cross_buff_timer > 0:
            self.cross_buff_timer -= 1
            speed_mult *= 1.0 + TROLL_BUFF_SPEED
        if self.slow_timer > 0: speed_mult *= 0.5
        frozen = self.freeze_timer > 0

        target = None
        if game is not None and not frozen:
            # 飞行单位负责空中拦截，索敌范围放到整屏
            rng = SCREEN_WIDTH if self.is_flying else self.SEEK_RANGE
            target = game.nearest_enemy_to(self.rect.centerx, self.rect.centery, rng)

        if frozen:
            self.velocity_x = 0
        elif self.is_flying:
            self._fly(target, speed_mult)
        elif self.is_elite:
            self._chase(target, speed_mult)
        else:
            self._patrol(speed_mult)

        if not self.is_flying:
            self.velocity_y += GRAVITY
            self.rect.x += self.velocity_x
            collision_sprites = list(platforms) + [b for b in barriers if b.visible]
            for sprite in collision_sprites:
                if pygame.sprite.collide_rect(self, sprite):
                    if try_step_up(self, sprite):
                        continue
                    if self.velocity_x > 0:
                        self.rect.right = sprite.rect.left
                        self.velocity_x = -abs(self.velocity_x)
                    elif self.velocity_x < 0:
                        self.rect.left = sprite.rect.right
                        self.velocity_x = abs(self.velocity_x)
            self.rect.y += self.velocity_y
            self.on_ground = False
            for platform in platforms:
                if pygame.sprite.collide_rect(self, platform):
                    if self.velocity_y > 0:
                        self.rect.bottom = platform.rect.top
                        self.velocity_y = 0
                        self.on_ground = True
                    elif self.velocity_y < 0:
                        self.rect.top = platform.rect.bottom
                        self.velocity_y = 0
            if self.rect.left < 0: self.rect.left = 0
            if self.rect.right > SCREEN_WIDTH: self.rect.right = SCREEN_WIDTH

        for affix in self.affix_instances:
            affix.update(game)

    def _patrol(self, speed_mult):
        self.velocity_x = (1 if self.velocity_x >= 0 else -1) * self.base_speed * speed_mult

    def _chase(self, target, speed_mult):
        if target is None:
            self.velocity_x = (1 if self.velocity_x >= 0 else -1) * self.base_speed * 0.6 * speed_mult
            return
        dx = target.rect.centerx - self.rect.centerx
        if abs(dx) > self.STOP_DIST:
            self.velocity_x = (1 if dx > 0 else -1) * self.base_speed * speed_mult
        else:
            self.velocity_x = 0

    def _fly(self, target, speed_mult):
        speed = self.base_speed * speed_mult
        if target is not None:
            dx = target.rect.centerx - self.rect.centerx
            if dx > 2: self.rect.x += speed
            elif dx < -2: self.rect.x -= speed
            dy = target.rect.centery - self.rect.centery
            if abs(dy) > 2:
                self.rect.y += 1.6 if dy > 0 else -1.6
        else:
            if self.velocity_x == 0:
                self.velocity_x = random.choice([-1, 1])
            self.rect.x += (1 if self.velocity_x > 0 else -1) * speed
        if self.rect.top < 30: self.rect.top = 30
        if self.rect.bottom > SCREEN_HEIGHT - 30: self.rect.bottom = SCREEN_HEIGHT - 30
        if self.rect.left < 0:
            self.rect.left = 0; self.velocity_x = 1
        elif self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH; self.velocity_x = -1

    def draw_health_bar(self, surface):
        bar_w = max(self.rect.width, 30)
        bar_h = 4
        x = self.rect.centerx - bar_w // 2
        y = self.rect.y - 9
        pygame.draw.rect(surface, (12, 30, 34), (x - 1, y - 1, bar_w + 2, bar_h + 2))
        ratio = max(0.0, self.health / self.max_health)
        if ratio > 0.5: c = (120, 240, 220)
        elif ratio > 0.25: c = (250, 210, 90)
        else: c = (230, 80, 80)
        pygame.draw.rect(surface, c, (x, y, bar_w * ratio, bar_h))
        pygame.draw.rect(surface, (200, 250, 245), (x, y, bar_w, bar_h), 1)
        if self.lifetime > 0:
            f = get_font(12)
            t = f.render(f"{self.lifetime / FPS:.0f}s", True, (180, 245, 220))
            surface.blit(t, (self.rect.centerx - t.get_width() // 2, y - 15))

    def draw_affix_icons(self, surface):
        draw_affix_icons_row(surface, self)


class EliteEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y, depth, scene_type, kind):
        super().__init__()
        self.kind = kind
        self.scene_type = scene_type
        self.depth = depth
        self.is_elite = True
        self.is_ember = False
        self.is_blood_minion = False
        self.is_undead = kind == "vampire"
        self.is_zombie = False
        self.is_giant_zombie = False
        self.is_bone_carrier = False
        self.is_church_cross = False
        self.contact_harmful = True
        self.enemy_type = -1
        self.is_flying = False
        self.split_done = True
        self.stun_timer = 0
        self.freeze_timer = 0
        self.black_hole_lock = 0
        self.black_hole_angle = None
        self.slow_timer = 0
        data = ELITE_STATS[kind]
        self.elite_name = data["name"]
        self.max_health = int(data["hp_base"] + depth * data["hp_scale"] + 1.0 * depth ** 2)
        self.health = self.max_health
        self.base_speed = data["speed"]
        self.damage_multiplier = 1.0
        self.aura_speed_bonus = 0.0
        self.aura_damage_reduction = 0.0
        self.buff_timer = 0          # 被巨魔狂呼者增幅的剩余帧数
        self.cross_buff_timer = 0    # 血腥十字架附近的增幅
        self.anim_timer = 0
        size = data["size"]
        self.body_size = size
        self.image = pygame.Surface(size, pygame.SRCALPHA)
        self._draw_body(data["color"], size, data.get("shape", "warden"))
        if data.get("giant"):
            # 大号巨魔：整体放大（对照巨型骷髅的 2.2 倍，这里温和一些）
            self.image = pygame.transform.scale(
                self.image, (int(size[0] * TROLL_GIANT_SCALE),
                             int(size[1] * TROLL_GIANT_SCALE)))
        self.rect = self.image.get_rect()
        self.rect.x = x; self.rect.y = y
        self.velocity_x = random.choice([-1, 1]) * self.base_speed
        self.velocity_y = 0
        self.on_ground = False
        self.facing = -1 if self.velocity_x < 0 else 1
        self.state = "IDLE"
        self.state_timer = 0
        self.skill_timer = data["skill_cd"] // 2
        self.skill_cd_base = data["skill_cd"]
        self.phase = 1
        self.phase_changed = False
        self.invincible_timer = 0
        self.shield_active = False
        fixed = list(data.get("fixed_affixes", []))
        random_count = 0
        if depth >= 10: random_count = 1
        if depth >= 15: random_count = 2
        random_affixes = roll_affixes(depth, random_count)
        self.affix_names = fixed + [a for a in random_affixes if a not in fixed]
        self.affix_instances = []
        for name in self.affix_names:
            cls = AFFIX_TABLE.get(name)
            if cls:
                inst = cls(self)
                self.affix_instances.append(inst)
                inst.on_spawn(None)

    def _draw_body(self, color, size, shape):
        w, h = size
        s = self.image
        pygame.draw.ellipse(s, (0, 0, 0, 90), (4, h - 5, w - 8, 6))
        if shape == "wolf":
            self._draw_wolf(s, w, h, color)
        elif shape == "troll":
            self._draw_troll(s, w, h, color)
        elif shape == "vampire":
            self._draw_vampire(s, w, h, color)
        elif shape in ("gargoyle", "gargoyle_fly"):
            self._draw_gargoyle(s, w, h, color, flying=(shape == "gargoyle_fly"))
        elif shape == "beast":
            pygame.draw.polygon(s, (90, 40, 120), [
                (w // 2 - 12, 20), (w // 2 + 12, 20),
                (w // 2 + 16, h - 4), (w // 2 - 16, h - 4)
            ])
            outlined_circle(s, color, (w // 2, h - 12), 16)
            outlined_circle(s, color, (w - 12, h // 3), 12)
            pygame.draw.circle(s, (255, 90, 60), (w - 8, h // 3), 3)
            pygame.draw.circle(s, (255, 90, 60), (w - 16, h // 3), 3)
            for i in range(3):
                pygame.draw.line(s, (200, 230, 250), (w - 20 - i * 6, h - 14), (w - 26 - i * 6, h - 4), 2)
            pygame.draw.line(s, color, (8, h - 14), (0, h - 26), 3)
        elif shape in ("witch", "mage", "priest", "necromancer"):
            body_c = color
            pygame.draw.polygon(s, (90, 40, 120), [
                (w // 2 - 12, 20), (w // 2 + 12, 20),
                (w // 2 + 16, h - 4), (w // 2 - 16, h - 4)
            ])
            outlined_rect(s, body_c, (w // 2 - 12, 22, 24, h - 34))
            pygame.draw.polygon(s, (60, 40, 90), [
                (w // 2 - 14, 22), (w // 2 + 14, 22), (w // 2 + 18, h - 4), (w // 2 - 18, h - 4)
            ])
            pygame.draw.polygon(s, body_c, [
                (w // 2 - 12, 24), (w // 2 + 12, 24), (w // 2 + 15, h - 6), (w // 2 - 15, h - 6)
            ])
            outlined_circle(s, body_c, (w // 2, 12), 12)
            pygame.draw.ellipse(s, (20, 15, 30), (w // 2 - 8, 10, 16, 10))
            pygame.draw.circle(s, (255, 200, 100), (w // 2 - 3, 14), 2)
            pygame.draw.circle(s, (255, 200, 100), (w // 2 + 3, 14), 2)
            pygame.draw.line(s, (70, 50, 30), (w - 8, 20), (w - 4, h - 4), 3)
            pygame.draw.circle(s, body_c, (w - 8, 18), 5)
            pygame.draw.circle(s, WHITE, (w - 8, 18), 2)
        else:
            pygame.draw.polygon(s, (90, 40, 120), [
                (w // 2 - 12, 20), (w // 2 + 12, 20),
                (w // 2 + 16, h - 4), (w // 2 - 16, h - 4)
            ])
            outlined_rect(s, color, (w // 2 - 13, 22, 26, h - 34))
            pygame.draw.rect(s, (250, 230, 200, 100), (w // 2 - 10, 26, 20, 4))
            pygame.draw.line(s, (255, 255, 255, 100), (w // 2 - 10, 26), (w // 2 - 10, h - 14), 1)
            outlined_circle(s, color, (w // 2, 12), 12)
            pygame.draw.rect(s, (255, 60, 60), (w // 2 - 6, 14, 12, 3))
            pygame.draw.line(s, (200, 200, 220), (w - 4, 20), (w - 8, h - 10), 3)
            pygame.draw.line(s, (250, 250, 255), (w - 4, 20), (w - 6, h - 10), 1)
        pygame.draw.rect(s, (255, 220, 130, 180), (0, 0, w, h), 2, border_radius=6)

    def _draw_vampire(self, s, w, h, color):
        """吸血鬼：暗红披风、苍白面孔与狭长獠牙。"""
        cx = w // 2
        pygame.draw.ellipse(s, (0, 0, 0, 100), (7, h - 5, w - 14, 6))
        pygame.draw.polygon(s, (54, 12, 22), [
            (cx - 17, 20), (cx + 17, 20), (cx + 21, h - 5), (cx - 21, h - 5)
        ])
        pygame.draw.polygon(s, color, [
            (cx - 12, 22), (cx + 12, 22), (cx + 15, h - 8), (cx - 15, h - 8)
        ])
        pygame.draw.polygon(s, (92, 22, 38), [
            (cx - 17, 24), (cx - 25, h - 8), (cx - 9, h - 18)
        ])
        pygame.draw.polygon(s, (92, 22, 38), [
            (cx + 17, 24), (cx + 25, h - 8), (cx + 9, h - 18)
        ])
        outlined_circle(s, (224, 202, 190), (cx, 13), 10)
        pygame.draw.polygon(s, (42, 8, 16), [
            (cx - 10, 11), (cx - 5, 2), (cx, 7), (cx + 5, 2), (cx + 10, 11)
        ])
        pygame.draw.circle(s, (255, 68, 78), (cx - 3, 12), 2)
        pygame.draw.circle(s, (255, 68, 78), (cx + 3, 12), 2)
        pygame.draw.polygon(s, WHITE, [(cx - 5, 19), (cx - 3, 24), (cx - 1, 19)])
        pygame.draw.polygon(s, WHITE, [(cx + 1, 19), (cx + 3, 24), (cx + 5, 19)])
        pygame.draw.line(s, (245, 210, 190), (cx - 18, 32), (cx - 8, 42), 3)
        pygame.draw.line(s, (245, 210, 190), (cx + 18, 32), (cx + 8, 42), 3)
        draw_glow(s, (224, 54, 78), (cx, h // 2), 20, 45)

    def _draw_gargoyle(self, s, w, h, color, flying=False):
        """石像鬼：青色的人形蝠翼怪物，石像阶段会换成灰色。"""
        cx = w // 2
        wing_span = 23 if flying else 17
        wing_y = h // 2 - 10 if flying else h // 2
        pygame.draw.polygon(s, _shade_color(color, -45), [
            (cx - 7, wing_y), (max(1, cx - wing_span), wing_y - 14),
            (max(2, cx - 15), wing_y + 18), (cx - 5, wing_y + 8)
        ])
        pygame.draw.polygon(s, _shade_color(color, -45), [
            (cx + 7, wing_y), (min(w - 1, cx + wing_span), wing_y - 14),
            (min(w - 2, cx + 15), wing_y + 18), (cx + 5, wing_y + 8)
        ])
        outlined_rect(s, color, (cx - 12, 22, 24, h - 30))
        outlined_circle(s, color, (cx, 14), 11)
        pygame.draw.polygon(s, color, [
            (cx - 9, 10), (cx - 12, 1), (cx - 3, 7)
        ])
        pygame.draw.polygon(s, color, [
            (cx + 9, 10), (cx + 12, 1), (cx + 3, 7)
        ])
        pygame.draw.circle(s, (255, 208, 90), (cx - 4, 13), 2)
        pygame.draw.circle(s, (255, 208, 90), (cx + 4, 13), 2)
        pygame.draw.line(s, _shade_color(color, -35), (cx - 7, h - 18), (cx - 9, h - 5), 4)
        pygame.draw.line(s, _shade_color(color, -35), (cx + 7, h - 18), (cx + 9, h - 5), 4)
        draw_glow(s, color, (cx, h // 2), 18 if flying else 12, 30 if flying else 12)

    def _draw_wolf(self, s, w, h, color):
        """冰爪狼：低伏的四足兽，银白爪牙与发亮的眼睛。"""
        body = (96, 140, 176)
        fur = (208, 236, 252)
        pygame.draw.ellipse(s, body, (6, h - 26, w - 12, 22))
        pygame.draw.ellipse(s, color, (8, h - 24, w - 16, 16))
        pygame.draw.ellipse(s, body, (w - 26, h - 34, 22, 18))          # 头
        pygame.draw.polygon(s, body, [(w - 26, h - 32), (w - 22, h - 40), (w - 16, h - 30)])
        pygame.draw.polygon(s, body, [(w - 16, h - 32), (w - 12, h - 40), (w - 8, h - 30)])
        pygame.draw.circle(s, (255, 220, 120), (w - 18, h - 28), 2)
        pygame.draw.polygon(s, (236, 240, 246), [(w - 8, h - 26), (w - 2, h - 24), (w - 8, h - 21)])
        for i in range(4):
            x = 10 + i * 9
            pygame.draw.line(s, body, (x, h - 8), (x - 2, h - 2), 3)
            pygame.draw.line(s, (226, 240, 252), (x - 2, h - 3), (x - 4, h - 1), 2)
        for i in range(3):
            pygame.draw.line(s, fur, (12 + i * 7, h - 26), (10 + i * 7, h - 18), 2)
        pygame.draw.line(s, color, (6, h - 22), (0, h - 32), 3)

    def _draw_troll(self, s, w, h, color):
        """巨魔：青色皮肤、银色獠牙、红色残破衣服。"""
        skin = color
        skin_dark = (max(0, color[0] - 46), max(0, color[1] - 46), max(0, color[2] - 46))
        cloth = (176, 58, 54)
        cloth_torn = (126, 38, 36)
        cx = w // 2
        # 腿与脚
        outlined_rect(s, skin_dark, (cx - 13, h - 20, 10, 18))
        outlined_rect(s, skin_dark, (cx + 3, h - 20, 10, 18))
        # 残破红袍
        pygame.draw.polygon(s, cloth, [(cx - 15, 26), (cx + 15, 26),
                                       (cx + 17, h - 20), (cx - 17, h - 20)])
        pygame.draw.polygon(s, cloth_torn, [(cx - 17, h - 20), (cx - 8, h - 26),
                                            (cx - 2, h - 19), (cx + 6, h - 27),
                                            (cx + 17, h - 20)])
        pygame.draw.line(s, cloth_torn, (cx - 4, 30), (cx + 2, h - 24), 2)
        # 手臂与手
        outlined_rect(s, skin, (cx - 20, 30, 8, 26))
        outlined_rect(s, skin, (cx + 12, 30, 8, 26))
        # 头、耳朵、獠牙
        outlined_circle(s, skin, (cx, 16), 13)
        pygame.draw.polygon(s, skin, [(cx - 13, 14), (cx - 22, 8), (cx - 12, 22)])
        pygame.draw.polygon(s, skin, [(cx + 13, 14), (cx + 22, 8), (cx + 12, 22)])
        pygame.draw.circle(s, (60, 30, 30), (cx - 5, 13), 3)
        pygame.draw.circle(s, (60, 30, 30), (cx + 5, 13), 3)
        pygame.draw.circle(s, (255, 210, 120), (cx - 5, 12), 1)
        pygame.draw.circle(s, (255, 210, 120), (cx + 5, 12), 1)
        pygame.draw.line(s, (36, 26, 30), (cx - 6, 22), (cx + 6, 22), 2)
        for sx, sgn in ((cx - 5, -1), (cx + 5, 1)):
            pygame.draw.polygon(s, (226, 230, 236),
                                [(sx, 22), (sx + sgn * 3, 30), (sx + sgn * 3, 22)])

    def apply_damage(self, damage, game=None):
        aura_dr = min(LEADER_AURA_MAX_DAMAGE_REDUCTION,
                      max(0.0, self.aura_damage_reduction))
        if aura_dr > 0:
            damage = int(damage * (1 - aura_dr))
        for affix in self.affix_instances:
            damage = affix.on_damaged(damage, game)
        damage = max(1, int(damage))
        self.health -= damage
        return damage

    def apply_freeze(self, freeze_dur, slow_dur):
        self.freeze_timer = max(self.freeze_timer, freeze_dur // 2)
        self.slow_timer = max(self.slow_timer, slow_dur)

    def update(self, platforms, barriers, ice_trails, all_sprites=None, game=None):
        self.anim_timer += 1
        if self.black_hole_lock > 0:
            self.black_hole_lock -= 1
            if self.freeze_timer > 0: self.freeze_timer -= 1
            if self.slow_timer > 0: self.slow_timer -= 1
            if self.stun_timer > 0: self.stun_timer -= 1
            if self.black_hole_lock == 0:
                resolve_platform_overlap(self, platforms)
            for affix in self.affix_instances:
                affix.update(game)
            return
        self.velocity_y += GRAVITY
        speed_mult = 1.0 + self.aura_speed_bonus
        if self.buff_timer > 0:
            self.buff_timer -= 1
            speed_mult *= 1.0 + TROLL_BUFF_SPEED
        if self.cross_buff_timer > 0:
            self.cross_buff_timer -= 1
            speed_mult *= 1.0 + TROLL_BUFF_SPEED

        frozen = self.freeze_timer > 0
        slowed = self.slow_timer > 0
        if self.freeze_timer > 0: self.freeze_timer -= 1
        if self.slow_timer > 0: self.slow_timer -= 1
        if slowed: speed_mult *= 0.5

        if self.stun_timer > 0:
            self.stun_timer -= 1
            self.velocity_x = 0
            self.rect.y += self.velocity_y
            self.on_ground = False
            for platform in platforms:
                if pygame.sprite.collide_rect(self, platform):
                    if self.velocity_y > 0:
                        self.rect.bottom = platform.rect.top
                        self.velocity_y = 0
                        self.on_ground = True
            for affix in self.affix_instances:
                affix.update(game)
            return

        if frozen:
            self.velocity_x = 0
            self.rect.y += self.velocity_y
            self.on_ground = False
            for platform in platforms:
                if pygame.sprite.collide_rect(self, platform):
                    if self.velocity_y > 0:
                        self.rect.bottom = platform.rect.top
                        self.velocity_y = 0
                        self.on_ground = True
            for affix in self.affix_instances:
                affix.update(game)
            return

        # 阶段转换：不再使用 nova，改为四周落地预警爆点
        if not self.phase_changed and self.health <= self.max_health * 0.5:
            self.phase_changed = True
            self.invincible_timer = 60
            self.skill_cd_base = int(self.skill_cd_base * 0.7)
            self.base_speed *= 1.2
            if game is not None:
                for i in range(4):
                    wx = self.rect.centerx + (i - 1.5) * 90
                    wx = max(60, min(wx, SCREEN_WIDTH - 60))
                    w = WarningCircle(wx, SCREEN_HEIGHT - 40, delay=45,
                                      radius=40, spawn_type="spike")
                    game.warnings.add(w); game.all_sprites.add(w)
                game.show_message(f"{self.elite_name} 进入狂暴状态！", 1500)

        if self.invincible_timer > 0: self.invincible_timer -= 1

        if self.state == "IDLE":
            self._idle_behavior(platforms, barriers, game, speed_mult)
        elif self.state == "LEAP":
            # 扑击：上升时穿过平台，落下时才踩地
            self.state_timer -= 1
            self.rect.x += self.velocity_x
            if self.rect.left < 0:
                self.rect.left = 0; self.velocity_x = abs(self.velocity_x)
            elif self.rect.right > SCREEN_WIDTH:
                self.rect.right = SCREEN_WIDTH; self.velocity_x = -abs(self.velocity_x)
            self.rect.y += self.velocity_y
            self.on_ground = False
            if self.velocity_y >= 0:
                for platform in platforms:
                    if pygame.sprite.collide_rect(self, platform):
                        self.rect.bottom = platform.rect.top
                        self.velocity_y = 0
                        self.on_ground = True
                        break
            if self.on_ground or self.state_timer <= 0:
                self.state = "IDLE"
                self.skill_timer = self.skill_cd_base
            for affix in self.affix_instances:
                affix.update(game)
            return
        else:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "IDLE"
                self.skill_timer = self.skill_cd_base

        for affix in self.affix_instances:
            affix.update(game)

        self.rect.x += self.velocity_x
        collision_sprites = list(platforms) + [b for b in barriers if b.visible]
        for sprite in collision_sprites:
            if pygame.sprite.collide_rect(self, sprite):
                if try_step_up(self, sprite):
                    continue
                if self.velocity_x > 0:
                    self.rect.right = sprite.rect.left; self.velocity_x = -abs(self.velocity_x)
                elif self.velocity_x < 0:
                    self.rect.left = sprite.rect.right; self.velocity_x = abs(self.velocity_x)

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

    def _idle_behavior(self, platforms, barriers, game, speed_mult=1.0):
        if game is None: return
        player = game.player
        dx = player.rect.centerx - self.rect.centerx
        dist = abs(dx)
        if dx > 0: self.facing = 1
        elif dx < 0: self.facing = -1
        if self.skill_timer > 0: self.skill_timer -= 1
        if self.skill_timer <= 0:
            self._cast_skill(game, player); return
        speed = self.base_speed * speed_mult
        if dist > 60: self.velocity_x = self.facing * speed
        else: self.velocity_x = 0

    def _cast_skill(self, game, player):
        kind = self.kind
        if kind == "hook_warden": self._skill_hook(game, player)
        elif kind == "shadow_blade": self._skill_blink(game, player)
        elif kind == "bone_caller": self._skill_summon(game)
        elif kind == "frost_claw": self._skill_charge(game, player)
        elif kind == "ice_witch": self._skill_ice_cone(game, player)
        elif kind == "ember_mage": self._skill_fireball(game, player)
        elif kind == "plague_priest": self._skill_plague(game, player)
        elif kind == "frost_wolf": self._skill_leap(game, player)
        elif kind == "troll_hunter": self._skill_shoot(game, player)
        elif kind == "troll_howler": self._skill_howl(game)

    def _skill_leap(self, game, player):
        """冰爪狼：蹲一下再扑向玩家。起跳后上升阶段无视平台，落下时才踩地，
        所以能跳上较低的平台，跳不上太高的。"""
        self.state = "LEAP"
        self.state_timer = 90
        dx = player.rect.centerx - self.rect.centerx
        self.facing = 1 if dx >= 0 else -1
        self.velocity_x = self.facing * 4.2
        self.velocity_y = JUMP_POWER_BASE          # 和玩家初始蓄力满跳一样高
        self.on_ground = False

    def _skill_shoot(self, game, player):
        """巨魔猎手：朝玩家方向打一发尖锐石子。"""
        self.state = "SHOOT"; self.state_timer = 30
        self.velocity_x = 0
        if game is None:
            return
        sx, sy = self.rect.centerx, self.rect.centery
        angle = math.atan2(player.rect.centery - sy, player.rect.centerx - sx)
        speed = 7.5
        shot = Fireball(sx, sy, math.cos(angle) * speed, math.sin(angle) * speed,
                        damage=int(9 + self.depth * 0.6), color=(206, 216, 228))
        game.fireballs.add(shot)
        game.all_sprites.add(shot)
        self.facing = 1 if player.rect.centerx >= sx else -1

    def _skill_howl(self, game):
        """巨魔狂呼者：半个屏幕内的敌人（含自己）增幅 5 秒。"""
        self.state = "HOWL"; self.state_timer = 60
        self.velocity_x = 0
        if game is None:
            return
        cx, cy = self.rect.centerx, self.rect.centery
        count = 0
        for other in list(game.enemies):
            if other is self or getattr(other, 'health', 0) <= 0:
                continue
            if (abs(other.rect.centerx - cx) <= TROLL_BUFF_RANGE
                    and abs(other.rect.centery - cy) <= TROLL_BUFF_RANGE):
                other.buff_timer = TROLL_BUFF_DURATION
                count += 1
        self.buff_timer = TROLL_BUFF_DURATION
        game.show_message(
            f"{self.elite_name} 怒吼！{count + 1} 个单位被增幅（移速与攻击 +50%）", 2000)

    def _skill_hook(self, game, player):
        self.state = "HOOK"; self.state_timer = 45
        self.velocity_x = 0
        sx = self.rect.centerx; sy = self.rect.centery
        px = player.rect.centerx; py = player.rect.centery
        angle = math.atan2(py - sy, px - sx)
        self.facing = 1 if px > sx else -1
        if game is not None:
            hook = HookProjectile(sx, sy, angle, owner=self, damage=10)
            game.hook_projectiles.add(hook); game.all_sprites.add(hook)

    def _skill_blink(self, game, player):
        self.state = "BLINK"; self.state_timer = 30
        side = -1 if player.facing_right else 1
        new_x = max(40, min(player.rect.centerx + side * 40, SCREEN_WIDTH - 40))
        self.rect.centerx = new_x
        self.rect.bottom = player.rect.bottom
        for angle_off in (-0.25, 0, 0.25):
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            angle = math.atan2(dy, dx) + angle_off
            fb = Fireball(self.rect.centerx, self.rect.centery,
                          math.cos(angle) * 7, math.sin(angle) * 7, damage=8,
                          color=(180, 130, 240))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _skill_summon(self, game):
        self.state = "SUMMON"; self.state_timer = 45
        for _ in range(2):
            x = random.randint(80, SCREEN_WIDTH - 80)
            y = SCREEN_HEIGHT - 60
            circle = SummonCircle(x, y - 15, 11, self.scene_type, self.depth, delay=45)
            game.summon_circles.add(circle); game.all_sprites.add(circle)

    def _skill_charge(self, game, player):
        self.state = "CHARGE"; self.state_timer = 45
        direction = 1 if player.rect.centerx > self.rect.centerx else -1
        self.velocity_x = direction * 12
        for i in range(3):
            x = max(40, min(self.rect.centerx + direction * (60 + i * 40), SCREEN_WIDTH - 40))
            trap = IceTrap(x, SCREEN_HEIGHT - 40)
            trap.cycle = [False] * 30 + [True] * 60 + [False] * (ICE_TRAP_COOLDOWN - 90)
            trap.timer = 0
            game.traps.add(trap); game.all_sprites.add(trap)

    def _skill_ice_cone(self, game, player):
        self.state = "ICE_CONE"; self.state_timer = 45
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        base_angle = math.atan2(dy, dx)
        for off in (-0.3, 0, 0.3):
            a = base_angle + off
            fb = Fireball(self.rect.centerx, self.rect.centery,
                          math.cos(a) * 6, math.sin(a) * 6, damage=8,
                          color=(150, 220, 255))
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _skill_fireball(self, game, player):
        self.state = "FIREBALL"; self.state_timer = 50
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        base_angle = math.atan2(dy, dx)
        for off in (-0.2, 0, 0.2):
            a = base_angle + off
            fb = Fireball(self.rect.centerx, self.rect.centery,
                          math.cos(a) * 7, math.sin(a) * 7, damage=10)
            game.fireballs.add(fb); game.all_sprites.add(fb)

    def _skill_plague(self, game, player):
        self.state = "PLAGUE"; self.state_timer = 50
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        base_angle = math.atan2(dy, dx)
        for off in (-0.25, 0, 0.25):
            a = base_angle + off
            fb = Fireball(self.rect.centerx, self.rect.centery,
                          math.cos(a) * 6, math.sin(a) * 6, damage=8,
                          color=POISON_BRIGHT)
            game.fireballs.add(fb); game.all_sprites.add(fb)
        px = player.rect.centerx
        pool = LavaPool(px, SCREEN_HEIGHT - 30, duration=240, damage=4, color=POISON_GREEN)
        game.lava_pools.add(pool); game.all_sprites.add(pool)

    def draw_health_bar(self, surface):
        bar_w = max(self.rect.width, 70)
        bar_h = 6
        x = self.rect.centerx - bar_w // 2
        y = self.rect.y - 18
        pygame.draw.rect(surface, (30, 10, 40), (x - 1, y - 1, bar_w + 2, bar_h + 2))
        ratio = max(0, self.health / self.max_health)
        pygame.draw.rect(surface, (200, 60, 180), (x, y, bar_w * ratio, bar_h))
        pygame.draw.rect(surface, (255, 200, 255), (x, y, bar_w * ratio, 1))
        pygame.draw.rect(surface, WHITE, (x, y, bar_w, bar_h), 1)
        font = get_font(14)
        text = font.render(self.elite_name, True, ELITE_PURPLE)
        ts = pygame.Surface((text.get_width() + 12, text.get_height() + 4), pygame.SRCALPHA)
        ts.fill((20, 10, 30, 180))
        ts.blit(text, (6, 2))
        tr = ts.get_rect(center=(self.rect.centerx, y - 12))
        surface.blit(ts, tr)

    def draw_affix_icons(self, surface):
        draw_affix_icons_row(surface, self)


class VampireEnemy(EliteEnemy):
    """教堂吸血鬼：持续召血族，并从附近的血仆与血蝠身上抽血。"""

    def __init__(self, x, y, depth, scene_type):
        super().__init__(x, y, depth, scene_type, "vampire")
        self.summon_timer = random.randint(VAMPIRE_SUMMON_INTERVAL // 2,
                                          VAMPIRE_SUMMON_INTERVAL)
        self.drain_timer = 0
        self.drain_target = None
        self.drain_fx_timer = 0
        self.is_blood_minion = False
        self.is_undead = True

    def update(self, platforms, barriers, ice_trails, all_sprites=None, game=None):
        super().update(platforms, barriers, ice_trails, all_sprites, game)
        if game is None or self.health <= 0:
            return
        if self.drain_fx_timer > 0:
            self.drain_fx_timer -= 1
        if self.drain_timer > 0:
            self.drain_timer -= 1
        if self.summon_timer > 0:
            self.summon_timer -= 1
        if self.health < self.max_health and self.drain_timer <= 0:
            self.drain_timer = VAMPIRE_DRAIN_INTERVAL
            self._drain_nearby_blood(game)
        if self.summon_timer <= 0:
            self.summon_timer = VAMPIRE_SUMMON_INTERVAL
            self._summon_blood_minion(game)

    def _drain_nearby_blood(self, game):
        candidates = []
        for other in game.enemies:
            if other is self or not getattr(other, 'is_blood_minion', False):
                continue
            if getattr(other, 'health', 0) <= 0:
                continue
            dx = other.rect.centerx - self.rect.centerx
            dy = other.rect.centery - self.rect.centery
            if dx * dx + dy * dy <= VAMPIRE_DRAIN_RADIUS * VAMPIRE_DRAIN_RADIUS:
                candidates.append(other)
        if not candidates:
            return
        target = min(candidates,
                     key=lambda e: abs(e.rect.centerx - self.rect.centerx)
                     + abs(e.rect.centery - self.rect.centery))
        want = int(VAMPIRE_DRAIN_BASE + self.depth * 0.35)
        amount = min(want, max(0.0, float(target.health)))
        if amount <= 0:
            return
        target.health -= amount
        healed = min(amount, self.max_health - self.health)
        self.health += healed
        self.drain_target = target
        self.drain_fx_timer = 14
        game.add_floating_text(self.rect.centerx, self.rect.top - 8,
                               f"+{int(healed)}", (255, 105, 120), 17)
        if target.health <= 0:
            spawn_x, spawn_y = target.rect.midbottom
            target.kill()
            circle = SummonCircle(spawn_x, min(spawn_y - 12, SCREEN_HEIGHT - 45),
                                  ENEMY_BLOOD_SERVANT, self.scene_type,
                                  self.depth, delay=25)
            game.summon_circles.add(circle)
            game.all_sprites.add(circle)
            self.drain_target = None

    def _summon_blood_minion(self, game):
        if len(game.enemies) >= game.enemy_cap + 4:
            return
        xs = [max(70, self.rect.centerx - 90), min(SCREEN_WIDTH - 70, self.rect.centerx + 90)]
        x = random.choice(xs)
        y = min(self.rect.bottom + 8, SCREEN_HEIGHT - 35)
        kind = random.choice((ENEMY_BLOOD_SERVANT, ENEMY_BLOOD_BAT))
        circle = SummonCircle(x, y, kind, self.scene_type, self.depth, delay=42)
        game.summon_circles.add(circle)
        game.all_sprites.add(circle)


class GargoyleEnemy(EliteEnemy):
    """三阶段石像鬼：石像 -> 地面追击 -> 回血石像 -> 飞行。"""

    STONE = 0
    GROUND = 1
    RECOVER = 2
    FLYING = 3

    def __init__(self, x, y, depth, scene_type):
        super().__init__(x, y, depth, scene_type, "gargoyle")
        self.phase = self.STONE
        self.phase_changed = False
        self.contact_harmful = False
        self.is_flying = False
        self.recover_rate = self.max_health / max(1, GARGOYLE_RECOVER_FRAMES)
        self._set_phase_image("stone")

    def _set_phase_image(self, mode):
        old_bottom = self.rect.bottom if hasattr(self, "rect") else None
        size = self.body_size
        self.image = pygame.Surface(size, pygame.SRCALPHA)
        if mode == "stone":
            self._draw_body((128, 134, 138), size, "gargoyle")
        elif mode == "ground":
            self._draw_body((88, 204, 194), size, "gargoyle")
        else:
            self._draw_body((105, 224, 216), size, "gargoyle_fly")
        if old_bottom is not None:
            self.rect = self.image.get_rect(midbottom=(self.rect.centerx, old_bottom))

    def apply_damage(self, damage, game=None):
        if self.phase == self.RECOVER:
            return super().apply_damage(damage, game)
        damage = super().apply_damage(damage, game)
        if self.health <= 0:
            if self.phase == self.STONE:
                self._enter_ground()
            elif self.phase == self.GROUND:
                self._enter_recover()
        return damage

    def _enter_ground(self):
        self.phase = self.GROUND
        self.health = self.max_health
        self.contact_harmful = True
        self.is_flying = False
        self._set_phase_image("ground")

    def _enter_recover(self):
        self.phase = self.RECOVER
        self.health = 1.0
        self.contact_harmful = False
        self.is_flying = False
        self.velocity_x = 0
        self.velocity_y = 0
        self._set_phase_image("stone")

    def _enter_flying(self):
        self.phase = self.FLYING
        self.health = self.max_health
        self.contact_harmful = True
        self.is_flying = True
        self._set_phase_image("flying")

    def update(self, platforms, barriers, ice_trails, all_sprites=None, game=None):
        self.anim_timer += 1
        if self.freeze_timer > 0:
            self.freeze_timer -= 1
        if self.slow_timer > 0:
            self.slow_timer -= 1
        if self.stun_timer > 0:
            self.stun_timer -= 1
        for affix in self.affix_instances:
            affix.update(game)

        if self.phase in (self.STONE, self.RECOVER):
            if self.phase == self.RECOVER:
                self.health = min(self.max_health, self.health + self.recover_rate)
                if self.health >= self.max_health:
                    self._enter_flying()
            return

        speed_mult = 1.0 + self.aura_speed_bonus
        if self.buff_timer > 0:
            self.buff_timer -= 1
            speed_mult *= 1.0 + TROLL_BUFF_SPEED
        if self.cross_buff_timer > 0:
            self.cross_buff_timer -= 1
            speed_mult *= 1.0 + TROLL_BUFF_SPEED
        if self.slow_timer > 0:
            speed_mult *= 0.5
        if self.freeze_timer > 0 or self.stun_timer > 0:
            return

        player = game.player if game is not None else None
        speed = self.base_speed * speed_mult
        if self.phase == self.FLYING:
            if player is not None:
                dx = player.rect.centerx - self.rect.centerx
                dy = player.rect.centery - self.rect.centery
                self.rect.x += max(-speed, min(speed, dx * 0.035))
                self.rect.y += max(-speed, min(speed, dy * 0.035))
            self.rect.clamp_ip(pygame.Rect(0, 24, SCREEN_WIDTH, SCREEN_HEIGHT - 48))
            return

        dx = 0
        if player is not None:
            dx = player.rect.centerx - self.rect.centerx
            if abs(dx) > 48:
                self.velocity_x = (1 if dx > 0 else -1) * speed
            else:
                self.velocity_x = 0
        self.velocity_y += GRAVITY
        self.rect.x += self.velocity_x
        for sprite in list(platforms) + [b for b in barriers if b.visible]:
            if pygame.sprite.collide_rect(self, sprite):
                if try_step_up(self, sprite):
                    continue
                if self.velocity_x > 0:
                    self.rect.right = sprite.rect.left
                elif self.velocity_x < 0:
                    self.rect.left = sprite.rect.right
                self.velocity_x = 0
        self.rect.y += self.velocity_y
        self.on_ground = False
        for platform in platforms:
            if pygame.sprite.collide_rect(self, platform) and self.velocity_y > 0:
                self.rect.bottom = platform.rect.top
                self.velocity_y = 0
                self.on_ground = True

    def draw_health_bar(self, surface):
        super().draw_health_bar(surface)
        if self.phase == self.RECOVER:
            font = get_font(11)
            text = font.render("复原中", True, (220, 220, 225))
            surface.blit(text, (self.rect.centerx - text.get_width() // 2,
                                self.rect.top - 32))


class BoneCarrierEnemy(EliteEnemy):
    """载骨机：吸收幽魂与骷髅的魂火，累计五道后进化为炼魂魔骷。"""

    def __init__(self, x, y, depth, scene_type):
        super().__init__(x, y, depth, scene_type, "bone_carrier")
        self.is_undead = True
        self.is_bone_carrier = True
        self.absorbed_ghosts = 0     # 兼容旧存档字段，现在表示累计幽火数
        self.evolved = False
        self.shock_timer = SOUL_SHOCK_INTERVAL
        self._rebuild_image()

    def _rebuild_image(self):
        old_bottom = self.rect.bottom if hasattr(self, "rect") else None
        if self.evolved:
            w, h = 70, 96
        else:
            w, h = self.body_size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2
        pygame.draw.ellipse(surf, (0, 0, 0, 100), (8, h - 7, w - 16, 7))
        bone = (224, 220, 202) if not self.evolved else (198, 236, 202)
        dark = (48, 54, 48) if not self.evolved else (24, 56, 36)
        if self.evolved:
            pygame.draw.polygon(surf, dark, [
                (cx - 21, 26), (cx + 21, 26), (cx + 24, h - 8), (cx - 24, h - 8)
            ])
        pygame.draw.line(surf, bone, (cx, 22), (cx, h - 18), 7)
        for i in range(5):
            y = 30 + i * 8
            pygame.draw.line(surf, bone, (cx - 15, y), (cx + 15, y), 3)
        pygame.draw.line(surf, bone, (cx - 5, h - 18), (cx - 13, h - 5), 5)
        pygame.draw.line(surf, bone, (cx + 5, h - 18), (cx + 13, h - 5), 5)
        pygame.draw.line(surf, bone, (cx - 12, 30), (cx - 24, 54), 5)
        pygame.draw.line(surf, bone, (cx + 12, 30), (cx + 25, 48), 5)
        outlined_circle(surf, bone, (cx, 15), 13 if self.evolved else 11)
        pygame.draw.circle(surf, (16, 24, 18),
                           (cx - 5, 15), 4 if self.evolved else 3)
        pygame.draw.circle(surf, (16, 24, 18),
                           (cx + 5, 15), 4 if self.evolved else 3)
        if self.evolved:
            draw_glow(surf, (82, 245, 122), (cx - 5, 15), 11, 150)
            draw_glow(surf, (82, 245, 122), (cx + 5, 15), 11, 150)
            pygame.draw.line(surf, (170, 232, 184),
                             (cx + 25, 48), (cx + 34, 16), 5)
            pygame.draw.polygon(surf, (210, 246, 218), [
                (cx + 34, 10), (cx + 29, 27), (cx + 40, 22)
            ])
            pygame.draw.line(surf, OUTLINE,
                             (cx + 25, 48), (cx + 34, 16), 2)
        for i in range(self.absorbed_ghosts):
            fx = cx - 16 + (i % 3) * 16
            fy = 30 + (i // 3) * 18
            draw_glow(surf, (82, 240, 120), (fx, fy), 8, 100)
            pygame.draw.circle(surf, (174, 255, 190), (fx, fy), 3)
        self.image = surf
        if old_bottom is not None:
            self.rect = self.image.get_rect(
                midbottom=(self.rect.centerx, old_bottom))

    def update(self, platforms, barriers, ice_trails, all_sprites=None, game=None):
        super().update(platforms, barriers, ice_trails, all_sprites, game)
        if game is None or self.health <= 0:
            return
        self._absorb_souls(game)
        if self.evolved:
            self.shock_timer -= 1
            if self.shock_timer <= 0:
                self.shock_timer = SOUL_SHOCK_INTERVAL
                self._fire_soul_shock(game)

    def _absorb_souls(self, game):
        for other in list(game.enemies):
            if other is self:
                continue
            enemy_type = getattr(other, "enemy_type", None)
            if enemy_type not in (ENEMY_GHOST, ENEMY_SKELETON):
                continue
            if getattr(other, "health", 0) <= 0:
                continue
            if not pygame.sprite.collide_rect(self, other):
                continue
            flames = 3 if (enemy_type == ENEMY_SKELETON
                           and getattr(other, "is_giant", False)) else 1
            other.kill()
            self.absorbed_ghosts += flames
            heal = max(1, int(self.max_health * 0.1 * flames))
            before = self.health
            self.health = min(self.max_health, self.health + heal)
            game.add_floating_text(self.rect.centerx, self.rect.top - 8,
                                   f"+{int(self.health - before)}",
                                   (130, 248, 160), 18)
            self._rebuild_image()
            if self.absorbed_ghosts >= 5 and not self.evolved:
                self._evolve(game)
            break

    def _evolve(self, game):
        self.evolved = True
        self.elite_name = "炼魂魔骷"
        self.is_giant = True
        self.max_health = int(self.max_health * 1.35)
        self.health = self.max_health
        self.base_speed *= 1.15
        if "soul_burn" not in self.affix_names:
            cls = AFFIX_TABLE.get("soul_burn")
            if cls:
                self.affix_names.append("soul_burn")
                inst = cls(self)
                self.affix_instances.append(inst)
                inst.on_spawn(game)
        self._rebuild_image()
        game.show_message("载骨机集聚五道魂火，进化为炼魂魔骷！", 2600)

    def _fire_soul_shock(self, game):
        player = game.player
        sx, sy = self.rect.centerx, self.rect.centery - 8
        dx = player.rect.centerx - sx
        dy = player.rect.centery - sy
        dist = math.hypot(dx, dy) or 1
        shot = SoulShock(
            sx, sy,
            dx / dist * SOUL_SHOCK_SPEED,
            dy / dist * SOUL_SHOCK_SPEED,
            damage=int(SOUL_SHOCK_DAMAGE + self.depth * 0.45),
            owner=self,
        )
        game.soul_shocks.add(shot)
        game.all_sprites.add(shot)


class EmberMinion(pygame.sprite.Sprite):
    def __init__(self, x, y, depth):
        super().__init__()
        self.image = pygame.Surface((28, 28), pygame.SRCALPHA)
        draw_glow(self.image, FIRE_ORANGE, (14, 14), 13, 130)
        pygame.draw.circle(self.image, FIRE_RED, (14, 14), 10)
        pygame.draw.circle(self.image, FIRE_ORANGE, (14, 14), 7)
        pygame.draw.circle(self.image, FIRE_YELLOW, (14, 14), 4)
        pygame.draw.circle(self.image, (255, 250, 200), (14, 14), 2)
        pygame.draw.circle(self.image, OUTLINE, (14, 14), 10, 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.depth = depth
        self.speed = 1.6
        self.health = 20; self.max_health = 20; self.base_health = 20
        self.explode_timer = 300
        self.exploded = False
        self.anim = 0
        self.is_ember = True
        self.is_elite = False
        self.enemy_type = -1
        self.split_done = True
        self.affix_instances = []
        self.base_speed = self.speed
        self.damage_multiplier = 1.0
        self.is_flying = True
        self.stun_timer = 0

    def apply_damage(self, damage, game=None):
        self.health -= damage
        return damage

    def update(self, player, platforms, *args, **kwargs):
        self.anim += 1
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.sqrt(dx * dx + dy * dy) or 1
        self.rect.x += self.speed * dx / dist
        self.rect.y += self.speed * dy / dist
        self.explode_timer -= 1
        if self.explode_timer <= 0: self.exploded = True
        if pygame.sprite.collide_rect(self, player): self.exploded = True

    def check_explosion(self, player):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        return math.sqrt(dx * dx + dy * dy) <= 60

    def draw_health_bar(self, surface): pass
    def draw_affix_icons(self, surface): pass
