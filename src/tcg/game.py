"""Game class for Fortress Conquest."""

import random

import pygame

from .config import (
    FPS,
    HEIGHT,
    SPEEDRATE,
    STEPLIMIT,
    WIDTH,
    A_coordinate,
    A_fortress_set,
    color_fortress,
    color_pawn,
    fortress_cool,
    fortress_limit,
    n_fortress,
    pos_fortress,
    swap_number_l,
)
from .controller import Controller
from .utils import flip_board_view


class Game:
    def __init__(self, controller1: Controller, controller2: Controller, window: bool = True):
        self.controller1 = controller1  # bottom
        self.controller2 = controller2  # up
        self.window_enabled = window

        self.team1 = self.controller1.team_name()
        self.team2 = self.controller2.team_name()

        if self.window_enabled:
            pygame.init()
            self.font = pygame.font.Font(None, 16)
            self.font_number = pygame.font.Font(None, 36)

            self.back_color = [150, 255, 150]

            self.window = pygame.display.set_mode((WIDTH, HEIGHT))
            self.fps = pygame.time.Clock().tick
        self.seconds = 0

        # team, kind, level, pawn_number, upgrade_time, to_set
        self.state = [
            [0, 0, 1, 10, -1, [1, 3, 4]],
            [2, 0, 2, 20, -1, [0, 2, 4]],
            [0, 0, 1, 10, -1, [1, 4, 5]],
            [0, 0, 2, 20, -1, [0, 4, 6, 7]],
            [0, 1, 3, 30, -1, [0, 1, 2, 3, 5, 6, 7, 8]],
            [0, 0, 2, 20, -1, [2, 4, 7, 8]],
            [0, 0, 2, 20, -1, [3, 4, 7, 9]],
            [0, 1, 3, 30, -1, [3, 4, 5, 6, 8, 9, 10, 11]],
            [0, 0, 2, 20, -1, [4, 5, 7, 11]],
            [0, 0, 1, 10, -1, [6, 7, 10]],
            [1, 0, 2, 20, -1, [7, 9, 11]],
            [0, 0, 1, 10, -1, [7, 8, 10]],
        ]

        self.step = 0

        self.spawning_pawns = []  # team, kind, pawn_number, from_, to, [pos]
        self.moving_pawns = []  # team, kind, from_, to, pos

        self.score = 0

        self.win_team = "Both"
        self.Red_fortress = 1
        self.Blue_fortress = 1

        self.isGameOver = False
        self.isGameOver_loop = False
        self.Overed = False
        self.done = False

    def draw_fortress(self):
        """Draw fortresses on screen."""
        if not self.window_enabled:
            return
        r = 0
        for x, y in pos_fortress:
            if r == 4 or r == 7:  # Draw square fortresses
                pygame.draw.rect(
                    self.window,
                    color_fortress[self.state[r][0]],
                    pygame.Rect(x - 40, y - 40, 80, 80),
                    width=0,
                )
            else:
                pygame.draw.circle(self.window, color_fortress[self.state[r][0]], (x, y), 45)
            r += 1

    def draw_road(self):
        """Draw roads between fortresses."""
        if not self.window_enabled:
            return
        for i in range(n_fortress):
            for j in range(n_fortress):
                if A_fortress_set[i][j] == 1:
                    pygame.draw.line(
                        self.window, [200, 150, 50], pos_fortress[i], pos_fortress[j], 25
                    )

    def draw_number(self):
        """Draw numbers on fortresses."""
        if not self.window_enabled:
            return
        for i in range(12):
            text = self.font.render(f"Lv {self.state[i][2]}", True, (0, 0, 0))
            position = (pos_fortress[i][0] - 20, pos_fortress[i][1] - 35)
            self.window.blit(text, position)

            if self.state[i][3] >= 10:
                text = self.font_number.render(f"{int(self.state[i][3])}", True, (0, 0, 0))
                position = (pos_fortress[i][0] - 20, pos_fortress[i][1] - 5)
                self.window.blit(text, position)
            else:
                text = self.font_number.render(f"{int(self.state[i][3])}", True, (0, 0, 0))
                position = (pos_fortress[i][0] - 10, pos_fortress[i][1] - 5)
                self.window.blit(text, position)

            if self.state[i][4] != -1:
                text = self.font.render(f"{int(self.state[i][4] // 2)}", True, (0, 0, 0))
                position = (pos_fortress[i][0] + 25, pos_fortress[i][1] - 5)
                self.window.blit(text, position)

        score_text = self.font.render(f"step: {self.step}", True, (255, 255, 255))
        score_position = (900, 10)
        self.window.blit(score_text, score_position)

        text = self.font.render(f"時間: {self.seconds}", True, (255, 255, 255))
        position = (900, 30)
        self.window.blit(text, position)

        len_text = self.font.render(f"pawn: {len(self.moving_pawns)}", True, (255, 255, 255))
        position = (900, 50)
        self.window.blit(len_text, position)

        len_text = self.font.render(f"spawn: {len(self.spawning_pawns)}", True, (255, 255, 255))
        position = (900, 70)
        self.window.blit(len_text, position)

        len_text = self.font.render(f"Rate: {SPEEDRATE}", True, (255, 255, 255))
        position = (900, 110)
        self.window.blit(len_text, position)

        len_text = self.font.render(f"fps: {FPS}", True, (255, 255, 255))
        position = (900, 130)
        self.window.blit(len_text, position)

    def draw_team_name(self):
        """Draw team names."""
        len_text = self.font_number.render(f"Red : {self.team2}", True, (200, 25, 25))
        position = (10, 10)
        self.window.blit(len_text, position)
        len_text = self.font_number.render(f"Blue: {self.team1}", True, (25, 25, 200))
        position = (10, HEIGHT - 50)
        self.window.blit(len_text, position)

    def draw_pawn(self):
        """Draw pawns on screen."""
        if not self.window_enabled:
            return
        for i in range(len(self.moving_pawns)):
            team, kind, from_, to, pos = self.moving_pawns[i]
            if kind == 0:
                pygame.draw.circle(self.window, color_pawn[team], pos, 5)
            elif kind == 1:
                x, y = pos[0], pos[1]
                pygame.draw.rect(
                    self.window, color_pawn[team], pygame.Rect(x - 2, y - 2, 8, 8), width=0
                )

    def pawn_born(self):
        """Pawns regenerate over time."""
        for i in range(12):
            team, kind, level, pawn_number, _, to_set = self.state[i]
            if self.step % fortress_cool[kind][level] == 0:
                if pawn_number < fortress_limit[level]:
                    self.state[i][3] += 1
                    if self.state[i][3] > fortress_limit[level]:
                        self.state[i][3] = fortress_limit[level]

    def pawn_over(self):
        """Remove pawns exceeding fortress limit."""
        for i in range(12):
            team, kind, level, pawn_number, _, to_set = self.state[i]
            if self.step % 40 == 0:
                if pawn_number > fortress_limit[level]:
                    self.state[i][3] -= 1

    def deliver(self, team, from_, to):
        """Create spawn point for pawns."""
        if team == self.state[from_][0] and self.state[from_][3] >= 2:
            if A_coordinate[from_][to] == 0:
                # print(f"team: {team}")
                return 0
            pos = [
                pos_fortress[from_][0] + A_coordinate[from_][to][0] * 42,
                pos_fortress[from_][1] + A_coordinate[from_][to][1] * 42,
            ]
            self.spawning_pawns.append(
                [team, self.state[from_][1], self.state[from_][3] // 2, from_, to, pos]
            )
            self.state[from_][3] -= self.state[from_][3] // 2

    def upgrade(self, team, subject):
        """Start fortress upgrade."""
        if (
            team == self.state[subject][0]
            and self.state[subject][3] >= fortress_limit[self.state[subject][2]] // 2
            and self.state[subject][4] == -1
            and 1 <= self.state[subject][2] <= 4
        ):
            self.state[subject][4] = 200
            self.state[subject][3] -= fortress_limit[self.state[subject][2]] // 2

    def check_upgrade(self):
        """Check if fortress upgrade is complete."""
        for i in range(n_fortress):
            if self.state[i][4] > 0:
                self.state[i][4] -= 1
            elif self.state[i][4] == 0:
                self.state[i][4] = -1
                self.state[i][2] += 1

    def pawn_departure(self):
        """Pawns depart from spawn points."""
        for i in range(len(self.spawning_pawns)):
            team, kind, pawn_number, from_, to, pos = self.spawning_pawns[i]
            r = random.random() - 0.5
            if self.step % 7 == 0 and kind == 0 and pawn_number > 0:
                pos = [
                    pos[0] + A_coordinate[from_][to][1] * r * 10,
                    pos[1] + A_coordinate[from_][to][0] * -1 * r * 10,
                ]
                self.moving_pawns.append([team, kind, from_, to, pos])
                self.spawning_pawns[i][2] -= 1

            elif self.step % 10 == 0 and kind == 1 and pawn_number > 0:
                pos = [
                    pos[0] + A_coordinate[from_][to][1] * r * 10,
                    pos[1] + A_coordinate[from_][to][0] * -1 * r * 10,
                ]
                self.moving_pawns.append([team, kind, from_, to, pos])
                self.spawning_pawns[i][2] -= 1

        for i in range(len(self.spawning_pawns)):
            if self.spawning_pawns[i][2] <= 0:
                self.spawning_pawns.remove(self.spawning_pawns[i])
                break

    def pawn_move(self):
        """Move pawns towards target fortress."""
        for i in range(len(self.moving_pawns)):
            team, kind, from_, to, pos = self.moving_pawns[i]
            if kind == 0:
                self.moving_pawns[i][4] = [
                    pos[0] + A_coordinate[from_][to][0] * 1.5,
                    pos[1] + A_coordinate[from_][to][1] * 1.5,
                ]
            elif kind == 1:
                self.moving_pawns[i][4] = [
                    pos[0] + A_coordinate[from_][to][0] * 1,
                    pos[1] + A_coordinate[from_][to][1] * 1,
                ]

        remove_list = []
        for i in range(len(self.moving_pawns)):
            team, kind, from_, to, pos = self.moving_pawns[i]
            x, y = pos_fortress[to]
            if (x - pos[0]) ** 2 + (y - pos[1]) ** 2 <= 45**2:
                remove_list.append(self.moving_pawns[i])

        for pawn in remove_list:
            self.pawn_arrive(pawn)

    def pawn_arrive(self, pawn):
        """Handle pawn arrival at fortress."""
        team, kind, from_, to, pos = pawn
        if team == self.state[to][0]:
            self.state[to][3] += 1
        elif team != self.state[to][0]:
            if kind == 0:
                self.state[to][3] -= 0.65
            elif kind == 1:
                self.state[to][3] -= 0.95

            if self.state[to][3] < 0:
                self.state[to] = [team, self.state[to][1], 1, 0, -1, self.state[to][5]]

        self.moving_pawns.remove(pawn)

    def order(self, team, command, subject, to):
        """Process player command."""
        if command == 0:
            return 0
        elif command == 1:
            self.deliver(team, subject, to)
        elif command == 2:
            self.upgrade(team, subject)

    def CheckGameOver(self):
        """Check if game is over."""
        self.Red_fortress = 0
        self.Blue_fortress = 0
        for i in range(n_fortress):
            if self.state[i][0] == 1:
                self.Blue_fortress += 1
            elif self.state[i][0] == 2:
                self.Red_fortress += 1

        if self.Red_fortress == self.Blue_fortress:
            self.win_team = "Both"
        elif self.Red_fortress > self.Blue_fortress:
            self.win_team = "Red"
        else:
            self.win_team = "Blue"

        if self.Red_fortress == 0:
            return True
        if self.Blue_fortress == 0:
            return True

        return False

    def check_event(self, event):
        """Check pygame events."""
        if not self.window_enabled:
            return
        for e in pygame.event.get():
            if e.type == event:
                return True
        return False

    def run(self):
        """Main game loop."""
        while True:
            self.seconds = (pygame.time.get_ticks() - 0) // 1000
            if self.isGameOver or self.step > STEPLIMIT:
                if self.Overed:
                    break
                print(
                    f"step: {self.step}  time: {int(self.seconds)}  //  "
                    f"{self.win_team} Win!!   B: {self.Blue_fortress}   R: {self.Red_fortress}"
                )
                break

            for _ in range(int(SPEEDRATE)):
                if self.isGameOver or self.step >= STEPLIMIT or self.isGameOver_loop or self.done:
                    self.Overed = True
                    self.isGameOver = True
                    print(
                        f"step: {self.step}  time: {int(self.seconds)}  //  "
                        f"{self.win_team} Win!!   B: {self.Blue_fortress}   "
                        f"R: {self.Red_fortress}   loop"
                    )
                    break

                if self.check_event(pygame.QUIT):
                    exit(0)
                    break

                self.pawn_move()
                self.done = self.CheckGameOver() or self.step == STEPLIMIT - 1

                # Controller1 gets team 1 perspective (bottom player)
                info_1 = [1, self.state, self.moving_pawns, self.spawning_pawns, self.done]
                # Controller2 gets flipped perspective (always sees themselves as team 1)
                info_2 = flip_board_view(
                    [2, self.state, self.moving_pawns, self.spawning_pawns, self.done]
                )

                command_1, subject_1, to_1 = self.controller1.update(info_1)
                command_2, subject_2, to_2 = self.controller2.update(info_2)

                # Convert controller2's commands back to original perspective
                subject_2 = swap_number_l[subject_2]
                to_2 = swap_number_l[to_2]

                self.order(1, command_1, subject_1, to_1)
                self.order(2, command_2, subject_2, to_2)

                self.pawn_departure()
                self.pawn_born()
                if self.step % 40 == 0:
                    self.pawn_over()

                self.check_upgrade()

                self.step += 1

                if self.CheckGameOver():
                    self.isGameOver_loop = True

            if self.window_enabled:
                back_color = [150, 150, 150]
                if self.Red_fortress == self.Blue_fortress:
                    back_color[1] += 105
                elif self.Red_fortress > self.Blue_fortress:
                    per = 2 * self.Red_fortress / (self.Red_fortress + self.Blue_fortress) - 1
                    back_color[0] += int(105 * per)
                    back_color[1] += int(105 * (1 - per))
                elif self.Red_fortress < self.Blue_fortress:
                    per = 2 * self.Blue_fortress / (self.Red_fortress + self.Blue_fortress) - 1
                    back_color[2] += int(105 * per)
                    back_color[1] += int(105 * (1 - per))

                if self.back_color[0] < back_color[0]:
                    self.back_color[0] += 1
                elif self.back_color[0] > back_color[0]:
                    self.back_color[0] -= 1

                if self.back_color[1] < back_color[1]:
                    self.back_color[1] += 1
                elif self.back_color[1] > back_color[1]:
                    self.back_color[1] -= 1

                if self.back_color[2] < back_color[2]:
                    self.back_color[2] += 1
                elif self.back_color[2] > back_color[2]:
                    self.back_color[2] -= 1

                self.window.fill(self.back_color)

                self.draw_road()
                self.draw_fortress()
                self.draw_pawn()
                self.draw_number()
                self.draw_team_name()

            if self.window_enabled:
                pygame.display.update()
                self.fps(int(FPS))

            if self.CheckGameOver():
                self.isGameOver = True
