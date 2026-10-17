"""程序入口：菜单与对局的循环。"""


# === IMPORTS ===
import pygame
from .game import Game
from .game.menu import RESUME, MainMenu
from .save import apply_saved_settings
from . import savegame
# === /IMPORTS ===

def main():
    apply_saved_settings()
    while True:
        menu = MainMenu()
        choice = menu.run()
        if not choice: break
        if choice == RESUME:
            game = savegame.load()
            if game is None:
                # 存档读不出来（多半是旧版本写的），清掉它免得主菜单一直挂着个点不动的选项
                savegame.clear()
                continue
        else:
            game = Game(mode=choice)
        while True:
            restart = game.run()
            if not restart:
                break
            game = Game(mode=game.mode)
    pygame.quit()
