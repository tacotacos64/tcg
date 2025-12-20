
import gymnasium as gym
import numpy as np
from tcg.gym_env import TCGEnv
from tcg.config import fortress_limit

class CounterTCGEnv(TCGEnv):
    """
    A subclass of TCGEnv with a reward function shaped to encourage the 'Iron Wall' strategy.
    """
    def __init__(self, opponent_class, render_mode=None):
        super().__init__(opponent_class, render_mode)
        self.previous_blue_fortresses = 0
        self.previous_owners = [0] * 12
        self.previous_levels = [1] * 12
        # Importance weights for capturing fortresses (0-11)
        # Blue base is 10. Target is 1.
        # 7 is center-defense. 4 is center-attack.
        self.fortress_importance = [
            5.0, 10.0, 5.0,  # 0, 1, 2 (Enemy Base area)
            3.0, 8.0, 3.0,   # 3, 4, 5 (Mid-Enemy)
            2.0, 5.0, 2.0,   # 6, 7, 8 (Mid-Self)
            1.0, 1.0, 1.0    # 9, 10, 11 (Self Base area)
        ]
        
        # Safety weights for upgrading (Higher for safer/home fortresses)
        # Encourages investing in secure assets that won't be reset easily
        self.fortress_safety = [
            0.1, 0.1, 0.1,   # 0, 1, 2 (Enemy Base - Very risky)
            0.3, 0.2, 0.3,   # 3, 4, 5 (Mid-Enemy - Risky)
            0.8, 0.5, 0.8,   # 6, 7, 8 (Mid-Self - Safer)
            1.0, 1.0, 1.0    # 9, 10, 11 (Self Base - Safest)
        ]
        
        # Track time since last capture to penalize stagnation
        self.steps_since_last_capture = 0

    def reset(self, seed=None, options=None):
        obs, info = super().reset(seed, options)
        self.previous_blue_fortresses = self.game.Blue_fortress
        self.previous_owners = [s[0] for s in self.game.state]
        self.previous_levels = [s[2] for s in self.game.state]
        self.steps_since_last_capture = 0
        return obs, info

    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        
        # Adjust Win/Loss Reward (Total +50/-50)
        if terminated:
            if self.game.win_team == "Blue":
                reward += 40.0
            elif self.game.win_team == "Red":
                reward -= 40.0

        # 0. Expansion Bonus with Priority
        # Check for ownership changes
        current_owners = [s[0] for s in self.game.state]
        current_levels = [s[2] for s in self.game.state]
        captured_something = False
        
        for i in range(12):
            # If I captured it (was not mine, now is mine)
            if self.previous_owners[i] != 1 and current_owners[i] == 1:
                # Base bonus + Importance (Reduced multiplier to prevent farming)
                reward += 0.2 * self.fortress_importance[i]
                captured_something = True
            
            # Upgrade Bonus
            # If it's mine and level increased
            if current_owners[i] == 1 and current_levels[i] > self.previous_levels[i]:
                # Reward for investing in economy/defense
                # Base 0.5 + safety factor (Higher for home base)
                reward += 0.5 + (0.5 * self.fortress_safety[i])
                
        self.previous_owners = current_owners
        self.previous_levels = current_levels
        self.previous_blue_fortresses = self.game.Blue_fortress
        
        # Stagnation Penalty (Increased)
        if captured_something:
            self.steps_since_last_capture = 0
        else:
            self.steps_since_last_capture += 1
            
        # If no capture for a long time (e.g., 500 steps ~ 12.5 seconds), apply penalty
        # But only if we don't own everything yet (less than 12 forts)
        if self.steps_since_last_capture > 500 and self.game.Blue_fortress < 12:
            reward -= 0.05 # Stronger penalty to urge action
        
        # Continuous Control Reward (Weighted by Importance)
        # Encourages holding territory rather than flipping it
        for i in range(12):
            if current_owners[i] == 1:
                reward += 0.001 * self.fortress_importance[i]

        # Add strategy-specific rewards
        
        # 1. Center Control (Fortress 7)
        # Reward for holding Fortress 7
        center_owner = self.game.state[7][0]
        if center_owner == 1: # Mine
            reward += 0.001
        elif center_owner == 2: # Enemy
            reward -= 0.001
            
        # 2. Flank Upgrades (Fortress 9, 11)
        # Reward for having high level flanks
        for f in [9, 11]:
            if self.game.state[f][0] == 1:
                level = self.game.state[f][2]
                if level >= 2:
                    reward += 0.0005 * (level - 1)
                    
        # 3. Center Defense (Fortress 7)
        # Reward for having many pawns at Fortress 7 (if owned)
        if center_owner == 1:
            pawns = self.game.state[7][3]
            # Encourage stacking up to 100
            if pawns < 100:
                reward += pawns * 0.00001
            else:
                # Diminishing returns or penalty for over-stacking?
                # Just cap it.
                reward += 100 * 0.00001
                
        return obs, reward, terminated, truncated, info
