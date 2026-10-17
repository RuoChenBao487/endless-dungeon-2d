"""主菜单。"""

RESUME = "resume"      # 主菜单返回这个值表示「继续上一局」


# === IMPORTS ===
import pygame
from .. import achievements
from .. import savegame
from .. import gallery
from ..data.biomes import BIOME_NORMAL
from ..data.modes import MODES, MODE_CHOICES, MODE_CLASSIC, MODE_ORDER
from ..save import profile, set_auto_fire, set_setting
from ..settings import CYAN, FPS, GAME_TITLE, GOLD, OUTLINE, SCREEN_HEIGHT, SCREEN_WIDTH, SETTINGS, VERSION, WHITE, clock, get_font, screen
from ..timing import advance_frame
from ..utils import (back_hit, draw_back_button, draw_panel, present, reward_cat_at,
                     reward_cat_rect, window_to_screen)
from ..world.background import draw_background
# === /IMPORTS ===

class MainMenu:
    def __init__(self):
        self.options = ["继续上一局", "开启无尽地牢", "更多模式", "游戏规则",
                        "敌人图鉴", "奖励说明", "冒险记录", "成就", "设置",
                        "更新日志", "退出游戏"]
        self.save_info = savegame.header()
        self.save_missing_timer = 0
        self.mouse = None          # 这一帧的鼠标位置（已换算到 800x600 的逻辑坐标）
        self.selected_index = 0
        self.show_modes = False
        self.mode_index = 0
        self.show_changelog = False
        self.show_rules = False
        self.show_enemy_info = False
        self.show_reward_info = False
        self.show_achievements = False
        self.show_records = False
        self.show_settings = False
        self.selected_enemy_idx = 0
        self.gallery_category = "all"
        self.gallery_place = "all"
        self.selected_achievement_idx = 0
        self.selected_reward_cat = 0
        self.rules_scroll = 0
        self.max_visible_rules = 14
        self.changelog_scroll = 0
        self.max_visible_lines = 14
        self.frame = 0
        self.settings_index = 0
        self.changelog = [
            "版本 16.0 古代大墓地 · 破败教堂 · 图鉴筛选",
            "- 新嵌套房：古代大墓地（亡灵墓穴）",
            "  进入亡灵墓穴房有 15% 概率出现，每段连续生态最多一次",
            "  出现后亡灵墓穴区域延长 2 间；1~3 座墓碑随机分布在地面",
            "  每座墓碑每 10 秒唤醒一只僵尸；房间必须清空敌人并摧毁墓碑",
            "- 新敌人：僵尸与巨型僵尸",
            "  僵尸移动极慢、血量厚、攻击力低，死亡后产生幽魂",
            "  非亡灵在僵尸附近死亡时额外生成僵尸，不替代原本的骷髅生成",
            "  附近有巨型僵尸时，额外生成的是巨型僵尸",
            "  巨型僵尸与巨型骷髅都属于精英",
            "- 新精英：载骨机",
            "  附近有敌人死亡时回复生命",
            "  幽魂/普通骷髅被吸收时各增加 1 道幽火，巨型骷髅增加 3 道",
            "  累计 5 道幽火后进化为炼魂魔骷，保留已有全部词缀",
            "- 炼魂魔骷",
            "  发射高速幽绿灵魂冲击，直接扣血并绕过护盾",
            "  自带专属词条「燃魂」，自身极慢掉血",
            "  玩家触碰后会持续受到无视护盾的燃魂伤害",
            "- 新成就：护盾谎言（护盾开启时死于炼魂魔骷的真实伤害）",
            "- 首领光环减伤可叠加，但最高只到 60%",
            "  同时修复叠层过高时伤害变负数、攻击敌人反而回血的 Bug",
            "- 图鉴新增分类和出没地筛选，并可滚轮翻阅全部条目",
            "- 成就页改为滚动列表 + 详情栏，支持鼠标与上下键翻阅",
            "- 新嵌套房：破败教堂（亡灵墓穴）",
            "  进入亡灵墓穴房有 15% 概率出现，每段连续生态最多一次",
            "  出现后亡灵墓穴区域延长 2 间，不占用事件房与领主房",
            "- 新普通敌人：血仆、血蝙蝠",
            "  两者都是亡灵并自带吸血词缀，也是吸血鬼唯一能抽取血液的单位",
            "  在墓穴规则下，亡灵死亡不会再额外生成骷髅",
            "  亡灵潮模式中，非幽魂亡灵死亡会转为幽魂",
            "- 新精英：吸血鬼",
            "  血量不满时快速抽取附近血仆/血蝙蝠的生命并等量回复",
            "  血族被抽干后转化为新的血仆",
            "  每隔一段时间随机召唤血仆或血蝙蝠",
            "- 新精英：石像鬼",
            "  教堂必定出现一只；灰色石像 → 青色地面追击",
            "  第二条血条清空后重新石化，从零开始回血",
            "  回血期间可彻底击杀；回满后进入飞行阶段",
            "- 新场景交互：教堂十字架",
            "  调查前外观完全相同，靠近按 F 后显露真身",
            "  血腥十字架：持续召唤亡灵，并强化半屏内敌人",
            "  圣光十字架：缓慢治疗玩家，并灼烧附近敌人",
            "  两者激活后都有精英级血量；血腥只受玩家伤害，圣光只受敌人伤害",
            "- 新背景与平台：塌落穹顶、残彩窗、长椅与暗红石台",
            "- 图鉴新增血仆、血蝙蝠、吸血鬼、石像鬼与两类十字架",
            "版本 15.5 代码重构 · 亡灵合体 · 战斗记录 · 随时继续",
            "- 新敌人：魔魂亡骨",
            "  幽灵与骷髅相撞时合体，继承双方的每一条词缀",
            "  对玩家的普通攻击与技能攻击减伤一半",
            "  炸弹、灼烧与反伤不受减伤影响",
            "  附近有骷髅、大骷髅或幽灵倒下时回复生命",
            "  巨型骷髅不会与幽灵合体",
            "- 结算新增战斗数据",
            "  伤害构成、承伤来源、最高单次伤害、无伤通过的房间数",
            "  高光时刻：终结领主 / 致命一击 / 残血逃生 / 爆发 / 滴水不漏",
            "- 敌人图鉴可以看到外形了",
            "  外形由现有敌人现场生成，敌人画法一改图鉴跟着变",
            "  图鉴记录击杀数与阵亡次数，没遇到过的写「尚未遭遇」",
            "  词缀对照表改为两列，条目多了列表会自动滚动",
            "- 暂停菜单新增「保存并退出」，主菜单新增「继续上一局」",
            "  关闭游戏后再次启动，也能从暂停的那一刻原样继续",
            "  敌人、血量、技能、状态、房间进度全部保留",
            "- 移动速度与跳跃高度各拿满 3 次后不再出现",
            "- 跳跃改为松键削顶：轻点小跳、长按高跳，落点更好控制",
            "- 新增成就系统，主菜单可查看进度与已解锁条目",
            "- 「更多模式」里不再重复列出经典无尽（主菜单第一项直接开）",
            "- 菜单支持鼠标：悬停选中、点击执行",
            "  子界面左上角有「返回」按钮，滚轮可滚动规则与日志",
            "- 生态改为区域制",
            "  一个生态持续 3~5 间房（往左回走也算），结束后必接一间普通地牢",
            "  之后每间继续是普通地牢的概率按 0.9 / 0.8 / 0.7… 递减",
            "- 新生态：暴雪山脉",
            "  每 30 秒刮一次暴风雪，持续 6 秒，有横向推风与飞雪挡视野",
            "  地面高低起伏但连续；风雪停后地上会留下疏雪层挡视线",
            "  疏雪层被走过或任何爆炸波及都会消失",
            "  冰爪狼：瞄准玩家扑击，起跳后无视平台",
            "  风灵：不造成伤害，只按风雪强度把人往外吹",
            "  巨魔（精英，自带再生）：士兵、猎手、狂呼者",
            "  巨魔狂呼者每 15 秒给半屏内敌人增幅 5 秒（移速攻击 +50%，脚下红环）",
            "  新领主：巨雪怪（结霜时怕火，火焰伤害翻倍）、巨魔酋长",
            "- 新房间：暴云寺庙（雪山深处，不是独立生态）",
            "  进入雪山房有 20% 概率变成寺庙，出现后雪山区域再延长 3 间",
            "  寺庙里没有风雪；最低的平台上会刷金色菱形水晶",
            "  靠近按 F 即可点亮：朝最近敌人射出金色光束，每秒伤害为攻击力两倍",
            "  持续 4 秒，冷却 20 秒；目标倒下会自动换最近的敌人",
            "- 拆成多个模块：数据、实体、领主、世界、对局、界面各司其职",
            "- 所有计时统一按帧推进，掉帧时不再互相错位",
            "- 各生物群系背景重做，并改为预渲染缓存，一帧只补动态部分",
            "- 新增局外存档：最高层数、累计击杀、冒险记录、最近一局数据",
            "版本 16.7 召唤物阵亡规则调整",
            "- 召唤物阵亡后槽位直接清空，需要重新捕捉",
            "- 不再进入再召唤冷却，收回仍然保留血量",
            "版本 16.6 新技能 · 新领主 · 新事件房",
            "- 新技能：亡者契约（UR 槽）",
            "  展开契约领域，期间击杀的敌人会作为临时友军站起来",
            "  临时友军存活18秒，会复制敌人的外形与词缀",
            "- 新领主：缝合怪·残躯",
            "  普通地牢深层与堕落骑士轮换出现",
            "  血量随本局累计击杀数膨胀（每杀1个+7，上限+1050）",
            "- 诅咒改为限时：持续3个房间后自动消退",
            "  主界面左侧会显示剩余房间数",
            "- 新事件房：词缀熔炉",
            "  给下个房间的所有敌人注入一条词缀，换1次强化+8晶体",
            "- 新事件房：属性交易所",
            "  生命↔能量 / 移速↔攻速 / 暴击↔噬血，也可以什么都不做",
            "- 新事件房：护核防守",
            "  核心在左、敌人在右，敌人无视玩家只拆核心，守住30秒",
            "- 新事件房：深渊轮盘",
            "  押生命或晶体，6个扇区：4奖励/1空白/1诅咒，指针停下即结算",
            "版本 16.5 召唤师重做",
            "- 召唤物改为占住技能槽：出战期间再按一次即可收回",
            "- 收回保留血量，阵亡后回到槽位并进入冷却",
            "- 商店第2页改为召唤物强化：显示生命/攻击/词缀",
            "- 召唤物强化：提升生命、提升攻击、赋予随机词缀",
            "- 召唤物会跟着玩家一起进入下一个房间",
            "- 修复房间清空后出口有时又被堵住的问题",
            "版本 16.4 新模式：精英地狱 / 召唤师",
            "- 词缀狂欢、亡灵潮开局改为携带 30 晶体",
            "- 新模式：精英地狱",
            "  普通敌人全部替换为精英，数量与血量不下调",
            "  精英种类无视生物群系随机抽取",
            "  开局 50 晶体，打开商店不再消耗晶体",
            "- 新模式：召唤师",
            "  U/I/O 开局解锁，但装的是召唤物而不是技能",
            "  按技能键进入捕捉状态，击杀敌人即收进该槽位",
            "  再按一次召唤它的友方版本，连词缀一起复制",
            "  普通盟友左右扫荡，精英盟友主动索敌",
            "  盟友会被敌人攻击，飞行敌人优先缠住盟友",
            "- 无限追猎的幽灵不再击退玩家",
            "版本 16.3 特殊模式与词缀扩充",
            "- 主菜单新增「更多模式」二级菜单",
            "- 新模式：词缀狂欢（敌人词缀无上限，越多越难出）",
            "- 新模式：亡灵潮（骷髅与幽灵的连锁死亡）",
            "- 新词缀：疾行、铁壁",
            "- 护盾词缀现在可见，并会在生成时立刻展开",
            "- 暂停时 ESC 继续游戏，空格结束本局回主菜单",
            "版本 16.2 新技能与事件房调整",
            "- 新增技能：暗影黑洞、时间回溯、灵魂锁链",
            "- 暗影黑洞进化：吞噬、扭曲",
            "- 时间回溯进化：自守、持恒",
            "- 灵魂锁链进化：共苦、灵魂汲取",
            "- 脆弱之路限时改为20秒",
            "- 事件交互新增离开选项，选择后解除边界",
            "- 护盾与回溯新增状态倒计时",
            "- 修复黑洞吸附导致敌人卡墙或离开可玩区域",
            "- 灵魂锁链只绘制目标之间的连线",
            "版本 16.1 反制性 Boss 重做",
            "- 移除全部 Boss 赖皮震荡波",
            "- 新增可跳跃躲避的贴地横波",
            "- 骷髅骨龙死亡龙息新增破防槽",
            "- 熔岩巨人自爆期间受伤翻倍",
            "- 新增技能 天降陨火：",
            "  按技能键进入吟唱，再按一次退出",
            "  吟唱期间无法移动（灵巧进化可移动）",
            "  火球威力=普攻+技能附加",
            "  灼烧进化：火球落地留持久燃烧区",
            "- 技能进化规则：每个技能仅能选一个方向",
            "- 商店在选择进化后自动移除另一方向",
            "- 镜像对决胜利可叠加第二个进化",
            "- 玩家初始只有 1 个技能槽且无技能",
            "",
            "版本 16.0 Boss 重做",
            "- 6 个全新 Boss，与场景深度绑定",
            "",
            "版本 15.0 新技能 + 亡灵墓穴机制 + 设置",
            "- 新增技能：寒冰新星",
            "- 护盾新增进化：防战",
            "- 新词缀：再生",
            "- 新事件：镜像对决",
            "- 亡灵墓穴：死亡气息跨层累积",
            "- 主菜单新增设置页",
        ]
        self.game_rules = [
            "游戏规则", "",
            "1. 基本操作:",
            "   A/D 移动    K 跳跃    J 射击",
            "   （可在主菜单设置页切换为自动射击模式）",
            "   U/I/O 释放技能    E 商店（消耗3晶体）",
            "   F 与事件祭坛、寺庙水晶或教堂十字架交互",
            "   鼠标左键放置炸弹",
            "   ESC 暂停 / 继续，暂停时按空格结束本局", "",
            "2. 生物群系:",
            "   普通地牢 / 冰晶洞穴 / 熔岩洞窟",
            "   腐沼秘境 / 亡灵墓穴", "",
            "3. 技能与能量:",
            "   初始只有 1 个技能槽（U键）且无技能",
            "   能量上限100，每秒恢复1.5点",
            "   技能升级无等级上限，威力线性成长", "",
            "4. 技能升级与进化:",
            "   商店第2页可用 A/D 翻页查看",
            "   升级：威力更强但耗能更多",
            "   进化：改变技能行为的分支选择",
            "   每个技能仅能选择一个进化方向",
            "   镜像对决胜利可叠加第二个进化", "",
            "5. 天降陨火:",
            "   按技能键进入吟唱，再按一次退出",
            "   吟唱期间无法移动",
            "   灵巧：吟唱可移动",
            "   灼烧：火球落地留持久燃烧区", "",
            "6. Boss:",
            "   已移除全部赖皮大范围震荡波",
            "   改为贴地横波（跳跃躲）/双层火环",
            "   骷髅骨龙死亡龙息可被破防打断", "",
            "7. 事件房:",
            "   非Boss层，深度≥2时有概率出现",
            "   靠近祭坛按 F 交互，做出选择", "",
            "   词缀熔炉：给下个房间敌人注入词缀换强化+晶体",
            "   属性交易所：互换两项属性，也可以什么都不做",
            "   护核防守：守住左侧核心30秒",
            "   深渊轮盘：押生命或晶体转轮盘，指哪得哪", "",
            "8. 亡灵墓穴:",
            "   非亡灵单位死亡后原地生成骷髅；亡灵死亡不再转化",
            "   非亡灵死亡累积死亡气息，每10点生成巨型骷髅",
            "   僵尸死亡产生幽魂，附近非亡灵死亡会额外唤醒僵尸", "",
            "9. 古代大墓地:",
            "   墓碑每10秒唤醒僵尸，玩家可以摧毁墓碑",
            "   载骨机吸收幽魂/骷髅，巨型骷髅记3道幽火，累计5道进化",
            "   炼魂魔骷的灵魂冲击与燃魂无视护盾", "",
            "10. 破败教堂:",
            "   亡灵墓穴的嵌套房，调查石十字架后显露血光或圣光",
            "   吸血鬼会抽血并召唤血仆/血蝙蝠；石像鬼分三阶段",
            "   血腥十字架召唤并强化亡灵，圣光十字架治疗玩家并灼烧敌人",
            "   血腥十字架只能被玩家攻击，圣光十字架只能被敌人攻击", "",
            "11. 强化:",
            "   每消灭10个敌人获得1次强化", "",
            "12. 特殊模式（主菜单 - 更多模式）:",
            "   词缀狂欢：开局30晶体，敌人至少1条词缀，数量无上限",
            "   亡灵潮：开局30晶体，非幽魂亡灵死亡化作幽灵，幽灵不再连锁",
            "   亡灵潮：精英与领主死亡降下巨大骷髅",
            "   亡灵潮：死亡气息常驻累积，满10点爆发",
            "   精英地狱：开局50晶体，商店免入场费",
            "   精英地狱：普通敌人全部变成精英，数量与血量不变",
            "   精英地狱：精英种类无视环境随机抽取",
            "   召唤师：U/I/O 开局可用，但装的是召唤物",
            "   召唤师：按技能键进入捕捉，击败敌人即收进该槽位",
            "   召唤师：再按一次放出盟友（复制其词缀）",
            "   召唤师：盟友出战期间再按一次即可收回，血量保留",
            "   召唤师：盟友阵亡后槽位直接清空，需要重新捕捉",
            "   召唤师：商店第2页可提升盟友生命/攻击/随机词缀",
            "   召唤师：普通盟友扫荡，精英盟友索敌最近的敌人",
            "   召唤师：盟友会被敌人攻击，飞行敌人优先缠住盟友",
        ]
        self.enemy_descriptions = gallery.ENTRIES
        self.reward_descriptions = [
            {"category": "基础资源", "items": [
                {"name": "生命值恢复", "desc": "恢复20点生命值"},
                {"name": "晶体", "desc": "在商店购买强化"},
                {"name": "炸弹", "desc": "鼠标左键引爆范围伤害"}
            ]},
            {"category": "属性强化", "items": [
                {"name": "跳跃高度", "desc": "+15%跳跃力度"},
                {"name": "攻击速度", "desc": "+20%攻击速度（间隔下限8帧）"},
                {"name": "移动速度", "desc": "+15%移动速度"},
                {"name": "最大生命值", "desc": "+5最大生命值（高权重）"},
                {"name": "攻击力", "desc": "固定+4基础攻击力（高权重）"},
                {"name": "精准射击", "desc": "穿透+1，攻击+10%"},
                {"name": "暴击伤害增加", "desc": "暴击=(伤害+加成)×2倍"}
            ]},
            {"category": "技能相关", "items": [
                {"name": "学习新技能", "desc": "随机获得一个新技能（含天降陨火）"},
                {"name": "解锁技能槽 II", "desc": "开启 I 键技能槽"},
                {"name": "解锁技能槽 III", "desc": "开启 O 键技能槽（需先解锁II）"},
                {"name": "能量上限 +20", "desc": "提高最大能量值（高权重）"},
                {"name": "能量恢复 +0.5/秒", "desc": "加快能量回复速度"},
                {"name": "技能升级", "desc": "在商店第2页升级技能（无上限）"},
                {"name": "技能进化", "desc": "每个技能仅能选一个进化方向"},
                {"name": "镜像叠加", "desc": "镜像对决胜利可叠加第二进化"},
            ]},
            {"category": "特殊能力", "items": [
                {"name": "二段跳", "desc": "空中可再次跳跃"},
                {"name": "暴击", "desc": "先到60%概率，溢出转暴击倍率"},
                {"name": "噬血·概率", "desc": "击杀回血概率（最高80%）"},
                {"name": "噬血·回血", "desc": "每次触发回血量"},
                {"name": "反伤", "desc": "受击时周围敌人掉5点血"},
                {"name": "防滑靴", "desc": "消除冰面滑行"},
                {"name": "爆破专家", "desc": "炸弹范围与持续伤害提升"},
                {"name": "应急护盾", "desc": "低血量自动激活"}
            ]},
            {"category": "事件房", "items": [
                {"name": "献祭祭坛", "desc": "以最大生命换取攻击/攻速/暴击"},
                {"name": "陷阱宝箱", "desc": "获得奖励后召唤敌人"},
                {"name": "许愿井", "desc": "投晶体得强化/进化"},
                {"name": "精英挑战", "desc": "召唤2精英，击败后获得强化与晶体"},
                {"name": "坠落炸弹挑战", "desc": "躲避20秒轰炸"},
                {"name": "无尽追猎", "desc": "撑过20秒幽灵追猎"},
                {"name": "脆弱之路", "desc": "踩脆弱平台到达顶部水晶"},
                {"name": "精英车轮战", "desc": "连杀3精英，奖励丰厚"},
                {"name": "镜像对决", "desc": "复制自己，胜利可叠加进化"},
                {"name": "词缀熔炉", "desc": "给下个房间的敌人注入一条词缀换奖励"},
                {"name": "属性交易所", "desc": "互换两项属性"},
                {"name": "护核防守", "desc": "守住左侧核心30秒"},
                {"name": "深渊轮盘", "desc": "押注转轮盘，指哪得哪"}
            ]}
        ]

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

    def handle_changelog_scroll(self, direction):
        max_scroll = max(0, len(self.changelog) - self.max_visible_lines)
        if direction == "up": self.changelog_scroll = max(0, self.changelog_scroll - 1)
        elif direction == "down": self.changelog_scroll = min(max_scroll, self.changelog_scroll + 1)

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
        for line in self.game_rules[start:start + self.max_visible_rules]:
            self.draw_text(line, 20, WHITE, SCREEN_WIDTH // 2, y_offset)
            y_offset += 28
        self.draw_text("按上下键滚动 | 按ESC返回", 22, (150, 150, 170), SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25)

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
        cat_rect = (50, 110, 200, SCREEN_HEIGHT - 180)
        info_rect = (300, 110, SCREEN_WIDTH - 350, SCREEN_HEIGHT - 180)
        draw_panel(screen, cat_rect, (100, 100, 140), 200)
        draw_panel(screen, info_rect, GOLD, 200)
        for i, cat in enumerate([c["category"] for c in self.reward_descriptions]):
            color = GOLD if i == self.selected_reward_cat else (150, 150, 170)
            y_pos = cat_rect[1] + 40 + i * 55
            box = reward_cat_rect(i)
            if self.mouse is not None and box.collidepoint(self.mouse) and i != self.selected_reward_cat:
                pygame.draw.rect(screen, (30, 36, 52, 200), box, border_radius=6)
            if i == self.selected_reward_cat:
                pygame.draw.rect(screen, (40, 50, 80, 200),
                                 (cat_rect[0] + 8, y_pos - 18, cat_rect[2] - 16, 40),
                                 border_radius=6)
            self.draw_text(cat, 22, color, cat_rect[0] + cat_rect[2] // 2, y_pos)
        if 0 <= self.selected_reward_cat < len(self.reward_descriptions):
            sc = self.reward_descriptions[self.selected_reward_cat]
            self.draw_text(sc["category"], 30, GOLD, info_rect[0] + info_rect[2] // 2, info_rect[1] + 35)
            pygame.draw.line(screen, (100, 100, 140),
                             (info_rect[0] + 30, info_rect[1] + 60),
                             (info_rect[0] + info_rect[2] - 30, info_rect[1] + 60), 1)
            y = info_rect[1] + 85
            for item in sc["items"]:
                self.draw_text(item["name"], 22, CYAN, info_rect[0] + 35, y, center=False)
                y += 26
                self.draw_text(item["desc"], 17, (200, 200, 220), info_rect[0] + 50, y, center=False)
                y += 30
        self.draw_text("点击或按上下键选择 | 按ESC返回", 22, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)
        draw_back_button(self.mouse)

    # ---- 鼠标与版面：绘制与点击判定共用同一套坐标 ------------------
    def _submenu_open(self):
        return (self.show_modes or self.show_changelog or self.show_rules
                or self.show_enemy_info or self.show_reward_info or self.show_records
                or self.show_achievements or self.show_settings)

    def _close_submenu(self):
        self.show_modes = False
        self.show_changelog = False
        self.show_rules = False
        self.show_enemy_info = False
        self.show_reward_info = False
        self.show_records = False
        self.show_achievements = False
        self.show_settings = False

    def _option_rect(self, i):
        y = 166 + i * 38
        return pygame.Rect(SCREEN_WIDTH // 2 - 220, y - 19, 440, 38)

    def _option_at(self, pos):
        if pos is None:
            return None
        for i in range(len(self.options)):
            if self._option_rect(i).collidepoint(pos):
                return i
        return None

    def _mode_row_rect(self, i):
        row_h = max(54, min(90, (SCREEN_HEIGHT - 175 - 50) // max(1, len(MODE_CHOICES))))
        centre = 105 + 40 + i * row_h + row_h // 2
        return pygame.Rect(56, centre - row_h // 2 + 1, 268, row_h - 2)

    def _mode_row_at(self, pos):
        if pos is None:
            return None
        for i in range(len(MODE_CHOICES)):
            if self._mode_row_rect(i).collidepoint(pos):
                return i
        return None

    def _mode_start_rect(self):
        """模式页右下角的「开始」按钮。"""
        info = (350, 105, SCREEN_WIDTH - 400, SCREEN_HEIGHT - 175)
        return pygame.Rect(info[0] + info[2] // 2 - 85, info[1] + info[3] - 84, 170, 44)

    def _settings_row_rect(self, i):
        y = 200 + (i % 2) * 96 + (i // 2) * 190
        return pygame.Rect(SCREEN_WIDTH // 2 - 280, y - 32, 560, 74)

    def _settings_row_at(self, pos):
        if pos is None:
            return None
        for i in range(4):
            if self._settings_row_rect(i).collidepoint(pos):
                return i
        return None

    def _activate_option(self):
        """执行当前选中的主菜单项；返回 run() 要交出去的值，None 表示留在菜单。"""
        choice = self.options[self.selected_index]
        if choice == "继续上一局":
            if self.save_info is None:
                self.save_missing_timer = 120
                return None
            return RESUME
        if choice == "开启无尽地牢":
            return MODE_CLASSIC
        if choice == "更多模式":
            if MODE_CHOICES:
                self.show_modes = True
                self.mode_index = 0
            return None
        if choice == "游戏规则":
            self.show_rules = True; self.rules_scroll = 0
        elif choice == "敌人图鉴":
            self.show_enemy_info = True
            self.selected_enemy_idx = 0
            self.gallery_category = "all"
            self.gallery_place = "all"
        elif choice == "奖励说明":
            self.show_reward_info = True; self.selected_reward_cat = 0
        elif choice == "冒险记录":
            self.show_records = True
        elif choice == "成就":
            self.show_achievements = True
            self.selected_achievement_idx = 0
        elif choice == "设置":
            self.show_settings = True
        elif choice == "更新日志":
            self.show_changelog = True; self.changelog_scroll = 0
        elif choice == "退出游戏":
            return False
        return None

    def _handle_click(self, pos):
        """鼠标左键：返回 run() 要交出去的值，没触发就返回 None。"""
        if pos is None:
            return None
        if self._submenu_open():
            if back_hit(pos):
                self._close_submenu()
                return None
            if self.show_modes:
                idx = self._mode_row_at(pos)
                if idx is not None:
                    if idx == self.mode_index:
                        return MODE_CHOICES[idx]     # 点在已选中的模式上就是开始
                    self.mode_index = idx
                elif self._mode_start_rect().collidepoint(pos):
                    return MODE_CHOICES[self.mode_index]
            elif self.show_enemy_info:
                hit = gallery.filter_hit(pos)
                if hit is not None:
                    kind, key = hit
                    if kind == "category":
                        self.gallery_category = key
                    else:
                        self.gallery_place = key
                    indices = gallery.filtered_indices(
                        self.gallery_category, self.gallery_place)
                    if indices and self.selected_enemy_idx not in indices:
                        self.selected_enemy_idx = indices[0]
                    return None
                indices = gallery.filtered_indices(
                    self.gallery_category, self.gallery_place)
                idx = gallery.list_index_at(
                    pos, self.selected_enemy_idx, indices)
                if idx is not None:
                    self.selected_enemy_idx = idx
            elif self.show_achievements:
                rows = achievements.progress(profile(), profile().last_run())
                idx = self._achievement_index_at(pos, rows)
                if idx is not None:
                    self.selected_achievement_idx = idx
            elif self.show_reward_info:
                idx = reward_cat_at(pos, len(self.reward_descriptions))
                if idx is not None:
                    self.selected_reward_cat = idx
            elif self.show_settings:
                idx = self._settings_row_at(pos)
                if idx is not None:
                    if idx < 2:
                        set_auto_fire(idx == 1)
                    else:
                        set_setting("charge_jump", idx == 3)
            return None
        idx = self._option_at(pos)
        if idx is None:
            return None
        self.selected_index = idx
        return self._activate_option()

    def _update_hover(self):
        """鼠标悬停即选中：主菜单与模式列表都这样，符合常见习惯。"""
        if self.mouse is None:
            return
        if not self._submenu_open():
            idx = self._option_at(self.mouse)
            if idx is not None and not (idx == 0 and self.save_info is None):
                self.selected_index = idx
        elif self.show_modes:
            idx = self._mode_row_at(self.mouse)
            if idx is not None:
                self.mode_index = idx

    def draw_changelog(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("更 新 日 志", 48, GOLD, SCREEN_WIDTH // 2, 55)
        draw_back_button(self.mouse)
        y_offset = 115
        start = self.changelog_scroll
        for line in self.changelog[start:start + self.max_visible_lines]:
            self.draw_text(line, 20, WHITE, SCREEN_WIDTH // 2, y_offset)
            y_offset += 30
        self.draw_text("按ESC返回 | 按上下键滚动", 22, (150, 150, 170), SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)

    def _achievement_list_layout(self, rows):
        visible = 12
        selected = max(0, min(self.selected_achievement_idx, len(rows) - 1))
        first = max(0, min(selected - visible // 2, max(0, len(rows) - visible)))
        return first, visible

    def _achievement_row_rect(self, row):
        return pygame.Rect(42, 126 + row * 33, 328, 31)

    def _achievement_index_at(self, pos, rows):
        if pos is None:
            return None
        first, visible = self._achievement_list_layout(rows)
        for row in range(visible):
            index = first + row
            if index >= len(rows):
                break
            if self._achievement_row_rect(row).collidepoint(pos):
                return index
        return None

    def draw_achievements(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("成 就", 48, GOLD, SCREEN_WIDTH // 2, 42)
        draw_back_button(self.mouse)

        book = profile()
        rows = achievements.progress(book, book.last_run())
        if not rows:
            self.draw_text("还没有成就数据", 24, (170, 170, 190),
                           SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            return
        self.selected_achievement_idx %= len(rows)
        done = sum(1 for _, _, ok in rows if ok)
        self.draw_text(f"已解锁 {done} / {len(rows)}", 20, CYAN,
                       SCREEN_WIDTH // 2, 78)

        list_rect = (34, 100, 344, SCREEN_HEIGHT - 154)
        detail_rect = (396, 100, SCREEN_WIDTH - 430, SCREEN_HEIGHT - 154)
        draw_panel(screen, list_rect, (100, 100, 140), 200)
        draw_panel(screen, detail_rect, GOLD, 200)

        first, visible = self._achievement_list_layout(rows)
        hovered = self._achievement_index_at(self.mouse, rows)
        for row in range(visible):
            index = first + row
            if index >= len(rows):
                break
            item, value, ok = rows[index]
            rect = self._achievement_row_rect(row)
            if index == self.selected_achievement_idx:
                pygame.draw.rect(screen, (42, 52, 82, 220), rect, border_radius=4)
            elif index == hovered:
                pygame.draw.rect(screen, (28, 34, 50, 200), rect, border_radius=4)
            color = GOLD if ok else (160, 162, 180)
            self.draw_text(("★ " if ok else "☆ ") + item["name"], 17, color,
                           rect.x + 8, rect.y + 3, center=False)
            rate = f"{value}/{item['target']}"
            width = get_font(14).size(rate)[0]
            self.draw_text(rate, 14, (150, 235, 190) if ok else (150, 152, 172),
                           rect.right - width - 8, rect.y + 4, center=False)

        item, value, ok = rows[self.selected_achievement_idx]
        cx = detail_rect[0] + detail_rect[2] // 2
        self.draw_text(("★ " if ok else "☆ ") + item["name"], 30,
                       GOLD if ok else WHITE, cx, detail_rect[1] + 48)
        pygame.draw.line(screen, (100, 100, 140),
                         (detail_rect[0] + 24, detail_rect[1] + 80),
                         (detail_rect[0] + detail_rect[2] - 24,
                          detail_rect[1] + 80), 1)
        self.draw_text(item["desc"], 19, (205, 205, 225),
                       detail_rect[0] + 30, detail_rect[1] + 112, center=False)
        self.draw_text("状态", 18, (150, 160, 180),
                       detail_rect[0] + 30, detail_rect[1] + 160, center=False)
        self.draw_text("已解锁" if ok else "进行中", 22,
                       (150, 235, 190) if ok else (220, 190, 120),
                       detail_rect[0] + 120, detail_rect[1] + 160, center=False)
        bar_x = detail_rect[0] + 30
        bar_y = detail_rect[1] + 200
        bar_w = detail_rect[2] - 60
        ratio = min(1.0, value / max(1, item["target"]))
        pygame.draw.rect(screen, (30, 34, 48), (bar_x, bar_y, bar_w, 12))
        pygame.draw.rect(screen, (146, 224, 160) if ok else GOLD,
                         (bar_x, bar_y, int(bar_w * ratio), 12))
        pygame.draw.rect(screen, (220, 220, 235), (bar_x, bar_y, bar_w, 12), 1)
        self.draw_text(f"{value} / {item['target']}", 18, WHITE,
                       cx, bar_y + 34)
        self.draw_text("滚轮 / 上下键翻阅 | 点击条目查看 | ESC返回", 18,
                       (150, 150, 170), SCREEN_WIDTH // 2, SCREEN_HEIGHT - 26)

    def draw_records(self):
        prof = profile()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("冒 险 记 录", 48, GOLD, SCREEN_WIDTH // 2, 52)
        draw_back_button(self.mouse)

        left = (50, 110, 300, SCREEN_HEIGHT - 180)
        right = (380, 110, SCREEN_WIDTH - 430, SCREEN_HEIGHT - 180)
        draw_panel(screen, left, (100, 100, 140), 200)
        draw_panel(screen, right, (100, 100, 140), 200)

        rows = [
            ("总场次", f"{prof.total_runs}"),
            ("累计击杀", f"{prof.total_kills}"),
            ("单局最高击杀", f"{prof.best_kills}"),
            ("最深到达", f"{prof.best_depth} 层"),
            ("最好成绩来自", prof.best_depth_mode or "尚无记录"),
        ]
        y = left[1] + 45
        for label, value in rows:
            self.draw_text(label, 19, (170, 170, 190), left[0] + 22, y, center=False)
            width = get_font(20).size(value)[0]
            self.draw_text(value, 20, WHITE, left[0] + left[2] - 22 - width, y + 1, center=False)
            y += 42
            pygame.draw.line(screen, (60, 60, 80),
                             (left[0] + 18, y - 12), (left[0] + left[2] - 18, y - 12), 1)

        self.draw_text("各模式最好成绩", 22, GOLD, right[0] + right[2] // 2, right[1] + 28)
        pygame.draw.line(screen, (100, 100, 140),
                         (right[0] + 18, right[1] + 48),
                         (right[0] + right[2] - 18, right[1] + 48), 1)
        y = right[1] + 72
        for mode_id in MODE_ORDER:
            best = prof.mode_best(mode_id)
            runs = prof.mode_runs(mode_id)
            self.draw_text(MODES[mode_id]["name"], 19,
                           GOLD if best else (130, 130, 150), right[0] + 22, y, center=False)
            summary = f"{best} 层 · {runs} 局"
            width = get_font(18).size(summary)[0]
            self.draw_text(summary, 18, (190, 190, 210),
                           right[0] + right[2] - 22 - width, y + 1, center=False)
            y += 30

        self.draw_text("最近几局", 22, GOLD, right[0] + right[2] // 2, y + 10)
        y += 42
        recent = prof.recent()
        if not recent:
            self.draw_text("还没有记录", 19, (150, 150, 170),
                           right[0] + right[2] // 2, y)
        for entry in recent[:4]:
            self.draw_text(f"{entry['mode']} · {entry['depth']} 层 · 击杀 {entry['kills']}",
                           18, (210, 210, 230), right[0] + right[2] // 2, y)
            y += 26

        last = prof.last_run()
        if last:
            y += 8
            self.draw_text(
                f"上一局：输出 {int(last.get('total_dealt', 0))}"
                f" · 承伤 {int(last.get('total_taken', 0))}"
                f" · 最高单次 {int(last.get('best_hit', 0))}",
                17, (190, 200, 220), right[0] + right[2] // 2, y)

        self.draw_text("按ESC返回", 22, (150, 150, 170), SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)

    def draw_settings(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("设 置", 48, GOLD, SCREEN_WIDTH // 2, 70)
        self.draw_text("攻击方式", 26, CYAN, SCREEN_WIDTH // 2, 138)
        self.draw_text("跳跃方式（雪山地形起伏，按需选择）", 26, CYAN,
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 22)

        options = [
            ("手动射击", "按 J 发射一颗子弹", not SETTINGS["auto_fire"]),
            ("自动射击", "按 J 开启/关闭自动射击，开启后自动发射", SETTINGS["auto_fire"]),
            ("固定跳跃高度", "按住多久都跳一样高，落点稳定", not SETTINGS["charge_jump"]),
            ("蓄力跳跃", "长按跳得更高、松手削顶，轻点是小跳", SETTINGS["charge_jump"]),
        ]
        for i, (name, desc, is_active) in enumerate(options):
            box = self._settings_row_rect(i)
            y = box.centery
            box = self._settings_row_rect(i)
            rect = (box.x, box.y, box.width, box.height)
            if self.mouse is not None and box.collidepoint(self.mouse) and not is_active:
                pygame.draw.rect(screen, (34, 38, 52), rect, border_radius=8)
            if is_active:
                pygame.draw.rect(screen, (60, 50, 30), rect, border_radius=8)
            pygame.draw.rect(screen, GOLD if is_active else (110, 110, 130), rect, 2, border_radius=8)
            marker = "●" if is_active else "○"
            self.draw_text(f"{marker} {name}", 28, GOLD if is_active else WHITE,
                           SCREEN_WIDTH // 2, y - 12)
            self.draw_text(desc, 17, (200, 210, 230), SCREEN_WIDTH // 2, y + 20)
        self.draw_text("点击或按 1/2/3/4 选择 | ESC 返回", 22, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)
        draw_back_button(self.mouse)

    def draw_mode_select(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 18, 235))
        screen.blit(overlay, (0, 0))
        self.draw_text("更 多 模 式", 48, GOLD, SCREEN_WIDTH // 2, 50)
        list_rect = (50, 105, 280, SCREEN_HEIGHT - 175)
        info_rect = (350, 105, SCREEN_WIDTH - 400, SCREEN_HEIGHT - 175)
        draw_panel(screen, list_rect, (100, 100, 140), 200)
        draw_panel(screen, info_rect, GOLD, 200)
        count = max(1, len(MODE_CHOICES))
        row_h = max(54, min(90, (list_rect[3] - 50) // count))
        for i, mode_id in enumerate(MODE_CHOICES):
            cfg = MODES[mode_id]
            box = self._mode_row_rect(i)
            y = box.centery
            selected = (i == self.mode_index)
            if selected:
                pygame.draw.rect(screen, (40, 50, 80, 200), box, border_radius=6)
            self.draw_text(cfg["name"], 24, GOLD if selected else (160, 160, 180),
                           list_rect[0] + list_rect[2] // 2, y - 12)
            self.draw_text(cfg["stars"], 16,
                           (230, 210, 120) if selected else (120, 120, 140),
                           list_rect[0] + list_rect[2] // 2, y + 13)

        cfg = MODES[MODE_CHOICES[self.mode_index]]
        self.draw_text(cfg["name"], 34, GOLD,
                       info_rect[0] + info_rect[2] // 2, info_rect[1] + 45)
        pygame.draw.line(screen, (100, 100, 140),
                         (info_rect[0] + 30, info_rect[1] + 75),
                         (info_rect[0] + info_rect[2] - 30, info_rect[1] + 75), 1)
        y = info_rect[1] + 110
        for line in cfg["desc"]:
            self.draw_text("· " + line, 20, WHITE, info_rect[0] + 30, y, center=False)
            y += 34
        start = self._mode_start_rect()
        hovered = self.mouse is not None and start.collidepoint(self.mouse)
        pygame.draw.rect(screen, (52, 42, 30) if hovered else (26, 28, 40), start,
                         border_radius=8)
        pygame.draw.rect(screen, GOLD if hovered else (120, 120, 145), start, 2,
                         border_radius=8)
        self.draw_text("开 始", 26, GOLD if hovered else WHITE, start.centerx, start.centery)
        self.draw_text("点击或按上下键选择 | 回车开始 | ESC 返回", 22, (150, 150, 170),
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)
        draw_back_button(self.mouse)

    def run(self):
        running = True
        while running:
            self.frame += 1
            self.mouse = window_to_screen(pygame.mouse.get_pos())
            self._update_hover()
            draw_background(BIOME_NORMAL, False, self.frame)
            title_font = get_font(70)
            title_text = title_font.render(GAME_TITLE, True, GOLD)
            title_shadow = title_font.render(GAME_TITLE, True, (80, 40, 10))
            tr = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
            screen.blit(title_shadow, (tr.x + 3, tr.y + 3))
            screen.blit(title_text, tr)
            pygame.draw.line(screen, GOLD, (SCREEN_WIDTH // 2 - 200, 132),
                             (SCREEN_WIDTH // 2 + 200, 132), 2)

            if not self._submenu_open():
                for i, option in enumerate(self.options):
                    y = 166 + i * 38
                    has_save = self.save_info is not None
                    if i == 0 and not has_save:
                        # 没有存档时「继续上一局」置灰
                        self.draw_text(option, 26, (95, 95, 110),
                                       SCREEN_WIDTH // 2, y)
                        continue
                    if i == self.selected_index:
                        box = self._option_rect(i)
                        rect = (box.x, box.y + 2, box.width, box.height - 4)
                        s = pygame.Surface((box.width, box.height - 4), pygame.SRCALPHA)
                        s.fill((80, 60, 30, 180))
                        screen.blit(s, (rect[0], rect[1]))
                        pygame.draw.rect(screen, GOLD, rect, 2, border_radius=8)
                        self.draw_text("» " + option, 30, GOLD, SCREEN_WIDTH // 2, y)
                    else:
                        self.draw_text(option, 26, (180, 180, 200), SCREEN_WIDTH // 2, y)
                if has_save:
                    info = self.save_info
                    self.draw_text(
                        f"存档：{info['mode_name']} 第 {info['depth']} 层"
                        f" · 击杀 {info['kills']} · {info['saved_at']}",
                        16, (150, 160, 185), SCREEN_WIDTH // 2, SCREEN_HEIGHT - 54)
            elif self.show_changelog: self.draw_changelog()
            elif self.show_rules: self.draw_rules()
            elif self.show_enemy_info: self.draw_enemy_info()
            elif self.show_reward_info: self.draw_reward_info()
            elif self.show_records: self.draw_records()
            elif self.show_achievements: self.draw_achievements()
            elif self.show_settings: self.draw_settings()
            elif self.show_modes: self.draw_mode_select()

            ver_text = f"版本 {VERSION}"
            ver_w = get_font(20).size(ver_text)[0]
            self.draw_text(ver_text, 20, (140, 140, 160),
                           SCREEN_WIDTH - ver_w - 12, SCREEN_HEIGHT - 25, False)
            if self.save_missing_timer > 0:
                self.save_missing_timer -= 1
                self.draw_text("没有可继续的存档", 20, (230, 140, 140),
                               SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: return False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._close_submenu()
                    elif event.key == pygame.K_UP:
                        if self.show_changelog: self.handle_changelog_scroll("up")
                        elif self.show_rules: self.handle_rules_scroll("up")
                        elif self.show_enemy_info:
                            indices = gallery.filtered_indices(
                                self.gallery_category, self.gallery_place)
                            self.selected_enemy_idx = gallery.scroll_selection(
                                self.selected_enemy_idx, indices, -1)
                        elif self.show_achievements:
                            rows = achievements.progress(profile(), profile().last_run())
                            self.selected_achievement_idx = (
                                self.selected_achievement_idx - 1) % max(1, len(rows))
                        elif self.show_reward_info:
                            self.selected_reward_cat = (self.selected_reward_cat - 1) % len(self.reward_descriptions)
                        elif self.show_modes:
                            self.mode_index = (self.mode_index - 1) % max(1, len(MODE_CHOICES))
                        else:
                            self.selected_index = (self.selected_index - 1) % len(self.options)
                    elif event.key == pygame.K_DOWN:
                        if self.show_changelog: self.handle_changelog_scroll("down")
                        elif self.show_rules: self.handle_rules_scroll("down")
                        elif self.show_enemy_info:
                            indices = gallery.filtered_indices(
                                self.gallery_category, self.gallery_place)
                            self.selected_enemy_idx = gallery.scroll_selection(
                                self.selected_enemy_idx, indices, 1)
                        elif self.show_achievements:
                            rows = achievements.progress(profile(), profile().last_run())
                            self.selected_achievement_idx = (
                                self.selected_achievement_idx + 1) % max(1, len(rows))
                        elif self.show_reward_info:
                            self.selected_reward_cat = (self.selected_reward_cat + 1) % len(self.reward_descriptions)
                        elif self.show_modes:
                            self.mode_index = (self.mode_index + 1) % max(1, len(MODE_CHOICES))
                        else:
                            self.selected_index = (self.selected_index + 1) % len(self.options)
                    elif event.key == pygame.K_RETURN:
                        if self.show_modes:
                            return MODE_CHOICES[self.mode_index]
                        elif not self._submenu_open():
                            action = self._activate_option()
                            if action is not None:
                                return action
                    elif self.show_settings:
                        if event.key == pygame.K_1:
                            set_auto_fire(False)
                        elif event.key == pygame.K_2:
                            set_auto_fire(True)
                        elif event.key == pygame.K_3:
                            set_setting("charge_jump", False)
                        elif event.key == pygame.K_4:
                            set_setting("charge_jump", True)
                elif event.type == pygame.MOUSEWHEEL:
                    if self.show_changelog:
                        self.handle_changelog_scroll("up" if event.y > 0 else "down")
                    elif self.show_rules:
                        self.handle_rules_scroll("up" if event.y > 0 else "down")
                    elif self.show_enemy_info:
                        indices = gallery.filtered_indices(
                            self.gallery_category, self.gallery_place)
                        self.selected_enemy_idx = gallery.scroll_selection(
                            self.selected_enemy_idx, indices,
                            -1 if event.y > 0 else 1)
                    elif self.show_achievements:
                        rows = achievements.progress(profile(), profile().last_run())
                        self.selected_achievement_idx = (
                            self.selected_achievement_idx
                            + (-1 if event.y > 0 else 1)) % max(1, len(rows))
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = self._handle_click(self.mouse)
                    if action is not None:
                        return action

            present()
            advance_frame()
            clock.tick(FPS)
        return False
