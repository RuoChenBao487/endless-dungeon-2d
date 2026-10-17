"""全局帧计时。

游戏里所有计时都按帧推进：主循环以及每个模态循环每轮调用一次 advance_frame()，
需要读数的地方调用 frame_count()。原来的写法把帧计数和墙上时钟混在一起，
一旦掉帧，攻击间隔、护盾时长这些就会和别的计时器对不上，改成单一时间轴后不会再有这个问题。
"""


# === IMPORTS ===
from .settings import FPS
# === /IMPORTS ===

_frame = 0


def frame_count():
    """当前帧号，从 0 开始单调递增。"""
    return _frame


def advance_frame():
    """每个循环开头调用一次，推进一帧。"""
    global _frame
    _frame += 1
    return _frame


def seconds(count):
    """把秒换算成帧数，便于阅读配置。"""
    return int(count * FPS)


def ms(count):
    """把毫秒换算成帧数，供界面提示时长沿用原来的写法。"""
    return max(1, int(count * FPS / 1000))


def frames_to_seconds(count):
    """把帧数换算回秒，用于界面显示。"""
    return count / FPS
