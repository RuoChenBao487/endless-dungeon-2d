"""领主包的出口：按场景挑选并创建领主。"""


# === IMPORTS ===
from .roster import (BoneDragonBoss, FallenKnightBoss, GiantYetiBoss, IceTitanBoss,
                     InfernalDemonBoss, MoltenGiantBoss, PoisonQueenBoss, StitchedBoss,
                     TrollChieftainBoss)
from ..data.biomes import (BIOME_ICE, BIOME_LAVA, BIOME_NORMAL, BIOME_POISON, BIOME_SNOW,
                           BIOME_TEMPLE, BIOME_TOMB)
from ..data.bosses import (BOSS_BONE_DRAGON, BOSS_FALLEN_KNIGHT, BOSS_GIANT_YETI,
                           BOSS_ICE_TITAN, BOSS_INFERNAL_DEMON, BOSS_MOLTEN_GIANT,
                           BOSS_POISON_QUEEN, BOSS_STITCHED, BOSS_TROLL_CHIEFTAIN)
# === /IMPORTS ===

def create_boss(kind, x, y, depth, scene_type):
    if kind == BOSS_FALLEN_KNIGHT: return FallenKnightBoss(x, y, depth, scene_type)
    if kind == BOSS_GIANT_YETI: return GiantYetiBoss(x, y, depth, scene_type)
    if kind == BOSS_TROLL_CHIEFTAIN: return TrollChieftainBoss(x, y, depth, scene_type)
    if kind == BOSS_ICE_TITAN: return IceTitanBoss(x, y, depth, scene_type)
    if kind == BOSS_MOLTEN_GIANT: return MoltenGiantBoss(x, y, depth, scene_type)
    if kind == BOSS_INFERNAL_DEMON: return InfernalDemonBoss(x, y, depth, scene_type)
    if kind == BOSS_POISON_QUEEN: return PoisonQueenBoss(x, y, depth, scene_type)
    if kind == BOSS_BONE_DRAGON: return BoneDragonBoss(x, y, depth, scene_type)
    if kind == BOSS_STITCHED: return StitchedBoss(x, y, depth, scene_type)
    return FallenKnightBoss(x, y, depth, scene_type)


def pick_boss_for_scene(scene_type, depth):
    if scene_type == BIOME_NORMAL:
        # 普通地牢两种轮换：缝合怪的血量跟本局击杀数挂钩
        if (depth // 10) % 2 == 0:
            return BOSS_FALLEN_KNIGHT
        return BOSS_STITCHED
    if scene_type == BIOME_ICE:
        return BOSS_ICE_TITAN
    if scene_type == BIOME_LAVA:
        if (depth // 10) % 2 == 0:
            return BOSS_MOLTEN_GIANT
        return BOSS_INFERNAL_DEMON
    if scene_type == BIOME_POISON:
        return BOSS_POISON_QUEEN
    if scene_type == BIOME_TOMB:
        return BOSS_BONE_DRAGON
    if scene_type in (BIOME_SNOW, BIOME_TEMPLE):
        # 雪山两位轮换；寺庙不是独立生态，领主也用雪山的
        if (depth // 10) % 2 == 0:
            return BOSS_GIANT_YETI
        return BOSS_TROLL_CHIEFTAIN
    return BOSS_FALLEN_KNIGHT
