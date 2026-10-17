"""玩家角色。"""


# === IMPORTS ===
import math
import pygame
import random
from ..data.biomes import BIOME_ICE
from ..data.skills import SKILL_SHIELD, skill_time_rewind_duration
from .projectiles import Bullet
from ..utils import try_step_up
from ..settings import (FPS, GRAVITY, JUMP_CUT_FACTOR, JUMP_POWER_BASE, OUTLINE,
                        SCREEN_HEIGHT, SCREEN_WIDTH, SETTINGS, SLIDE_FACTOR,
                        SOUL_BURN_DAMAGE, SOUL_BURN_DURATION, SOUL_BURN_TICK,
                        WHITE)
from ..timing import frame_count
# === /IMPORTS ===

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.create_player_images()
        self.image = self.right_image
        self.rect = self.image.get_rect()
        self.rect.x = 100; self.rect.y = SCREEN_HEIGHT - 100
        self.velocity_x = 0; self.velocity_y = 0
        self.speed_base = 8; self.speed_multiplier = 1.0
        self.on_ground = False; self.on_ice = False
        self.health = 100; self.max_health = 100
        self.kills = 0
        self.facing_right = True
        self.jump_power_multiplier = 1.0
        self.attack_speed_multiplier = 1.2
        self.last_shot_time = 0
        self.attack_bonus = 0
        self.attack_damage_multiplier = 1.0
        self.bombs = 0
        self.shield_active = False; self.shield_end_time = 0
        self.crystals = 0
        self.anti_slide = False
        self.bomb_upgrade = 0
        self.emergency_shield = False
        self.emergency_shield_cooldown = 0
        self.piercing_bullets = 0
        self.double_jump = False
        self.jumps_remaining = 0
        self.crit_chance = 0.0
        self.crit_multiplier = 2.0
        self.crit_damage_bonus = 0
        self.lifesteal_chance = 0.0
        self.lifesteal_amount = 0
        self.thorns_damage = 0
        self.invincible_timer = 0
        self.slow_timer = 0
        self.hurt_cooldown = 0
        self.damage_reporter = None      # 由 Game 挂上，用来统计受到的伤害
        self.ice_chaos_timer = 0
        self.ice_chaos_offset = 0.0
        self.burn_timer = 0; self.burn_tick = 0
        self.soul_burn_timer = 0
        self.soul_burn_tick = 0
        self.soul_burn_damage = SOUL_BURN_DAMAGE
        self.soul_burn_source = ""
        self.last_damage_codex = None
        self.freeze_timer = 0; self.freeze_immune = 0
        self.anim_timer = 0
        self.hook_pull_timer = 0; self.hook_pull_target = None
        self.max_energy = 100.0; self.energy = 100.0
        self.energy_regen = 1.5
        # 玩家初始只有 1 个技能槽，且无技能
        self.skills = [None, None, None]
        self.skill_slots = 1
        self.dash_timer = 0; self.dash_dir = (1, 0); self.dash_speed = 0.0
        self.dash_damage = 0; self.dash_hit = set(); self.dash_skill = None
        self.pending_shockwave = False; self.shockwave_cd = 0
        # 陨火吟唱状态
        self.meteor_active = False
        self.meteor_skill = None
        self.meteor_slot = -1
        self.meteor_drop_timer = 0
        # 时间回溯状态
        self.rewind_active = False
        self.rewind_timer = 0
        self.rewind_pos = None
        self.rewind_health = 0
        self.rewind_energy = 0.0
        self.rewind_skill = None
        self.rewind_slot = -1
        # 独立于正常生命的临时生命
        self.temp_health = 0.0
        # 亡者契约领域剩余时间
        self.pact_timer = 0

    @property
    def speed(self):
        base = self.speed_base * self.speed_multiplier
        if self.slow_timer > 0: base *= 0.6
        if self.freeze_timer > 0: base *= 0.0
        return base

    @property
    def jump_power(self): return JUMP_POWER_BASE * self.jump_power_multiplier

    @property
    def attack_cooldown(self): return int(max(8, 24 / self.attack_speed_multiplier))

    @property
    def attack_damage(self):
        base = (10 + self.attack_bonus) * self.attack_damage_multiplier
        if self.shield_active:
            for s in self.skills:
                if s and s.kind == SKILL_SHIELD and s.has_evolution("bulwark"):
                    base *= 1.5
                    break
        return base

    def roll_crit_damage(self, base_damage):
        is_crit = random.random() < self.crit_chance
        if is_crit:
            return (base_damage + self.crit_damage_bonus) * 2, True
        return base_damage, False

    def has_shockwave(self):
        for s in self.skills:
            if s and s.kind == SKILL_SHIELD and s.has_evolution("shockwave"): return True
        return False

    # ---- 陨火吟唱 ----
    def has_meteor_nimble(self):
        return (self.meteor_skill is not None
                and self.meteor_skill.has_evolution("nimble"))

    def is_casting_locked(self):
        return self.meteor_active and not self.has_meteor_nimble()

    def stop_meteor(self):
        self.meteor_active = False
        self.meteor_skill = None
        self.meteor_slot = -1
        self.meteor_drop_timer = 0

    def begin_time_rewind(self, skill, slot):
        self.rewind_active = True
        self.rewind_timer = skill_time_rewind_duration(skill.level)
        self.rewind_pos = self.rect.center
        self.rewind_health = self.health
        self.rewind_energy = self.energy
        self.rewind_skill = skill
        self.rewind_slot = slot

    def finish_time_rewind(self, restore=True):
        if not self.rewind_active:
            return
        if restore:
            if self.rewind_pos is not None:
                self.rect.center = self.rewind_pos
                self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
                self.velocity_x = 0
                self.velocity_y = 0
                self.hook_pull_timer = 0
                self.hook_pull_target = None
            if self.rewind_skill is not None and self.rewind_skill.has_evolution("self_guard"):
                self.health = max(self.health, self.rewind_health)
                self.health = min(self.health, self.max_health)
                self.energy = max(self.energy, self.rewind_energy)
                self.energy = min(self.energy, self.max_energy)
        self.rewind_active = False
        self.rewind_timer = 0
        self.rewind_pos = None
        self.rewind_skill = None
        self.rewind_slot = -1

    def cancel_time_rewind(self):
        self.finish_time_rewind(restore=False)

    def has_time_persistence(self):
        return (self.rewind_active and self.rewind_skill is not None
                and self.rewind_skill.has_evolution("persistence"))

    def gain_temp_health(self, amount):
        if amount <= 0:
            return
        cap = max(10, int(self.max_health * 0.5))
        self.temp_health = min(cap, self.temp_health + amount)

    def create_player_images(self):
        W, H = 48, 68
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 90), (8, H - 6, 32, 6))
        pygame.draw.polygon(surf, (110, 30, 45), [(10, 22), (0, 58), (8, 60), (14, 32)])
        pygame.draw.polygon(surf, (160, 50, 60), [(13, 24), (5, 54), (11, 56), (18, 30)])
        pygame.draw.rect(surf, (38, 46, 74), (14, 46, 8, 18))
        pygame.draw.rect(surf, (38, 46, 74), (26, 46, 8, 18))
        pygame.draw.rect(surf, (24, 30, 48), (14, 46, 8, 3))
        pygame.draw.rect(surf, (24, 30, 48), (26, 46, 8, 3))
        pygame.draw.rect(surf, (22, 26, 42), (12, 60, 12, 6))
        pygame.draw.rect(surf, (22, 26, 42), (24, 60, 12, 6))
        pygame.draw.rect(surf, (10, 12, 22), (12, 60, 12, 6), 1)
        pygame.draw.rect(surf, (10, 12, 22), (24, 60, 12, 6), 1)
        pygame.draw.polygon(surf, (58, 78, 116), [(12, 24), (36, 24), (38, 48), (10, 48)])
        pygame.draw.polygon(surf, OUTLINE, [(12, 24), (36, 24), (38, 48), (10, 48)], 2)
        pygame.draw.polygon(surf, (86, 112, 156), [(14, 26), (34, 26), (34, 42), (14, 42)])
        pygame.draw.line(surf, (150, 180, 220), (16, 28), (16, 40), 2)
        pygame.draw.rect(surf, (150, 110, 40), (10, 44, 28, 5))
        pygame.draw.rect(surf, (230, 180, 80), (10, 44, 28, 2))
        pygame.draw.rect(surf, OUTLINE, (10, 44, 28, 5), 1)
        pygame.draw.circle(surf, (86, 112, 156), (13, 28), 6)
        pygame.draw.circle(surf, (130, 160, 200), (13, 27), 4)
        pygame.draw.circle(surf, OUTLINE, (13, 28), 6, 2)
        pygame.draw.circle(surf, (232, 200, 170), (26, 16), 11)
        pygame.draw.circle(surf, OUTLINE, (26, 16), 11, 2)
        pygame.draw.polygon(surf, (46, 32, 28), [(16, 12), (22, 4), (34, 6), (36, 14), (30, 10), (20, 13)])
        pygame.draw.polygon(surf, OUTLINE, [(16, 12), (22, 4), (34, 6), (36, 14), (30, 10), (20, 13)], 2)
        pygame.draw.circle(surf, (70, 200, 235), (22, 16), 2)
        pygame.draw.circle(surf, (70, 200, 235), (30, 16), 2)
        pygame.draw.circle(surf, WHITE, (22, 15), 1)
        pygame.draw.circle(surf, WHITE, (30, 15), 1)
        pygame.draw.rect(surf, (55, 65, 85), (36, 30, 12, 6))
        pygame.draw.rect(surf, (110, 120, 140), (36, 30, 12, 3))
        pygame.draw.rect(surf, OUTLINE, (36, 30, 12, 6), 1)
        pygame.draw.rect(surf, (30, 38, 55), (34, 33, 6, 9))
        pygame.draw.rect(surf, OUTLINE, (34, 33, 6, 9), 1)
        pygame.draw.circle(surf, (110, 220, 255), (47, 33), 3)
        pygame.draw.circle(surf, WHITE, (47, 33), 1)
        self.right_image = surf
        self.left_image = pygame.transform.flip(surf, True, False)

    def update(self, platforms, barriers, traps, scene_type):
        self.anim_timer += 1
        self.energy = min(self.max_energy, self.energy + self.energy_regen / FPS)
        if self.shockwave_cd > 0: self.shockwave_cd -= 1

        if self.hook_pull_timer > 0:
            self.hook_pull_timer -= 1
            target = self.hook_pull_target
            if target is not None and target.alive():
                dx = target.rect.centerx - self.rect.centerx
                dy = target.rect.centery - self.rect.centery
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 52:
                    pull_speed = 18
                    self.rect.x += dx / dist * pull_speed
                    self.rect.y += dy / dist * pull_speed
                    self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
                    self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - self.rect.height))
                    self.velocity_x = 0; self.velocity_y = 0
                    if dx > 0: self.facing_right = True; self.image = self.right_image
                    elif dx < 0: self.facing_right = False; self.image = self.left_image
                    return
                else:
                    self.hook_pull_timer = 0; self.hook_pull_target = None
            else:
                self.hook_pull_timer = 0; self.hook_pull_target = None

        if self.dash_timer > 0:
            self.dash_timer -= 1
            self.invincible_timer = max(self.invincible_timer, 2)
            skill = self.dash_skill
            if skill is not None and skill.has_evolution("slide"):
                keys = pygame.key.get_pressed()
                dx = dy = 0
                if keys[pygame.K_a]: dx -= 1
                if keys[pygame.K_d]: dx += 1
                if keys[pygame.K_w]: dy -= 1
                if dx or dy:
                    m = math.hypot(dx, dy) or 1
                    self.dash_dir = (dx / m, dy / m)
            self.rect.x += self.dash_dir[0] * self.dash_speed
            self.rect.y += self.dash_dir[1] * self.dash_speed
            self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
            self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - self.rect.height))
            if self.dash_dir[0] > 0: self.facing_right = True; self.image = self.right_image
            elif self.dash_dir[0] < 0: self.facing_right = False; self.image = self.left_image
            if self.dash_timer <= 0: self.dash_skill = None
            return

        # 陨火吟唱：无法移动
        if self.is_casting_locked():
            self.velocity_x = 0
            self.ice_chaos_offset = 0

        ct = frame_count()
        if self.shield_active and ct > self.shield_end_time: self.shield_active = False
        if self.emergency_shield and self.health < self.max_health * 0.2 and ct > self.emergency_shield_cooldown:
            self.shield_active = True
            self.shield_end_time = ct + 180
            self.emergency_shield_cooldown = ct + 3600
        if self.invincible_timer > 0: self.invincible_timer -= 1
        if self.slow_timer > 0: self.slow_timer -= 1
        if self.hurt_cooldown > 0: self.hurt_cooldown -= 1
        if self.freeze_timer > 0: self.freeze_timer -= 1
        if self.freeze_immune > 0: self.freeze_immune -= 1

        if self.burn_timer > 0:
            self.burn_timer -= 1; self.burn_tick += 1
            if self.burn_tick >= 60:
                self.burn_tick = 0
                self.take_damage(2, source='burn')

        if self.soul_burn_timer > 0:
            self.soul_burn_timer -= 1
            self.soul_burn_tick += 1
            if self.soul_burn_tick >= SOUL_BURN_TICK:
                self.soul_burn_tick = 0
                self.take_true_damage(self.soul_burn_damage, source="soul_burn",
                                      codex=self.soul_burn_source)
            if self.soul_burn_timer <= 0:
                self.soul_burn_source = ""

        self.velocity_y += GRAVITY
        self.on_ice = (scene_type == BIOME_ICE and self.on_ground and not self.anti_slide)
        if self.on_ice:
            self.velocity_x *= SLIDE_FACTOR
            if abs(self.velocity_x) < 0.4: self.velocity_x = 0
            self.ice_chaos_timer -= 1
            if self.ice_chaos_timer <= 0:
                self.ice_chaos_offset = random.uniform(-2.0, 2.0)
                self.ice_chaos_timer = random.randint(12, 30)
            else:
                self.ice_chaos_offset *= 0.9
        else:
            self.ice_chaos_offset = 0.0; self.ice_chaos_timer = 0

        old_x = self.rect.x
        self.rect.x += self.velocity_x + self.ice_chaos_offset
        if self.velocity_x > 0: self.facing_right = True; self.image = self.right_image
        elif self.velocity_x < 0: self.facing_right = False; self.image = self.left_image

        collision_sprites = list(platforms) + [b for b in barriers if b.visible]
        for sprite in collision_sprites:
            if pygame.sprite.collide_rect(self, sprite):
                if try_step_up(self, sprite):
                    continue          # 缓坡就抬上去，别当墙挡住
                self.rect.x = old_x; self.velocity_x = 0; self.ice_chaos_offset = 0
                break

        if self.rect.left < 0: self.rect.left = 0; self.velocity_x = 0
        elif self.rect.right > SCREEN_WIDTH: self.rect.right = SCREEN_WIDTH; self.velocity_x = 0

        was_on_ground = self.on_ground
        self.rect.y += self.velocity_y
        self.on_ground = False
        for platform in platforms:
            if pygame.sprite.collide_rect(self, platform):
                if self.velocity_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.velocity_y = 0; self.on_ground = True
                    self.jumps_remaining = (2 if self.double_jump else 1) - 1
                    if not was_on_ground and getattr(platform, 'fragile', False):
                        platform.hit_count += 1
                        if platform.hit_count >= 3: platform.kill()
                elif self.velocity_y < 0:
                    self.rect.top = platform.rect.bottom
                    self.velocity_y = 0

        if not self.shield_active and self.hurt_cooldown <= 0:
            for trap in traps:
                if trap.active and pygame.sprite.collide_rect(self, trap):
                    self.take_damage(2, source='trap'); break
        if self.rect.top < 0:
            self.rect.top = 0; self.velocity_y = 0

    def take_damage(self, damage, source=None):
        if damage <= 0: return False
        self.last_damage_codex = None
        if self.shield_active:
            if self.has_shockwave() and self.shockwave_cd <= 0:
                self.pending_shockwave = True
                self.shockwave_cd = 40
            return False
        if self.invincible_timer > 0: return False
        took = float(damage)
        damage = float(damage)
        if self.temp_health > 0:
            absorbed = min(self.temp_health, damage)
            self.temp_health -= absorbed
            damage -= absorbed
            if self.temp_health < 0.001:
                self.temp_health = 0.0
        if damage > 0:
            self.health -= damage
            if self.health <= 0:
                self.health = 1 if self.has_time_persistence() else 0
        self.invincible_timer = 30; self.hurt_cooldown = 30
        # 记账回调由 Game 挂上：这样无论伤害来自哪条路径都会被统计
        if self.damage_reporter is not None:
            self.damage_reporter(took, source)
        return True

    def take_true_damage(self, damage, source=None, codex=None):
        """护盾、临时生命与普通减伤都无法阻挡的真实生命损失。"""
        if damage <= 0:
            return False
        took = float(damage)
        self.last_damage_codex = codex
        self.health -= took
        if self.health <= 0:
            self.health = 1 if self.has_time_persistence() else 0
        if self.damage_reporter is not None:
            self.damage_reporter(took, source)
        return True

    def apply_soul_burn(self, source="炼魂魔骷"):
        self.soul_burn_timer = max(self.soul_burn_timer, SOUL_BURN_DURATION)
        self.soul_burn_damage = SOUL_BURN_DAMAGE
        self.soul_burn_source = source

    def move_left(self):
        if self.freeze_timer > 0: return
        if self.dash_timer > 0: return
        if self.is_casting_locked(): return
        self.velocity_x = -self.speed

    def move_right(self):
        if self.freeze_timer > 0: return
        if self.dash_timer > 0: return
        if self.is_casting_locked(): return
        self.velocity_x = self.speed

    def stop(self):
        if not self.on_ground: return
        if self.on_ice: return
        self.velocity_x = 0

    def jump(self):
        if self.freeze_timer > 0: return
        if self.dash_timer > 0: return
        max_jumps = 2 if self.double_jump else 1
        if self.on_ground:
            self.jumps_remaining = max_jumps - 1
            self.velocity_y = self.jump_power
            self.on_ground = False
        elif self.jumps_remaining > 0:
            self.jumps_remaining -= 1
            self.velocity_y = self.jump_power * 0.9

    def cut_jump(self):
        """松开跳跃键：上冲速度削掉一截，于是轻点小跳、长按高跳。"""
        if not SETTINGS.get("charge_jump", True):
            return
        if self.freeze_timer > 0 or self.dash_timer > 0:
            return
        if self.velocity_y < 0:
            self.velocity_y *= JUMP_CUT_FACTOR

    def can_shoot(self):
        return frame_count() - self.last_shot_time >= self.attack_cooldown

    def shoot(self):
        if not self.can_shoot(): return None
        direction = 1 if self.facing_right else -1
        self.last_shot_time = frame_count()
        damage = self.attack_damage
        damage, is_crit = self.roll_crit_damage(damage)
        color = (255, 130, 130) if is_crit else (110, 240, 180)
        bullet = Bullet(self.rect.centerx + direction * 20, self.rect.centery,
                        direction * 15, 0, damage, self.piercing_bullets, False, color)
        bullet.is_crit = is_crit
        return [bullet]

    def draw_shield(self, surface):
        if self.shield_active:
            cx = self.rect.centerx; cy = self.rect.centery
            r = max(self.rect.width, self.rect.height) // 2 + 12
            t = frame_count() / 12
            pulse = 0.5 + 0.5 * math.sin(t)
            alpha = int(60 + 60 * pulse)
            s = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(s, (90, 220, 255, alpha), (r + 4, r + 4), r, 3)
            pygame.draw.circle(s, (200, 240, 255, alpha // 2), (r + 4, r + 4), r - 5, 2)
            pts = []
            for i in range(6):
                a = math.pi / 3 * i + t / 4
                pts.append((r + 4 + r * math.cos(a), r + 4 + r * math.sin(a)))
            pygame.draw.polygon(s, (140, 230, 255, alpha), pts, 2)
            surface.blit(s, (cx - r - 4, cy - r - 4))
