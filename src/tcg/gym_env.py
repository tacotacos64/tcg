
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from tcg.gym_game import GymGame
from tcg.controller import Controller
from tcg.config import fortress_limit, A_fortress_set, n_fortress

class GymController(Controller):
    """A controller that takes actions from an external source."""
    def __init__(self):
        self.next_action = (0, 0, 0)
        self.team = "GymAgent"

    def team_name(self) -> str:
        return self.team

    def set_action(self, action):
        self.next_action = action

    def update(self, info):
        return self.next_action

class TCGEnv(gym.Env):
    """
    Gymnasium environment for Fortress Conquest.
    """
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}

    def __init__(self, opponent_class, render_mode=None):
        super().__init__()
        self.opponent_class = opponent_class
        self.render_mode = render_mode
        self.window = None
        self.clock = None
        
        # Action Space: MultiDiscrete([3, 12, 12])
        # 0: Command (0: None, 1: Move, 2: Upgrade)
        # 1: Subject Fortress (0-11)
        # 2: Target Fortress (0-11)
        self.action_space = spaces.MultiDiscrete([3, 12, 12])

        # Observation Space
        # We need to flatten the game state into a fixed-size vector.
        # State (12 fortresses * 5 features) = 60
        #   Features: [team(0-2), kind(0-1), level(1-5), pawn_count, upgrade_timer]
        # Edge Traffic (12*12 edges * 2 teams) = 288
        #   Features: [my_troops, enemy_troops] on each edge
        # Total: 348
        
        self.observation_space = spaces.Box(
            low=-1, high=50000, shape=(348,), dtype=np.float32
        )

        self.game = None
        self.gym_controller = None

    def _get_obs(self):
        # 1. Fortress State (12 * 5)
        # Normalize or keep raw? Let's keep raw for now but convert to float
        state_obs = []
        for s in self.game.state:
            # s: [team, kind, level, pawn_number, upgrade_time, neighbors]
            # We exclude neighbors list as it's static topology
            state_obs.extend([s[0], s[1], s[2], s[3], s[4]])
        
        # 2. Edge Traffic (12 * 12 * 2)
        # Map moving pawns to edges
        edge_traffic = np.zeros((12, 12, 2), dtype=np.float32)
        
        for pawn in self.game.moving_pawns:
            # pawn: [team, kind, from_, to, pos]
            team = pawn[0]
            from_ = pawn[2]
            to = pawn[3]
            
            # Team 1 is index 0, Team 2 is index 1
            team_idx = 0 if team == 1 else 1
            
            edge_traffic[from_][to][team_idx] += 1 # Count pawns
            
        return np.concatenate([
            np.array(state_obs, dtype=np.float32),
            edge_traffic.flatten()
        ])

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.gym_controller = GymController()
        opponent = self.opponent_class()
        
        # Randomize sides? For now, Agent is always Player 1 (Blue/Bottom)
        self.game = GymGame(self.gym_controller, opponent, window=(self.render_mode == "human"))
        
        # Initial observation
        return self._get_obs(), {}

    def step(self, action):
        # Set action for the agent
        # action is [command, subject, target]
        self.gym_controller.set_action(tuple(action))
        
        # Run game for N steps (frame skip)
        # In the original game, SPEEDRATE=40 steps per frame.
        # If we want the agent to act every frame, we run 40 steps.
        # But 40 steps might be too long for reaction?
        # Let's stick to SPEEDRATE for now to match the game speed.
        
        reward = 0
        terminated = False
        truncated = False
        
        # Execute one frame (SPEEDRATE simulation steps)
        # Or should we execute just 1 simulation step?
        # If we execute 1 step, the game will be very slow for the agent (50000 steps total).
        # Let's execute SPEEDRATE steps (one visual frame).
        
        steps_to_run = 40 # SPEEDRATE
        
        prev_blue_fortresses = self.game.Blue_fortress
        prev_red_fortresses = self.game.Red_fortress
        
        for _ in range(steps_to_run):
            if not self.game.process_step():
                terminated = True
                break
        
        # Calculate Reward
        # 1. Win/Loss
        if terminated:
            if self.game.win_team == "Blue": # Agent won
                reward += 100
            elif self.game.win_team == "Red": # Agent lost
                reward -= 100
            else: # Draw
                reward -= 10
        
        # 2. Shaping: Fortress Count Difference
        # Reward for capturing, penalty for losing
        # We need to track changes.
        # Game updates Blue_fortress/Red_fortress in CheckGameOver which is called in process_step
        
        current_blue = 0
        current_red = 0
        for s in self.game.state:
            if s[0] == 1: current_blue += 1
            elif s[0] == 2: current_red += 1
            
        # Simple shaping: Reward = (My Fortresses - Enemy Fortresses) * 0.1
        reward += (current_blue - current_red) * 0.1
        
        # 3. Shaping: Total Troops?
        
        obs = self._get_obs()
        info = {}
        
        if self.game.step >= 50000:
            truncated = True
            
        return obs, reward, terminated, truncated, info

    def render(self):
        if self.render_mode == "human" and self.game.window_enabled:
            # The game draws itself in process_step if window is enabled
            # But we need to handle the display update if we are controlling the loop
            import pygame
            pygame.display.update()
            self.game.fps(30)

    def close(self):
        if self.window is not None:
            import pygame
            pygame.quit()
