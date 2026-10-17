"""生态区域、暴风雪与暴云寺庙。

区域规则：
  * 一个生态区域持续 3~5 间房（往左回走也算），数值在这个区间波动；
  * 区域走完后的下一间必定是普通地牢；
  * 之后每间"继续是普通地牢"的概率按 0.9 / 0.8 / 0.7… 递减，直到新的区域开始；
  * 暴云寺庙不是独立生态，它是雪山区域里的一种房间：每进一间雪山房有
    TEMPLE_ROOM_CHANCE 的概率变成寺庙，出现寺庙则雪山区域再延长几间。
"""

import math
import random

import pygame

from ..data.biomes import (BIOME_CHURCH, BIOME_GREAT_TOMB, BIOME_NORMAL,
                           BIOME_SNOW, BIOME_TEMPLE, BIOME_TOMB, SPECIAL_BIOMES)
from ..entities.props import Platform, SnowDrift, StormCrystal
from ..settings import (BLIZZARD_DURATION, BLIZZARD_INTERVAL, BLIZZARD_PUSH,
                        CRYSTAL_COOLDOWN, CRYSTAL_DAMAGE_RATE, CRYSTAL_MAX, CRYSTAL_MIN,
                        CHURCH_REGION_EXTRA, CHURCH_ROOM_CHANCE,
                        GREAT_TOMB_REGION_EXTRA, GREAT_TOMB_ROOM_CHANCE,
                        CRYSTAL_RANGE, CRYSTAL_TICK, FPS, NORMAL_GAP_START,
                        REGION_ROOMS_MAX, REGION_ROOMS_MIN, SCREEN_HEIGHT, SCREEN_WIDTH,
                        SNOW_DRIFT_MAX, SNOW_DRIFT_MIN, SNOW_DRIFT_RADIUS,
                        TEMPLE_REGION_EXTRA, TEMPLE_ROOM_CHANCE, screen)
from ..utils import draw_glow

SNOW_GROUND_SEGMENTS = 80       # 碰撞用很细的段（10px），走上去就是缓坡
SNOW_GROUND_MAX_LIFT = 84       # 最高处比最低处高多少


