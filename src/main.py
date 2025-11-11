import pygame

from tcg.game import Game
from tcg.players.sample_random import RandomPlayer
from tcg.players.strategic_player import StrategicPlayer

if __name__ == "__main__":
    # StrategicPlayer vs RandomPlayer で対戦
    print("=== StrategicPlayer (Blue) vs RandomPlayer (Red) ===")

    # デフォルト: ウィンドウ表示あり
    # Game(StrategicPlayer(), RandomPlayer()).run()

    # ウィンドウ表示なし（高速実行）の場合:
    Game(StrategicPlayer(), RandomPlayer(), window=False).run()

    pygame.quit()
