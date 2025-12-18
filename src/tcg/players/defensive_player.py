from pathlib import Path
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from tcg.controller import Controller
from tcg.config import fortress_limit, A_coordinate
from tcg.utils import flip_board_view

class DefensivePlayer(Controller):
    """
    AI Player using the trained Defensive MaskablePPO model.
    Trained to play defensively against various strategies.
    """
    def __init__(self, model_path=None):
        self.team = "Defensive"
        if model_path is None:
            # Only use the final model. If not found, do not load any model.
            root_dir = Path(__file__).parents[3]  # src/tcg/players/ -> src/
            final_model = root_dir / "defensive_model_960000_steps.zip"
            if final_model.exists():
                self.model_path = final_model
            else:
                print("Warning: No trained model found for DefensivePlayer!")
                self.model_path = None
        else:
            self.model_path = Path(model_path)

        self.model = None
        if self.model_path and self.model_path.exists():
            try:
                self.model = MaskablePPO.load(
                    self.model_path,
                    custom_objects={
                        "policy_class": MaskableActorCriticPolicy,
                        "learning_rate": 0.0,
                        "clip_range": 0.0,
                    }
                )
            except Exception as e:
                print(f"Error loading model: {e}")

    def team_name(self) -> str:
        return self.team

    def action_masks(self, state):
        # state is list of [team, kind, level, pawn_number, upgrade_time, neighbors]
        # 432 actions
        mask = [False] * 432
        mask[0] = True  # Wait is always valid
        # Move: 144 + subject*12 + target
        for s in range(12):
            if state[s][0] != 1:
                continue
            if state[s][3] < 2:
                continue
            for t in range(12):
                if A_coordinate[s][t] != 0:
                    idx = 144 + s * 12 + t
                    mask[idx] = True
        # Upgrade: 288 + subject*12 + target
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

    def _get_obs(self, state, moving_pawns):
        # Construct observation vector matching the Gym environment
        state_obs = []
        for s in state:
            team_val = 0.0
            if s[0] == 1: team_val = 1.0
            elif s[0] == 2: team_val = -1.0
            kind = float(s[1])
            level = s[2] * 0.2
            pawns = np.log1p(s[3]) * 0.1
            upgrade = s[4] * 0.005 if s[4] != -1 else -1.0
            state_obs.extend([team_val, kind, level, pawns, upgrade])
        edge_traffic = np.zeros((12, 12, 2), dtype=np.float32)
        for pawn in moving_pawns:
            team = pawn[0]
            from_ = pawn[2]
            to = pawn[3]
            team_idx = 0 if team == 1 else 1
            edge_traffic[from_][to][team_idx] += 0.01
        return np.concatenate([
            np.array(state_obs, dtype=np.float32),
            edge_traffic.flatten()
        ])

    def update(self, info):
        if self.model is None:
            return 0, 0, 0  # Wait
        flipped_info = flip_board_view(info)
        _, state, moving_pawns, spawning_pawns, done = flipped_info
        obs = self._get_obs(state, moving_pawns)
        mask = self.action_masks(state)
        action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)
        action = int(action)
        if action == 0:
            return 0, 0, 0
        elif action < 144:
            return 0, 0, 0  # Should be masked out
        elif action < 288:
            idx = action - 144
            sub = idx // 12
            tgt = idx % 12
            return 1, sub, tgt
        else:
            idx = action - 288
            sub = idx // 12
            tgt = idx % 12
            return 2, sub, tgt
