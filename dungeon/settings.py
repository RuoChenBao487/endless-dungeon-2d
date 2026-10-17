"""显示、帧率与全局常数：颜色表、物理常数、字体缓存、设置项。"""


# === IMPORTS ===
import pygame
# === /IMPORTS ===

pygame.init()


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

WINDOW_SCALE = 1.5
WINDOW_WIDTH = int(SCREEN_WIDTH * WINDOW_SCALE)
WINDOW_HEIGHT = int(SCREEN_HEIGHT * WINDOW_SCALE)

window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert()

pygame.display.set_caption("无尽地牢2D版")
clock = pygame.time.Clock()
FPS = 60

_scaled_buffer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()


SETTINGS = {
    "auto_fire": False,
    # 蓄力跳跃：按住跳得更高、松手即削顶；关掉就是固定高度跳
    "charge_jump": True,
}


GRAVITY = 0.8
JUMP_POWER_BASE = -18
ENEMY_JUMP_POWER = -15
BOMB_RADIUS = 80
SHIELD_DURATION = 600
ICE_TRAP_COOLDOWN = 300
SLIDE_FACTOR = 0.9
VERSION = "16.0"
GAME_TITLE = "无尽地牢2D版"

METEOR_DROP_INTERVAL = 30
FRAGILE_PATH_SECONDS = 20

# 拿到上限次数后，移速与跳跃强化就不再出现在奖励池里
LIMITED_ENHANCE_PICKS = 3
# 跳跃时松开按键会把上冲速度削到这个比例：轻点小跳、长按高跳
JUMP_CUT_FACTOR = 0.45

# ---- 生态区域 ----
REGION_ROOMS_MIN = 3              # 一个生态区域至少持续几间
REGION_ROOMS_MAX = 5              # 最多几间（数值在这之间波动）
NORMAL_GAP_START = 0.9            # 区域结束后的第一间必是普通地牢，
                                  # 之后每间"继续是普通"的概率按 0.9 / 0.8 / 0.7… 递减
TEMPLE_ROOM_CHANCE = 0.2          # 雪山区域里，每进入一间雪山房有 0.2 概率变成暴云寺庙
TEMPLE_REGION_EXTRA = 3           # 出现寺庙则雪山区域再延长这么多间
CHURCH_ROOM_CHANCE = 0.15         # 亡灵墓穴里每间房变成破败教堂的概率
CHURCH_REGION_EXTRA = 2           # 出现教堂后，本次亡灵墓穴区域再延长几间
GREAT_TOMB_ROOM_CHANCE = 0.15     # 古代大墓地的出现概率
GREAT_TOMB_REGION_EXTRA = 2       # 出现古代大墓地后延长的房间数

# ---- 暴风雪 ----
BLIZZARD_INTERVAL = 30 * FPS      # 每 30 秒刮一次
BLIZZARD_DURATION = 6 * FPS       # 一次持续 6 秒
BLIZZARD_PUSH = 0.55              # 横向推力（像素/帧），幅度适中、看得出影响即可
BLIZZARD_VEIL_ALPHA = 105         # 飞雪遮挡视野的不透明度
SNOW_DRIFT_MIN = 12                # 暴风雪过后地上出现的疏雪层数量
SNOW_DRIFT_MAX = 18
SNOW_DRIFT_RADIUS = 52            # 玩家走过 / 爆炸波及的清除范围

# ---- 巨魔 ----
TROLL_BUFF_INTERVAL = 15 * FPS    # 狂呼者每 15 秒喊一次
TROLL_BUFF_DURATION = 5 * FPS     # 增幅持续 5 秒
TROLL_BUFF_SPEED = 0.5            # 移速 +50%
TROLL_BUFF_DAMAGE = 0.5           # 攻击力 +50%
TROLL_BUFF_RANGE = SCREEN_WIDTH // 2   # 半个屏幕范围
TROLL_GIANT_SCALE = 1.7           # 大号巨魔的放大倍数（对照巨型骷髅的 2.2）

# ---- 暴云寺庙的金色水晶 ----
CRYSTAL_COOLDOWN = 20 * FPS       # 用完冷却 20 秒
CRYSTAL_BEAM_DURATION = 4 * FPS   # 光束持续 4 秒
CRYSTAL_DAMAGE_RATE = 2.0         # 每秒伤害 = 玩家攻击力的两倍
CRYSTAL_TICK = 30                 # 每 0.5 秒结算一次伤害
CRYSTAL_RANGE = 78                # 玩家靠近多少像素内可以按 F
CRYSTAL_MIN = 1                   # 寺庙房里的水晶数量
CRYSTAL_MAX = 3

