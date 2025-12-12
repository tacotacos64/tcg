from pathlib import Path
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from tcg.controller import Controller
from tcg.config import fortress_limit, A_coordinate, swap_number_l
from tcg.utils import flip_board_view
import numpy as np

class MLPlayer(Controller):
    """
    AI Player using a trained MaskablePPO model.
    """
    def __init__(self, model_path=None):
        if model_path is None:
            # Default path relative to project root
            # This file is in src/tcg/players/player_ml/ml_player.py
            # We want src/tcg/players_kishida/tcg_ppo_final.zip
            # parents[0] = player_ml
            # parents[1] = players
            # parents[2] = tcg
            tcg_dir = Path(__file__).parents[2]
            model_path = tcg_dir / "players_kishida/tcg_ppo_finetuned.zip"
        
        # Check if model exists
        if not model_path.exists():
             print(f"Warning: Model file not found at {model_path}")
             # Fallback to pretrained if finetuned not found
             fallback_path = tcg_dir / "players_kishida/tcg_ppo_final.zip"
             if fallback_path.exists():
                 print(f"Falling back to {fallback_path}")
                 model_path = fallback_path
        
        # Fix for loading issue: explicitly set policy_class
        try:
            self.model = MaskablePPO.load(
                model_path, 
                custom_objects={
                    "policy_class": MaskableActorCriticPolicy,
                }
            )
            self.team = "ML_PPO"
        except Exception as e:
            print(f"Error loading model: {e}")
            # Create a dummy model or raise error?
            # For now, let's just set team name to indicate error
            self.team = "ML_Error"
            self.model = None

    def team_name(self) -> str:
        return self.team

    def action_masks(self, state):
        # state is from flipped_info, so My Team is always 1
        mask = [False] * 432
        mask[0] = True
        
        for s in range(12):
            # Check ownership (My team is 1)
            if state[s][0] != 1:
                continue
            
            # Check pawns >= 2
            if state[s][3] < 2:
                continue
                
            for t in range(12):
                if A_coordinate[s][t] != 0:
                    idx = 144 + s * 12 + t
                    mask[idx] = True
                    
        for s in range(12):
            if state[s][0] != 1:
                continue
            level = state[s][2]
            if level >= 5:
                continue
            cost = fortress_limit[level] // 2
            if state[s][3] < cost:
                continue
            if state[s][4] != -1:
                continue
            idx = 288 + s * 12 + s
            mask[idx] = True
            
        return mask

    def update(self, info):
        # info: [team_id, state, moving_pawns, spawning_pawns, done]
        original_team_id = info[0]
        
        # Flip view so we are always Team 1
        flipped_info = flip_board_view(info)
        _, state, moving_pawns, _, _ = flipped_info
        
        # Construct Observation
        state_obs = []
        for s in state:
            # Normalize to match training environment
            # team: 0->0, 1->1 (Me), 2->-1 (Enemy)
            team_val = 0.0
            if s[0] == 1: team_val = 1.0
            elif s[0] == 2: team_val = -1.0
            
            kind = float(s[1])
            level = s[2] * 0.2
            # Use log scale for pawns
            pawns = np.log1p(s[3]) * 0.1
            upgrade = s[4] * 0.005 if s[4] != -1 else -1.0
            
            state_obs.extend([team_val, kind, level, pawns, upgrade])
            
        edge_traffic = np.zeros((12, 12, 2), dtype=np.float32)
        for pawn in moving_pawns:
            # pawn: [team, kind, from_, to, pos]
            team = pawn[0]
            from_ = pawn[2]
            to = pawn[3]
            
            # Team 1 is index 0, Team 2 is index 1
            team_idx = 0 if team == 1 else 1
            
            edge_traffic[from_][to][team_idx] += 0.01 # Scale by 0.01
            
        obs = np.concatenate([
            np.array(state_obs, dtype=np.float32),
            edge_traffic.flatten()
        ])
        
        # Get mask
        mask = self.action_masks(state)
        
        # Predict action
        action, _states = self.model.predict(obs, action_masks=mask, deterministic=True)
        action = int(action)
        
        # Decode action
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
            
        # If we flipped the board, we need to flip the action back
        if original_team_id == 2:
            # Flip subject and target
            sub = swap_number_l[sub]
            tgt = swap_number_l[tgt]
            
        return cmd, sub, tgt
