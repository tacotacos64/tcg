"""
Sample AI Player: RandomPlayer

ランダムに行動するAIプレイヤー。
参考用のサンプル実装です。
"""

import random

from tcg.config import fortress_limit
from tcg.controller import Controller


class RandomPlayer(Controller):
    """Random AI player that makes random valid moves."""

    def __init__(self) -> None:
        super().__init__()
        self.d = {}
        self.step = 0

    def team_name(self):
        return "Random_kun"

    def update(self, info) -> tuple[int, int, int]:
        self.team, self.state, self.moving_pawns, self.spawning_pawns, self.done = info
        self.step += 1

        subject = random.randint(0, 11)
        command = random.randint(0, 2)
        to = random.choice(self.state[subject][5])

        if self.state[subject][3] >= fortress_limit[self.state[subject][2]] // 2:
            if (
                random.random()
                < (self.state[subject][3] / fortress_limit[self.state[subject][2]] - 0.5) / 3
            ):
                pass
            else:
                command = 0
        else:
            command = 0

        return command, subject, to
