"""词缀系统：词缀类族、抽取规则与图标/护盾绘制。"""


# === IMPORTS ===
import math
import pygame
import random
from .projectiles import SummonCircle
from .units import MirrorImage
from ..settings import (LEADER_AURA_MAX_DAMAGE_REDUCTION, OUTLINE, SCREEN_WIDTH,
                        SOUL_BURN_TICK, get_font)
from ..timing import frame_count
# === /IMPORTS ===

class Affix:
    name = "词缀"; color = (200, 200, 200); icon = "?"; threat = 0.5
    def __init__(self, owner):
        self.owner = owner; self.timer = 0
    def on_spawn(self, game): pass
    def update(self, game): pass
    def on_hit_player(self, player, game): pass
    def on_damaged(self, amount, game): return amount
    def on_death(self, game): pass


class BerserkAffix(Affix):
    name = "狂暴"; color = (255, 90, 90); icon = "狂"
    def __init__(self, owner):
        super().__init__(owner); self.active = False
    def update(self, game):
        if not self.active and self.owner.health <= self.owner.max_health * 0.5:
            self.active = True
            self.owner.base_speed *= 1.4
            self.owner.damage_multiplier = getattr(self.owner, 'damage_multiplier', 1.0) * 1.2


class ShieldAffix(Affix):
    name = "护盾"; color = (120, 200, 255); icon = "盾"
    def __init__(self, owner):
        super().__init__(owner)
        # cd 直接给满，让护盾在生成的第一帧就亮起来，否则要等 8 秒
        self.cd = 480; self.active_timer = 0; self.shield_hp = 0; self.max_shield = 0
    def update(self, game):
        if self.active_timer > 0:
            self.active_timer -= 1
            if self.active_timer <= 0: self.shield_hp = 0
        else:
            self.cd += 1
            if self.cd >= 480:
                self.cd = 0; self.active_timer = 300
                self.max_shield = int(self.owner.max_health * 0.25)
                self.shield_hp = self.max_shield
    def on_damaged(self, amount, game):
        if self.active_timer > 0 and self.shield_hp > 0:
            absorbed = min(self.shield_hp, amount)
            self.shield_hp -= absorbed
            if self.shield_hp <= 0:
                self.active_timer = 0; self.cd = 0
            return amount - absorbed
        return amount


class SplitAffix(Affix):
    name = "分裂"; color = (150, 255, 150); icon = "裂"
    def on_death(self, game):
        from .enemies import Enemy
        if self.owner.is_elite or getattr(self.owner, 'enemy_type', None) == 6: return
        if len(game.enemies) >= 20: return
        for _ in range(2):
            x = max(50, min(self.owner.rect.x + random.randint(-25, 25), SCREEN_WIDTH - 50))
            y = self.owner.rect.y
            small = Enemy(x, y, self.owner.depth, self.owner.enemy_type, self.owner.scene_type)
            small.base_health = max(10, int(self.owner.base_health * 0.3))
            small.health = small.base_health; small.max_health = small.base_health
            small.affix_names = []; small.affix_instances = []
            game.enemies.add(small); game.all_sprites.add(small)


class SummonAffix(Affix):
    name = "召唤"; color = (200, 150, 255); icon = "召"
    def on_death(self, game):
        if len(game.enemies) >= 20: return
        x = self.owner.rect.centerx; y = self.owner.rect.bottom
        circle = SummonCircle(x, y - 15, 0, self.owner.scene_type, self.owner.depth, delay=45)
        game.summon_circles.add(circle); game.all_sprites.add(circle)


class BurningAffix(Affix):
    name = "燃烧"; color = (255, 120, 30); icon = "燃"
    def on_hit_player(self, player, game):
        if getattr(player, 'burn_timer', 0) <= 0:
            player.burn_timer = 180; player.burn_tick = 0


class FreezingAffix(Affix):
    name = "冰冻"; color = (180, 220, 255); icon = "冻"
    def __init__(self, owner):
        super().__init__(owner); self.freeze_cd = 0
    def update(self, game):
        if self.freeze_cd > 0: self.freeze_cd -= 1
    def on_hit_player(self, player, game):
        if getattr(player, 'freeze_immune', 0) > 0: return
        if self.freeze_cd > 0: return
        if random.random() < 0.3:
            player.freeze_timer = 45; player.freeze_immune = 120; self.freeze_cd = 120
        else:
            player.slow_timer = max(player.slow_timer, 120)