class GameRegionMixin:
    # ---- 生态区域 ----------------------------------------------------
    def _pick_scene_type(self):
        """按区域规则决定这一间是什么生态。"""
        if self.is_boss_room:
            if self.current_depth < 10:
                return BIOME_NORMAL          # 第一位领主照旧在普通地牢
            return self.region_biome or BIOME_NORMAL
        if self.region_biome and self.region_rooms_left > 0:
            self.region_rooms_left -= 1
            if (self.region_biome == BIOME_SNOW
                    and not self.temple_seen
                    and random.random() < TEMPLE_ROOM_CHANCE):
                # 雪山深处藏着寺庙：这间变寺庙，雪山区域再延长
                self.temple_seen = True
                self.nested_seen.add("temple")
                self.region_rooms_left += TEMPLE_REGION_EXTRA
                self.show_message("雪线之上，一座暴云寺庙浮现在风雪里", 2600)
                return BIOME_TEMPLE
            if (self.region_biome == BIOME_TOMB
                    and "church" not in self.nested_seen
                    and random.random() < CHURCH_ROOM_CHANCE):
                self.nested_seen.add("church")
                self.region_rooms_left += CHURCH_REGION_EXTRA
                self.show_message("墓穴深处传来破败教堂的钟声", 2400)
                return BIOME_CHURCH
            if (self.region_biome == BIOME_TOMB
                    and "great_tomb" not in self.nested_seen
                    and random.random() < GREAT_TOMB_ROOM_CHANCE):
                self.nested_seen.add("great_tomb")
                self.region_rooms_left += GREAT_TOMB_REGION_EXTRA
                self.show_message("墓碑向地底延伸，古代大墓地苏醒了", 2400)
                return BIOME_GREAT_TOMB
            return self.region_biome
        if self.region_biome:
            # 区域刚走完：必定接一间普通地牢当缓冲
            self.region_biome = None
            self.normal_gap_chance = NORMAL_GAP_START
            return BIOME_NORMAL
        if random.random() < self.normal_gap_chance:
            self.normal_gap_chance = max(0.1, self.normal_gap_chance - 0.1)
            return BIOME_NORMAL
        # 开新区域：这一间就是区域的第一间
        self.region_biome = random.choice(SPECIAL_BIOMES)
        self.region_rooms_left = random.randint(REGION_ROOMS_MIN, REGION_ROOMS_MAX) - 1
        self.normal_gap_chance = NORMAL_GAP_START
        self.temple_seen = False
        self.nested_seen = set()
        return self.region_biome

    def enter_region_room(self):
        """进入新房间时重置天气与寺庙状态。"""
        for group in (self.snow_drifts, self.storm_crystals):
            for sprite in list(group):
                sprite.kill()
        self.blizzard_timer = 0
        self.blizzard_cooldown = BLIZZARD_INTERVAL
        self.blizzard_dir = random.choice((-1, 1))
        self.blizzard_drift = 0.0
        # 雪坡的绘制数据只在雪山房里有效，换房间必须清掉，
        # 否则离开雪山后那条雪坡会一直画在后面的房间上
        self.snow_profile = []

    def spawn_room_props(self):
        """房间布置完成之后再放场地道具。

        寺庙的金色水晶要落在空中平台上，必须等平台建好；
        （这里曾经在平台生成之前调用，结果一颗水晶都刷不出来）
        """
        if self.scene_type == BIOME_TEMPLE:
            self.spawn_storm_crystals()

    # ---- 雪山地形 ----------------------------------------------------
    def build_snow_ground(self):
        """雪山地面是连续渐变的缓坡：用细段铺出平滑起伏，没有台阶感。

        返回最高处的顶面高度；空中平台仍按它 + MIN_GROUND_CLEARANCE 生成，
        所以地面不会顶到最低的空中平台。
        """
        base = SCREEN_HEIGHT - 30
        peaks = random.randint(1, 3)                     # 坡的个数
        phase = random.uniform(0, math.pi * 2)
        heights = []
        for i in range(SNOW_GROUND_SEGMENTS):
            t = i / (SNOW_GROUND_SEGMENTS - 1)
            wave = (math.sin(t * math.pi * peaks + phase) + 1) / 2
            heights.append(int(base - SNOW_GROUND_MAX_LIFT * wave))
        seg_w = SCREEN_WIDTH // SNOW_GROUND_SEGMENTS
        self.snow_profile = []
        for i, top in enumerate(heights):
            x0 = i * seg_w
            width = seg_w + 2 if i < SNOW_GROUND_SEGMENTS - 1 else SCREEN_WIDTH - x0
            platform = Platform(x0, top, width, SCREEN_HEIGHT - top, BIOME_SNOW)
            # 碰撞段不参与绘制：地面整体由 draw_snow_ground() 画成一条连续的雪坡
            platform.image = pygame.Surface((width, SCREEN_HEIGHT - top), pygame.SRCALPHA)
            self.platforms.add(platform)
            self.all_sprites.add(platform)
            self.snow_profile.append((x0, top))
        return min(heights)

    def draw_snow_ground(self):
        """沿着高度剖面一次性画出连续的雪坡，避免一段段平台的接缝。"""
        profile = getattr(self, "snow_profile", None)
        if not profile:
            return
        points = list(profile) + [(SCREEN_WIDTH, SCREEN_HEIGHT), (0, SCREEN_HEIGHT)]
        pygame.draw.polygon(screen, (226, 236, 248), points)
        # 坡面高光与投影，让起伏看得出来
        pygame.draw.lines(screen, (250, 253, 255), False, list(profile), 3)
        shadow = [(x, y + 6) for x, y in profile]
        pygame.draw.lines(screen, (186, 202, 222), False, shadow, 2)
        for i in range(0, len(profile), 3):
            x, y = profile[i]
            pygame.draw.circle(screen, (244, 250, 255), (x + 4, y + 10), 2)

    # ---- 暴风雪 ------------------------------------------------------
    def is_blizzard(self):
        return self.scene_type == BIOME_SNOW and self.blizzard_timer > 0

    def update_blizzard(self):
        """雪山房间的风雪循环：每 30 秒刮一次，持续 6 秒。"""
        if self.scene_type != BIOME_SNOW:
            return
        if self.blizzard_timer > 0:
            self.blizzard_timer -= 1
            self.push_player(self.blizzard_dir)
            if self.blizzard_timer == 0:
                self.spawn_snow_drifts()
            return
        self.blizzard_cooldown -= 1
        if self.blizzard_cooldown <= 0:
            self.blizzard_timer = BLIZZARD_DURATION
            self.blizzard_cooldown = BLIZZARD_INTERVAL
            self.blizzard_dir = random.choice((-1, 1))
            self.show_message("暴风雪来袭！", 1600)

    def push_player(self, direction, strength=BLIZZARD_PUSH):
        """直接位移推一下玩家：用位移而不是速度，免得被输入覆盖掉。

        推力不能把人推进屏障里——那样他会嵌在墙里出不来，只能一直被吹在墙上。
        """
        player = self.player
        # 推力比 1 像素还小，直接取整会被每帧截断成 0，所以先把余量攒起来
        self.blizzard_drift += direction * strength
        step = int(self.blizzard_drift)
        if step == 0:
            self._free_player_from_walls()
            return
        target = player.rect.copy()
        target.x = player.rect.x + step
        if target.left < 0 or target.right > SCREEN_WIDTH:
            self.blizzard_drift = 0.0
            self._free_player_from_walls()
            return
        for barrier in self.barriers:
            if barrier.visible and target.colliderect(barrier.rect):
                self.blizzard_drift = 0.0
                self._free_player_from_walls()
                return
        player.rect.x = target.x
        self.blizzard_drift -= step

    def _free_player_from_walls(self):
        """万一已经被推进墙里（旧存档或边界情况），把玩家挤回场内。"""
        player = self.player
        for barrier in self.barriers:
            if not barrier.visible or not player.rect.colliderect(barrier.rect):
                continue
            if barrier.rect.centerx <= SCREEN_WIDTH // 2:
                player.rect.left = barrier.rect.right
            else:
                player.rect.right = barrier.rect.left
        if player.rect.left < 0:
            player.rect.left = 0
        elif player.rect.right > SCREEN_WIDTH:
            player.rect.right = SCREEN_WIDTH

    # ---- 疏雪层 ------------------------------------------------------
    def spawn_snow_drifts(self):
        """风雪停后，地面与不高的平台上堆起疏雪层。

        雪山地面是很多细段拼的缓坡，所以按 x 找出覆盖范围里最低的那块平台当雪面。
        """
        want = random.randint(SNOW_DRIFT_MIN, SNOW_DRIFT_MAX)
        for _ in range(want * 6):
            if want <= 0:
                break
            width = random.randint(96, 170)
            x = random.randint(0, max(1, SCREEN_WIDTH - width))
            tops = [p.rect.top for p in self.platforms
                    if p.rect.top >= SCREEN_HEIGHT - 260
                    and p.rect.left < x + width and p.rect.right > x]
            if not tops:
                continue
            drift = SnowDrift(x, max(tops), width)
            self.snow_drifts.add(drift)
            want -= 1

    def update_snow_drifts(self):
        """玩家走过就铲掉身边的疏雪层。"""
        if not self.snow_drifts:
            return
        px = self.player.rect.centerx
        py = self.player.rect.bottom
        for drift in list(self.snow_drifts):
            if abs(drift.rect.centerx - px) <= drift.rect.width // 2 + 12 \
                    and abs(drift.rect.centery - py) <= 40:
                drift.kill()

    def destroy_snow_drifts(self, x, y, radius):
        """爆炸波及范围内的疏雪层一并铲掉。"""
        if not self.snow_drifts:
            return
        for drift in list(self.snow_drifts):
            dx = drift.rect.centerx - x
            dy = drift.rect.centery - y
            if dx * dx + dy * dy <= (radius + SNOW_DRIFT_RADIUS) ** 2:
                drift.kill()

    # ---- 暴云寺庙的金色水晶 ------------------------------------------
    def spawn_storm_crystals(self):
        """水晶落在最低的几块空中平台上（地面不算）。"""
        aerial = [p for p in self.platforms
                  if p.rect.top < SCREEN_HEIGHT - 100 and p.rect.width >= 60]
        if not aerial:
            return
        aerial.sort(key=lambda p: p.rect.top, reverse=True)   # 越靠下越低
        count = min(random.randint(CRYSTAL_MIN, CRYSTAL_MAX), len(aerial))
        for platform in aerial[:count]:
            margin = min(30, platform.rect.width // 4)
            x = random.randint(platform.rect.left + margin,
                               max(platform.rect.left + margin,
                                   platform.rect.right - margin))
            crystal = StormCrystal(x, platform.rect.top)
            self.storm_crystals.add(crystal)
            self.all_sprites.add(crystal)

    def interactive_crystal(self):
        """玩家附近可以点亮的水晶。"""
        best, best_d = None, CRYSTAL_RANGE
        for crystal in self.storm_crystals:
            if not crystal.ready:
                continue
            dx = crystal.rect.centerx - self.player.rect.centerx
            dy = crystal.rect.centery - self.player.rect.centery
            d = math.hypot(dx, dy)
            if d <= best_d:
                best, best_d = crystal, d
        return best

    def use_storm_crystal(self):
        """按 F：让最近的金色水晶朝最近的敌人射出光束。"""
        crystal = self.interactive_crystal()
        if crystal is None:
            return False
        target = self.nearest_enemy_to(crystal.rect.centerx, crystal.rect.centery)
        if target is None or getattr(target, 'health', 0) <= 0:
            self.show_message("附近没有可以照射的目标", 1200)
            return False
        crystal.activate(target)
        self.show_message("金色水晶射出光束！", 1200)
        return True

    def update_storm_crystals(self):
        """水晶自身的计时 + 光束的持续伤害。"""
        for crystal in list(self.storm_crystals):
            if crystal.beam_timer > 0:
                # 先结算这一帧的光束再走计时：否则光束的最后一跳会被计时吃掉
                target = crystal.target
                if target is None or getattr(target, 'health', 0) <= 0:
                    # 目标倒了就换最近的敌人继续照
                    target = self.nearest_enemy_to(crystal.rect.centerx,
                                                   crystal.rect.centery)
                    crystal.target = target
                if target is not None:
                    crystal.tick += 1
                    if crystal.tick >= CRYSTAL_TICK:
                        crystal.tick = 0
                        damage = max(1, int(self.player.attack_damage * CRYSTAL_DAMAGE_RATE
                                            * CRYSTAL_TICK / FPS))
                        self.damage_enemy(target, damage, source='temple_beam')
            crystal.update()

    def draw_crystal_beams(self):
        """水晶的亮灭状态、冷却环与金色光束。"""
        for crystal in self.storm_crystals:
            cx, cy = crystal.rect.centerx, crystal.rect.top + 14
            if crystal.beam_timer > 0 and crystal.target is not None:
                tx, ty = crystal.target.rect.centerx, crystal.target.rect.centery
                wobble = math.sin(self.frame * 0.5) * 2
                pygame.draw.line(screen, (255, 228, 140, 220), (cx, cy), (tx, ty + wobble), 5)
                pygame.draw.line(screen, (255, 252, 226), (cx, cy), (tx, ty + wobble), 2)
                draw_glow(screen, (255, 216, 120), (tx, ty), 20, 110)
                draw_glow(screen, (255, 232, 160), (cx, cy), 16, 120)
            elif not crystal.ready:
                ratio = 1.0 - max(0, crystal.cooldown) / max(1, CRYSTAL_COOLDOWN)
                pygame.draw.arc(screen, (150, 130, 90),
                                (cx - 16, cy - 16, 32, 32), 0.0, math.pi * 2 * ratio, 3)
            else:
                pulse = 0.5 + 0.5 * math.sin(self.frame * 0.08)
                draw_glow(screen, (255, 214, 110), (cx, cy), int(10 + 6 * pulse), 70)

    # ---- 增幅光环 ----------------------------------------------------
    def draw_unit_buffs(self):
        """被巨魔狂呼者增幅的单位，脚下画一圈红环。"""
        for enemy in list(self.enemies):
            if (getattr(enemy, 'buff_timer', 0) > 0
                    or getattr(enemy, 'cross_buff_timer', 0) > 0):
                self._draw_buff_ring(enemy)
        boss = self.boss
        if boss is not None and (getattr(boss, 'buff_timer', 0) > 0
                                 or getattr(boss, 'cross_buff_timer', 0) > 0):
            self._draw_buff_ring(boss)

    def _draw_buff_ring(self, target):
        rect = target.rect
        pulse = int(2 + 2 * math.sin(self.frame * 0.25))
        pygame.draw.ellipse(screen, (226, 62, 62),
                            (rect.centerx - rect.width // 2 - 8, rect.bottom - 10,
                             rect.width + 16, 12 + pulse), 3)
        pygame.draw.ellipse(screen, (255, 150, 150, 120),
                            (rect.centerx - rect.width // 2 - 4, rect.bottom - 8,
                             rect.width + 8, 8 + pulse), 1)
