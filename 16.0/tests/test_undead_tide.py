import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from dungeon.data.enemies import ENEMY_GHOST, ENEMY_SKELETON
from dungeon.game.events import GameEventMixin


class TideHarness(GameEventMixin):
    def __init__(self):
        self.death_essence = 0
        self.spawned_units = []
        self.spawned_giants = 0

    def _spawn_tomb_unit(self, source, enemy_type):
        self.spawned_units.append(enemy_type)
        return object()

    def _spawn_giant_skeleton(self, x=None):
        self.spawned_giants += 1


def enemy(enemy_type, *, undead=False, elite=False, death_spawn=False):
    return SimpleNamespace(
        enemy_type=enemy_type,
        is_undead=undead,
        is_elite=elite,
        is_death_spawn=death_spawn,
        is_summoned=False,
        rect=SimpleNamespace(centerx=400),
    )


class UndeadTideDeathTests(unittest.TestCase):
    def test_ghost_does_not_spawn_another_ghost(self):
        game = TideHarness()

        game._undead_tide_death(
            enemy(ENEMY_GHOST, undead=True), False, False)

        self.assertEqual(game.spawned_units, [])
        self.assertEqual(game.spawned_giants, 0)

    def test_skeleton_spawns_exactly_one_ghost(self):
        game = TideHarness()

        game._undead_tide_death(
            enemy(ENEMY_SKELETON, undead=True), False, False)

        self.assertEqual(game.spawned_units, [ENEMY_GHOST])

    def test_original_elite_spawns_giant_skeleton(self):
        game = TideHarness()

        game._undead_tide_death(enemy(-1), True, False)

        self.assertEqual(game.spawned_giants, 1)
        self.assertEqual(game.spawned_units, [])

    def test_death_spawn_giant_turns_into_ghost_only(self):
        game = TideHarness()

        game._undead_tide_death(
            enemy(ENEMY_SKELETON, undead=True, elite=True, death_spawn=True),
            True,
            False,
        )

        self.assertEqual(game.spawned_giants, 0)
        self.assertEqual(game.spawned_units, [ENEMY_GHOST])

    def test_death_essence_still_triggers_once(self):
        game = TideHarness()
        game.death_essence = 9

        game._undead_tide_death(
            enemy(ENEMY_GHOST, undead=True), False, False)

        self.assertEqual(game.death_essence, 0)
        self.assertEqual(game.spawned_giants, 1)
        self.assertEqual(game.spawned_units, [])


if __name__ == "__main__":
    unittest.main()
