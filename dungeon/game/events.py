"""事件房与房间流程。"""


# === IMPORTS ===
import math
import pygame
import random
import sys
from ..data.biomes import BIOME_NORMAL, BIOME_TOMB
from ..data.enemies import BIOME_ENEMY_POOL, ELITE_STATS, ENEMY_CONFIG
from ..data.events import CORE_BASE_HEALTH, CORE_DEFENSE_SECONDS, CORE_WAVE_INTERVAL, CURSE_ROOMS, CURSE_TABLE, MIRROR_SKILLS, MIRROR_SKILL_NAMES, ROULETTE_SECTORS
from ..data.modes import MODE_AFFIX_FRENZY
from ..data.skills import SLOT_KEY_NAMES
from ..entities.affix import AFFIX_TABLE, roll_affixes
from ..entities.enemies import EliteEnemy, Enemy
from ..entities.projectiles import WarningCircle
from ..entities.props import Platform
from ..entities.units import CoreCrystal, EventAltar, EventGoal, HunterGhost, MirrorDuelist
from ..settings import CYAN, ELITE_PURPLE, FPS, FRAGILE_PATH_SECONDS, GOLD, OUTLINE, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE, clock, get_font, screen
from ..timing import advance_frame, frame_count, ms
from ..utils import draw_panel, draw_pie_slice, present
# === /IMPORTS ===

