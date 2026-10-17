"""技能释放与技能效果结算。"""


# === IMPORTS ===
import math
import pygame
import random
from ..data.modes import MODE_SUMMONER
from ..data.skills import SKILL_BLACK_HOLE, SKILL_DASH, SKILL_FIREBALL, SKILL_ICE_NOVA, SKILL_METEOR, SKILL_PACT, SKILL_SHIELD, SKILL_SOUL_CHAIN, SKILL_TIME_REWIND, SLOT_KEY_NAMES, Skill, skill_black_hole_damage, skill_black_hole_duration, skill_dash_damage, skill_dash_stun, skill_fireball_bonus, skill_fireball_radius, skill_ice_nova_freeze, skill_ice_nova_slow, skill_meteor_bonus, skill_meteor_drain, skill_meteor_scorch_duration, skill_pact_duration, skill_shield_duration, skill_soul_chain_duration, skill_soul_chain_targets, skill_time_rewind_duration
from ..entities.projectiles import BlackHole, BlackHoleBullet, Bomb, IceShard, LavaPool, MeteorFireball, NovaWave, SkillFireball
from ..entities.props import IceTrap
from ..settings import FIRE_ORANGE, FPS, ICE_TRAP_COOLDOWN, METEOR_DROP_INTERVAL, SCREEN_HEIGHT, SCREEN_WIDTH, screen
from ..timing import frame_count
# === /IMPORTS ===

