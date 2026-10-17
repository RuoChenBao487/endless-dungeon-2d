"""奖励选择与强化。"""


# === IMPORTS ===
import pygame
import random
import sys
from ..data.biomes import BIOME_NORMAL
from ..data.modes import MODE_SUMMONER
from ..data.skills import SKILL_DATA, SKILL_ORDER, SLOT_KEY_NAMES, Skill
from ..settings import (BOMB_RADIUS, CYAN, FPS, GOLD, GREEN, LIMITED_ENHANCE_PICKS,
                        SCREEN_HEIGHT, SCREEN_WIDTH, WHITE, clock, screen)
from ..timing import advance_frame
from ..utils import draw_panel, present
# === /IMPORTS ===

class GameRewardMixin:
    def _apply_random_enhancement(self):
        available = self._get_available_enhancements()
        available = [e for e in available if "学习新技能" not in e["name"]]
        if not available: return None
        total_weight = sum(e['weight'] for e in available)
        r = random.uniform(0, total_weight)
        upto = 0
        chosen = available[-1]
        for e in available:
            upto += e['weight']
            if upto >= r:
                chosen = e
                break
        try:
            return chosen["func"]()
        except Exception:
            return None


    def _get_available_enhancements(self):
        # 召唤师模式的槽位不装技能，剔除所有技能相关的强化
        skill_funcs = ("enhance_new_skill", "enhance_unlock_slot_i",
                       "enhance_unlock_slot_o")
        available = []
        for e in self.enhancements:
            if (self.mode == MODE_SUMMONER
                    and getattr(e["func"], "__name__", "") in skill_funcs):
                continue
            key = e.get("key")
            if key and self.enhance_counts.get(key, 0) >= LIMITED_ENHANCE_PICKS:
                continue
            if e.get("check") and e["check"](): continue
            available.append(e)
        return available


    def show_reward_selection(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("获得强化奖励！", 52, GOLD, SCREEN_WIDTH // 2, 100)
        self.draw_text("选择一项强化", 30, (200, 200, 220), SCREEN_WIDTH // 2, 155)
        available = self._get_available_enhancements()
        if not available:
            self.reward_points -= 1
            return
        selected = []
        for _ in range(min(3, len(available))):
            total_weight = sum(e['weight'] for e in available)
            r = random.uniform(0, total_weight)
            upto = 0
            for e in available:
                upto += e['weight']
                if upto >= r:
                    selected.append(e); available.remove(e); break
        card_w = 220; card_h = 100
        start_x = SCREEN_WIDTH // 2 - (len(selected) * card_w + (len(selected) - 1) * 20) // 2
        for i, enh in enumerate(selected):
            x = start_x + i * (card_w + 20)
            y = 220
            rect = (x, y, card_w, card_h)
            draw_panel(screen, rect, GOLD, 200)
            self.draw_text(f"[{i + 1}]", 22, GOLD, x + 30, y + 22)
            name = enh['name']
            if len(name) > 12:
                line1 = name[:12]; line2 = name[12:]
                self.draw_text(line1, 20, WHITE, x + card_w // 2, y + 50)
                self.draw_text(line2, 20, WHITE, x + card_w // 2, y + 76)
            else:
                self.draw_text(name, 22, WHITE, x + card_w // 2, y + 60)
        present()
        waiting = True
        while waiting:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1 and len(selected) >= 1:
                        msg = selected[0]["func"]()
                        self.show_enhancement_message(msg); waiting = False
                    elif event.key == pygame.K_2 and len(selected) >= 2:
                        msg = selected[1]["func"]()
                        self.show_enhancement_message(msg); waiting = False
                    elif event.key == pygame.K_3 and len(selected) >= 3:
                        msg = selected[2]["func"]()
                        self.show_enhancement_message(msg); waiting = False
        self.reward_points -= 1


    def show_replace_selection(self, new_kind):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("技能槽已满", 48, GOLD, SCREEN_WIDTH // 2, 110)
        self.draw_text(f"获得新技能：{SKILL_DATA[new_kind]['name']}", 30, CYAN, SCREEN_WIDTH // 2, 165)
        self.draw_text("请选择要替换的技能", 26, (200, 200, 220), SCREEN_WIDTH // 2, 205)
        p = self.player
        card_w = 200; card_h = 140
        n = max(1, p.skill_slots)
        start_x = SCREEN_WIDTH // 2 - (n * card_w + (n - 1) * 20) // 2
        for i in range(n):
            skill = p.skills[i]
            x = start_x + i * (card_w + 20); y = 260
            rect = (x, y, card_w, card_h)
            draw_panel(screen, rect, GOLD, 200)
            if skill:
                self.draw_text(f"[{i + 1}] {skill.name}", 24, WHITE, x + card_w // 2, y + 35)
                self.draw_text(f"Lv.{skill.level}", 20, (200, 200, 220), x + card_w // 2, y + 70)
                self.draw_text(f"进化：{skill.evolution_name()}", 18, (160, 180, 200), x + card_w // 2, y + 100)
            else:
                self.draw_text(f"[{i + 1}] 空槽", 24, (120, 120, 140), x + card_w // 2, y + 65)
        self.draw_text("按 1-3 选择替换槽位（ESC 放弃）", 22, (150, 150, 170), SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)
        present()
        while True:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: return None
                    if pygame.K_1 <= event.key <= pygame.K_3:
                        idx = event.key - pygame.K_1
                        if idx < p.skill_slots: return idx


    def check_scene_transition(self):
        is_cleared = self.update_barriers()
        if not is_cleared or self.paused: return
        if self.player.rect.left <= self.left_barrier.rect.right:
            self.change_dungeon('left')
        elif self.player.rect.right >= self.right_barrier.rect.left:
            self.change_dungeon('right')


    def check_rewards(self):
        if self.paused: return
        new_kills = self.player.kills - self.last_kill_count
        if new_kills >= 10:
            points_earned = new_kills // 10
            self.reward_points += points_earned
            self.last_kill_count += points_earned * 10
            while self.reward_points > 0:
                self.show_reward_selection()


    def check_elite_challenge_reward(self):
        if (self.is_event_room and self.pending_elite_reward
                and len(self.enemies) == 0):
            self.pending_elite_reward = False
            self.player.crystals += 8
            self.pending_event_rewards += 4
            self.show_message("挑战完成！+8晶体 + 4次强化！", 2500)


    def check_crystal_collection(self):
        if not (self.scene_type != BIOME_NORMAL or self.is_boss_room): return
        if self.paused: return
        hits = pygame.sprite.spritecollide(self.player, self.crystals, True)
        if hits:
            self.player.crystals += len(hits)
            self.show_message(f"拾取 {len(hits)} 个晶体", 800)


    def enhance_heal(self):
        self.player.health = min(self.player.health + 20, self.player.max_health)
        return "恢复了20点生命值！"


    def enhance_jump(self):
        self.enhance_counts["jump"] = self.enhance_counts.get("jump", 0) + 1
        self.player.jump_power_multiplier += 0.15
        return "跳跃高度提升了！"


    def enhance_attack_speed(self):
        self.player.attack_speed_multiplier += 0.2
        cd = 24 / self.player.attack_speed_multiplier
        return f"攻击速度提升了！攻击间隔 {cd:.1f} 帧"


    def enhance_move_speed(self):
        self.enhance_counts["move_speed"] = self.enhance_counts.get("move_speed", 0) + 1
        self.player.speed_multiplier += 0.15
        return "移动速度提升了！"


    def enhance_max_health(self):
        self.player.max_health += 5
        self.player.health = min(self.player.health + 5, self.player.max_health)
        return "最大生命值提升了！"


    def enhance_attack_damage(self):
        self.player.attack_bonus += 4
        return f"攻击力 +4！当前基础攻击 {int(self.player.attack_damage)}"


    def enhance_bombs(self):
        self.player.bombs += 3
        return f"获得了3个炸弹！现在拥有{self.player.bombs}个！"


    def enhance_anti_slide(self):
        self.player.anti_slide = True
        self.player.speed_multiplier += 0.08
        return "获得防滑靴！冰面无滑行，普通场景速度+8%！"


    def enhance_bomb_upgrade(self):
        self.player.bomb_upgrade += 1
        lvl = self.player.bomb_upgrade
        radius = int(BOMB_RADIUS * (1.3 + 0.15 * lvl))
        tick = 8 + 5 * lvl
        return f"爆破专家 Lv.{lvl}！范围 → {radius}，持续伤害 → {tick}/跳"


    def enhance_emergency_shield(self):
        self.player.emergency_shield = True
        return "获得应急护盾！低血量自动激活！"


    def enhance_piercing_bullets(self):
        self.player.piercing_bullets += 1
        self.player.attack_damage_multiplier += 0.1
        return f"精准射击！穿透+1，当前穿透{self.player.piercing_bullets}！"


    def enhance_double_jump(self):
        self.player.double_jump = True
        return "解锁二段跳！空中可再次跳跃！"


    def enhance_crit(self):
        if self.player.crit_chance < 0.6:
            self.player.crit_chance = min(0.6, self.player.crit_chance + 0.10)
            return f"暴击率提升至 {int(self.player.crit_chance * 100)}%！"
        else:
            self.player.crit_damage_bonus += 5
            return f"暴击率已满，暴击伤害加成 +5！（当前 +{self.player.crit_damage_bonus}）"


    def enhance_crit_damage(self):
        self.player.crit_damage_bonus += 5
        return (f"暴击伤害加成 +5！暴击时：(伤害+{self.player.crit_damage_bonus})×"
                f"{self.player.crit_multiplier:.1f}")


    def enhance_lifesteal_chance(self):
        self.player.lifesteal_chance = min(0.8, self.player.lifesteal_chance + 0.10)
        return f"噬血概率提升至 {int(self.player.lifesteal_chance * 100)}%！"


    def enhance_lifesteal_amount(self):
        self.player.lifesteal_amount += 1
        return f"噬血回血量提升至 {self.player.lifesteal_amount}！"


    def enhance_thorns(self):
        self.player.thorns_damage += 5
        return f"反伤！受击时周围敌人掉 {self.player.thorns_damage} 点血！"


    def enhance_max_energy(self):
        self.player.max_energy += 20
        self.player.energy = min(self.player.max_energy, self.player.energy + 20)
        return f"能量上限提升至 {int(self.player.max_energy)}！"


    def enhance_energy_regen(self):
        self.player.energy_regen += 0.5
        return f"能量恢复提升至 {self.player.energy_regen:.1f}/秒！"


    def enhance_unlock_slot_i(self):
        self.player.skill_slots = max(self.player.skill_slots, 2)
        return "解锁技能槽 II！按 I 键释放技能！"


    def enhance_unlock_slot_o(self):
        self.player.skill_slots = max(self.player.skill_slots, 3)
        return "解锁技能槽 III！按 O 键释放技能！"


    def enhance_new_skill(self):
        p = self.player
        empty = None
        for i in range(p.skill_slots):
            if p.skills[i] is None:
                empty = i; break
        pool = [k for k in SKILL_ORDER if not any(s and s.kind == k for s in p.skills)]
        if not pool: return "所有技能已掌握！"
        new_kind = random.choice(pool)
        if empty is not None:
            p.skills[empty] = Skill(new_kind)
            return f"获得新技能：{SKILL_DATA[new_kind]['name']}（{SLOT_KEY_NAMES[empty]}键）！"
        idx = self.show_replace_selection(new_kind)
        if idx is None: return "放弃了新技能"
        old = p.skills[idx]
        p.skills[idx] = Skill(new_kind)
        return f"{old.name if old else '空槽'} → {SKILL_DATA[new_kind]['name']}！"


    def show_enhancement_message(self, message):
        if not message: return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 220))
        screen.blit(overlay, (0, 0))
        self.draw_text("生效！", 52, GREEN, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)
        self.draw_text(message, 26, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)
        self.draw_text("按任意键继续", 22, (150, 150, 170), SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100)
        present()
        waiting = True
        while waiting:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif event.type == pygame.KEYDOWN:
                    waiting = False