# ---- 破败教堂 ----
CHURCH_CROSS_HP_BASE = 220        # 十字架血量按精英标准计算
CHURCH_CROSS_HP_SCALE = 24
CHURCH_CROSS_RANGE = 82           # 靠近多少像素内可以按 F 调查
CHURCH_CROSS_AURA_RANGE = SCREEN_WIDTH // 2
CHURCH_CROSS_AURA_TICKS = 5       # 离开范围后增幅很快消失
CHURCH_CROSS_SUMMON_INTERVAL = 8 * FPS
CHURCH_CROSS_HOLY_HEAL = 0.035    # 每帧为玩家恢复的生命
CHURCH_CROSS_HOLY_TICK = 30       # 圣光每 0.5 秒灼烧一次敌人
CHURCH_CROSS_HOLY_RADIUS = 185
VAMPIRE_DRAIN_RADIUS = 190
VAMPIRE_DRAIN_INTERVAL = 8
VAMPIRE_DRAIN_BASE = 5
VAMPIRE_SUMMON_INTERVAL = 10 * FPS
GARGOYLE_RECOVER_FRAMES = 5 * FPS

# ---- 古代大墓地 ----
GRAVESTONE_MIN = 1
GRAVESTONE_MAX = 3
GRAVESTONE_INTERVAL = 10 * FPS
GRAVESTONE_HP_BASE = 90
GRAVESTONE_HP_SCALE = 6
ZOMBIE_CORPSE_RADIUS = 190
BONE_CARRIER_HEAL_RADIUS = 220
LEADER_AURA_MAX_DAMAGE_REDUCTION = 0.6
SOUL_SHOCK_INTERVAL = int(2.5 * FPS)
SOUL_SHOCK_SPEED = 12.0
SOUL_SHOCK_DAMAGE = 8
SOUL_BURN_DURATION = 8 * FPS
SOUL_BURN_TICK = 60
SOUL_BURN_DAMAGE = 2


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 70, 70)
GREEN = (90, 200, 120)
BLUE = (90, 140, 220)
PURPLE = (150, 90, 190)
YELLOW = (240, 200, 80)
CYAN = (110, 210, 230)
DARK_BLUE = (40, 60, 110)
LIGHT_BLUE = (170, 210, 245)
BROWN = (130, 95, 65)
LIGHT_BROWN = (180, 140, 95)
ICE_BLUE = (150, 200, 240)
ICE_WHITE = (225, 240, 255)
GRAY = (140, 140, 150)
DARK_GRAY = (50, 50, 60)
GOLD = (240, 200, 90)
DARK_RED = (130, 40, 40)
ORANGE = (240, 150, 70)
BOSS_BLUE = (50, 90, 160)
CORE_BLUE = (120, 210, 250)
CORE_PURPLE = (210, 110, 220)
ELITE_PURPLE = (190, 130, 250)

BG_TOP = (18, 14, 26)
BG_MID = (26, 20, 36)
BG_BOT = (34, 24, 44)

FIRE_RED = (210, 60, 30)
FIRE_ORANGE = (245, 130, 50)
FIRE_YELLOW = (255, 210, 100)
LAVA_RED = (170, 45, 20)
LAVA_BRIGHT = (250, 110, 40)
DARK_LAVA = (55, 15, 8)

POISON_GREEN = (110, 190, 80)
POISON_DARK = (40, 70, 35)
POISON_BRIGHT = (170, 245, 110)

TOMB_GRAY = (130, 130, 145)
TOMB_DARK = (45, 45, 58)
BONE_WHITE = (230, 225, 205)
GHOST_PURPLE = (185, 150, 230)

STEEL = (170, 180, 200)
STEEL_DARK = (80, 90, 110)
DARK_KNIGHT = (60, 65, 90)

OUTLINE = (20, 16, 28)


_font_cache = {}


def get_font(size):
    if size in _font_cache: return _font_cache[size]
    try:
        font = pygame.font.SysFont(["SimHei", "Microsoft YaHei", "黑体", "SimSun"], size, bold=True)
    except Exception:
        try:
            font = pygame.font.Font("C:/Windows/Fonts/msyh.ttc", size)
        except Exception:
            font = pygame.font.Font(None, size)
    _font_cache[size] = font
    return font


SHOP_PAGES = 2
