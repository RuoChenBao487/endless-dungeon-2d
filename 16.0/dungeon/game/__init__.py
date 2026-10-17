"""对局主体。

Game 本身只做组装：各个职责拆在 core / events / skills / summoner / combat /
rewards / shop / hud 这些 mixin 里，方法体保持原样，因此 self 上的状态互通。
"""


# === IMPORTS ===
from .combat import GameCombatMixin
from .church import GameChurchMixin
from .core import GameCoreMixin
from .events import GameEventMixin
from .graveyard import GameGraveyardMixin
from .hud import GameHudMixin
from .rewards import GameRewardMixin
from .regions import GameRegionMixin
from .shop import GameShopMixin
from .skills import GameSkillMixin
from .summoner import GameSummonerMixin
# === /IMPORTS ===

class Game(GameCoreMixin, GameEventMixin, GameSkillMixin, GameSummonerMixin,
           GameCombatMixin, GameRewardMixin, GameRegionMixin, GameShopMixin,
           GameChurchMixin, GameGraveyardMixin, GameHudMixin):
    """一局无尽地牢。"""