class GameSkillMixin:
    def shoot(self):
        bullets = self.player.shoot()
        if bullets:
            self.stats.record_shot()
            for b in bullets:
                self.bullets.add(b); self.all_sprites.add(b)


    def place_bomb(self, x, y):
        if self.player.bombs > 0 and not self.paused:
            bomb = Bomb(x, y, self.scene_type, self.player.bomb_upgrade)
            self.bombs.add(bomb); self.all_sprites.add(bomb)
            self.player.bombs -= 1
            return True
        return False


    def spawn_nova_wave(self, x, y, max_radius=340, delay=0, damage=12, speed=6,
                        small=False, color=None):
        wave = NovaWave(x, y, max_radius, delay, damage, speed, small, color)
        self.nova_waves.add(wave); self.all_sprites.add(wave)


    def spawn_temporary_spike(self, x, y):
        trap = IceTrap(x, y)
        trap.cycle = [True] * 180 + [False] * (ICE_TRAP_COOLDOWN - 180)
        trap.timer = 0
        self.traps.add(trap); self.all_sprites.add(trap)


    def explode_at(self, x, y, damage, radius):
        self.destroy_snow_drifts(x, y, radius)      # 爆炸顺手铲掉疏雪层
        for enemy in list(self.enemies):
            if enemy.health <= 0: continue
            dx = enemy.rect.centerx - x; dy = enemy.rect.centery - y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= radius:
                factor = 1.0 - (dist / radius) * 0.5
                self.damage_enemy(enemy, int(damage * factor), source='explosion')
        if self.boss is not None and not self.boss.invincible:
            dx = self.boss.rect.centerx - x; dy = self.boss.rect.centery - y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= radius:
                factor = 1.0 - (dist / radius) * 0.5
                self.damage_boss(int(damage * factor), source='explosion')
        self.spawn_nova_wave(x, y, max_radius=radius, damage=0,
                             speed=max(6, radius // 10), small=True, color=FIRE_ORANGE)


    def use_skill(self, slot):
        p = self.player
        if self.mode == MODE_SUMMONER:
            if slot >= 3: return False
            return self._summoner_key(slot)
        if slot >= p.skill_slots: return False
        skill = p.skills[slot]
        if skill is None:
            self.show_message(f"{SLOT_KEY_NAMES[slot]} 键无技能", 700); return False

        # 陨火：开关式
        if skill.kind == SKILL_METEOR:
            if p.meteor_active and p.meteor_slot == slot:
                p.stop_meteor()
                self.show_message("陨火结束", 800)
                return False
            if p.meteor_active:
                p.stop_meteor()
            if p.energy < skill.cost:
                self.show_message("能量不足！", 700); return False
            p.energy -= skill.cost
            p.meteor_active = True
            p.meteor_skill = skill
            p.meteor_slot = slot
            p.meteor_drop_timer = METEOR_DROP_INTERVAL
            self.show_message("天降陨火！再按一次结束", 900)
            return True

        if p.energy < skill.cost:
            self.show_message("能量不足！", 700); return False
        ok = self._execute_skill(skill, slot)
        if ok: p.energy -= skill.cost
        return ok


    def _execute_skill(self, skill, slot):
        p = self.player
        if skill.kind == SKILL_SHIELD:
            dur = skill_shield_duration(skill.level)
            p.shield_active = True
            p.shield_end_time = frame_count() + dur
            return True
        if skill.kind == SKILL_DASH:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]: d = (0, -1)
            else: d = (1 if p.facing_right else -1, 0)
            p.dash_dir = d
            p.dash_timer = 40 if skill.has_evolution("slide") else 16
            p.dash_speed = 15 + skill.level * 1.0
            p.dash_damage = skill_dash_damage(skill.level)
            p.dash_hit = set()
            p.dash_skill = skill
            return True
        if skill.kind == SKILL_FIREBALL:
            base_attack = p.attack_damage
            skill_bonus = skill_fireball_bonus(skill.level)
            direct_damage = base_attack + skill_bonus
            explosion_damage = 2 * base_attack + skill_bonus
            is_crit = random.random() < p.crit_chance
            if is_crit:
                direct_damage = (direct_damage + p.crit_damage_bonus) * 2
            radius = skill_fireball_radius(skill.level)
            dirs = []
            base_ang = 0 if p.facing_right else math.pi
            target = None
            if skill.has_evolution("snipe"):
                target = self._nearest_enemy()
                if target is not None:
                    dx = target.rect.centerx - p.rect.centerx
                    dy = target.rect.centery - p.rect.centery
                    base_ang = math.atan2(dy, dx)
                    if dx > 0: p.facing_right = True
                    elif dx < 0: p.facing_right = False
                    p.image = p.right_image if p.facing_right else p.left_image
            if skill.has_evolution("sweep"):
                dirs = [base_ang - 0.30, base_ang, base_ang + 0.30]
            else:
                dirs = [base_ang]
            for ang in dirs:
                vx = math.cos(ang) * 11; vy = math.sin(ang) * 11
                fb = SkillFireball(p.rect.centerx, p.rect.centery, vx, vy,
                                   direct_damage, explosion_damage, radius,
                                   skill, is_crit, target)
                self.skill_fireballs.add(fb); self.all_sprites.add(fb)
            return True
        if skill.kind == SKILL_ICE_NOVA:
            direction = 1 if p.facing_right else -1
            damage = p.attack_damage
            damage, is_crit = p.roll_crit_damage(damage)
            freeze_dur = skill_ice_nova_freeze(skill.level)
            slow_dur = freeze_dur + skill_ice_nova_slow(skill.level)
            shard = IceShard(p.rect.centerx + direction * 24, p.rect.centery,
                             direction * 14, 0, damage,
                             p.piercing_bullets, is_crit,
                             freeze_dur, slow_dur, owner=skill)
            self.ice_shards.add(shard); self.all_sprites.add(shard)
            return True
        if skill.kind == SKILL_BLACK_HOLE:
            direction = 1 if p.facing_right else -1
            shot = BlackHoleBullet(p.rect.centerx + direction * 24, p.rect.centery,
                                   direction * 10, 0, skill)
            self.black_hole_bullets.add(shot)
            self.all_sprites.add(shot)
            return True
        if skill.kind == SKILL_TIME_REWIND:
            if p.rewind_active:
                self.show_message("时间回溯进行中", 700)
                return False
            p.begin_time_rewind(skill, slot)
            self.show_message(f"记录时空坐标，{skill_time_rewind_duration(skill.level) // FPS}秒后回溯", 1200)
            return True
        if skill.kind == SKILL_SOUL_CHAIN:
            limit = skill_soul_chain_targets(skill.level)
            targets = self._soul_chain_candidates()[:limit]
            if not targets:
                self.show_message("附近没有可以链接的目标", 800)
                return False
            self.soul_chain_targets = targets
            self.soul_chain_timer = skill_soul_chain_duration(skill.level)
            self.soul_chain_skill = skill
            self.show_message(f"灵魂锁链链接了{len(targets)}个目标", 1000)
            return True
        if skill.kind == SKILL_PACT:
            dur = skill_pact_duration(skill.level)
            if skill.has_evolution("long_pact"):
                dur = int(dur * 1.6)
            p.pact_timer = max(p.pact_timer, dur)
            self.show_message("亡者契约展开：击杀的敌人会为你而战", 1400)
            return True
        return False


    def _nearest_enemy(self):
        candidates = []
        if self.boss is not None and not self.boss.invincible and self.boss.health > 0:
            candidates.append(self.boss)
        for e in self.enemies:
            if getattr(e, 'health', 0) > 0 and not getattr(e, 'is_ember', False):
                candidates.append(e)
        if not candidates: return None
        px, py = self.player.rect.centerx, self.player.rect.centery
        elites = [c for c in candidates if getattr(c, 'is_elite', False)]
        if elites:
            return min(elites, key=lambda e: (e.rect.centerx - px)**2 + (e.rect.centery - py)**2)
        return min(candidates, key=lambda e: (e.rect.centerx - px)**2 + (e.rect.centery - py)**2)


    def nearest_enemy_to(self, x, y, max_dist=None):
        """离 (x, y) 最近的敌人（含领主），供召唤物索敌。"""
        candidates = []
        if self.boss is not None and not self.boss.invincible and self.boss.health > 0:
            candidates.append(self.boss)
        for e in self.enemies:
            if getattr(e, 'health', 0) > 0 and not getattr(e, 'is_ember', False):
                candidates.append(e)
        best = None; best_d = None
        for c in candidates:
            d = math.hypot(c.rect.centerx - x, c.rect.centery - y)
            if max_dist is not None and d > max_dist:
                continue
            if best_d is None or d < best_d:
                best = c; best_d = d
        return best


    def nearest_ally(self, x, y, max_dist=None):
        """离 (x, y) 最近的召唤物，供飞行敌人索敌。"""
        best = None; best_d = None
        for a in self.allies:
            if a.health <= 0:
                continue
            d = math.hypot(a.rect.centerx - x, a.rect.centery - y)
            if max_dist is not None and d > max_dist:
                continue
            if best_d is None or d < best_d:
                best = a; best_d = d
        return best


    def _circle_rect_collide(self, cx, cy, radius, rect):
        closest_x = max(rect.left, min(cx, rect.right))
        closest_y = max(rect.top, min(cy, rect.bottom))
        dx = cx - closest_x; dy = cy - closest_y
        return dx * dx + dy * dy <= radius * radius


    def spawn_skill_explosion(self, x, y, damage, radius):
        self.destroy_snow_drifts(x, y, radius)
        for enemy in list(self.enemies):
            if enemy.health <= 0: continue
            if self._circle_rect_collide(x, y, radius, enemy.rect):
                dx = enemy.rect.centerx - x; dy = enemy.rect.centery - y
                dist = math.hypot(dx, dy)
                factor = max(0.5, 1.0 - 0.5 * (dist / radius))
                self.damage_enemy(enemy, int(damage * factor), source='skill_fireball_explosion')
        if self.boss is not None and not self.boss.invincible:
            if self._circle_rect_collide(x, y, radius, self.boss.rect):
                dx = self.boss.rect.centerx - x; dy = self.boss.rect.centery - y
                dist = math.hypot(dx, dy)
                factor = max(0.5, 1.0 - 0.5 * (dist / radius))
                self.damage_boss(int(damage * factor), source='skill_fireball_explosion')
        self.spawn_nova_wave(x, y, max_radius=radius, damage=0,
                             speed=max(6, radius // 8), small=True, color=(255, 140, 60))


    def spawn_black_hole(self, x, y, skill):
        hole = BlackHole(x, y, skill, skill_black_hole_duration(skill.level))
        self.black_holes.add(hole)


    def update_black_hole_bullets(self):
        for shot in list(self.black_hole_bullets):
            shot.update(self.barriers)
            if not shot.alive():
                continue
            hits = pygame.sprite.spritecollide(shot, self.enemies, False)
            if hits:
                self.spawn_black_hole(shot.rect.centerx, shot.rect.centery, shot.skill)
                shot.kill()
                continue
            if (self.boss is not None and not self.boss.invincible
                    and pygame.sprite.collide_rect(shot, self.boss)):
                self.spawn_black_hole(shot.rect.centerx, shot.rect.centery, shot.skill)
                shot.kill()


    def _warp_enemy_projectiles(self, cx, cy):
        outer_radius = 190
        inner_radius = 62
        projectiles = list(self.fireballs)
        projectiles.extend(shard for shard in self.ice_shards
                           if getattr(shard, 'hostile', False))
        for proj in projectiles:
            if not proj.alive():
                continue
            dx = cx - proj.rect.centerx
            dy = cy - proj.rect.centery
            dist = math.hypot(dx, dy)
            if dist <= 1 or dist > outer_radius:
                continue
            nx = dx / dist
            ny = dy / dist
            if dist <= inner_radius:
                proj.vx += nx * 0.95
                proj.vy += ny * 0.95
                if dist <= 18:
                    proj.kill()
            else:
                strength = 0.28 * (1.0 - dist / outer_radius)
                proj.vx += nx * strength
                proj.vy += ny * strength


    def update_black_holes(self):
        for hole in list(self.black_holes):
            hole.update()
            if not hole.alive():
                continue
            cx, cy = hole.rect.center
            pull_radius = hole.pull_radius
            for enemy in list(self.enemies):
                if getattr(enemy, 'health', 0) <= 0 or getattr(enemy, 'is_ember', False):
                    continue
                dx = cx - enemy.rect.centerx
                dy = cy - enemy.rect.centery
                dist = math.hypot(dx, dy)
                if dist > pull_radius:
                    continue
                if getattr(enemy, 'black_hole_angle', None) is None:
                    enemy.black_hole_angle = random.uniform(0, math.tau)
                gather_radius = 26 + (id(enemy) % 5) * 7
                target_x = cx + math.cos(enemy.black_hole_angle) * gather_radius
                target_y = cy + math.sin(enemy.black_hole_angle) * gather_radius
                pull_x = target_x - enemy.rect.centerx
                pull_y = target_y - enemy.rect.centery
                pull_dist = math.hypot(pull_x, pull_y)
                enemy.black_hole_lock = 6
                if pull_dist > 1:
                    strength = 1.4 + 5.6 * (1.0 - dist / pull_radius)
                    step = min(strength, pull_dist)
                    enemy.rect.x += pull_x / pull_dist * step
                    enemy.rect.y += pull_y / pull_dist * step
                top = 30 if getattr(enemy, 'is_flying', False) else 0
                bounds = pygame.Rect(0, top, SCREEN_WIDTH, SCREEN_HEIGHT - 30 - top)
                enemy.rect.clamp_ip(bounds)

            if hole.skill.has_evolution("devour"):
                hole.damage_timer += 1
                if hole.damage_timer >= 30:
                    hole.damage_timer = 0
                    damage = skill_black_hole_damage(hole.skill.level)
                    for enemy in list(self.enemies):
                        if getattr(enemy, 'health', 0) <= 0:
                            continue
                        if self._circle_rect_collide(cx, cy, hole.radius, enemy.rect):
                            dealt = self.damage_enemy(enemy, damage, source='black_hole_devour')
                            self._heal_player_from_damage(dealt)
                    if (self.boss is not None and not self.boss.invincible
                            and self._circle_rect_collide(cx, cy, hole.radius, self.boss.rect)):
                        dealt = self.damage_boss(damage, source='black_hole_devour')
                        self._heal_player_from_damage(dealt)

            if hole.skill.has_evolution("warp"):
                self._warp_enemy_projectiles(cx, cy)


    def _heal_player_from_damage(self, dealt):
        if dealt <= 0:
            return
        self.player.health = min(self.player.max_health, self.player.health + dealt)


    def _soul_chain_candidates(self):
        px, py = self.player.rect.center
        targets = []
        if self.boss is not None and not self.boss.invincible and self.boss.health > 0:
            targets.append(self.boss)
        for enemy in self.enemies:
            if getattr(enemy, 'health', 0) > 0 and not getattr(enemy, 'is_ember', False):
                targets.append(enemy)
        targets.sort(key=lambda e: (e.rect.centerx - px) ** 2 + (e.rect.centery - py) ** 2)
        return targets


    def update_soul_chain(self):
        if self.soul_chain_timer <= 0:
            self.soul_chain_targets = []
            self.soul_chain_skill = None
            return
        self.soul_chain_timer -= 1
        alive_targets = []
        for target in self.soul_chain_targets:
            if target is self.boss:
                if target.health > 0 and not target.invincible:
                    alive_targets.append(target)
            elif (target.alive() and self.enemies.has(target)
                  and getattr(target, 'health', 0) > 0):
                alive_targets.append(target)
        self.soul_chain_targets = alive_targets
        if self.soul_chain_timer <= 0 or not self.soul_chain_targets:
            self.soul_chain_timer = 0
            self.soul_chain_targets = []
            self.soul_chain_skill = None


    def _soul_chain_has(self, evolution_key):
        return (self.soul_chain_timer > 0 and self.soul_chain_skill is not None
                and self.soul_chain_skill.has_evolution(evolution_key))


    def _is_soul_linked(self, target):
        return self._soul_chain_has("shared_pain") and target in self.soul_chain_targets


    def _spread_soul_chain_damage(self, source_target, dealt, damage_source, was_linked=None):
        if dealt <= 0 or damage_source == 'soul_chain_shared':
            return
        if was_linked is None:
            was_linked = self._is_soul_linked(source_target)
        if not was_linked or not self._soul_chain_has("shared_pain"):
            return
        for target in list(self.soul_chain_targets):
            if target is source_target:
                continue
            if target is self.boss:
                self.damage_boss(dealt, source='soul_chain_shared')
            elif (target.alive() and self.enemies.has(target)
                  and getattr(target, 'health', 0) > 0):
                self.damage_enemy(target, dealt, source='soul_chain_shared')


    def draw_soul_chains(self):
        if not self.soul_chain_targets or self.soul_chain_skill is None:
            return
        points = [
            target.rect.center
            for target in self.soul_chain_targets
            if target is self.boss or target.alive()
        ]
        if len(points) < 2:
            return
        for i in range(len(points) - 1):
            pygame.draw.line(screen, (125, 55, 175), points[i], points[i + 1], 5)
            pygame.draw.line(screen, (205, 135, 255), points[i], points[i + 1], 2)
        for point in points:
            pygame.draw.circle(screen, (175, 95, 230), point, 7, 2)
            pygame.draw.circle(screen, (235, 215, 255), point, 2)


    def update_meteor_casting(self):
        p = self.player
        if not p.meteor_active: return
        if p.meteor_slot < 0 or p.meteor_slot >= p.skill_slots:
            p.stop_meteor(); return
        skill = p.skills[p.meteor_slot]
        if skill is None or skill.kind != SKILL_METEOR:
            p.stop_meteor(); return

        p.energy -= skill_meteor_drain(skill.level) / FPS
        if p.energy <= 0:
            p.energy = 0
            p.stop_meteor()
            self.show_message("能量耗尽，陨火结束", 900)
            return

        p.meteor_drop_timer += 1
        if p.meteor_drop_timer >= METEOR_DROP_INTERVAL:
            p.meteor_drop_timer = 0
            self._drop_meteor(skill)


    def _drop_meteor(self, skill):
        target = self._nearest_enemy()
        if target is not None and random.random() < 0.55:
            x = target.rect.centerx + random.randint(-40, 40)
        else:
            x = random.randint(50, SCREEN_WIDTH - 50)
        x = max(30, min(x, SCREEN_WIDTH - 30))

        base = self.player.attack_damage + skill_meteor_bonus(skill.level)
        is_crit = random.random() < self.player.crit_chance
        if is_crit:
            base = (base + self.player.crit_damage_bonus) * 2

        scorch = skill.has_evolution("scorch")
        dur = skill_meteor_scorch_duration(skill.level)
        m = MeteorFireball(x, -40, 13, int(base), 80, scorch=scorch, scorch_dur=dur)
        m.is_crit = is_crit
        self.meteors.add(m); self.all_sprites.add(m)


    def update_meteors(self):
        ground_y = SCREEN_HEIGHT - 30
        for m in list(self.meteors):
            m.rect.y += m.vy
            m.lifetime -= 1
            if m.lifetime <= 0:
                m.kill();
                continue

            # 只有到达最底部地面才算落地（悬空平台不触发）
            hit_ground = m.rect.bottom >= ground_y

            hit_enemy = False
            if self.enemies and pygame.sprite.spritecollide(m, self.enemies, False):
                hit_enemy = True
            if (not hit_enemy and self.boss is not None
                    and not self.boss.invincible
                    and pygame.sprite.collide_rect(m, self.boss)):
                hit_enemy = True

            if hit_enemy:
                if m.is_crit:
                    self.add_floating_text(m.rect.centerx, m.rect.top, "暴击", (255, 90, 90), 20)
                self.spawn_skill_explosion(m.rect.centerx, m.rect.centery, m.damage, m.radius)
                m.kill();
                continue

            if hit_ground:
                if m.scorch:
                    pool = LavaPool(m.rect.centerx, ground_y - 5,
                                    duration=m.scorch_dur,
                                    damage=max(3, m.damage // 4),
                                    width=100,
                                    team="player")  # ← 新增
                    self.lava_pools.add(pool);
                    self.all_sprites.add(pool)
                else:
                    self.spawn_skill_explosion(m.rect.centerx, m.rect.centery, m.damage, m.radius)
                m.kill()


    def update_skill_effects(self):
        p = self.player
        if p.rewind_active:
            p.rewind_timer -= 1
            if p.rewind_timer <= 0:
                had_self_guard = (p.rewind_skill is not None
                                  and p.rewind_skill.has_evolution("self_guard"))
                p.finish_time_rewind(restore=True)
                self.show_message("时间回溯发动" + ("，生命与能量已恢复" if had_self_guard else ""), 1200)
        self.update_soul_chain()
        if p.pending_shockwave:
            p.pending_shockwave = False
            cx, cy = p.rect.centerx, p.rect.centery
            self.spawn_nova_wave(cx, cy, max_radius=150, damage=0, speed=9,
                                 small=True, color=(120, 210, 255))
            for enemy in list(self.enemies):
                if enemy.health <= 0: continue
                dx = enemy.rect.centerx - cx; dy = enemy.rect.centery - cy
                if math.hypot(dx, dy) <= 150:
                    self.damage_enemy(enemy, 20, source='shockwave')
            if self.boss is not None and not self.boss.invincible:
                dx = self.boss.rect.centerx - cx; dy = self.boss.rect.centery - cy
                if math.hypot(dx, dy) <= 150:
                    self.damage_boss(15, source='shockwave')

        if p.dash_timer > 0 and p.dash_damage > 0:
            for enemy in list(self.enemies):
                if enemy in p.dash_hit: continue
                if getattr(enemy, 'health', 0) <= 0: continue
                if pygame.sprite.collide_rect(p, enemy):
                    p.dash_hit.add(enemy)
                    self.damage_enemy(enemy, p.dash_damage, source='dash')
                    if p.dash_skill is not None and p.dash_skill.has_evolution("paralyze"):
                        enemy.stun_timer = skill_dash_stun(p.dash_skill.level)
                    else:
                        enemy.stun_timer = max(getattr(enemy, 'stun_timer', 0), 12)
            if self.boss is not None and self.boss not in p.dash_hit:
                if pygame.sprite.collide_rect(p, self.boss):
                    p.dash_hit.add(self.boss)
                    self.damage_boss(p.dash_damage, source='dash')

        for fb in list(self.skill_fireballs):
            if fb.homing and fb.target is not None and fb.target.alive() and getattr(fb.target, 'health', 1) > 0:
                dx = fb.target.rect.centerx - fb.rect.centerx
                dy = fb.target.rect.centery - fb.rect.centery
                dist = math.hypot(dx, dy)
                if dist > 0:
                    desired_vx = dx / dist * 11; desired_vy = dy / dist * 11
                    turn_rate = 0.15
                    fb.vx += (desired_vx - fb.vx) * turn_rate
                    fb.vy += (desired_vy - fb.vy) * turn_rate
                    speed = math.hypot(fb.vx, fb.vy)
                    if speed > 0:
                        fb.vx = fb.vx / speed * 11; fb.vy = fb.vy / speed * 11
            elif fb.homing and (fb.target is None or not fb.target.alive() or getattr(fb.target, 'health', 1) <= 0):
                new_target = self._nearest_enemy()
                if new_target: fb.target = new_target
            fb.rect.x += fb.vx
            fb.rect.y += fb.vy
            fb.lifetime -= 1
            exploded = False
            direct_hit_target = None
            if fb.lifetime <= 0: exploded = True
            if (fb.rect.right < -40 or fb.rect.left > SCREEN_WIDTH + 40 or
                    fb.rect.bottom < -40 or fb.rect.top > SCREEN_HEIGHT + 40):
                exploded = True
            if not exploded:
                for b in self.barriers:
                    if b.visible and pygame.sprite.collide_rect(fb, b):
                        exploded = True; break
            if not exploded:
                hits = pygame.sprite.spritecollide(fb, self.enemies, False)
                if hits:
                    target_hit = None
                    for e in hits:
                        if e == fb.target: target_hit = e; break
                    if target_hit is None: target_hit = hits[0]
                    direct_hit_target = target_hit
                    exploded = True
            if not exploded and self.boss is not None and not self.boss.invincible:
                if pygame.sprite.collide_rect(fb, self.boss):
                    direct_hit_target = self.boss
                    exploded = True
            if exploded:
                if direct_hit_target is not None:
                    if direct_hit_target == self.boss:
                        self.damage_boss(fb.direct_damage, source='skill_fireball_direct')
                    else:
                        self.damage_enemy(direct_hit_target, fb.direct_damage, source='skill_fireball_direct')
                    if fb.is_crit:
                        self.add_floating_text(direct_hit_target.rect.centerx, direct_hit_target.rect.top - 6,
                                               "暴击", (255, 90, 90), 20)
                self.spawn_skill_explosion(fb.rect.centerx, fb.rect.centery,
                                           fb.explosion_damage, fb.radius)
                fb.kill()

        for shard in list(self.ice_shards):
            shard.update(self.barriers, self.platforms, self.ice_trails, self.all_sprites)
            if not shard.alive(): continue
            hit_barrier = False
            for b in self.barriers:
                if b.visible and pygame.sprite.collide_rect(shard, b):
                    hit_barrier = True; break
            if hit_barrier:
                shard.kill(); continue

            if shard.hostile:
                if not shard.hit_player and pygame.sprite.collide_rect(shard, p):
                    took = p.take_damage(shard.damage, source='ice_shard')
                    if took:
                        p.freeze_timer = max(p.freeze_timer, shard.freeze_dur)
                        p.slow_timer = max(p.slow_timer, shard.slow_dur)
                    shard.hit_player = True
                    shard.kill()
                continue

            hits = pygame.sprite.spritecollide(shard, self.enemies, False)
            for enemy in hits:
                if enemy in shard.hit_enemies: continue
                shard.hit_enemies.add(enemy)
                self.damage_enemy(enemy, shard.damage, source='ice_shard')
                if hasattr(enemy, 'apply_freeze'):
                    enemy.apply_freeze(shard.freeze_dur, shard.slow_dur)
                else:
                    enemy.freeze_timer = max(getattr(enemy, 'freeze_timer', 0), shard.freeze_dur)
                    enemy.slow_timer = max(getattr(enemy, 'slow_timer', 0), shard.slow_dur)
                if shard.is_crit:
                    self.add_floating_text(enemy.rect.centerx, enemy.rect.top - 6,
                                           "暴击", (255, 90, 90), 20)
                if shard.owner is not None and isinstance(shard.owner, Skill) and shard.owner.has_evolution("shatter"):
                    if getattr(enemy, 'freeze_timer', 0) > 0:
                        bonus = int(shard.damage * 0.5)
                        self.damage_enemy(enemy, bonus, source='ice_shatter')
                if shard.pierce_count < shard.pierce_max:
                    shard.pierce_count += 1
                else:
                    shard.kill()
                    break
            if not shard.alive(): continue
            if self.boss is not None and not self.boss.invincible:
                if pygame.sprite.collide_rect(shard, self.boss):
                    self.damage_boss(shard.damage, source='ice_shard')
                    if shard.is_crit:
                        self.add_floating_text(self.boss.rect.centerx, self.boss.rect.top - 6,
                                               "暴击", (255, 90, 90), 20)
                    if shard.pierce_count < shard.pierce_max:
                        shard.pierce_count += 1
                    else:
                        shard.kill()

