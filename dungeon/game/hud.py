"""界面绘制：HUD、技能栏、规则、图鉴、结算画面。"""


# === IMPORTS ===
import pygame
import sys
from .. import gallery
from .. import savegame
from .. import achievements
from ..data.biomes import BIOME_COLORS, BIOME_GREAT_TOMB, BIOME_NAMES, BIOME_TOMB
from ..data.modes import MODE_CLASSIC, MODE_SUMMONER, MODE_UNDEAD_TIDE
from ..data.skills import SKILL_METEOR, SKILL_SOUL_CHAIN, SKILL_TIME_REWIND, SLOT_KEY_NAMES
from ..save import profile
from ..settings import CYAN, ELITE_PURPLE, FPS, FRAGILE_PATH_SECONDS, GOLD, GREEN, ORANGE, OUTLINE, RED, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE, YELLOW, clock, get_font, screen
from ..timing import advance_frame, frame_count
from ..utils import (back_hit, draw_back_button, draw_panel, present, reward_cat_at,
                     reward_cat_rect)
# === /IMPORTS ===

class GameHudMixin:
    def draw_message(self):
        elapsed = frame_count() - self.message_start_frame
        if elapsed < self.message_duration:
            alpha = 255 - elapsed / self.message_duration * 255
            font = get_font(34)
            t1 = font.render(self.message_text, True, (255, 255, 255))
            t2 = font.render(self.message_text, True, (10, 10, 20))
            ts = pygame.Surface((t1.get_width() + 40, t1.get_height() + 20), pygame.SRCALPHA)
            ts.blit(t2, (22, 12)); ts.blit(t1, (20, 10))
            ts.set_alpha(int(alpha))
            rect = ts.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
            screen.blit(ts, rect)


    def draw_text(self, text, size, color, x, y, center=True):
        font = get_font(size)
        shadow = font.render(text, True, (10, 10, 18))
        ts = font.render(text, True, color)
        if center:
            tr = ts.get_rect(center=(x, y))
            screen.blit(shadow, (tr.x + 2, tr.y + 2))
            screen.blit(ts, tr)
        else:
            tr = ts.get_rect(topleft=(x, y))
            screen.blit(shadow, (tr.x + 2, tr.y + 2))
            screen.blit(ts, tr)
        return tr


    def handle_rules_scroll(self, direction):
        max_scroll = max(0, len(self.game_rules) - self.max_visible_rules)
        if direction == "up": self.rules_scroll = max(0, self.rules_scroll - 1)
        elif direction == "down": self.rules_scroll = min(max_scroll, self.rules_scroll + 1)


    def draw_rules(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("游 戏 规 则", 48, GOLD, SCREEN_WIDTH // 2, 60)
        draw_back_button(self.mouse)
        y_offset = 125
        start = self.rules_scroll
        end = start + self.max_visible_rules
        for line in self.game_rules[start:end]:
            self.draw_text(line, 20, WHITE, SCREEN_WIDTH // 2, y_offset)
            y_offset += 28
        self.draw_text("按上下键滚动 | 按ESC返回", 22, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25)


    def draw_enemy_info(self):
        if self.selected_enemy_idx >= len(gallery.ENTRIES):
            self.selected_enemy_idx = 0
        gallery.draw_panel(self.draw_text, self.selected_enemy_idx, self.mouse,
                           self.gallery_category, self.gallery_place)


    def draw_reward_info(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("奖 励 与 强 化", 48, GOLD, SCREEN_WIDTH // 2, 50)
        draw_back_button(self.mouse)
        cat_rect = (50, 110, 200, SCREEN_HEIGHT - 180)
        info_rect = (300, 110, SCREEN_WIDTH - 350, SCREEN_HEIGHT - 180)
        draw_panel(screen, cat_rect, (100, 100, 140), 200)
        draw_panel(screen, info_rect, GOLD, 200)
        categories = [cat["category"] for cat in self.reward_descriptions]
        for i, cat in enumerate(categories):
            color = GOLD if i == self.selected_reward_cat else (150, 150, 170)
            y_pos = cat_rect[1] + 40 + i * 55
            box = reward_cat_rect(i)
            if (self.mouse is not None and box.collidepoint(self.mouse)
                    and i != self.selected_reward_cat):
                pygame.draw.rect(screen, (30, 36, 52, 200), box, border_radius=6)
            if i == self.selected_reward_cat:
                pygame.draw.rect(screen, (40, 50, 80, 200),
                                 (cat_rect[0] + 8, y_pos - 18, cat_rect[2] - 16, 40),
                                 border_radius=6)
            self.draw_text(cat, 22, color, cat_rect[0] + cat_rect[2] // 2, y_pos)
        if 0 <= self.selected_reward_cat < len(self.reward_descriptions):
            sc = self.reward_descriptions[self.selected_reward_cat]
            self.draw_text(sc["category"], 30, GOLD,
                           info_rect[0] + info_rect[2] // 2, info_rect[1] + 35)
            pygame.draw.line(screen, (100, 100, 140),
                             (info_rect[0] + 30, info_rect[1] + 60),
                             (info_rect[0] + info_rect[2] - 30, info_rect[1] + 60), 1)
            y_offset = info_rect[1] + 85
            for item in sc["items"]:
                self.draw_text(item["name"], 22, CYAN, info_rect[0] + 35, y_offset, center=False)
                y_offset += 26
                self.draw_text(item["desc"], 17, (200, 200, 220),
                               info_rect[0] + 50, y_offset, center=False)
                y_offset += 30
        self.draw_text("按上下键选择 | 按ESC返回", 22, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)


    def draw_pause_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 220))
        screen.blit(overlay, (0, 0))
        self.draw_text("游 戏 暂 停", 72, GOLD, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 170)
        options = [
            "按 ESC / K 键继续游戏",
            "按 S 键保存并退出（下次可从主菜单继续）",
            "按 空格 键结束本局（回主菜单）",
            "按 E 键打开图鉴",
            "按 P 键查看游戏规则",
            "按 R 键查看奖励说明",
        ]
        for i, opt in enumerate(options):
            self.draw_text(opt, 28, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 96 + i * 44)


    def draw_hud(self):
        if self.is_boss_room:
            scene_text = f"BOSS · {BIOME_NAMES.get(self.scene_type, '未知')}"
            scene_color = BIOME_COLORS.get(self.scene_type, WHITE)
        elif self.is_event_room:
            scene_text = f"事件房 · {BIOME_NAMES.get(self.scene_type, '地牢')}"
            scene_color = (255, 220, 130)
        else:
            scene_text = BIOME_NAMES.get(self.scene_type, "地牢")
            scene_color = BIOME_COLORS.get(self.scene_type, WHITE)

        top_bar = pygame.Surface((SCREEN_WIDTH, 30), pygame.SRCALPHA)
        top_bar.fill((10, 12, 22, 150))
        screen.blit(top_bar, (0, 0))
        self.draw_text(scene_text, 24, scene_color, SCREEN_WIDTH // 2, 15)
        if self.mode != MODE_CLASSIC:
            self.draw_text(f"【{self.mode_name}】", 16, (255, 200, 120),
                           SCREEN_WIDTH - 80, 15)

        hb_x, hb_y, hb_w, hb_h = 15, 42, 220, 20
        pygame.draw.rect(screen, (10, 12, 22, 200), (hb_x - 3, hb_y - 3, hb_w + 6, hb_h + 6))
        pygame.draw.rect(screen, (60, 20, 30), (hb_x, hb_y, hb_w, hb_h))
        ratio = self.player.health / self.player.max_health
        hp_color = (110, 220, 130) if ratio > 0.5 else ((240, 200, 90) if ratio > 0.25 else (230, 80, 80))
        pygame.draw.rect(screen, hp_color, (hb_x, hb_y, hb_w * ratio, hb_h))
        pygame.draw.rect(screen, (255, 255, 255, 80), (hb_x, hb_y, hb_w * ratio, 3))
        pygame.draw.rect(screen, (200, 200, 220), (hb_x, hb_y, hb_w, hb_h), 2)
        self.draw_text(f"HP {int(self.player.health)}/{self.player.max_health}",
                       16, WHITE, hb_x + hb_w // 2, hb_y + hb_h // 2 + 1)

        eb_x, eb_y, eb_w, eb_h = 15, 68, 220, 12
        pygame.draw.rect(screen, (10, 12, 22, 200), (eb_x - 3, eb_y - 3, eb_w + 6, eb_h + 6))
        pygame.draw.rect(screen, (20, 30, 50), (eb_x, eb_y, eb_w, eb_h))
        eratio = self.player.energy / self.player.max_energy
        pygame.draw.rect(screen, (90, 170, 250), (eb_x, eb_y, eb_w * eratio, eb_h))
        pygame.draw.rect(screen, (200, 220, 255, 120), (eb_x, eb_y, eb_w * eratio, 3))
        pygame.draw.rect(screen, (200, 200, 220), (eb_x, eb_y, eb_w, eb_h), 2)
        self.draw_text(f"EN {int(self.player.energy)}/{int(self.player.max_energy)}",
                       13, WHITE, eb_x + eb_w // 2, eb_y + eb_h // 2)

        self.draw_text(f"深度 {self.current_depth}", 20, WHITE, 15, 96, False)
        if self.is_event_room:
            if self.event_running:
                if self.event_kind in ("bomb_rain", "endless_hunt"):
                    remain = max(0, (self.event_data.get('total', 0) - self.event_timer)) // FPS
                    self.draw_text(f"挑战剩余 {remain}s", 18, (255, 220, 130), 15, 120, False)
                elif self.event_kind == "fragile_path":
                    remain = max(0, (FRAGILE_PATH_SECONDS * FPS - self.event_timer)) // FPS
                    self.draw_text(f"剩余 {remain}s", 18, (255, 220, 130), 15, 120, False)
                elif self.event_kind == "elite_gauntlet":
                    idx = self.event_data.get('gauntlet_idx', 0)
                    total = self.event_data.get('gauntlet_total', 3)
                    self.draw_text(f"车轮战 {idx}/{total}", 18, (255, 220, 130), 15, 120, False)
            else:
                self.draw_text("事件房", 18, (255, 220, 130), 15, 120, False)
        elif not self.is_boss_room:
            self.draw_text(f"剩余 {len(self.enemies)}/{self.initial_enemy_count}",
                           18, (200, 200, 220), 15, 120, False)
        else:
            total_minions = len(self.enemies) + len(self.embers)
            self.draw_text(f"召唤物 {total_minions}", 18, (200, 200, 220), 15, 120, False)

        self.draw_text(f"击杀 {self.player.kills}", 18, WHITE, 15, 144, False)
        prog_x, prog_y, prog_w, prog_h = 85, 149, 100, 8
        pygame.draw.rect(screen, (30, 30, 45), (prog_x, prog_y, prog_w, prog_h))
        pygame.draw.rect(screen, GOLD, (prog_x, prog_y, prog_w * (self.player.kills % 10 / 10), prog_h))
        pygame.draw.rect(screen, (200, 200, 220), (prog_x, prog_y, prog_w, prog_h), 1)

        if (self.mode == MODE_UNDEAD_TIDE
                or self.scene_type in (BIOME_TOMB, BIOME_GREAT_TOMB)
                or self.death_essence > 0):
            self.draw_text(f"死亡气息 {self.death_essence}/10",
                           16, (200, 180, 240), 15, 166, False)

        if self.active_curses:
            cy = 190
            for curse in self.active_curses:
                self.draw_text(f"诅咒 {curse['name']} ({curse['rooms']}房)",
                               15, (235, 130, 150), 15, cy, False)
                cy += 17

        rx = SCREEN_WIDTH - 190
        pygame.draw.polygon(screen, (170, 220, 250), [
            (rx + 8, 100), (rx + 16, 108), (rx + 8, 118), (rx, 108)
        ])
        pygame.draw.polygon(screen, OUTLINE, [
            (rx + 8, 100), (rx + 16, 108), (rx + 8, 118), (rx, 108)
        ], 2)
        self.draw_text(f"x {self.player.crystals}", 18, CYAN, rx + 30, 108, False)
        pygame.draw.circle(screen, (240, 130, 50), (rx + 8, 135), 8)
        pygame.draw.circle(screen, (255, 220, 120), (rx + 8, 135), 4)
        pygame.draw.circle(screen, OUTLINE, (rx + 8, 135), 8, 2)
        self.draw_text(f"x {self.player.bombs}", 18, ORANGE, rx + 30, 135, False)

        bonus_y = 162
        if self.player.piercing_bullets > 0:
            self.draw_text(f"穿透 {self.player.piercing_bullets}", 15, GREEN, rx, bonus_y, False)
            bonus_y += 18
        if self.player.crit_chance > 0 or self.player.crit_damage_bonus > 0:
            self.draw_text(
                f"暴击 {int(self.player.crit_chance * 100)}% +{self.player.crit_damage_bonus} (x2)",
                15, YELLOW, rx, bonus_y, False)
            bonus_y += 18
        if self.player.lifesteal_chance > 0 or self.player.lifesteal_amount > 0:
            self.draw_text(f"噬血 {int(self.player.lifesteal_chance * 100)}% / {self.player.lifesteal_amount}",
                           15, (230, 100, 130), rx, bonus_y, False)
            bonus_y += 18
        if self.player.thorns_damage > 0:
            self.draw_text(f"反伤 {self.player.thorns_damage}", 15, ORANGE, rx, bonus_y, False)
            bonus_y += 18
        if self.player.double_jump:
            self.draw_text("二段跳", 15, CYAN, rx, bonus_y, False)
            bonus_y += 18
        if self.auto_fire_active:
            self.draw_text("自动射击", 15, (255, 200, 100), rx, bonus_y, False)
            bonus_y += 18
        if self.player.meteor_active:
            self.draw_text("吟唱中", 15, (255, 130, 50), rx, bonus_y, False)
            bonus_y += 18
        if self.player.temp_health > 0:
            self.draw_text(f"临时生命 {int(self.player.temp_health)}", 15, (180, 235, 255), rx, bonus_y, False)
            bonus_y += 18
        if self.player.soul_burn_timer > 0:
            remain = self.player.soul_burn_timer / FPS
            self.draw_text(f"燃魂 {remain:.1f}s", 15, (112, 244, 146),
                           rx, bonus_y, False)
            bonus_y += 18
        if self.soul_chain_timer > 0:
            remain = max(0, self.soul_chain_timer) / FPS
            self.draw_text(f"锁链 {remain:.1f}s", 15, (205, 135, 255), rx, bonus_y, False)
            bonus_y += 18

        self.draw_skill_bar()
        self.draw_active_skill_timers()

        if self.is_event_room and not self.event_done and not self.event_running:
            self.draw_text("靠近祭坛按 F 交互", 18, (255, 220, 130),
                           SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18)
        elif self.is_event_room and self.event_running:
            self.draw_text("挑战进行中...", 18, (255, 220, 130),
                           SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18)
        elif not self.is_boss_room:
            if (len(self.enemies) > 0
                    or (self.scene_type == BIOME_GREAT_TOMB
                        and len(self.gravestones) > 0)):
                text = ("消灭敌人并摧毁全部墓碑"
                        if self.scene_type == BIOME_GREAT_TOMB
                        else "消灭敌人以解除屏障")
                self.draw_text(text, 18, (255, 130, 130),
                               SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18)
            else:
                self.draw_text("可以前进！", 18, (130, 240, 150),
                               SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18)

        if self.boss is not None:
            bar_w = 520; bar_h = 24
            bar_x = (SCREEN_WIDTH - bar_w) // 2
            bar_y = 55
            pygame.draw.rect(screen, (10, 12, 22, 220), (bar_x - 6, bar_y - 24, bar_w + 12, bar_h + 50))
            pygame.draw.rect(screen, (60, 20, 30), (bar_x, bar_y, bar_w, bar_h))
            ratio = max(0, self.boss.health / self.boss.max_health)
            hp_color = self.boss.get_hp_color()
            pygame.draw.rect(screen, hp_color, (bar_x, bar_y, bar_w * ratio, bar_h))
            pygame.draw.rect(screen, (255, 255, 255, 100), (bar_x, bar_y, bar_w * ratio, 4))
            pygame.draw.rect(screen, (220, 220, 240), (bar_x, bar_y, bar_w, bar_h), 2)
            for marker in self.boss.PHASE_HP:
                mx = bar_x + bar_w * (1 - marker)
                pygame.draw.line(screen, (240, 240, 250), (mx, bar_y), (mx, bar_y + bar_h), 2)
            self.draw_text(self.boss.BOSS_NAME, 24, WHITE, SCREEN_WIDTH // 2, bar_y - 14)
            self.draw_text(f"阶段 {self.boss.phase} / 3", 16, GOLD, SCREEN_WIDTH // 2, bar_y + bar_h + 10)
            self.boss.draw_break_gauge(screen)

        if self.elite_banner_timer > 0:
            self.elite_banner_timer -= 1
            alpha = min(255, self.elite_banner_timer * 3)
            text_surface = get_font(40).render(f"精英出现：{self.elite_banner_name}", True, ELITE_PURPLE)
            text_surface.set_alpha(alpha)
            rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 220))
            bg = pygame.Surface((text_surface.get_width() + 40, text_surface.get_height() + 16), pygame.SRCALPHA)
            bg.fill((20, 10, 40, int(alpha * 0.6)))
            bg_rect = bg.get_rect(center=(SCREEN_WIDTH // 2, 220))
            screen.blit(bg, bg_rect)
            screen.blit(text_surface, rect)


    def draw_skill_bar(self):
        p = self.player
        if self.mode == MODE_SUMMONER:
            self.draw_summon_bar()
            return
        box_size = 60
        gap = 10
        total_w = p.skill_slots * box_size + (p.skill_slots - 1) * gap
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        if self.boss is not None: y = 102
        else: y = 42
        for i in range(p.skill_slots):
            skill = p.skills[i]
            x = start_x + i * (box_size + gap)
            rect = (x, y, box_size, box_size)
            if skill is None:
                s = pygame.Surface((box_size, box_size), pygame.SRCALPHA)
                s.fill((20, 22, 34, 190))
                screen.blit(s, (x, y))
                pygame.draw.rect(screen, (90, 90, 110), rect, 2, border_radius=8)
                self.draw_text("空", 18, (110, 110, 130), x + box_size // 2, y + box_size // 2 + 8)
            else:
                can_use = p.energy >= skill.cost
                base_col = skill.color if can_use else (90, 90, 100)
                s = pygame.Surface((box_size, box_size), pygame.SRCALPHA)
                s.fill((14, 18, 30, 210))
                screen.blit(s, (x, y))
                # 陨火激活时高亮
                if skill.kind == SKILL_METEOR and p.meteor_active and p.meteor_slot == i:
                    pygame.draw.rect(screen, (255, 200, 100), rect, 4, border_radius=8)
                elif skill.kind == SKILL_TIME_REWIND and p.rewind_active and p.rewind_slot == i:
                    pygame.draw.rect(screen, (105, 220, 235), rect, 4, border_radius=8)
                elif (skill.kind == SKILL_SOUL_CHAIN and self.soul_chain_skill is skill
                      and self.soul_chain_timer > 0):
                    pygame.draw.rect(screen, (205, 135, 255), rect, 4, border_radius=8)
                else:
                    pygame.draw.rect(screen, base_col, rect, 3, border_radius=8)
                self.draw_text(skill.icon, 22, base_col, x + box_size // 2, y + 16)
                self.draw_text(f"Lv{skill.level}", 12, (220, 220, 240), x + box_size // 2, y + box_size - 22)
                cost_col = CYAN if can_use else RED
                self.draw_text(f"{skill.cost}", 12, cost_col, x + box_size // 2, y + box_size - 8)
                if skill.evolutions:
                    pygame.draw.circle(screen, GOLD, (x + box_size - 8, y + 8), 4)
                    if len(skill.evolutions) > 1:
                        pygame.draw.circle(screen, GOLD, (x + box_size - 18, y + 8), 4)
            self.draw_text(SLOT_KEY_NAMES[i], 15, GOLD, x + box_size // 2, y - 10)


    def draw_summon_bar(self):
        """召唤师模式的 U/I/O 槽位：空 / 捕捉中 / 已出战（可收回）/ 待命（可召唤）。"""
        box_size = 60
        gap = 10
        slots = 3
        total_w = slots * box_size + (slots - 1) * gap
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        y = 102 if self.boss is not None else 42
        for i in range(slots):
            x = start_x + i * (box_size + gap)
            rect = (x, y, box_size, box_size)
            template = self.captured[i]
            s = pygame.Surface((box_size, box_size), pygame.SRCALPHA)
            s.fill((14, 18, 30, 210))
            screen.blit(s, (x, y))
            if self.capture_slot == i:
                pygame.draw.rect(screen, (255, 200, 100), rect, 3, border_radius=8)
                self.draw_text("捕捉中", 14, (255, 200, 100),
                               x + box_size // 2, y + box_size // 2 + 5)
            elif template is None:
                pygame.draw.rect(screen, (90, 90, 110), rect, 2, border_radius=8)
                self.draw_text("空", 18, (110, 110, 130),
                               x + box_size // 2, y + box_size // 2 + 8)
            else:
                out = self.ally_out[i]
                ready = self.summon_cd[i] <= 0
                border = (110, 240, 220) if ready else (80, 115, 115)
                if out:
                    border = (255, 190, 110) if ready else (140, 110, 80)
                img = template["image"]
                scale = min((box_size - 12) / max(1, img.get_width()),
                            (box_size - 30) / max(1, img.get_height()))
                small = pygame.transform.smoothscale(img, (
                    max(1, int(img.get_width() * scale)),
                    max(1, int(img.get_height() * scale))))
                screen.blit(small, small.get_rect(center=(x + box_size // 2, y + 22)))
                pygame.draw.rect(screen, border, rect, 3, border_radius=8)
                if out:
                    # 出战状态额外画一条小血条
                    ally = self.summoned[i]
                    if ally is not None and ally.max_health > 0:
                        ratio = max(0.0, ally.health / ally.max_health)
                        bx = x + 7
                        bw = box_size - 14
                        pygame.draw.rect(screen, (20, 30, 34), (bx, y + box_size - 20, bw, 4))
                        pygame.draw.rect(screen, (120, 240, 220),
                                         (bx, y + box_size - 20, bw * ratio, 4))
                if not ready:
                    self.draw_text(f"{self.summon_cd[i] / FPS:.1f}s", 13, (200, 200, 220),
                                   x + box_size // 2, y + box_size - 9)
                else:
                    self.draw_text("收回" if out else "召唤", 13, border,
                                   x + box_size // 2, y + box_size - 9)
            self.draw_text(SLOT_KEY_NAMES[i], 15, GOLD, x + box_size // 2, y - 10)


    def draw_active_skill_timers(self):
        p = self.player
        timers = []
        if p.shield_active:
            remain = max(0, p.shield_end_time - frame_count()) / FPS
            timers.append(("护盾", remain, (120, 215, 255)))
        if p.rewind_active:
            remain = max(0, p.rewind_timer) / FPS
            timers.append(("回溯", remain, (105, 220, 235)))
        if p.pact_timer > 0:
            remain = max(0, p.pact_timer) / FPS
            timers.append(("契约领域", remain, (140, 235, 190)))
        if not timers:
            return
        y = (102 if self.boss is not None else 42) + 60 + 26
        total_w = sum(get_font(18).size(f"{name} {remain:.1f}s")[0] for name, remain, _ in timers)
        total_w += max(0, len(timers) - 1) * 24
        x = SCREEN_WIDTH // 2 - total_w // 2
        for name, remain, color in timers:
            text = f"{name} {remain:.1f}s"
            self.draw_text(text, 18, color, x, y, False)
            x += get_font(18).size(text)[0] + 24


    def game_over(self):
        savegame.clear()          # 这一局到此结束，不能再续了
        # 先落账：死亡归因、图鉴、战斗数据与纪录
        if self.lethal_source:
            self.codex_deaths[self.lethal_source] = \
                self.codex_deaths.get(self.lethal_source, 0) + 1
        highlights = self.stats.build_highlights(died=True)
        self.flush_codex()
        summary = self.run_summary(highlights)
        profile().record_last_run(summary)
        result = profile().record_run(self.mode, self.mode_name,
                                      self.current_depth, self.player.kills, self.frame)
        # 成绩先入账，再结算成就，否则「累计击杀 / 层数」这类会晚一局才解锁
        self.achievements_unlocked = [
            item["name"] for item in achievements.evaluate(profile(), summary)]

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 232))
        screen.blit(overlay, (0, 0))
        self.draw_text("游 戏 结 束", 58, (230, 80, 80), SCREEN_WIDTH // 2, 68)

        left = (46, 116, 330, 404)
        right = (396, 116, 358, 404)
        draw_panel(screen, left, (100, 100, 140), 190)
        draw_panel(screen, right, GOLD, 190)
        self._draw_run_summary(left, result)
        self._draw_battle_stats(right, highlights)
        self.draw_text("按 R 键重新开始　·　按 ESC 返回主菜单", 24, (200, 200, 220),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)
        present()
        waiting = True
        while waiting:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r: return True
                    elif event.key == pygame.K_ESCAPE: return False
        return False

    def _draw_run_summary(self, rect, result):
        """左栏：这一局走到哪、杀了多少、有没有破纪录。"""
        cx = rect[0] + rect[2] // 2
        self.draw_text("本 局", 26, GOLD, cx, rect[1] + 30)
        rows = [
            ("最深到达", f"{self.current_depth} 层"),
            ("本局击杀", f"{self.player.kills}"),
            ("精英击杀", f"{self.stats.elite_kills}"),
            ("领主击杀", f"{len(self.stats.boss_kills)}"),
            (f"{self.mode_name} 最好", f"{profile().mode_best(self.mode)} 层"),
        ]
        y = rect[1] + 78
        for label, value in rows:
            self.draw_text(label, 20, (170, 170, 190), rect[0] + 26, y, center=False)
            width = get_font(20).size(value)[0]
            self.draw_text(value, 20, WHITE,
                           rect[0] + rect[2] - 26 - width, y, center=False)
            y += 40
        if result["broke_overall"]:
            self.draw_text("新纪录！", 26, (255, 215, 90), cx, rect[1] + rect[3] - 52)
        elif result["broke_mode"]:
            self.draw_text("刷新本模式纪录！", 23, (140, 235, 190), cx, rect[1] + rect[3] - 52)

    def _draw_battle_stats(self, rect, highlights):
        """右栏：伤害构成、承伤来源与本局高光。"""
        cx = rect[0] + rect[2] // 2
        left = rect[0] + 24
        bar_w = rect[2] - 48
        self.draw_text("战 斗 数 据", 26, GOLD, cx, rect[1] + 30)

        y = rect[1] + 62
        total_dealt = self.stats.total_dealt()
        self.draw_text(f"总输出 {int(total_dealt)}", 18, CYAN, left, y, center=False)
        y += 22
        for name, value, ratio in self.stats.dealt_rows(3):
            self.draw_text(name, 17, (205, 205, 225), left + 8, y, center=False)
            self.draw_text(f"{int(value)}", 17, WHITE,
                           rect[0] + rect[2] - 24 - get_font(17).size(str(int(value)))[0],
                           y, center=False)
            pygame.draw.rect(screen, (38, 42, 58), (left, y + 19, bar_w, 5))
            pygame.draw.rect(screen, (140, 185, 255),
                             (left, y + 19, int(bar_w * ratio), 5))
            y += 32

        y += 6
        self.draw_text(f"总承伤 {int(self.stats.total_taken())}", 18, ORANGE, left, y, center=False)
        y += 22
        for name, value, _ratio in self.stats.taken_rows(3):
            self.draw_text(name, 17, (225, 200, 200), left + 8, y, center=False)
            width = get_font(17).size(str(int(value)))[0]
            self.draw_text(f"{int(value)}", 17, WHITE,
                           rect[0] + rect[2] - 24 - width, y, center=False)
            y += 24

        y += 6
        self.draw_text(
            f"最高单次 {int(self.stats.best_hit)}　·　无伤房间 {self.stats.clean_rooms}",
            17, (170, 170, 190), left, y, center=False)
        y += 28
        for line in highlights[:3]:
            self.draw_text(line, 17, (255, 215, 130), left, y, center=False)
            y += 22
        if self.achievements_unlocked:
            y += 6
            names = "、".join(self.achievements_unlocked[:2])
            more = f" 等 {len(self.achievements_unlocked)} 项" \
                if len(self.achievements_unlocked) > 2 else ""
            self.draw_text(f"解锁成就：{names}{more}", 17, (150, 235, 190),
                           left, y, center=False)

