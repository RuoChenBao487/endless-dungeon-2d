"""商店：生成商品、绘制与购买。"""


# === IMPORTS ===
import pygame
import random
from ..data.modes import MODE_SUMMONER
from ..data.skills import ALLY_AFFIX_POOL, ALLY_BAD_AFFIXES, SKILL_BLACK_HOLE, SKILL_DASH, SKILL_FIREBALL, SKILL_ICE_NOVA, SKILL_METEOR, SKILL_PACT, SKILL_SHIELD, SKILL_SOUL_CHAIN, SKILL_TIME_REWIND, SLOT_KEY_NAMES, skill_black_hole_damage, skill_black_hole_duration, skill_dash_damage, skill_dash_stun, skill_fireball_bonus, skill_ice_nova_freeze, skill_ice_nova_slow, skill_meteor_bonus, skill_meteor_drain, skill_meteor_scorch_duration, skill_pact_duration, skill_shield_duration, skill_soul_chain_targets, skill_soul_chain_temp_health, skill_time_rewind_duration
from ..entities.affix import AFFIX_TABLE
from ..entities.enemies import AllyUnit
from ..settings import CYAN, DARK_RED, FPS, GOLD, RED, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE, screen
from ..utils import draw_back_button
# === /IMPORTS ===

class GameShopMixin:
    def open_shop(self):
        self.shop_page = 0
        self._gen_shop_items()
        self.paused = True
        self.show_shop = True


    def _gen_shop_items(self):
        self.shop_items = []
        if self.shop_page == 0:
            available = self._get_available_enhancements()
            if not available: return
            n = min(5, len(available))
            chosen = random.sample(available, n)
            for e in chosen:
                price = random.randint(3, 8)
                self.shop_items.append({
                    "type": "enhance", "enhancement": e, "price": price,
                    "sold": False, "name": e["name"], "desc": ""
                })
        else:
            if self.mode == MODE_SUMMONER:
                self._gen_ally_shop_items()
                return
            p = self.player
            for slot_i in range(p.skill_slots):
                skill = p.skills[slot_i]
                if skill is None: continue
                price = 3 + skill.level * 2
                self.shop_items.append({
                    "type": "skill_upgrade", "slot": slot_i, "price": price,
                    "sold": False,
                    "name": f"[{SLOT_KEY_NAMES[slot_i]}] {skill.name} 升级  Lv.{skill.level}→Lv.{skill.level + 1}",
                    "desc": self._skill_upgrade_desc(skill),
                })
                # 只有没有进化方向的技能才会显示进化选项（每个技能仅能选一个）
                for evo in skill.available_evolutions():
                    self.shop_items.append({
                        "type": "skill_evolve", "slot": slot_i, "price": 12,
                        "sold": False,
                        "name": f"[{SLOT_KEY_NAMES[slot_i]}] {skill.name} 进化·{evo['name']}",
                        "desc": evo["desc"] + "（只能选一个方向）",
                        "evolution": evo,
                    })
                if len(self.shop_items) >= 9: break


    @staticmethod
    def _preview_ally_stats(tpl, hp_mult=None, atk_bonus=None):
        probe = dict(tpl)
        if hp_mult is not None: probe["hp_mult"] = hp_mult
        if atk_bonus is not None: probe["atk_bonus"] = atk_bonus
        hp = AllyUnit._health_of(probe)
        return hp, AllyUnit._attack_of(probe, hp)


    def _ally_affix_text(self, tpl):
        names = [AFFIX_TABLE[n].name for n in (tpl.get("affix_names") or [])
                 if n in AFFIX_TABLE and n not in ALLY_BAD_AFFIXES]
        if len(names) > 4:
            names = names[:4] + [f"+{len(names) - 4}"]
        return " / ".join(names) if names else "无"


    def _gen_ally_shop_items(self):
        """第 2 页列出每只已捕捉召唤物的属性与三条强化。"""
        for slot in range(len(self.captured)):
            tpl = self.captured[slot]
            if tpl is None:
                continue
            key = SLOT_KEY_NAMES[slot]
            name = tpl["name"]
            hp, atk = self._preview_ally_stats(tpl)
            affix_txt = self._ally_affix_text(tpl)
            hp_up = tpl.get("hp_mult", 1.0) + 0.25
            atk_up = tpl.get("atk_bonus", 0) + 4
            hp_next, atk_next = self._preview_ally_stats(tpl, hp_mult=hp_up)
            hp_same, atk_next2 = self._preview_ally_stats(tpl, atk_bonus=atk_up)
            self.shop_items.append({
                "type": "ally_hp", "slot": slot, "sold": False,
                "price": 8 + 4 * tpl.get("hp_buys", 0),
                "name": f"[{key}] {name} 生命 {hp}→{hp_next}",
                "desc": f"攻击 {atk}→{atk_next} · 词条 {affix_txt}",
            })
            self.shop_items.append({
                "type": "ally_atk", "slot": slot, "sold": False,
                "price": 8 + 4 * tpl.get("atk_buys", 0),
                "name": f"[{key}] {name} 攻击 {atk}→{atk_next2}",
                "desc": f"生命 {hp_same} · 词条 {affix_txt}",
            })
            self.shop_items.append({
                "type": "ally_affix", "slot": slot, "sold": False,
                "price": 12 + 6 * tpl.get("affix_buys", 0),
                "name": f"[{key}] {name} 赋予随机词条",
                "desc": f"生命 {hp} · 攻击 {atk} · 当前词条 {affix_txt}",
            })
            if len(self.shop_items) >= 9:
                break


    def _skill_upgrade_desc(self, skill):
        k = skill.kind
        if k == SKILL_SHIELD:
            cur = skill_shield_duration(skill.level) / FPS
            nxt = skill_shield_duration(skill.level + 1) / FPS
            return f"持续时间 {cur:.1f}s → {nxt:.1f}s"
        if k == SKILL_DASH:
            extra = ""
            if skill.has_evolution("paralyze"):
                cur_s = skill_dash_stun(skill.level) / FPS
                nxt_s = skill_dash_stun(skill.level + 1) / FPS
                extra = f"  眩晕 {cur_s:.1f}s→{nxt_s:.1f}s"
            return f"冲刺伤害 {skill_dash_damage(skill.level)} → {skill_dash_damage(skill.level + 1)}{extra}"
        if k == SKILL_FIREBALL:
            cur_bonus = skill_fireball_bonus(skill.level)
            nxt_bonus = skill_fireball_bonus(skill.level + 1)
            return (f"技能附加 {cur_bonus} → {nxt_bonus}  "
                    f"直击=普攻+附加  爆炸=2×普攻+附加")
        if k == SKILL_ICE_NOVA:
            cur_f = skill_ice_nova_freeze(skill.level) / FPS
            nxt_f = skill_ice_nova_freeze(skill.level + 1) / FPS
            cur_s = skill_ice_nova_slow(skill.level) / FPS
            nxt_s = skill_ice_nova_slow(skill.level + 1) / FPS
            return f"冻结 {cur_f:.1f}s→{nxt_f:.1f}s  减速 {cur_s:.1f}s→{nxt_s:.1f}s"
        if k == SKILL_METEOR:
            cur_b = skill_meteor_bonus(skill.level)
            nxt_b = skill_meteor_bonus(skill.level + 1)
            cur_d = skill_meteor_drain(skill.level)
            nxt_d = skill_meteor_drain(skill.level + 1)
            txt = f"火球附加 {cur_b}→{nxt_b}  能耗 {cur_d:.1f}→{nxt_d:.1f}/秒"
            if skill.has_evolution("scorch"):
                cs = skill_meteor_scorch_duration(skill.level) / FPS
                ns = skill_meteor_scorch_duration(skill.level + 1) / FPS
                txt += f"  灼烧 {cs:.1f}s→{ns:.1f}s"
            return txt
        if k == SKILL_BLACK_HOLE:
            cur = skill_black_hole_duration(skill.level) / FPS
            nxt = skill_black_hole_duration(skill.level + 1) / FPS
            txt = f"持续时间 {cur:.0f}s → {nxt:.0f}s"
            if skill.has_evolution("devour"):
                txt += (f"  吞噬伤害 {skill_black_hole_damage(skill.level)}"
                        f"→{skill_black_hole_damage(skill.level + 1)}")
            return txt
        if k == SKILL_TIME_REWIND:
            cur = skill_time_rewind_duration(skill.level) / FPS
            nxt = skill_time_rewind_duration(skill.level + 1) / FPS
            return f"回溯倒计时 {cur:.0f}s → {nxt:.0f}s"
        if k == SKILL_SOUL_CHAIN:
            cur = skill_soul_chain_targets(skill.level)
            nxt = skill_soul_chain_targets(skill.level + 1)
            tmp = skill_soul_chain_temp_health(skill.level)
            nxt_tmp = skill_soul_chain_temp_health(skill.level + 1)
            txt = f"链接数量 {cur} → {nxt}"
            if skill.has_evolution("soul_drain"):
                txt += f"  临时生命 {tmp}→{nxt_tmp}"
            return txt
        if k == SKILL_PACT:
            cur = skill_pact_duration(skill.level) / FPS
            nxt = skill_pact_duration(skill.level + 1) / FPS
            txt = f"契约领域 {cur:.1f}s → {nxt:.1f}s"
            if skill.has_evolution("soul_tax"):
                txt += "  魂税 回血 6"
            return txt
        return ""


    def draw_shop(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 240))
        screen.blit(overlay, (0, 0))
        self.draw_text("商 店", 44, GOLD, SCREEN_WIDTH // 2, 40)
        draw_back_button(self.mouse)
        if self.mode == MODE_SUMMONER:
            page_names = ["属性强化", "召唤物强化"]
        else:
            page_names = ["属性强化", "技能强化"]
        for i, name in enumerate(page_names):
            x = SCREEN_WIDTH // 2 - 120 + i * 240
            rect = (x - 90, 68, 180, 30)
            col = GOLD if i == self.shop_page else (110, 110, 130)
            if i == self.shop_page:
                pygame.draw.rect(screen, (60, 50, 30), rect, border_radius=6)
            pygame.draw.rect(screen, col, rect, 2, border_radius=6)
            self.draw_text(name, 20, col, x, 83)
        self.draw_text(f"晶体: {self.player.crystals}", 22, CYAN, SCREEN_WIDTH // 2, 118)
        self.draw_text("A/D 翻页 | 1-9 购买 | ESC 关闭", 16, (150, 150, 170), SCREEN_WIDTH // 2, 144)
        if not self.shop_items:
            hint = "此页暂无可购买项"
            if self.mode == MODE_SUMMONER and self.shop_page == 1:
                hint = "还没有捕捉到召唤物"
            self.draw_text(hint, 24, (170, 170, 190), SCREEN_WIDTH // 2, 300)
            return
        for i, item in enumerate(self.shop_items):
            y = 172 + i * 44
            box = (60, y, SCREEN_WIDTH - 120, 40)
            if item["sold"]:
                s = pygame.Surface((box[2], box[3]), pygame.SRCALPHA)
                s.fill((20, 30, 20, 180))
                screen.blit(s, (box[0], box[1]))
                pygame.draw.rect(screen, (70, 90, 70), box, 2, border_radius=6)
                self.draw_text(f"[{i + 1}] {item['name']}", 17, (120, 130, 120),
                               box[0] + 16, y + 11, center=False)
                self.draw_text("已购买", 16, (100, 110, 100), box[0] + box[2] - 90, y + 13)
            else:
                can_afford = self.player.crystals >= item["price"]
                bg_col = (30, 50, 80, 200) if can_afford else (50, 20, 25, 200)
                s = pygame.Surface((box[2], box[3]), pygame.SRCALPHA)
                s.fill(bg_col)
                screen.blit(s, (box[0], box[1]))
                border = GOLD if can_afford else DARK_RED
                pygame.draw.rect(screen, border, box, 2, border_radius=6)
                self.draw_text(f"[{i + 1}] {item['name']}", 17,
                               WHITE if can_afford else (150, 150, 150),
                               box[0] + 16, y + 4, center=False)
                if item.get("desc"):
                    self.draw_text(item["desc"], 13, (180, 200, 220),
                                   box[0] + 16, y + 24, center=False)
                price_col = CYAN if can_afford else RED
                self.draw_text(f"{item['price']}晶", 17, price_col, box[0] + box[2] - 70, y + 11)


    def handle_shop_purchase(self, idx):
        if not (0 <= idx < len(self.shop_items)): return
        item = self.shop_items[idx]
        if item["sold"]:
            self.show_message("已售出", 800); return
        if self.player.crystals < item["price"]:
            self.show_message("晶体不足", 800); return
        self.player.crystals -= item["price"]
        msg = ""
        t = item["type"]
        if t == "enhance":
            msg = item["enhancement"]["func"]()
            item["sold"] = True
        elif t == "skill_upgrade":
            skill = self.player.skills[item["slot"]]
            if skill is None: item["sold"] = True
            else:
                skill.level += 1
                msg = f"{skill.name} 升级至 Lv.{skill.level}！"
                item["price"] = 3 + skill.level * 2
                item["name"] = (f"[{SLOT_KEY_NAMES[item['slot']]}] {skill.name} "
                                f"升级  Lv.{skill.level}→Lv.{skill.level + 1}")
                item["desc"] = self._skill_upgrade_desc(skill)
        elif t == "skill_evolve":
            skill = self.player.skills[item["slot"]]
            if skill is None: item["sold"] = True
            else:
                evo_key = item["evolution"]["key"]
                if evo_key not in skill.evolutions:
                    skill.evolutions.append(evo_key)
                msg = f"{skill.name} 获得进化·{item['evolution']['name']}！"
                item["sold"] = True
                # 重新生成商店物品：另一个方向的进化自动消失
                self._gen_shop_items()
        elif t in ("ally_hp", "ally_atk", "ally_affix"):
            slot = item["slot"]
            tpl = self.captured[slot] if 0 <= slot < len(self.captured) else None
            if tpl is None:
                self.player.crystals += item["price"]   # 槽位空了就退钱
                item["sold"] = True
            elif t == "ally_hp":
                tpl["hp_mult"] = tpl.get("hp_mult", 1.0) + 0.25
                tpl["hp_buys"] = tpl.get("hp_buys", 0) + 1
                self._refresh_ally(slot)
                msg = f"{tpl['name']} 生命提升！"
                self._gen_shop_items()
            elif t == "ally_atk":
                tpl["atk_bonus"] = tpl.get("atk_bonus", 0) + 4
                tpl["atk_buys"] = tpl.get("atk_buys", 0) + 1
                self._refresh_ally(slot)
                msg = f"{tpl['name']} 攻击提升！"
                self._gen_shop_items()
            else:
                owned = set(tpl.get("affix_names") or [])
                pool = [n for n in ALLY_AFFIX_POOL if n not in owned]
                if not pool:
                    self.player.crystals += item["price"]
                    msg = "它已经拥有全部可用词缀"
                else:
                    gained = random.choice(pool)
                    tpl.setdefault("affix_names", []).append(gained)
                    tpl["affix_buys"] = tpl.get("affix_buys", 0) + 1
                    self._refresh_ally(slot)
                    msg = f"{tpl['name']} 获得词缀·{AFFIX_TABLE[gained].name}！"
                    self._gen_shop_items()
        self.show_message(msg or "", 1500)

