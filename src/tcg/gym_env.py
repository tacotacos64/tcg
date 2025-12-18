import gymnasium as gym
import numpy as np
from gymnasium import spaces

from tcg.gym_game import GymGame
from tcg.controller import Controller
from tcg.config import fortress_limit, A_fortress_set, n_fortress, A_coordinate

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
        
        # Action Space: Discrete(432)
        # 0-143: Command 0 (Wait) - Only 0 is canonical
        # 144-287: Command 1 (Move) - 144 + subject*12 + target
        # 288-431: Command 2 (Upgrade) - 288 + subject*12 + target
        self.action_space = spaces.Discrete(432)

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
        # Normalize to help training stability
        state_obs = []
        for s in self.game.state:
            # s: [team, kind, level, pawn_number, upgrade_time, neighbors]
            # team: 0->0, 1->1 (Me), 2->-1 (Enemy)
            # kind: 0-1 -> keep
            # level: 1-5 -> scale by 0.2
            # pawn_number: 0-N -> scale by 0.02 (50 pawns = 1.0)
            # upgrade_time: -1 or 0-200 -> scale by 0.005 (200 steps = 1.0)
            
            team_val = 0.0
            if s[0] == 1: team_val = 1.0
            elif s[0] == 2: team_val = -1.0
            
            kind = float(s[1])
            level = s[2] * 0.2
            # Use log scale for pawns to handle large numbers (0-5000+)
            # log(10) ~ 2.3, log(100) ~ 4.6, log(1000) ~ 6.9
            # Scale by 0.1 to keep it around 0-1 range
            pawns = np.log1p(s[3]) * 0.1
            upgrade = s[4] * 0.005 if s[4] != -1 else -1.0
            
            state_obs.extend([team_val, kind, level, pawns, upgrade])
        
        # 2. Edge Traffic (12 * 12 * 2)
        # Map moving pawns to edges
        # Scale by 0.01 (100 pawns = 1.0)
        edge_traffic = np.zeros((12, 12, 2), dtype=np.float32)
        
        for pawn in self.game.moving_pawns:
            # pawn: [team, kind, from_, to, pos]
            team = pawn[0]
            from_ = pawn[2]
            to = pawn[3]
            
            # Team 1 is index 0, Team 2 is index 1
            team_idx = 0 if team == 1 else 1
            
            edge_traffic[from_][to][team_idx] += 0.01 # Count pawns (scaled)
            
        return np.concatenate([
            np.array(state_obs, dtype=np.float32),
            edge_traffic.flatten()
        ])

    def action_masks(self):
        # 432 actions
        # 0: Wait
        # 1..143: Invalid (Wait duplicates)
        # 144..287: Move (Cmd 1)
        # 288..431: Upgrade (Cmd 2)
        
        mask = [False] * 432
        mask[0] = True # Wait is always valid
        
        # Move: 144 + subject*12 + target
        for s in range(12):
            # Check ownership
            if self.game.state[s][0] != 1: # Not mine
                continue
            
            # Check pawns >= 2
            if self.game.state[s][3] < 2:
                continue
                
            for t in range(12):
                # Check connection
                if A_coordinate[s][t] != 0:
                    idx = 144 + s * 12 + t
                    mask[idx] = True
                    
        # Upgrade: 288 + subject*12 + target
        # Only target=subject is valid for canonical upgrade
        for s in range(12):
             # Check ownership
            if self.game.state[s][0] != 1:
                continue
            
            # Check level < 5
            level = self.game.state[s][2]
            if level >= 5:
                continue
                
            # Check cost
            cost = fortress_limit[level] // 2
            if self.game.state[s][3] < cost:
                continue
                
            # Check not upgrading
            if self.game.state[s][4] != -1:
                continue
                
            # Enable for target=subject (canonical)
            idx = 288 + s * 12 + s
            mask[idx] = True
            
        return mask

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.gym_controller = GymController()
        
        # Select opponent
        if isinstance(self.opponent_class, list):
            import random
            opponent_cls = random.choice(self.opponent_class)
            opponent = opponent_cls()
        else:
            opponent = self.opponent_class()
        
        # Randomize sides? For now, Agent is always Player 1 (Blue/Bottom)
        self.game = GymGame(self.gym_controller, opponent, window=(self.render_mode == "human"))
        
        # Initial observation
        return self._get_obs(), {}

    def step(self, action):
        # Decode action
        action = int(action)
        if action == 0:
            cmd, sub, tgt = 0, 0, 0
        elif action < 144:
            # Should be masked out, but handle just in case
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
        # 1. Win/Loss (Terminal)
        if terminated:
            if self.game.win_team == "Blue": # Agent won
                reward += 10.0
            elif self.game.win_team == "Red": # Agent lost
                reward -= 10.0
            else: # Draw
                reward -= 5.0 # Penalize draw
        
        # 2. State Analysis
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
            
        # 3. Shaping: Fortress Capture (Event-based)
        diff_blue = current_blue - prev_blue_fortresses
        diff_red = current_red - prev_red_fortresses
        
        # Capture/Loss is a significant event
        reward += diff_blue * 1.0
        reward -= diff_red * 1.0
        
        # 4. Shaping: Production Capacity (Continuous)
        # Encourages upgrading and holding high-level fortresses
        # Difference in total capacity (e.g., +100 capacity) gives small continuous reward
        reward += (current_blue_prod - current_red_prod) * 0.0001
        
        # 5. Shaping: Army Size (Continuous)
        # Encourages preserving troops and building army
        reward += (current_blue_pawns - current_red_pawns) * 0.00001
        
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