class GameEventMixin:
    def _roll_enemy_affixes(self):
        """按模式决定这个敌人带几条词缀。"""
        if self.mode == MODE_AFFIX_FRENZY:
            # 至少 1 条，之后每多一条都要再过一次递减的判定：
            # 2条78% 3条43% 4条16% 5条4.4% 6条0.8%，越堆越难
            count = 1
            chance = 0.78
            while chance > 0.02 and count < len(AFFIX_TABLE):
                if random.random() >= chance:
                    break
                count += 1
                chance *= 0.7
            return roll_affixes(self.current_depth, count)
        if self.current_depth >= 3:
            chance = 0.10 + min(0.25, self.current_depth * 0.02)
            if random.random() < chance:
                return roll_affixes(self.current_depth, 1)
        return []


    def _attach_affixes(self, enemy, names=None):
        """给已经构造好的敌人补词缀（事件怪等）。"""
        if names is None:
            names = self._roll_enemy_affixes()
        for name in names:
            cls = AFFIX_TABLE.get(name)
            if not cls:
                continue
            enemy.affix_names.append(name)
            inst = cls(enemy)
            enemy.affix_instances.append(inst)
            inst.on_spawn(self)
        return names


    def _boost_affixes(self, enemy, extra_count):
        """词缀狂欢下给精英与巨型骷髅再堆几条词缀。"""
        if self.mode != MODE_AFFIX_FRENZY:
            return []
        extra = roll_affixes(self.current_depth, extra_count, exclude=enemy.affix_names)
        return self._attach_affixes(enemy, extra)


    def _elite_kind_pool(self):
        """精英种类候选。精英地狱里无视生物群系，全种类随机。"""
        if self.all_elite_mode:
            return list(ELITE_STATS.keys())
        pool = [k for k, v in ELITE_STATS.items() if v.get("scene") == self.scene_type]
        if not pool:
            pool = [k for k, v in ELITE_STATS.items() if v.get("scene") == BIOME_NORMAL]
        if not pool:
            pool = list(ELITE_STATS.keys())
        return pool


    def _setup_event_room(self):
        ground = Platform(0, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 30, self.scene_type)
        self.platforms.add(ground); self.all_sprites.add(ground)

        self.event_altar = EventAltar(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)
        self.all_sprites.add(self.event_altar)

        self.event_kind = random.choice([
            "sacrifice", "trap_chest", "wishing_well", "elite_challenge",
            "bomb_rain", "endless_hunt", "fragile_path", "elite_gauntlet",
            "mirror_duel", "affix_forge", "attribute_swap", "core_defense",
            "abyss_roulette",
        ])

        if self.event_kind == "sacrifice":
            self.event_title, self.event_choices = self._event_sacrifice()
        elif self.event_kind == "trap_chest":
            self.event_title, self.event_choices = self._event_trap_chest()
        elif self.event_kind == "wishing_well":
            self.event_title, self.event_choices = self._event_wishing_well()
        elif self.event_kind == "elite_challenge":
            self.event_title, self.event_choices = self._event_elite_challenge()
        elif self.event_kind == "bomb_rain":
            self.event_title, self.event_choices = self._event_bomb_rain()
        elif self.event_kind == "endless_hunt":
            self.event_title, self.event_choices = self._event_endless_hunt()
        elif self.event_kind == "fragile_path":
            self.event_title, self.event_choices = self._event_fragile_path()
        elif self.event_kind == "elite_gauntlet":
            self.event_title, self.event_choices = self._event_elite_gauntlet()
        elif self.event_kind == "mirror_duel":
            self.event_title, self.event_choices = self._event_mirror_duel()
        elif self.event_kind == "affix_forge":
            self.event_title, self.event_choices = self._event_affix_forge()
        elif self.event_kind == "attribute_swap":
            self.event_title, self.event_choices = self._event_attribute_swap()
        elif self.event_kind == "core_defense":
            self.event_title, self.event_choices = self._event_core_defense()
        elif self.event_kind == "abyss_roulette":
            self.event_title, self.event_choices = self._event_abyss_roulette()

        self.event_done = False
        self.event_running = False
        self.event_timer = 0
        self.event_data = {}
        self.pending_elite_reward = False
        self.pending_event_rewards = 0
        self.initial_enemy_count = 0


    def _event_sacrifice(self):
        return ("献祭祭坛", [
            {"name": "献祭生命", "desc": "最大生命-20，攻击力+8",
             "func": lambda: self._evt_sacrifice(20, 0, 0, 8, 0)},
            {"name": "献祭血肉", "desc": "最大生命-15，攻速+20%",
             "func": lambda: self._evt_sacrifice(15, 0.20, 0, 0, 0)},
            {"name": "献祭灵魂", "desc": "最大生命-10，暴击率+10%、暴伤+5",
             "func": lambda: self._evt_sacrifice(10, 0, 0.10, 0, 5)},
            {"name": "离开", "desc": "什么也不做",
             "func": lambda: "你离开了祭坛"},
        ])


    def _evt_sacrifice(self, hp_cost, atk_speed, crit_chance, atk_bonus, crit_dmg_bonus):
        p = self.player
        old_max = p.max_health
        p.max_health = max(30, p.max_health - hp_cost)
        p.health = min(p.health, p.max_health)
        parts = [f"最大生命-{old_max - p.max_health}"]
        if atk_speed:
            p.attack_speed_multiplier += atk_speed
            parts.append(f"攻速+{int(atk_speed * 100)}%")
        if crit_chance:
            p.crit_chance = min(0.6, p.crit_chance + crit_chance)
            parts.append(f"暴击率+{int(crit_chance * 100)}%")
        if atk_bonus:
            p.attack_bonus += atk_bonus
            parts.append(f"攻击力+{atk_bonus}")
        if crit_dmg_bonus:
            p.crit_damage_bonus += crit_dmg_bonus
            parts.append(f"暴击伤害加成+{crit_dmg_bonus}")
        return "献祭完成：" + "，".join(parts)


    def _event_trap_chest(self):
        return ("陷阱宝箱", [
            {"name": "打开宝箱", "desc": "获得2次强化+5晶体，但触发陷阱召唤敌人",
             "func": self._evt_trap_open},
            {"name": "检查陷阱", "desc": "消耗2晶体，安全打开获得1次强化",
             "func": self._evt_trap_safe},
            {"name": "离开", "desc": "什么也不做",
             "func": lambda: "你离开了宝箱"},
        ])


    def _evt_trap_open(self):
        self.player.crystals += 5
        budget = 2 + self.current_depth // 3
        count = self._spawn_enemies_from_budget(budget)
        self.pending_event_rewards += 2
        return f"开启宝箱：+5晶体，但召唤了{count}个敌人！请选择2次强化"


    def _evt_trap_safe(self):
        if self.player.crystals < 2:
            return "晶体不足，你放弃了宝箱"
        self.player.crystals -= 2
        self.pending_event_rewards += 1
        return "安全打开宝箱，请选择1次强化"


    def _spawn_enemies_from_budget(self, budget):
        count = 0
        GROUND_TOP = SCREEN_HEIGHT - 30
        while budget >= 4:
            budget -= 4
            kind = random.choice(self._elite_kind_pool())
            x = random.randint(80, SCREEN_WIDTH - 130)
            y = GROUND_TOP - 90
            elite = EliteEnemy(x, y, self.current_depth, self.scene_type, kind)
            self._boost_affixes(elite, 2)
            self.enemies.add(elite); self.all_sprites.add(elite)
            count += 1
        pool = BIOME_ENEMY_POOL.get(self.scene_type, BIOME_ENEMY_POOL[BIOME_NORMAL])
        for _ in range(budget):
            enemy_type = random.choice(pool)
            x = random.randint(80, SCREEN_WIDTH - 80)
            y = GROUND_TOP - 60
            enemy = Enemy(x, y, self.current_depth, enemy_type, self.scene_type,
                          affix_names=self._roll_enemy_affixes())
            self.enemies.add(enemy); self.all_sprites.add(enemy)
            count += 1
        self.initial_enemy_count = len(self.enemies)
        return count


    def _event_wishing_well(self):
        return ("许愿井", [
            {"name": "投入3晶体", "desc": "获得1次随机强化",
             "func": self._evt_well_3},
            {"name": "投入6晶体", "desc": "随机技能进化（无进化的技能）",
             "func": self._evt_well_6},
            {"name": "投入10晶体", "desc": "获得2次随机强化",
             "func": self._evt_well_10},
            {"name": "投入0晶体", "desc": "获得一个诅咒（作为补偿获得3晶体）",
             "func": self._evt_well_0},
            {"name": "离开", "desc": "什么都不做",
             "func": lambda: "你离开了许愿井"},
        ])


    def _evt_well_3(self):
        if self.player.crystals < 3: return "晶体不足，井水毫无反应"
        self.player.crystals -= 3
        self.pending_event_rewards += 1
        return "井水涌动，请选择1次强化"


    def _evt_well_6(self):
        if self.player.crystals < 6: return "晶体不足，井水毫无反应"
        candidates = [s for s in self.player.skills if s and s.available_evolutions()]
        if not candidates:
            return "没有可进化的技能，井水毫无反应"
        self.player.crystals -= 6
        skill = random.choice(candidates)
        evo = random.choice(skill.available_evolutions())
        skill.evolutions.append(evo["key"])
        return f"{skill.name} 获得进化·{evo['name']}！"


    def _evt_well_10(self):
        if self.player.crystals < 10: return "晶体不足，井水毫无反应"
        self.player.crystals -= 10
        self.pending_event_rewards += 2
        return "井水涌动，请选择2次强化"


    def _evt_well_0(self):
        curse = self._apply_random_curse()
        self.player.crystals += 3
        return f"诅咒缠身：{curse}（{CURSE_ROOMS}个房间后消退，补偿3晶体）"


    def _apply_random_curse(self):
        """施加一个限时诅咒，返回它的名字。"""
        p = self.player
        # 优先挑一个真的能生效的诅咒，避免出现"诅咒了但属性没变"
        usable = [c for c in CURSE_TABLE
                  if max(c["floor"], getattr(p, c["attr"]) + c["delta"])
                  != getattr(p, c["attr"])]
        curse = random.choice(usable or CURSE_TABLE)
        before = getattr(p, curse["attr"])
        after = max(curse["floor"], before + curse["delta"])
        setattr(p, curse["attr"], after)
        self.active_curses.append({
            "name": curse["name"], "desc": curse["desc"],
            "attr": curse["attr"], "applied": after - before,
            "rooms": CURSE_ROOMS,
        })
        self.player.health = min(self.player.health, self.player.max_health)
        return curse["name"]


    def _tick_curses(self):
        """换房间时推进诅咒倒计时，到期的原样还回去。"""
        still_active = []
        for curse in self.active_curses:
            curse["rooms"] -= 1
            if curse["rooms"] > 0:
                still_active.append(curse)
                continue
            p = self.player
            setattr(p, curse["attr"], getattr(p, curse["attr"]) - curse["applied"])
            self.show_message(f"诅咒消退：{curse['name']}", 1600)
        self.active_curses = still_active


    def _event_elite_challenge(self):
        return ("精英挑战", [
            {"name": "接受挑战", "desc": "召唤2个精英，击败后获得4次强化+8晶体",
             "func": self._evt_elite_accept},
            {"name": "拒绝", "desc": "失去3晶体",
             "func": self._evt_elite_refuse},
            {"name": "离开", "desc": "什么也不做",
             "func": lambda: "你选择不参与挑战"},
        ])


    def _evt_elite_accept(self):
        GROUND_TOP = SCREEN_HEIGHT - 30
        for _ in range(2):
            kind = random.choice(self._elite_kind_pool())
            x = random.randint(100, SCREEN_WIDTH - 130)
            y = GROUND_TOP - 90
            elite = EliteEnemy(x, y, self.current_depth, self.scene_type, kind)
            self.enemies.add(elite); self.all_sprites.add(elite)
        self.initial_enemy_count = len(self.enemies)
        self.pending_elite_reward = True
        return "精英已降临！击败它们获得4次强化+8晶体"


    def _evt_elite_refuse(self):
        self.player.crystals = max(0, self.player.crystals - 3)
        return "你退缩了，失去3晶体"


    def _event_bomb_rain(self):
        return ("坠落炸弹挑战", [
            {"name": "开始挑战", "desc": "撑过20秒轰炸，奖励2次强化+5晶体",
             "func": self._start_bomb_rain},
            {"name": "放弃", "desc": "什么也不做",
             "func": lambda: "你离开了"},
        ])


    def _start_bomb_rain(self):
        self.event_running = True
        self.event_timer = 0
        self.event_data['total'] = 20 * FPS
        return "炸弹风暴来袭，撑过20秒！"


    def _update_bomb_rain(self):
        self.event_timer += 1
        progress = self.event_timer / self.event_data['total']
        if progress < 0.5: interval = 28
        elif progress < 0.8: interval = 20
        else: interval = 14
        if self.event_timer % interval == 0:
            x = random.randint(80, SCREEN_WIDTH - 80)
            w = WarningCircle(x, SCREEN_HEIGHT - 40, delay=45, radius=45, spawn_type="bomb")
            self.warnings.add(w); self.all_sprites.add(w)
        if self.event_timer >= self.event_data['total']:
            self.pending_event_rewards += 2
            self.player.crystals += 5
            self.event_done = True
            self.event_running = False
            self.show_message("坠落炸弹挑战成功！+5晶体 +2次强化", 2500)


    def _event_endless_hunt(self):
        return ("无尽追猎", [
            {"name": "开始挑战", "desc": "撑过20秒幽灵追猎，奖励3次强化",
             "func": self._start_endless_hunt},
            {"name": "放弃", "desc": "什么也不做",
             "func": lambda: "你离开了"},
        ])


    def _start_endless_hunt(self):
        self.event_running = True
        self.event_timer = 0
        self.event_data['total'] = 20 * FPS
        from_x = random.choice([-60, SCREEN_WIDTH + 60])
        ghost = HunterGhost(from_x, SCREEN_HEIGHT // 2)
        self.hunter_ghost = ghost
        self.all_sprites.add(ghost)
        return "幽灵来了！撑过20秒！"


    def _update_endless_hunt(self):
        self.event_timer += 1
        ghost = self.hunter_ghost
        if ghost is not None and ghost.alive():
            ghost.speed = 2.0 + self.event_timer / FPS * 0.30
            ghost.update(self.player)
            if pygame.sprite.collide_rect(ghost, self.player):
                self.player.take_damage(15, source='hunter')
        if self.event_timer >= self.event_data['total']:
            if ghost is not None:
                ghost.kill()
            self.hunter_ghost = None
            self.pending_event_rewards += 3
            self.event_done = True
            self.event_running = False
            self.show_message("成功摆脱幽灵！+3次强化", 2500)


    def _event_fragile_path(self):
        return ("脆弱之路", [
            {"name": "开始挑战", "desc": f"{FRAGILE_PATH_SECONDS}秒内踩脆弱平台到达顶部水晶，成功得20晶体",
             "func": self._start_fragile_path},
            {"name": "放弃", "desc": "什么也不做",
             "func": lambda: "你离开了"},
        ])


    def _start_fragile_path(self):
        self.event_running = True
        self.event_timer = 0
        self.event_data['goal_reached'] = False
        GROUND_TOP = SCREEN_HEIGHT - 30
        y_positions = [GROUND_TOP - 100 - i * 80 for i in range(6)]
        for i, y in enumerate(y_positions):
            count = 1 if i % 2 == 0 else 2
            placed = 0
            for _ in range(30):
                if placed >= count: break
                w = random.randint(90, 130)
                x = random.randint(60, SCREEN_WIDTH - w - 60)
                test_rect = pygame.Rect(x, y, w, 20)
                conflict = False
                for p in self.platforms:
                    if test_rect.colliderect(p.rect.inflate(30, 30)):
                        conflict = True; break
                if conflict: continue
                p = Platform(x, y, w, 20, self.scene_type, fragile=True)
                self.platforms.add(p); self.all_sprites.add(p)
                placed += 1
        goal_x = random.randint(200, SCREEN_WIDTH - 200)
        self.event_goal = EventGoal(goal_x, 70)
        self.event_goals.add(self.event_goal)
        self.all_sprites.add(self.event_goal)
        return "到达顶部水晶！失败无奖励"


    def _update_fragile_path(self):
        self.event_timer += 1
        if self.event_goal is not None and self.event_goal.alive():
            if pygame.sprite.collide_rect(self.player, self.event_goal):
                self.event_data['goal_reached'] = True
                self._end_fragile_path(success=True)
                return
        if self.event_timer >= FRAGILE_PATH_SECONDS * FPS:
            self._end_fragile_path(success=False)


    def _end_fragile_path(self, success):
        self.event_done = True
        self.event_running = False
        if self.event_goal is not None:
            self.event_goal.kill()
            self.event_goal = None
        if success:
            self.player.crystals += 20
            self.show_message("到达顶部！+20晶体", 2500)
        else:
            self.show_message("挑战失败，无奖励", 2000)


    def _event_elite_gauntlet(self):
        return ("精英车轮战", [
            {"name": "接受挑战", "desc": "连续击败3个精英，奖励5次强化+10晶体",
             "func": self._start_elite_gauntlet},
            {"name": "放弃", "desc": "什么也不做",
             "func": lambda: "你离开了"},
        ])


    def _start_elite_gauntlet(self):
        self.event_running = True
        self.event_timer = 0
        self.event_data['gauntlet_idx'] = 0
        self.event_data['gauntlet_total'] = 3
        return "3个精英依次降临，击败它们！"


    def _update_elite_gauntlet(self):
        elites_alive = [e for e in self.enemies if getattr(e, 'is_elite', False)]
        if elites_alive:
            return
        idx = self.event_data.get('gauntlet_idx', 0)
        total = self.event_data.get('gauntlet_total', 3)
        if idx >= total:
            self.pending_event_rewards += 5
            self.player.crystals += 10
            self.event_done = True
            self.event_running = False
            self.show_message("车轮战完成！+10晶体 +5次强化", 2500)
            return
        self.event_data['gauntlet_idx'] = idx + 1
        kind = random.choice(self._elite_kind_pool())
        x = random.randint(150, SCREEN_WIDTH - 200)
        elite = EliteEnemy(x, SCREEN_HEIGHT - 120, self.current_depth + idx * 3,
                           self.scene_type, kind)
        self.enemies.add(elite); self.all_sprites.add(elite)
        self.show_message(f"车轮战 {idx+1}/{total}：{elite.elite_name}", 1800)


    def _event_mirror_duel(self):
        return ("镜像对决", [
            {"name": "开始对决", "desc": "复制自己（含3个随机技能），胜利后 晶体×20 或 为任意技能叠加进化",
             "func": self._start_mirror_duel},
            {"name": "放弃", "desc": "什么也不做",
             "func": lambda: "你离开了"},
        ])


    def _start_mirror_duel(self):
        self.event_running = True
        self.event_timer = 0
        skills = random.sample(MIRROR_SKILLS, 3)
        self.event_data['mirror_skills'] = skills
        GROUND_TOP = SCREEN_HEIGHT - 30
        mirror = MirrorDuelist(SCREEN_WIDTH // 2, GROUND_TOP,
                               self.current_depth, self.scene_type, skills)
        self.enemies.add(mirror); self.all_sprites.add(mirror)
        self.initial_enemy_count = 1
        skill_names = " / ".join(MIRROR_SKILL_NAMES.get(k, k) for k in skills)
        return f"镜像降临！技能：{skill_names}"


    def _update_mirror_duel(self):
        if self.event_done:
            return


    def _grant_mirror_duel_reward(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 240))
        screen.blit(overlay, (0, 0))
        self.draw_text("镜像对决 · 胜利", 48, GOLD, SCREEN_WIDTH // 2, 90)
        self.draw_text("选择一项奖励", 28, (200, 200, 220), SCREEN_WIDTH // 2, 145)

        has_evo = any(
            s and s.unused_evolutions()
            for s in self.player.skills[:self.player.skill_slots]
        )

        card_w = 280; card_h = 160; gap = 30
        total_w = 2 * card_w + gap
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        y = 230

        rect1 = (start_x, y, card_w, card_h)
        draw_panel(screen, rect1, GOLD, 200)
        self.draw_text("[1]", 26, GOLD, start_x + 40, y + 24)
        self.draw_text("晶体 ×20", 26, CYAN, start_x + card_w // 2, y + 60)
        self.draw_text("立即获得 20 个晶体", 16, (200, 210, 230),
                       start_x + card_w // 2, y + 100)

        rect2 = (start_x + card_w + gap, y, card_w, card_h)
        draw_panel(screen, rect2, GOLD, 200)
        self.draw_text("[2]", 26, GOLD, start_x + card_w + gap + 40, y + 24)
        self.draw_text("进化选择", 26, ELITE_PURPLE,
                       start_x + card_w + gap + card_w // 2, y + 60)
        if has_evo:
            self.draw_text("为一个技能选择进化方向", 15, (200, 210, 230),
                           start_x + card_w + gap + card_w // 2, y + 95)
            self.draw_text("（已有进化的技能也可叠加）", 14, (180, 180, 200),
                           start_x + card_w + gap + card_w // 2, y + 115)
        else:
            self.draw_text("（当前没有可添加进化的技能）", 15, (150, 150, 170),
                           start_x + card_w + gap + card_w // 2, y + 100)
        self.draw_text("按 1 或 2 选择", 20, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)
        present()

        chosen = None
        while chosen is None:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        chosen = 1
                    elif event.key == pygame.K_2:
                        if not has_evo:
                            self.show_message("没有可添加进化的技能！", 1500)
                        else:
                            chosen = 2

        if chosen == 1:
            self.player.crystals += 20
            self.show_message("获得 20 晶体！", 2000)
        else:
            self._show_mirror_evolution_pick()


    def _show_mirror_evolution_pick(self):
        """列出所有可添加进化的技能，并让玩家选择。"""
        p = self.player
        candidates = [(i, s) for i, s in enumerate(p.skills[:p.skill_slots])
                      if s and s.unused_evolutions()]
        if not candidates:
            self.show_message("没有可添加进化的技能！", 1500)
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 240))
        screen.blit(overlay, (0, 0))
        self.draw_text("选择要添加进化的技能", 42, GOLD, SCREEN_WIDTH // 2, 80)
        self.draw_text("（已有进化的技能可叠加第二个方向）", 20, (200, 210, 230),
                       SCREEN_WIDTH // 2, 125)
        card_w = 200; card_h = 120
        gap = 20
        total_w = len(candidates) * card_w + (len(candidates) - 1) * gap
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        y = 180
        for i, (idx, skill) in enumerate(candidates):
            x = start_x + i * (card_w + gap)
            rect = (x, y, card_w, card_h)
            draw_panel(screen, rect, GOLD, 200)
            self.draw_text(f"[{i+1}] {SLOT_KEY_NAMES[idx]}", 22, GOLD,
                           x + 40, y + 24)
            self.draw_text(skill.name, 24, WHITE, x + card_w // 2, y + 56)
            self.draw_text(f"Lv.{skill.level}", 16, (200, 200, 220),
                           x + card_w // 2, y + 82)
            self.draw_text(f"进化：{skill.evolution_name()}", 14, CYAN,
                           x + card_w // 2, y + 104)
        self.draw_text("按数字键选择，ESC 取消", 20, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)
        present()

        chosen_idx = None
        while chosen_idx is None:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if pygame.K_1 <= event.key <= pygame.K_9:
                        ii = event.key - pygame.K_1
                        if ii < len(candidates):
                            chosen_idx = ii

        idx, skill = candidates[chosen_idx]
        avail = skill.unused_evolutions()
        if not avail:
            return
        # 让玩家选择进化方向
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 240))
        screen.blit(overlay, (0, 0))
        self.draw_text(f"为 {skill.name} 选择进化方向", 42, GOLD, SCREEN_WIDTH // 2, 100)
        card_w = 280; card_h = 160; gap = 30
        total_w = len(avail) * card_w + (len(avail) - 1) * gap
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        y = 230
        for i, evo in enumerate(avail):
            x = start_x + i * (card_w + gap)
            rect = (x, y, card_w, card_h)
            draw_panel(screen, rect, ELITE_PURPLE, 200)
            self.draw_text(f"[{i+1}] {evo['name']}", 26, ELITE_PURPLE,
                           x + card_w // 2, y + 40)
            desc = evo["desc"]
            lines = []
            while len(desc) > 14:
                lines.append(desc[:14]); desc = desc[14:]
            if desc: lines.append(desc)
            for li, line in enumerate(lines[:4]):
                self.draw_text(line, 16, (210, 210, 230),
                               x + card_w // 2, y + 85 + li * 20)
        self.draw_text("按数字键选择", 20, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)
        present()

        evo_chosen = None
        while evo_chosen is None:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if pygame.K_1 <= event.key <= pygame.K_9:
                        ii = event.key - pygame.K_1
                        if ii < len(avail):
                            evo_chosen = ii
        evo = avail[evo_chosen]
        skill.evolutions.append(evo["key"])
        self.show_message(f"{skill.name} 获得进化·{evo['name']}！", 2200)


    def _event_affix_forge(self):
        keys = random.sample(list(AFFIX_TABLE.keys()), 3)
        choices = []
        for key in keys:
            choices.append({
                "name": f"注入·{AFFIX_TABLE[key].name}",
                "desc": f"下个房间所有敌人带上「{AFFIX_TABLE[key].name}」，换1次强化+8晶体",
                "func": (lambda k=key: self._evt_forge_pick(k)),
            })
        choices.append({"name": "什么都不做", "desc": "不碰熔炉",
                        "func": lambda: "你离开了熔炉"})
        return ("词缀熔炉", choices)


    def _evt_forge_pick(self, key):
        self.pending_room_affixes.append(key)
        self.pending_event_rewards += 1
        self.player.crystals += 8
        return f"熔炉已注入「{AFFIX_TABLE[key].name}」，下个房间的敌人会带上它"


    def _event_attribute_swap(self):
        return ("属性交易所", [
            {"name": "生命 ↔ 能量", "desc": "最大生命与能量上限互换",
             "func": self._evt_swap_hp_energy},
            {"name": "移速 ↔ 攻速", "desc": "移动速度与攻击速度倍率互换",
             "func": self._evt_swap_speed},
            {"name": "暴击 ↔ 噬血", "desc": "暴击率与噬血触发概率互换",
             "func": self._evt_swap_crit_lifesteal},
            {"name": "什么都不做", "desc": "保留现状",
             "func": lambda: "你离开了交易所"},
        ])


    def _evt_swap_hp_energy(self):
        p = self.player
        new_health = int(p.max_energy)
        new_energy = float(p.max_health)
        p.max_health, p.max_energy = new_health, new_energy
        p.health = min(p.health, p.max_health)
        p.energy = min(p.energy, p.max_energy)
        return f"最大生命与能量上限互换：{int(p.max_health)} / {int(p.max_energy)}"


    def _evt_swap_speed(self):
        p = self.player
        p.speed_multiplier, p.attack_speed_multiplier = (
            p.attack_speed_multiplier, p.speed_multiplier)
        return (f"移动速度 ↔ 攻击速度：{p.speed_multiplier:.2f} / "
                f"{p.attack_speed_multiplier:.2f}")


    def _evt_swap_crit_lifesteal(self):
        p = self.player
        p.crit_chance, p.lifesteal_chance = p.lifesteal_chance, p.crit_chance
        return (f"暴击率 ↔ 噬血概率：{int(p.crit_chance * 100)}% / "
                f"{int(p.lifesteal_chance * 100)}%")


    def _event_core_defense(self):
        hp = CORE_BASE_HEALTH + self.current_depth * 12
        return ("护核防守", [
            {"name": "开始防守",
             "desc": f"守住左侧核心 {CORE_DEFENSE_SECONDS} 秒；敌人从右侧来袭且只攻击核心",
             "func": self._start_core_defense},
            {"name": "什么都不做", "desc": "放弃防守",
             "func": lambda: "你放弃了防守"},
        ])


    def _start_core_defense(self):
        self.event_running = True
        self.event_timer = 0
        self.event_data['total'] = CORE_DEFENSE_SECONDS * FPS
        self.event_data['wave_cd'] = 45
        self.event_data['wave_idx'] = 0
        x = 90
        self.core = CoreCrystal(x, SCREEN_HEIGHT - 30, CORE_BASE_HEALTH + self.current_depth * 12)
        self.all_sprites.add(self.core)
        return "敌人从右侧涌来，守住核心！"


    def _spawn_defense_wave(self):
        self.event_data['wave_idx'] = self.event_data.get('wave_idx', 0) + 1
        count = min(5, 1 + self.event_data['wave_idx'])
        pool = [i for i, cfg in ENEMY_CONFIG.items()
                if not cfg.get("flying", False) and i not in (11, 12)]
        for _ in range(count):
            etype = random.choice(pool)
            x = SCREEN_WIDTH - random.randint(40, 130)
            enemy = Enemy(x, SCREEN_HEIGHT - 120, self.current_depth, etype,
                          self.scene_type, affix_names=self._roll_enemy_affixes())
            enemy.core_target = self.core
            self.enemies.add(enemy); self.all_sprites.add(enemy)
        self.initial_enemy_count = len(self.enemies)
        self.show_message(f"第 {self.event_data['wave_idx']} 波来袭！", 1200)


    def _update_core_defense(self):
        self.event_timer += 1
        core = self.core
        if core is None or core.health <= 0:
            self._end_core_defense(False); return
        core.update()
        for enemy in list(self.enemies):
            if getattr(enemy, 'health', 0) <= 0: continue
            if pygame.sprite.collide_rect(enemy, core):
                dmg = (2.5 if getattr(enemy, 'is_elite', False) else 1.4) \
                    * (1 + self.current_depth * 0.06)
                if core.take_damage(dmg):
                    self.add_floating_text(core.rect.centerx, core.rect.top - 4,
                                           f"-{int(dmg)}", (255, 120, 140), 16)
        self.event_data['wave_cd'] -= 1
        if (self.event_data['wave_cd'] <= 0
                and self.event_timer < self.event_data['total'] - 150):
            self._spawn_defense_wave()
            self.event_data['wave_cd'] = CORE_WAVE_INTERVAL
        if self.event_timer >= self.event_data['total']:
            self._end_core_defense(True)


    def _end_core_defense(self, success):
        self.event_running = False
        self.event_done = True
        if success:
            self.pending_event_rewards += 3
            self.player.crystals += 12
            self.show_message("核心守住了！+3次强化 +12晶体", 2500)
        else:
            self.pending_event_rewards += 1
            self.show_message("核心被击碎！只剩保底奖励", 2500)
        if self.core is not None:
            self.core.kill();
            self.core = None
        # 清除所有剩余敌人，防止它们卡住导致屏障无法开启
        for enemy in list(self.enemies):
            enemy.kill()
        self.enemies.empty()
        self.initial_enemy_count = 0
        self.update_barriers()


    def _event_abyss_roulette(self):
        return ("深渊轮盘", [
            {"name": "献上生命", "desc": "消耗当前生命的25%转动轮盘，指哪得哪",
             "func": self._evt_roulette_hp},
            {"name": "献上晶体", "desc": "消耗15晶体转动轮盘，指哪得哪",
             "func": self._evt_roulette_crystal},
            {"name": "什么都不做", "desc": "不冒这个险",
             "func": lambda: "你离开了轮盘"},
        ])


    def _evt_roulette_hp(self):
        cost = max(20, int(self.player.health * 0.25))
        if self.player.health - cost < 1:
            return "生命不足，轮盘纹丝不动"
        self.player.health -= cost
        return self._run_roulette(f"押上 {cost} 点生命")


    def _evt_roulette_crystal(self):
        if self.player.crystals < 15:
            return "晶体不足，轮盘纹丝不动"
        self.player.crystals -= 15
        return self._run_roulette("押上 15 晶体")


    def _draw_roulette(self, pointer_deg, bet_desc):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 245))
        screen.blit(overlay, (0, 0))
        self.draw_text("深 渊 轮 盘", 46, GOLD, SCREEN_WIDTH // 2, 54)
        self.draw_text(bet_desc, 22, (235, 205, 140), SCREEN_WIDTH // 2, 96)
        cx, cy, r = SCREEN_WIDTH // 2, 336, 168
        seg = 360.0 / len(ROULETTE_SECTORS)
        for i, sector in enumerate(ROULETTE_SECTORS):
            a0 = i * seg
            draw_pie_slice(screen, sector["color"], (cx, cy), r, a0, a0 + seg)
            mid = math.radians(a0 + seg / 2)
            lx = cx + math.cos(mid) * r * 0.62
            ly = cy + math.sin(mid) * r * 0.62
            self.draw_text(sector["label"], 17, (22, 16, 30), lx, ly)
        pygame.draw.circle(screen, (30, 26, 44), (cx, cy), 26)
        pygame.draw.circle(screen, GOLD, (cx, cy), 26, 3)
        ang = math.radians(pointer_deg)
        tip = (cx + math.cos(ang) * (r - 4), cy + math.sin(ang) * (r - 4))
        pygame.draw.line(screen, (255, 245, 210), (cx, cy), tip, 4)
        pygame.draw.circle(screen, (255, 240, 180), (int(tip[0]), int(tip[1])), 7)
        pygame.draw.circle(screen, OUTLINE, (int(tip[0]), int(tip[1])), 7, 2)
        self.draw_text("指针停在哪一格就结算哪一格", 18, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)


    def _run_roulette(self, bet_desc):
        n = len(ROULETTE_SECTORS)
        seg = 360.0 / n
        result = random.randrange(n)
        final_offset = (result * seg + seg / 2 + 90) % 360
        total_spin = 360 * random.randint(4, 6) + final_offset
        duration = ms(1400)
        start = frame_count()
        while True:
            elapsed = frame_count() - start
            t = min(1.0, elapsed / duration)
            pointer = -90 + total_spin * (1 - (1 - t) ** 3)
            self._draw_roulette(pointer, bet_desc)
            present()
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
            if t >= 1.0 and elapsed > duration + ms(200):
                break
        return self._apply_roulette(result)


    def _apply_roulette(self, idx):
        sector = ROULETTE_SECTORS[idx]
        kind = sector["kind"]
        if kind == "blank":
            return "指针停在「空白」……什么都没有"
        if kind == "curse":
            name = self._apply_random_curse()
            return f"指针停在「诅咒」！获得诅咒：{name}（{CURSE_ROOMS}个房间后消退）"
        if kind == "crystals":
            self.player.crystals += sector["value"]
        elif kind == "rewards":
            self.pending_event_rewards += sector["value"]
        elif kind == "heal":
            self.player.health = self.player.max_health
        elif kind == "bombs":
            self.player.bombs += sector["value"]
            self.player.energy = self.player.max_energy
        return f"指针停在「{sector['label']}」！"


    def _update_event(self):
        if not self.event_running:
            return
        k = self.event_kind
        if k == "bomb_rain":
            self._update_bomb_rain()
        elif k == "endless_hunt":
            self._update_endless_hunt()
        elif k == "fragile_path":
            self._update_fragile_path()
        elif k == "elite_gauntlet":
            self._update_elite_gauntlet()
        elif k == "mirror_duel":
            self._update_mirror_duel()
        elif k == "core_defense":
            self._update_core_defense()


    def _spawn_tomb_unit(self, source, enemy_type):
        """在尸体位置拉起一只墓穴单位（11 骷髅 / 12 幽灵）。"""
        if len(self.enemies) >= self.enemy_cap:
            return None
        spawn_x = max(30, min(source.rect.centerx, SCREEN_WIDTH - 30))
        unit = Enemy(spawn_x, source.rect.bottom - 52, self.current_depth,
                     enemy_type, BIOME_TOMB)
        unit.rect.bottom = source.rect.bottom
        self.enemies.add(unit); self.all_sprites.add(unit)
        return unit


    def _undead_tide_death(self, enemy, is_elite, is_mirror_duelist):
        """亡灵潮的核心链条：非骷髅非幽灵 -> 骷髅 -> 幽灵 -> 终止。"""
        if is_mirror_duelist:
            return
        if getattr(enemy, 'is_summoned', False) and not getattr(enemy, 'is_undead', False):
            return
        etype = getattr(enemy, 'enemy_type', -1)
        self.death_essence += 1
        if is_elite:
            self._spawn_giant_skeleton(enemy.rect.centerx)
        elif etype == 11:
            self._spawn_tomb_unit(enemy, 12)
        elif getattr(enemy, 'is_undead', False):
            self._spawn_tomb_unit(enemy, 12)
        elif etype != 12:
            self._spawn_tomb_unit(enemy, 11)
        while self.death_essence >= 10:
            self.death_essence -= 10
            self._spawn_giant_skeleton()


    def _spawn_giant_skeleton(self, x=None):
        if len(self.enemies) >= self.enemy_cap:
            return
        if x is None:
            x = SCREEN_WIDTH // 2
        x = max(120, min(x, SCREEN_WIDTH - 120))
        giant = Enemy(x, SCREEN_HEIGHT - 30, self.current_depth, 11, BIOME_TOMB)
        new_w = int(giant.image.get_width() * 2.2)
        new_h = int(giant.image.get_height() * 2.2)
        giant.image = pygame.transform.scale(giant.image, (new_w, new_h))
        giant.rect = giant.image.get_rect(midbottom=(x, SCREEN_HEIGHT - 30))
        giant.base_health = int(giant.base_health * 5)
        giant.health = giant.base_health
        giant.max_health = giant.base_health
        giant.base_speed *= 0.7
        giant.is_giant = True
        giant.is_elite = True
        giant.elite_name = "巨型骷髅"
        affix_count = min(3, 1 + self.current_depth // 6)
        giant.affix_names = []
        giant.affix_instances = []
        self._attach_affixes(giant, roll_affixes(self.current_depth, affix_count))
        self._boost_affixes(giant, 2)
        self.enemies.add(giant)
        self.all_sprites.add(giant)
        self.initial_enemy_count += 1
        if giant.affix_names:
            affix_str = "·".join(
                AFFIX_TABLE[n].name for n in giant.affix_names if n in AFFIX_TABLE
            )
            self.show_message(f"死亡气息爆发！巨型骷髅降临！【{affix_str}】", 2500)
        else:
            self.show_message("死亡气息爆发！巨型骷髅降临！", 2500)


    def _spawn_elite(self, placed_rects, safe_zones, GROUND_TOP):
        kind = random.choice(self._elite_kind_pool())
        for _ in range(30):
            ex = random.randint(120, SCREEN_WIDTH - 150)
            ey = GROUND_TOP - 90
            test_rect = pygame.Rect(ex, ey, 50, 70)
            if test_rect.colliderect(safe_zones[0]): continue
            if any(test_rect.colliderect(r.inflate(10, 10)) for r in placed_rects): continue
            elite = EliteEnemy(ex, ey, self.current_depth, self.scene_type, kind)
            self._boost_affixes(elite, 2)
            self.enemies.add(elite); self.all_sprites.add(elite)
            self.elite_banner_name = elite.elite_name
            self.elite_banner_timer = 180
            self.show_message(f"精英出现：{elite.elite_name}！", 2200)
            return


    def show_event_selection(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 240))
        screen.blit(overlay, (0, 0))
        self.draw_text(self.event_title, 48, GOLD, SCREEN_WIDTH // 2, 90)
        self.draw_text("做出你的选择", 26, (200, 200, 220), SCREEN_WIDTH // 2, 145)

        n = len(self.event_choices)
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        gap_x = 16
        gap_y = 14
        card_w = min(230, (SCREEN_WIDTH - 80 - (cols - 1) * gap_x) // cols)
        card_h = 170 if rows > 1 else 185
        start_y = 170 if rows > 1 else 220
        name_font = get_font(20)
        desc_font = get_font(14)

        def wrap_text(text, font, max_width):
            lines = []
            current = ""
            for ch in text:
                trial = current + ch
                if not current or font.size(trial)[0] <= max_width:
                    current = trial
                else:
                    lines.append(current)
                    current = ch
            if current:
                lines.append(current)
            return lines

        for i, choice in enumerate(self.event_choices):
            row = i // cols
            col = i % cols
            row_count = min(cols, n - row * cols)
            row_total_w = row_count * card_w + (row_count - 1) * gap_x
            start_x = SCREEN_WIDTH // 2 - row_total_w // 2
            x = start_x + col * (card_w + gap_x)
            y = start_y + row * (card_h + gap_y)
            rect = (x, y, card_w, card_h)
            draw_panel(screen, rect, GOLD, 200)
            self.draw_text(f"[{i+1}]", 24, GOLD, x + 30, y + 22)
            name_lines = wrap_text(choice["name"], name_font, card_w - 28)
            name_y = y + 48
            for li, line in enumerate(name_lines):
                self.draw_text(line, 20, WHITE, x + card_w // 2, name_y + li * 21)
            desc_lines = wrap_text(choice["desc"], desc_font, card_w - 28)
            desc_y = name_y + len(name_lines) * 21 + 8
            max_desc_lines = 4 if len(name_lines) == 1 else 3
            for li, line in enumerate(desc_lines[:max_desc_lines]):
                self.draw_text(line, 15, (200, 210, 230),
                               x + card_w // 2, desc_y + li * 17)
        self.draw_text(f"按 1-{n} 选择，ESC 返回", 20, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)
        present()
        while True:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if pygame.K_1 <= event.key <= pygame.K_9:
                        idx = event.key - pygame.K_1
                        if idx < len(self.event_choices):
                            msg = self.event_choices[idx]["func"]()
                            self.show_enhancement_message(msg or "")
                            if not self.event_running:
                                self.event_done = True
                                self.update_barriers()
                            return


    def _show_event_enhancement_pick(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("事件奖励强化", 52, GOLD, SCREEN_WIDTH // 2, 100)
        self.draw_text("选择一项强化", 30, (200, 200, 220), SCREEN_WIDTH // 2, 155)

        available = self._get_available_enhancements()
        available = [e for e in available if "学习新技能" not in e["name"]]
        if not available:
            return

        selected = []
        for _ in range(min(3, len(available))):
            total_weight = sum(e['weight'] for e in available)
            r = random.uniform(0, total_weight)
            upto = 0
            for e in available:
                upto += e['weight']
                if upto >= r:
                    selected.append(e)
                    available.remove(e)
                    break

        card_w = 220
        card_h = 100
        start_x = SCREEN_WIDTH // 2 - (len(selected) * card_w + (len(selected) - 1) * 20) // 2
        for i, enh in enumerate(selected):
            x = start_x + i * (card_w + 20)
            y = 220
            rect = (x, y, card_w, card_h)
            draw_panel(screen, rect, GOLD, 200)
            self.draw_text(f"[{i + 1}]", 22, GOLD, x + 30, y + 22)
            name = enh['name']
            if len(name) > 12:
                self.draw_text(name[:12], 20, WHITE, x + card_w // 2, y + 50)
                self.draw_text(name[12:], 20, WHITE, x + card_w // 2, y + 76)
            else:
                self.draw_text(name, 22, WHITE, x + card_w // 2, y + 60)

        self.draw_text("按 1-3 选择", 20, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)
        present()

        chosen = None
        while chosen is None:
            advance_frame()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1 and len(selected) >= 1:
                        chosen = selected[0]
                    elif event.key == pygame.K_2 and len(selected) >= 2:
                        chosen = selected[1]
                    elif event.key == pygame.K_3 and len(selected) >= 3:
                        chosen = selected[2]

        try:
            chosen["func"]()
        except Exception:
            pass

