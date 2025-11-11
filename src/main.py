import pygame

from tcg.game import Game
from tcg.players.sample_random import RandomPlayer

if __name__ == "__main__":
    Game(RandomPlayer(), RandomPlayer()).run()

    pygame.quit()
