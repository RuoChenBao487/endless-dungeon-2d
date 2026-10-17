"""无尽地牢 2D 版。

按职责分层的包结构：

    settings   显示、配色与全局常数
    timing     全局帧计时
    utils      绘图与几何小工具
    save       局外存档
    data/*     纯数据表（群系、领主、模式、技能、敌人、事件）
    world/*    场景背景
    entities/* 玩家、敌人、投射物、词缀、场景物件
    bosses/*   领主基类与各领主实现
    game/*     Game 的各职责 mixin 与主菜单
    app        程序入口
"""


# === IMPORTS ===
# === /IMPORTS ===
