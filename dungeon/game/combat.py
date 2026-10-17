"""伤害结算、死亡处理与碰撞。"""


# === IMPORTS ===
import pygame
import random
from ..bosses.roster import BoneDragonBoss
from ..data.biomes import BIOME_CHURCH, BIOME_GREAT_TOMB, BIOME_ICE, BIOME_TOMB
from ..data.enemies import (CODEX_ELITE_NAME, ENEMY_GHOST, ENEMY_SKELETON,
                            ENEMY_WRAITHBONE, ENEMY_ZOMBIE, FUSION_HEAL_MIN,
                            FUSION_HEAL_RATIO, FUSION_HEAL_RADIUS,
                            FUSION_HEALTH_RATIO, WRAITHBONE_DR,
                            WRAITHBONE_RESIST_SOURCES)
from ..data.modes import MODE_SUMMONER, MODE_UNDEAD_TIDE
from ..data.skills import skill_soul_chain_temp_health
from ..entities.enemies import EliteEnemy, Enemy
from ..entities.affix import AFFIX_TABLE
from ..entities.projectiles import Fireball, IceSpike, LavaPool
from ..save import profile
from ..settings import (BLIZZARD_PUSH, POISON_GREEN, SCREEN_HEIGHT, SCREEN_WIDTH,
                        SNOW_DRIFT_RADIUS, TROLL_BUFF_DAMAGE)
from ..stats import source_label
# === /IMPORTS ===

# 这些来源与敌人无关，玩家因此阵亡时不该算在领主头上
NON_ENEMY_SOURCES = ("burn", "trap")