class LifestealAffix(Affix):
    name = "吸血"; color = (220, 60, 90); icon = "吸"
    def on_hit_player(self, player, game):
        self.owner.health = min(self.owner.health + 4, self.owner.max_health)


class DeathExplosionAffix(Affix):
    name = "死亡爆炸"; color = (255, 180, 60); icon = "爆"
    def on_death(self, game):
        cx = self.owner.rect.centerx; cy = self.owner.rect.centery
        game.spawn_nova_wave(cx, cy, max_radius=110, damage=10, speed=4, small=True, color=(255, 160, 60))
        if not game.player.shield_active:
            dx = game.player.rect.centerx - cx; dy = game.player.rect.centery - cy
            if math.sqrt(dx * dx + dy * dy) < 100:
                game.player.take_damage(8, source='death_explosion')


class MirrorAffix(Affix):
    name = "镜像"; color = (200, 200, 220); icon = "镜"
    def __init__(self, owner):
        super().__init__(owner); self.cd = 0; self.mirrors = []
    def update(self, game):
        if self.cd > 0: self.cd -= 1; return
        if len(self.mirrors) >= 2: return
        self.cd = 300
        mirror = MirrorImage(self.owner.rect.centerx, self.owner.rect.centery, self.owner.image, 240)
        self.mirrors.append(mirror)
        game.all_sprites.add(mirror); game.mirrors.add(mirror)
    def on_death(self, game):
        for m in self.mirrors: m.kill()
        self.mirrors = []


class LeaderAuraAffix(Affix):
    name = "首领光环"; color = (255, 215, 80); icon = "环"
    RADIUS = 160
    def __init__(self, owner):
        super().__init__(owner); self.applied = set()
    def update(self, game):
        if game is None: return
        for enemy in game.enemies:
            if enemy is self.owner: continue
            dx = enemy.rect.centerx - self.owner.rect.centerx
            dy = enemy.rect.centery - self.owner.rect.centery
            if math.sqrt(dx * dx + dy * dy) < self.RADIUS:
                if enemy not in self.applied:
                    enemy.aura_speed_bonus = getattr(enemy, 'aura_speed_bonus', 0) + 0.15
                    enemy.aura_damage_reduction = min(
                        LEADER_AURA_MAX_DAMAGE_REDUCTION,
                        getattr(enemy, 'aura_damage_reduction', 0) + 0.2)
                    self.applied.add(enemy)
    def on_death(self, game):
        for enemy in list(self.applied):
            enemy.aura_speed_bonus = max(0, getattr(enemy, 'aura_speed_bonus', 0) - 0.15)
            sources = 0
            if game is not None:
                for other in game.enemies:
                    if other is self.owner or other is enemy:
                        continue
                    for affix in getattr(other, 'affix_instances', ()):
                        if (isinstance(affix, LeaderAuraAffix)
                                and enemy in affix.applied):
                            sources += 1
            enemy.aura_damage_reduction = min(
                LEADER_AURA_MAX_DAMAGE_REDUCTION, sources * 0.2)
        self.applied.clear()


class RegenerationAffix(Affix):
    name = "再生"; color = (100, 240, 140); icon = "生"
    def __init__(self, owner):
        super().__init__(owner); self.tick_timer = 0
    def update(self, game):
        self.tick_timer += 1
        if self.tick_timer >= 60:
            self.tick_timer = 0
            heal = max(1, int(self.owner.max_health * 0.05))
            self.owner.health = min(self.owner.health + heal, self.owner.max_health)


class SwiftAffix(Affix):
    name = "疾行"; color = (110, 245, 210); icon = "疾"
    def on_spawn(self, game):
        self.owner.base_speed *= 1.35
        self.owner.slow_immune = True
    def update(self, game):
        # 冰痕、冰锥、冰冻词缀都无法拖慢它
        if getattr(self.owner, 'slow_timer', 0) > 0:
            self.owner.slow_timer = 0


class ArmorAffix(Affix):
    name = "铁壁"; color = (150, 165, 200); icon = "铁"
    REDUCTION = 0.25
    def on_damaged(self, amount, game):
        return max(1, int(amount * (1 - self.REDUCTION)))


class SoulBurnAffix(Affix):
    """燃魂：持有者自己极慢掉血，被它接触的玩家也会持续损失真实生命。"""

    name = "燃魂"
    color = (104, 238, 142)
    icon = "魂"

    def __init__(self, owner):
        super().__init__(owner)
        self.tick = 0

    def update(self, game):
        if game is None or getattr(self.owner, "health", 0) <= 0:
            return
        self.tick += 1
        if self.tick < SOUL_BURN_TICK * 2:
            return
        self.tick = 0
        damage = max(1, int(getattr(self.owner, "max_health", 1) * 0.002))
        game.damage_enemy(self.owner, damage, source="soul_burn_self")


