"""召唤师模式：捕捉、召唤、盟友战斗。"""


# === IMPORTS ===
import pygame
import random
from ..data.modes import MODE_SUMMONER
from ..data.skills import ALLY_INCOMING_DAMAGE, PACT_ALLY_CAP, PACT_ALLY_LIFETIME, SKILL_PACT, SLOT_KEY_NAMES, SUMMON_COOLDOWN
from ..entities.enemies import AllyUnit
from ..settings import SCREEN_HEIGHT, SCREEN_WIDTH
# === /IMPORTS ===

class GameSummonerMixin:
    def _summoner_key(self, slot):
        """U/I/O 在召唤师模式下的行为：捕捉 -> 召唤 -> 收回 -> 再召唤。"""
        if self.capture_slot == slot:
            self.capture_slot = -1
            self.show_message("已取消捕捉", 800)
            return False
        if self.captured[slot] is not None:
            if self.ally_out[slot]:
                return self._recall_ally(slot)
            return self._summon_ally(slot)
        self.capture_slot = slot
        self.show_message(f"{SLOT_KEY_NAMES[slot]} 捕捉开启：击败一名敌人", 1400)
        return True


    def _capture_enemy(self, enemy):
        """把刚被击杀的敌人记进正在捕捉的槽位。"""
        if self.mode != MODE_SUMMONER or self.capture_slot < 0:
            return
        if getattr(enemy, 'is_ember', False) or getattr(enemy, 'is_mirror_duelist', False):
            return
        slot = self.capture_slot
        self.captured[slot] = self._enemy_to_template(enemy)
        # 重新捕捉时丢掉这一槽旧的召唤物
        old = self.summoned[slot]
        if old is not None:
            old.kill()
            self.summoned[slot] = None
        self.ally_out[slot] = False
        self.capture_slot = -1
        self.show_message(f"{SLOT_KEY_NAMES[slot]} 已捕捉：{self.captured[slot]['name']}", 1600)


    def _enemy_to_template(self, enemy):
        """把一只敌人抽成召唤模板：外形、词缀、基础属性都带上。"""
        cfg = getattr(enemy, 'cfg', None) or {}
        name = (getattr(enemy, 'elite_name', None) or cfg.get("name") or "敌人")
        return {
            "enemy_type": getattr(enemy, 'enemy_type', 0),
            "elite_kind": getattr(enemy, 'kind', None),
            "is_elite": bool(getattr(enemy, 'is_elite', False)),
            "is_flying": bool(getattr(enemy, 'is_flying', False)),
            "cfg": cfg,
            "base_speed": float(getattr(enemy, 'base_speed', 2.0)),
            "max_health": float(getattr(enemy, 'max_health', 30)),
            "affix_names": list(getattr(enemy, 'affix_names', []) or []),
            "image": enemy.image.copy(),
            "name": name,
            "hp_mult": 1.0, "atk_bonus": 0,
            "hp_buys": 0, "atk_buys": 0, "affix_buys": 0,
            "lifetime": 0,
        }


    def _pact_has(self, key):
        for s in self.player.skills:
            if s is not None and s.kind == SKILL_PACT and s.has_evolution(key):
                return True
        return False


    def _raise_pact_ally(self, enemy):
        """亡者契约：把刚死的敌人拉起来当临时友军。"""
        if getattr(enemy, 'is_ember', False) or getattr(enemy, 'is_mirror_duelist', False):
            return
        pact_count = sum(1 for a in self.allies if getattr(a, 'is_pact', False))
        if pact_count >= PACT_ALLY_CAP:
            return
        template = self._enemy_to_template(enemy)
        template["lifetime"] = PACT_ALLY_LIFETIME
        x = max(50, min(enemy.rect.centerx, SCREEN_WIDTH - 50))
        ally = AllyUnit(x, enemy.rect.bottom, self.current_depth, template,
                        self.scene_type, slot=-1)
        ally.is_pact = True
        self.allies.add(ally); self.all_sprites.add(ally)
        if self._pact_has("soul_tax"):
            self.player.health = min(self.player.health + 6, self.player.max_health)
        self.add_floating_text(x, enemy.rect.top - 8, "契约", (140, 235, 190), 16)


    def _summon_ally(self, slot):
        """把这一槽绑定的召唤物放出来，它会一直占着这个槽位直到被收回或阵亡。"""
        if self.summon_cd[slot] > 0:
            self.show_message(f"{SLOT_KEY_NAMES[slot]} 冷却中", 700)
            return False
        template = self.captured[slot]
        x = max(60, min(self.player.rect.centerx + random.choice([-70, 70]),
                        SCREEN_WIDTH - 60))
        y = SCREEN_HEIGHT - 200 if template["is_flying"] else SCREEN_HEIGHT - 30
        ally = self.summoned[slot]
        if ally is None:
            ally = AllyUnit(x, y, self.current_depth, template, self.scene_type,
                            slot=slot)
            self.summoned[slot] = ally
        else:
            # 收回或阵亡过的召唤物：重新摆位并带上商店的强化
            ally.refresh_from_template(template)
            ally.teleport_to(x, y)
        self.allies.add(ally); self.all_sprites.add(ally)
        self.ally_out[slot] = True
        self.summon_cd[slot] = SUMMON_COOLDOWN
        self.show_message(f"召唤 {template['name']}！", 1200)
        return True


    def _recall_ally(self, slot):
        """把出场的召唤物收回槽位，血量保留，再按一次可以重新放出。"""
        ally = self.summoned[slot]
        if ally is not None:
            ally.kill()
        self.ally_out[slot] = False
        self.summon_cd[slot] = SUMMON_COOLDOWN
        self.show_message(f"收回 {self.captured[slot]['name']}", 900)
        return True


    def _refresh_ally(self, slot):
        """商店强化之后，同步给已经出场的那一只。"""
        ally = self.summoned[slot]
        if ally is not None and self.ally_out[slot] and ally.alive():
            ally.refresh_from_template(self.captured[slot])


    def _reposition_allies(self):
        """换房间时把还在场上的召唤物一起带过去。"""
        # 亡者契约唤起的临时友军只服务于当前房间
        for ally in list(self.allies):
            if getattr(ally, 'is_pact', False):
                ally.kill()
        offsets = [-60, 60, -110]
        i = 0
        for slot, ally in enumerate(self.summoned):
            if ally is None or not self.ally_out[slot]:
                continue
            x = max(40, min(self.player.rect.centerx + offsets[i % len(offsets)],
                            SCREEN_WIDTH - 40))
            i += 1
            y = SCREEN_HEIGHT - 30 if not ally.is_flying else max(70, self.player.rect.centery - 60)
            ally.teleport_to(x, y)


    def _update_ally_combat(self):
        """友军与敌人的接触结算：双方互相造成伤害。"""
        if not self.allies:
            return
        dmg_scale = 1 + self.current_depth * 0.08
        for ally in list(self.allies):
            if ally.health <= 0:
                self._ally_defeated(ally); continue
            if (self.boss is not None and self.boss.health > 0
                    and pygame.sprite.collide_rect(ally, self.boss)):
                if ally.attack_cd <= 0:
                    ally.attack_cd = AllyUnit.CONTACT_CD
                    self.damage_boss(ally.contact_damage, source='ally')
                ally.take_damage(1.5 * getattr(self.boss, 'dmg_mult', 1.0)
                                 * dmg_scale * ALLY_INCOMING_DAMAGE, self)
            for enemy in pygame.sprite.spritecollide(ally, self.enemies, False):
                if getattr(enemy, 'is_ember', False):
                    continue
                if ally.attack_cd <= 0:
                    ally.attack_cd = AllyUnit.CONTACT_CD
                    self.damage_enemy(enemy, ally.contact_damage, source='ally')
                    # 复制来的攻击型词缀（冰冻/吸血等）打到敌人身上
                    for affix in ally.affix_instances:
                        affix.on_hit_player(enemy, self)
                damage = 0.6
                if getattr(enemy, 'is_elite', False):
                    damage += 0.9
                else:
                    etype = getattr(enemy, 'enemy_type', -1)
                    if etype == 2: damage += 0.3
                    elif etype == 3: damage += 0.5
                    elif etype == 5: damage += 0.6
                damage *= getattr(enemy, 'damage_multiplier', 1.0)
                ally.take_damage(damage * dmg_scale * ALLY_INCOMING_DAMAGE, self)


    def _ally_defeated(self, ally):
        """召唤物阵亡：槽位直接清空，需要重新捕捉。"""
        slot = getattr(ally, 'slot', -1)
        name = "召唤物"
        if 0 <= slot < len(self.captured) and self.captured[slot] is not None:
            name = self.captured[slot].get("name", name)
        ally.kill()
        ally.health = ally.max_health
        if 0 <= slot < len(self.captured):
            self.ally_out[slot] = False
            self.captured[slot] = None
            self.summoned[slot] = None
            self.summon_cd[slot] = 0
            if self.capture_slot == slot:
                self.capture_slot = -1
            self.show_message(
                f"{SLOT_KEY_NAMES[slot]} 的{name}阵亡，槽位已空", 1600)