class GameCombatMixin:
    # ---- 命名与记账 --------------------------------------------------
    def enemy_label(self, enemy):
        """图鉴与统计里用的名字：精英统一记成“精英怪”。"""
        if getattr(enemy, 'is_church_cross', False):
            cfg = getattr(enemy, 'cfg', None)
            return cfg.get("name", "血腥十字架") if cfg else "血腥十字架"
        if getattr(enemy, 'is_elite', False):
            if (getattr(enemy, 'is_bone_carrier', False)
                    or getattr(enemy, 'is_giant_zombie', False)
                    or getattr(enemy, 'elite_name', None) == "巨型骷髅"
                    or (getattr(enemy, 'scene_type', None) == BIOME_CHURCH
                        and getattr(enemy, 'elite_name', None))):
                return enemy.elite_name
            return CODEX_ELITE_NAME
        cfg = getattr(enemy, 'cfg', None)
        if cfg and cfg.get("name"):
            return cfg["name"]
        return getattr(enemy, 'elite_name', None) or "敌人"

    def boss_label(self):
        return self.boss.BOSS_NAME if self.boss is not None else ""

    def note_codex_kill(self, name):
        if name:
            self.codex_kills[name] = self.codex_kills.get(name, 0) + 1

    def hurt_player(self, damage, source, codex=None):
        """玩家受伤的统一入口：记账、归因，供结算面板与图鉴使用。"""
        if damage <= 0:
            return False
        took = self.player.take_damage(damage, source=source)
        if took and self.player.health <= 0 and codex:
            self.lethal_source = codex
        return took

    def hurt_player_true(self, damage, source, codex=None):
        """绕过护盾的真实伤害入口，用于灵魂冲击与燃魂。"""
        took = self.player.take_true_damage(damage, source=source, codex=codex)
        if took and self.player.health <= 0:
            self.lethal_source = codex or self.lethal_source
        return took

    def note_player_damage(self, damage, source):
        """玩家挨打的统一记账点：由 Player.take_damage 回调，兜住所有伤害来源。"""
        self.stats.record_taken(source_label(source), damage)
        self.stats.note_health(self.player.health)
        if self.player.health <= 0 and getattr(self.player, "last_damage_codex", None):
            self.lethal_source = self.player.last_damage_codex
        if (self.player.health <= 0 and self.player.shield_active
                and getattr(self.player, "last_damage_codex", None) == "炼魂魔骷"):
            self.soul_reaper_shield_death = True
        if self.player.health > 0 or self.lethal_source:
            return
        # 没给明确死因时按现场推断：领主房里多半就是领主干的
        if self.boss is not None and source not in NON_ENEMY_SOURCES:
            self.lethal_source = self.boss.BOSS_NAME

    def flush_codex(self):
        """把本局攒下的图鉴数据写进存档，避免每杀一个敌人就写盘。"""
        kills, deaths = self.codex_kills, self.codex_deaths
        if not kills and not deaths:
            return
        self.codex_kills = {}
        self.codex_deaths = {}
        profile().record_codex(kills, deaths)

    # ---- 亡灵合体 ----------------------------------------------------
    def update_undead_fusion(self):
        """幽灵与骷髅撞在一起会合体成魔魂亡骨（巨型骷髅不参与）。"""
        ghosts = [e for e in self.enemies
                  if isinstance(e, Enemy) and e.enemy_type == ENEMY_GHOST and e.health > 0]
        if not ghosts:
            return
        skeletons = [e for e in self.enemies
                     if isinstance(e, Enemy) and e.enemy_type == ENEMY_SKELETON
                     and not getattr(e, 'is_giant', False) and e.health > 0]
        if not skeletons:
            return
        for ghost in ghosts:
            if not ghost.alive():
                continue
            partner = None
            for skel in skeletons:
                if skel.alive() and pygame.sprite.collide_rect(ghost, skel):
                    partner = skel
                    break
            if partner is None:
                continue
            self._fuse_wraithbone(ghost, partner)
            skeletons = [s for s in skeletons if s is not partner and s.alive()]

    def _fuse_wraithbone(self, ghost, skeleton):
        """合成魔魂亡骨：继承双方的全部词缀，血量按两者之和计算。"""
        x = (ghost.rect.centerx + skeleton.rect.centerx) // 2
        y = (ghost.rect.centery + skeleton.rect.centery) // 2
        fused = Enemy(x, y, self.current_depth, ENEMY_WRAITHBONE, self.scene_type)
        fused.base_health = max(40, int((ghost.base_health + skeleton.base_health)
                                        * FUSION_HEALTH_RATIO))
        fused.max_health = fused.base_health
        fused.health = fused.base_health
        fused.base_speed = (ghost.base_speed + skeleton.base_speed) * 0.5
        fused.velocity_x = 0
        names = []
        for parent in (ghost, skeleton):
            for name in getattr(parent, 'affix_names', []):
                if name not in names:
                    names.append(name)
        fused.affix_names = []
        fused.affix_instances = []
        self._attach_affixes(fused, names)
        fused.rect = fused.image.get_rect(center=(x, y))
        fused.rect.bottom = min(max(ghost.rect.bottom, skeleton.rect.bottom),
                                SCREEN_HEIGHT - 30)
        for parent in (ghost, skeleton):
            parent.kill()
        self.enemies.add(fused)
        self.all_sprites.add(fused)
        self.initial_enemy_count = max(1, self.initial_enemy_count - 1)
        self.spawn_nova_wave(fused.rect.centerx, fused.rect.centery,
                             max_radius=110, damage=0, speed=7,
                             color=(170, 150, 240))
        label = "·".join(AFFIX_TABLE[n].name for n in names if n in AFFIX_TABLE)
        self.add_floating_text(fused.rect.centerx, fused.rect.top - 12,
                               "魔魂亡骨", (200, 175, 255), 22)
        self.show_message(
            f"幽灵与骷髅合体成魔魂亡骨！{('【' + label + '】') if label else ''}", 2200)

    def _heal_nearby_wraithbones(self, dead):
        """附近有亡灵倒下时，魔魂亡骨会回一部分血量。"""
        cx, cy = dead.rect.center
        for other in list(self.enemies):
            if not getattr(other, 'is_wraithbone', False) or other is dead:
                continue
            if other.health <= 0:
                continue
            dx = other.rect.centerx - cx
            dy = other.rect.centery - cy
            if dx * dx + dy * dy > FUSION_HEAL_RADIUS * FUSION_HEAL_RADIUS:
                continue
            amount = max(FUSION_HEAL_MIN, int(other.max_health * FUSION_HEAL_RATIO))
            healed = other.heal_from_undead(amount)
            if healed > 0:
                self.add_floating_text(other.rect.centerx, other.rect.top - 8,
                                       f"+{int(healed)}", (170, 240, 200), 18)

    def damage_enemy(self, enemy, damage, source=None):
        if enemy.health <= 0: return 0
        # 魔魂亡骨：对玩家的普通攻击与技能攻击减伤一半
        if getattr(enemy, 'is_wraithbone', False) and source in WRAITHBONE_RESIST_SOURCES:
            damage = damage * (1 - WRAITHBONE_DR)
        before = float(enemy.health)
        was_linked = enemy in self.soul_chain_targets
        if enemy.is_ember:
            enemy.apply_damage(damage, self)
            dealt = max(0, before - max(0.0, float(enemy.health)))
            self.stats.record_dealt(source, dealt, "余烬")
            if enemy.health <= 0:
                if self.boss is not None and isinstance(self.boss, BoneDragonBoss):
                    self.boss.on_minion_death()
                if self.embers.has(enemy): self.embers.remove(enemy)
                if self.enemies.has(enemy): self.enemies.remove(enemy)
                enemy.kill()
            if was_linked:
                self._spread_soul_chain_damage(enemy, dealt, source, was_linked=True)
            return dealt
        if hasattr(enemy, 'apply_damage'): enemy.apply_damage(damage, self)
        else: enemy.health -= damage
        dealt = max(0, before - max(0.0, float(enemy.health)))
        self.stats.record_dealt(source, dealt, self.enemy_label(enemy))
        if enemy.health <= 0: self.kill_enemy(enemy)
        if was_linked:
            self._spread_soul_chain_damage(enemy, dealt, source, was_linked=True)
        return dealt


    def damage_boss(self, damage, source=None):
        if self.boss is None or self.boss.invincible: return 0
        boss = self.boss
        # 某些领主有元素克制（例如巨雪怪结霜时怕火）
        if hasattr(boss, 'adjust_incoming'):
            damage = boss.adjust_incoming(damage, source)
        before = float(boss.health)
        was_linked = boss in self.soul_chain_targets
        if self.boss.break_gauge_max > 0 and not self.boss.break_broken:
            if self.boss.apply_break_damage(damage):
                pass
        if self.boss.shield_active:
            damage = int(damage * 0.6)
            self.boss.shield_hp -= damage
            if self.boss.shield_hp <= 0:
                self.boss.shield_active = False
                color = self.boss.PHASE_NOVA_COLOR
                self.spawn_nova_wave(self.boss.rect.centerx, self.boss.rect.centery,
                                     max_radius=220, damage=8, speed=5, small=True, color=color)
            dealt = max(0, before - max(0.0, float(boss.health)))
            if was_linked:
                self._spread_soul_chain_damage(boss, dealt, source, was_linked=True)
            return dealt
        if hasattr(self.boss, 'apply_damage'):
            self.boss.apply_damage(damage, self)
        else:
            self.boss.health -= damage
        dealt = max(0, before - max(0.0, float(boss.health)))
        self.stats.record_dealt(source, dealt, self.boss.BOSS_NAME)
        if self.boss.health <= 0: self.kill_boss()
        if was_linked:
            self._spread_soul_chain_damage(boss, dealt, source, was_linked=True)
        return dealt


    def kill_enemy(self, enemy):
        is_elite = getattr(enemy, 'is_elite', False)
        is_mirror_duelist = getattr(enemy, 'is_mirror_duelist', False)
        if getattr(enemy, 'has_revive', False) and not getattr(enemy, 'revived', False):
            enemy.revived = True
            enemy.health = enemy.max_health // 2
            enemy.apply_damage(0, self)
            enemy.health = enemy.max_health // 2
            self.show_message(f"{enemy.cfg['name']} 复活了！", 800)
            return
        self.heal_bone_carriers_on_death(enemy)
        self.spawn_zombie_from_death(enemy)
        if getattr(enemy, 'is_zombie', False):
            self.spawn_ghost_from_zombie(enemy)
        # 图鉴与统计：普通敌人与精英都在这里记账
        label = self.enemy_label(enemy)
        self.note_codex_kill(label)
        self.stats.record_kill(is_elite, self.frame)
        if getattr(enemy, 'enemy_type', None) in (ENEMY_SKELETON, ENEMY_GHOST):
            self._heal_nearby_wraithbones(enemy)
        if self.mode == MODE_SUMMONER and not getattr(enemy, 'is_church_cross', False):
            self._capture_enemy(enemy)
        elif (self.player.pact_timer > 0
              and not getattr(enemy, 'is_church_cross', False)):
            self._raise_pact_ally(enemy)
        if enemy in self.soul_chain_targets:
            if self._soul_chain_has("soul_drain"):
                self.player.gain_temp_health(
                    skill_soul_chain_temp_health(self.soul_chain_skill.level))
            self.soul_chain_targets = [t for t in self.soul_chain_targets if t is not enemy]
        if self.boss is not None and isinstance(self.boss, BoneDragonBoss):
            self.boss.on_minion_death()
        if getattr(enemy, 'enemy_type', None) == 8:
            pool = LavaPool(enemy.rect.centerx, enemy.rect.bottom, duration=240, damage=4)
            self.lava_pools.add(pool); self.all_sprites.add(pool)
        if getattr(enemy, 'enemy_type', None) == 9:
            pool = LavaPool(enemy.rect.centerx, enemy.rect.bottom, duration=180, damage=3, color=POISON_GREEN)
            self.lava_pools.add(pool); self.all_sprites.add(pool)
        if (getattr(enemy, 'enemy_type', None) == 6
                and not getattr(enemy, 'split_done', True)
                and self.scene_type == BIOME_ICE):
            enemy.split_done = True
            for _ in range(2):
                offset_x = random.randint(-15, 15)
                offset_y = random.randint(-10, 5)
                new_x = max(50, min(enemy.rect.x + offset_x, SCREEN_WIDTH - 50))
                new_y = max(50, min(enemy.rect.y + offset_y, SCREEN_HEIGHT - 100))
                small_enemy = Enemy(new_x, new_y, self.current_depth, 6, self.scene_type)
                small_enemy.base_health = 15
                small_enemy.health = 15; small_enemy.max_health = 15
                small_enemy.base_speed = 2.5
                small_enemy.affix_names = []; small_enemy.affix_instances = []
                small_enemy.image = pygame.transform.scale(small_enemy.image, (30, 30))
                small_enemy.rect = small_enemy.image.get_rect(center=(new_x, new_y))
                small_enemy.split_done = True
                small_enemy.rect.bottom = SCREEN_HEIGHT - 30
                self.enemies.add(small_enemy); self.all_sprites.add(small_enemy)

        if self.mode == MODE_UNDEAD_TIDE:
            self._undead_tide_death(enemy, is_elite, is_mirror_duelist)
        elif (self.scene_type in (BIOME_TOMB, BIOME_CHURCH, BIOME_GREAT_TOMB)
              and not is_elite and not is_mirror_duelist):
            etype = getattr(enemy, 'enemy_type', -1)
            if etype >= 0 and not getattr(enemy, 'is_undead', False):
                self.death_essence += 1
                spawn_x = max(30, min(enemy.rect.centerx, SCREEN_WIDTH - 30))
                skel = Enemy(spawn_x, enemy.rect.bottom - 52,
                             self.current_depth, 11, self.scene_type)
                skel.rect.bottom = enemy.rect.bottom
                self.enemies.add(skel); self.all_sprites.add(skel)
                while self.death_essence >= 10:
                    self.death_essence -= 10
                    self._spawn_giant_skeleton()

        for affix in getattr(enemy, 'affix_instances', []):
            affix.on_death(self)
        if self.embers.has(enemy): self.embers.remove(enemy)
        enemy.kill()
        self.player.kills += 1
        if (self.player.lifesteal_amount > 0
                and random.random() < self.player.lifesteal_chance):
            self.player.health = min(self.player.health + self.player.lifesteal_amount,
                                     self.player.max_health)
        if not self.is_boss_room and not is_elite:
            self.initial_enemy_count = max(0, self.initial_enemy_count - 1)
        if is_elite:
            self.player.bombs += 1
            self.player.crystals += 2

        if is_mirror_duelist and self.is_event_room and not self.event_done:
            self.event_done = True
            self.event_running = False
            self._grant_mirror_duel_reward()

        self.update_barriers()
        self.check_rewards()


    def kill_boss(self):
        if self.boss is None: return
        if self.boss in self.soul_chain_targets:
            if self._soul_chain_has("soul_drain"):
                self.player.gain_temp_health(
                    skill_soul_chain_temp_health(self.soul_chain_skill.level))
            self.soul_chain_targets = [t for t in self.soul_chain_targets if t is not self.boss]
        self.player.bombs += 3
        self.player.crystals += 5
        self.reward_points += 2
        self.player.health = min(self.player.health + 20, self.player.max_health)
        self.boss_defeated = True
        self.note_codex_kill(self.boss.BOSS_NAME)
        self.stats.record_boss_kill(self.boss.BOSS_NAME, self.current_depth)
        self.boss.kill(); self.boss = None
        self.update_barriers()
        self.show_message("领主已被击败！获得丰厚奖励！", 3000)
        if self.mode == MODE_UNDEAD_TIDE:
            self.death_essence += 5
            self._spawn_giant_skeleton(SCREEN_WIDTH // 2)
        while self.reward_points > 0:
            self.show_reward_selection()


    def check_collisions(self):
        self.update_undead_fusion()
        for bullet in list(self.bullets):
            if not bullet.alive(): continue
            hit_barrier = False
            for barrier in self.barriers:
                if barrier.visible and pygame.sprite.collide_rect(bullet, barrier):
                    hit_barrier = True; break
            if hit_barrier:
                if bullet.explosive:
                    self.explode_at(bullet.rect.centerx, bullet.rect.centery, bullet.damage, 90)
                bullet.kill(); continue
            hits = pygame.sprite.spritecollide(bullet, self.enemies, False)
            for enemy in hits:
                if enemy in bullet.hit_enemies: continue
                bullet.hit_enemies.add(enemy)
                if bullet.explosive:
                    self.explode_at(bullet.rect.centerx, bullet.rect.centery, bullet.damage, 90)
                    bullet.kill(); break
                else:
                    if getattr(bullet, 'is_crit', False):
                        self.add_floating_text(enemy.rect.centerx, enemy.rect.top - 6,
                                               "暴击", (255, 90, 90), 20)
                    self.damage_enemy(enemy, bullet.damage, source='bullet')
                    if bullet.pierce_count < bullet.pierce_max: bullet.pierce_count += 1
                    else: bullet.kill(); break
            if not bullet.alive(): continue
            for grave in list(self.gravestones):
                if getattr(grave, "health", 0) <= 0:
                    continue
                if pygame.sprite.collide_rect(bullet, grave):
                    self.damage_gravestone(grave, bullet.damage)
                    if bullet.pierce_count < bullet.pierce_max:
                        bullet.pierce_count += 1
                    else:
                        bullet.kill()
                    break
            if not bullet.alive(): continue
            if self.boss is not None and not self.boss.invincible:
                if pygame.sprite.collide_rect(bullet, self.boss):
                    if bullet.explosive:
                        self.explode_at(bullet.rect.centerx, bullet.rect.centery, bullet.damage, 90)
                        bullet.kill()
                    else:
                        if getattr(bullet, 'is_crit', False):
                            self.add_floating_text(self.boss.rect.centerx, self.boss.rect.top - 6,
                                                   "暴击", (255, 90, 90), 20)
                        self.damage_boss(bullet.damage, source='bullet')
                        if bullet.pierce_count < bullet.pierce_max: bullet.pierce_count += 1
                        else: bullet.kill()

        for bomb in self.bombs:
            if bomb.exploded:
                # 炸弹的爆炸也算"任何爆炸"，范围内的疏雪层一并铲掉
                self.destroy_snow_drifts(bomb.rect.centerx, bomb.rect.centery,
                                         getattr(bomb, 'radius', 80))
                results = bomb.check_explosion_damage(self.enemies)
                for enemy, damage in results:
                    self.damage_enemy(enemy, damage, source='bomb')
                grave_results = bomb.check_explosion_damage(self.gravestones)
                for grave, damage in grave_results:
                    self.damage_gravestone(grave, damage, source='bomb')
                if self.boss is not None:
                    boss_results = bomb.check_explosion_damage([self.boss])
                    for b, damage in boss_results:
                        self.damage_boss(damage, source='bomb')

        if not self.paused:
            dmg_scale = 1 + self.current_depth * 0.08
            hits = pygame.sprite.spritecollide(self.player, self.enemies, False)
            if hits:
                for enemy in hits:
                    if enemy.is_ember: continue
                    if getattr(enemy, 'is_church_cross', False): continue
                    if not getattr(enemy, 'contact_harmful', True): continue
                    if getattr(enemy, 'evolved', False) \
                            and getattr(enemy, 'is_bone_carrier', False):
                        self.player.apply_soul_burn(
                            getattr(enemy, 'elite_name', "炼魂魔骷"))
                    if getattr(enemy, 'is_wind', False):
                        # 风灵不造成伤害，只按风向把玩家往外推
                        self.push_player(1 if enemy.rect.centerx > self.player.rect.centerx
                                         else -1)
                        continue
                    damage = 0.5
                    if getattr(enemy, 'is_elite', False): damage += 0.8
                    elif enemy.enemy_type == 2: damage += 0.3
                    elif enemy.enemy_type == 3: damage += 0.5
                    elif enemy.enemy_type == 5: damage += 0.6
                    elif enemy.enemy_type == ENEMY_ZOMBIE: damage += 0.1
                    damage *= getattr(enemy, 'damage_multiplier', 1.0)
                    if getattr(enemy, 'buff_timer', 0) > 0:
                        damage *= 1.0 + TROLL_BUFF_DAMAGE      # 狂呼者的增幅
                    if getattr(enemy, 'cross_buff_timer', 0) > 0:
                        damage *= 1.0 + TROLL_BUFF_DAMAGE
                    target_name = self.enemy_label(enemy)
                    took = self.hurt_player(damage * dmg_scale, target_name,
                                            codex=target_name)
                    if took:
                        for affix in getattr(enemy, 'affix_instances', []):
                            affix.on_hit_player(self.player, self)
                        if self.player.thorns_damage > 0:
                            self.damage_enemy(enemy, self.player.thorns_damage, source='thorns')

        if not self.paused and self.church_crosses:
            cross_damage = max(2, int(2 + self.current_depth * 0.35))
            for cross in list(self.church_crosses):
                if cross.kind != "holy" or not cross.active or cross.health <= 0:
                    continue
                for enemy in self.enemies:
                    if enemy is cross or getattr(enemy, 'is_ember', False):
                        continue
                    if getattr(enemy, 'health', 0) <= 0:
                        continue
                    if pygame.sprite.collide_rect(cross, enemy):
                        if cross.enemy_hit_timer <= 0:
                            self.damage_church_cross(cross, cross_damage,
                                                     source='cross_contact')
                            cross.enemy_hit_timer = 30
                        break

        if not self.paused:
            self._update_ally_combat()

        for spike in self.ice_spikes:
            if not spike.hit_player and not spike.landed:
                if spike.check_player_hit(self.player):
                    self.hurt_player(spike.damage, self.boss_label() or "冰刺",
                                     codex=self.boss_label())

        for wave in self.nova_waves:
            if wave.check_player_hit(self.player):
                self.hurt_player(wave.damage, self.boss_label() or "冲击波",
                                 codex=self.boss_label())

        for gw in self.ground_waves:
            if gw.hit_timer > 0: continue
            if pygame.sprite.collide_rect(gw, self.player):
                self.hurt_player(gw.damage, self.boss_label() or "贴地横波",
                                 codex=self.boss_label())
                gw.hit_timer = 40

        for hook in list(self.hook_projectiles):
            if not hook.alive(): continue
            hit_barrier = False
            for b in self.barriers:
                if b.visible and pygame.sprite.collide_rect(hook, b):
                    hit_barrier = True; break
            if hit_barrier:
                hook.kill(); continue
            if pygame.sprite.collide_rect(hook, self.player):
                hook_name = self.enemy_label(hook.owner) if hook.owner is not None else "铁钩"
                took = self.hurt_player(hook.damage, hook_name, codex=hook_name)
                if took and hook.owner is not None and hook.owner.alive():
                    self.player.hook_pull_timer = 60
                    self.player.hook_pull_target = hook.owner
                    self.player.velocity_x = 0; self.player.velocity_y = 0
                hook.kill()

        self.check_scene_transition()


    def update_boss_projectiles(self):
        for w in list(self.warnings):
            triggered = w.update()
            if triggered:
                scale = 1 + self.current_depth * 0.05
                if w.spawn_type == "spike":
                    spike = IceSpike(w.x, w.y)
                    spike.damage = int(18 * scale)
                    self.ice_spikes.add(spike); self.all_sprites.add(spike)
                elif w.spawn_type == "meteor":
                    pool = LavaPool(w.x, w.y - 5, duration=180, damage=int(6 * scale))
                    self.lava_pools.add(pool); self.all_sprites.add(pool)
                    fb = Fireball(w.x, w.y - 300, 0, 18, damage=int(18 * scale))
                    self.fireballs.add(fb); self.all_sprites.add(fb)
                elif w.spawn_type == "bomb":
                    fb = Fireball(w.x, w.y - 300, 0, 16, damage=int(12 * scale),
                                  color=(180, 100, 60))
                    self.fireballs.add(fb); self.all_sprites.add(fb)
                elif w.spawn_type == "bone":
                    fb = Fireball(w.x, w.y - 300, 0, 20, damage=int(14 * scale),
                                  color=(220, 210, 240))
                    self.fireballs.add(fb); self.all_sprites.add(fb)
                w.kill()

        for spike in list(self.ice_spikes):
            spike.update()
            if spike.landed:
                spike.ground_timer += 1
                if spike.ground_timer > 90: spike.kill()

        for wave in self.nova_waves: wave.update()
        for gw in self.ground_waves: gw.update()

        for circle in list(self.summon_circles):
            triggered = circle.update()
            if triggered:
                ex = max(40, min(circle.x - 15, SCREEN_WIDTH - 70))
                spawn_y = circle.y - 70
                if getattr(circle, 'elite_kind', None):
                    # 召唤精英（例如酋长叫来的巨魔士兵）
                    enemy = EliteEnemy(ex, spawn_y, self.current_depth,
                                       circle.scene_type, circle.elite_kind)
                else:
                    enemy = Enemy(ex, spawn_y,
                                  self.current_depth, circle.enemy_type, circle.scene_type)
                # 体型大的召唤物可能比地面还低，兜一下免得直接掉出房间
                if enemy.rect.bottom > circle.y - 20:
                    # 按体型把落点抬到圆心上方，大号巨魔也不会塞进地面
                    enemy.rect.bottom = circle.y - 20
                if enemy.rect.bottom > SCREEN_HEIGHT - 30:
                    enemy.rect.bottom = SCREEN_HEIGHT - 30
                enemy.is_summoned = True
                self.enemies.add(enemy); self.all_sprites.add(enemy)
                circle.kill()

        for fb in list(self.fireballs):
            fb.update(self.barriers)
            if not fb.alive(): continue
            if pygame.sprite.collide_rect(fb, self.player):
                self.hurt_player(fb.damage, self.boss_label() or "火球",
                                 codex=self.boss_label())
                fb.kill()
                continue
            for cross in list(self.church_crosses):
                if cross.kind != "holy" or not cross.active or cross.health <= 0:
                    continue
                if pygame.sprite.collide_rect(fb, cross):
                    self.damage_church_cross(cross, max(2, int(fb.damage * 0.7)),
                                             source='enemy_projectile')
                    fb.kill()
                    break

        for shot in list(self.soul_shocks):
            shot.update(self.barriers)
            if not shot.alive():
                continue
            if pygame.sprite.collide_rect(shot, self.player):
                codex = (getattr(shot.owner, "elite_name", None)
                         or "炼魂魔骷")
                self.hurt_player_true(shot.damage, "soul_shock", codex=codex)
                shot.kill()

        for wall in list(self.flame_walls):
            wall.update()
            if not wall.alive(): continue
            if wall.hit_timer > 0: wall.hit_timer -= 1
            if pygame.sprite.collide_rect(wall, self.player):
                if wall.hit_timer <= 0:
                    self.hurt_player(wall.damage, self.boss_label() or "火墙",
                                     codex=self.boss_label())
                    wall.hit_timer = 30

        for pool in list(self.lava_pools):
            pool.update()
            if not pool.alive(): continue

            if pool.team == "player":
                # ---- 玩家方燃烧区：伤害敌人 ----
                if pool.tick_timer > 0:
                    pool.tick_timer -= 1
                else:
                    hit_any = False
                    for enemy in list(self.enemies):
                        if getattr(enemy, 'health', 0) <= 0: continue
                        if pygame.sprite.collide_rect(pool, enemy):
                            self.damage_enemy(enemy, pool.damage, source='scorch')
                            hit_any = True
                    if (self.boss is not None and not self.boss.invincible
                            and pygame.sprite.collide_rect(pool, self.boss)):
                        self.damage_boss(pool.damage, source='scorch')
                        hit_any = True
                    if hit_any:
                        pool.tick_timer = 30  # 每 0.5 秒结算一次
            else:
                # ---- Boss 生成的岩浆池：伤害玩家（保持原逻辑）----
                if pool.hit_timer > 0: pool.hit_timer -= 1
                if pygame.sprite.collide_rect(pool, self.player):
                    if pool.hit_timer <= 0:
                        self.hurt_player(pool.damage, self.boss_label() or "岩浆",
                                         codex=self.boss_label())
                        pool.hit_timer = 30

        for ember in list(self.embers):
            ember.update(self.player, self.platforms)
            if ember.exploded:
                if ember.check_explosion(self.player):
                    self.hurt_player(15, self.boss_label() or "余烬自爆",
                                     codex=self.boss_label())
                if self.boss is not None and isinstance(self.boss, BoneDragonBoss):
                    self.boss.on_minion_death()
                self.embers.remove(ember)
                if self.enemies.has(ember): self.enemies.remove(ember)
                ember.kill()

        for hook in list(self.hook_projectiles):
            hook.update(self.barriers, self.platforms)