AFFIX_TABLE = {
    "berserk": BerserkAffix, "shield": ShieldAffix, "split": SplitAffix,
    "summon": SummonAffix, "burning": BurningAffix, "freezing": FreezingAffix,
    "lifesteal": LifestealAffix, "death_explosion": DeathExplosionAffix,
    "mirror": MirrorAffix, "leader_aura": LeaderAuraAffix,
    "regeneration": RegenerationAffix,
    "swift": SwiftAffix, "armor": ArmorAffix,
    "soul_burn": SoulBurnAffix,
}


AFFIX_MUTEX = {
    "split": {"summon", "death_explosion"}, "summon": {"split"},
    "lifesteal": {"shield"}, "shield": {"lifesteal"},
    "leader_aura": {"berserk"}, "berserk": {"leader_aura"},
    "regeneration": {"lifesteal"},
}


AFFIX_MIN_DEPTH = {
    "berserk": 0, "burning": 0, "death_explosion": 0, "regeneration": 0,
    "shield": 4, "split": 4, "summon": 4, "freezing": 4, "lifesteal": 4,
    "swift": 4, "armor": 4,
    "leader_aura": 7, "mirror": 7,
}


def roll_affixes(depth, count, exclude=None):
    taken = set(exclude or ())
    pool = [k for k, min_depth in AFFIX_MIN_DEPTH.items()
            if depth >= min_depth and k in AFFIX_TABLE and k not in taken]
    chosen = []
    for _ in range(count):
        candidates = [k for k in pool if k not in chosen]
        for c in list(candidates):
            if c in AFFIX_MUTEX and AFFIX_MUTEX[c] & (taken | set(chosen)):
                candidates.remove(c)
        if not candidates: break
        chosen.append(random.choice(candidates))
    return chosen


def draw_affix_icons_row(surface, sprite):
    """画敌人头顶的词缀图标：自动收进屏幕，超过 6 条时折叠成 +N。"""
    affixes = getattr(sprite, 'affix_instances', None)
    if not affixes:
        return
    shown = affixes[:5] if len(affixes) > 6 else affixes
    extra = len(affixes) - len(shown)
    slot = 18
    total = slot * len(shown) + (slot if extra > 0 else 0)
    x = max(4, min(sprite.rect.centerx - total // 2, SCREEN_WIDTH - total - 4))
    y = sprite.rect.y - 26
    if y < 4:
        y = sprite.rect.bottom + 4
    font = get_font(11)
    for affix in list(shown) + ([None] if extra > 0 else []):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(s, (30, 30, 40, 220), (8, 8), 8)
        pygame.draw.circle(s, affix.color if affix else (235, 235, 245), (8, 8), 7)
        pygame.draw.circle(s, OUTLINE, (8, 8), 7, 2)
        try:
            t = font.render(affix.icon if affix else f"+{extra}", True, OUTLINE)
            s.blit(t, (8 - t.get_width() // 2, 8 - t.get_height() // 2))
        except Exception:
            pass
        surface.blit(s, (x, y))
        x += slot


def draw_affix_shield(surface, sprite):
    """画出敌人身上还在生效的词缀护盾，让"护盾"词缀可见。"""
    active = None
    for affix in getattr(sprite, 'affix_instances', []):
        if isinstance(affix, ShieldAffix) and affix.active_timer > 0 and affix.shield_hp > 0:
            active = affix
            break
    if active is None:
        return
    cx, cy = sprite.rect.centerx, sprite.rect.centery
    r = max(sprite.rect.width, sprite.rect.height) // 2 + 8
    ratio = max(0.0, min(1.0, active.shield_hp / max(1, active.max_shield)))
    t = frame_count() / 12
    alpha = int(50 + 70 * ratio)
    s = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
    pygame.draw.circle(s, (90, 220, 255, alpha), (r + 4, r + 4), r, 3)
    pts = []
    for i in range(6):
        a = math.pi / 3 * i + t / 4
        pts.append((r + 4 + r * math.cos(a), r + 4 + r * math.sin(a)))
    pygame.draw.polygon(s, (160, 235, 255, alpha), pts, 2)
    surface.blit(s, (cx - r - 4, cy - r - 4))
