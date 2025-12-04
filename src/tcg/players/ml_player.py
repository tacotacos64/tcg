
from stable_baselines3 import PPO
from tcg.controller import Controller
from tcg.gym_env import TCGEnv, GymController
import numpy as np

class MLPlayer(Controller):
    """
    AI Player using a trained PPO model.
    """
    def __init__(self, model_path="tcg_ppo_final"):
        self.model = PPO.load(model_path)
        # We need a dummy env or just the observation logic to process info
        # Since we can't easily reuse TCGEnv._get_obs without an instance linked to a game,
        # we'll replicate the observation logic here.
        self.team = "ML_PPO"

    def team_name(self) -> str:
        return self.team

    def update(self, info):
        # info: [team_id, state, moving_pawns, spawning_pawns, done]
        team_id, state, moving_pawns, spawning_pawns, done = info
        
        # Construct Observation
        # 1. Fortress State
        state_obs = []
        for s in state:
            state_obs.extend([s[0], s[1], s[2], s[3], s[4]])
            
        # 2. Edge Traffic
        edge_traffic = np.zeros((12, 12, 2), dtype=np.float32)
        for pawn in moving_pawns:
            # pawn: [team, kind, from_, to, pos]
            p_team = pawn[0]
            from_ = pawn[2]
            to = pawn[3]
            
            # Map team ID to 0/1 index relative to US
            # If we are team 1, team 1 is 0, team 2 is 1.
            # If we are team 2, the game flips the view so we see ourselves as team 1.
            # So 'team' in info is always relative?
            # Wait, flip_board_view swaps team IDs.
            # So if we are team 2, flip_board_view converts our ID to 1.
            # So 'p_team' 1 is always US, 2 is always ENEMY in 'info'.
            
            team_idx = 0 if p_team == 1 else 1
            edge_traffic[from_][to][team_idx] += 1
            
        obs = np.concatenate([
            np.array(state_obs, dtype=np.float32),
            edge_traffic.flatten()
        ])
        
        # Predict action
        action, _states = self.model.predict(obs, deterministic=True)
        
        # action is [command, subject, target]
        return int(action[0]), int(action[1]), int(action[2])
