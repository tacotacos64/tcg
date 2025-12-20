
import gymnasium as gym
import numpy as np
from gymnasium import spaces
from tcg.gym_game import GymGame
from tcg.controller import Controller
from tcg.config import fortress_limit, A_fortress_set, n_fortress, A_coordinate

class DefensiveTCGEnv(gym.Env):
    """
    Gymnasium environment for Fortress Conquest with defensive reward shaping.
    Rewards:
    - Capture Neutral: +1.0
    - Capture Enemy: +3.0
    - Lose Own: -5.0
    - Enemy Expands (to Neutral): -1.0 (Default)
    """
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}

    def __init__(self, opponent_class, render_mode=None):
        super().__init__()
        self.opponent_class = opponent_class
        self.render_mode = render_mode
        self.window = None
        self.clock = None
        self.action_space = spaces.Discrete(432)
        self.observation_space = spaces.Box(
            low=-1, high=50000, shape=(348,), dtype=np.float32
        )
        self.game = None
        self.gym_controller = None

    def _get_obs(self):
        state_obs = []
        for s in self.game.state:
            team_val = 0.0
            if s[0] == 1: team_val = 1.0
            elif s[0] == 2: team_val = -1.0
            kind = float(s[1])
            level = s[2] * 0.2
            pawns = np.log1p(s[3]) * 0.1
            upgrade = s[4] * 0.005 if s[4] != -1 else -1.0
            state_obs.extend([team_val, kind, level, pawns, upgrade])
        edge_traffic = np.zeros((12, 12, 2), dtype=np.float32)
        for pawn in self.game.moving_pawns:
            team = pawn[0]
            from_ = pawn[2]
            to = pawn[3]
            team_idx = 0 if team == 1 else 1
            edge_traffic[from_][to][team_idx] += 0.01
        return np.concatenate([
            np.array(state_obs, dtype=np.float32),
            edge_traffic.flatten()
        ])

    def action_masks(self):
        mask = [False] * 432
        mask[0] = True
        for s in range(12):
            if self.game.state[s][0] != 1:
                continue
            if self.game.state[s][3] < 2:
                continue
            for t in range(12):
                if A_coordinate[s][t] != 0:
                    idx = 144 + s * 12 + t
                    mask[idx] = True
        for s in range(12):
            if self.game.state[s][0] != 1:
                continue
            level = self.game.state[s][2]
            if level >= 5:
                continue
            cost = fortress_limit[level] // 2
            if self.game.state[s][3] < cost:
                continue
            if self.game.state[s][4] != -1:
                continue
            idx = 288 + s * 12 + s
            mask[idx] = True
        return mask

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        from tcg.gym_env import GymController
        self.gym_controller = GymController()
        if isinstance(self.opponent_class, list):
            import random
            opponent_cls = random.choice(self.opponent_class)
            opponent = opponent_cls()
        else:
            opponent = self.opponent_class()
        self.game = GymGame(self.gym_controller, opponent, window=(self.render_mode == "human"))
        return self._get_obs(), {}

    def step(self, action):
        action = int(action)
        if action == 0:
            cmd, sub, tgt = 0, 0, 0
        elif action < 144:
            cmd, sub, tgt = 0, 0, 0
        elif action < 288:
            cmd = 1
            rem = action - 144
            sub = rem // 12
            tgt = rem % 12
        else:
            cmd = 2
            rem = action - 288
            sub = rem // 12
            tgt = rem % 12
        self.gym_controller.set_action((cmd, sub, tgt))

        # Defensive reward shaping: capture fortress counts before step
        prev_blue = 0
        prev_red = 0
        for s in self.game.state:
            if s[0] == 1: prev_blue += 1
            elif s[0] == 2: prev_red += 1

        reward = 0
        terminated = False
        truncated = False
        steps_to_run = 40
        for _ in range(steps_to_run):
            if not self.game.process_step():
                terminated = True
                break

        # Win/Loss reward
        if terminated:
            if self.game.win_team == "Blue":
                reward += 10.0
            elif self.game.win_team == "Red":
                reward -= 10.0
            else:
                reward -= 5.0

        # State analysis
        current_blue = 0
        current_red = 0
        current_blue_prod = 0
        current_red_prod = 0
        current_blue_pawns = 0
        current_red_pawns = 0
        for s in self.game.state:
            if s[0] == 1:
                current_blue += 1
                current_blue_prod += fortress_limit[s[2]]
                current_blue_pawns += s[3]
            elif s[0] == 2:
                current_red += 1
                current_red_prod += fortress_limit[s[2]]
                current_red_pawns += s[3]

        diff_blue = current_blue - prev_blue
        diff_red = current_red - prev_red

        # Remove default fortress capture rewards
        # (gym_env.py: reward += diff_blue * 1.0; reward -= diff_red * 1.0)
        # So, subtract them out if present
        reward -= (diff_blue * 1.0 - diff_red * 1.0)

        # Defensive shaping
        if diff_blue > 0 and diff_red == 0:
            reward += 1.0
        elif diff_blue > 0 and diff_red < 0:
            reward += 3.0
        elif diff_blue < 0:
            reward -= 5.0
        elif diff_blue == 0 and diff_red > 0:
            reward -= 1.0
        elif diff_blue == 0 and diff_red < 0:
            reward += 1.0

        # Production/army shaping (same as gym_env)
        reward += (current_blue_prod - current_red_prod) * 0.0001
        reward += (current_blue_pawns - current_red_pawns) * 0.00001

        obs = self._get_obs()
        info = {}
        if self.game.step >= 50000:
            truncated = True
        return obs, reward, terminated, truncated, info

    def render(self):
        if self.render_mode == "human" and self.game.window_enabled:
            import pygame
            pygame.display.update()
            self.game.fps(30)

    def close(self):
        if self.window is not None:
            import pygame
            pygame.quit()
