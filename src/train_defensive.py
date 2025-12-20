
import os
import sys
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import CheckpointCallback

from tcg.defensive_gym_env import DefensiveTCGEnv
from tcg.players.player_kishida_mlppo.ml_player import MLPlayer
from tcg.players.player_kishida_counter.ONCT import ONCT
from tcg.players.strategy_right_flank_aggressive import RightFlankAggressive
from tcg.players.strategy_secure_home_aggressive import SecureHomeAggressive
from tcg.players.anti_ml_player import AntiMLPlayer
from tcg.players.strategy_economist_aggressive import EconomistAggressive
from tcg.players.strategy_right_heavy_aggressive import RightHeavyAggressive
from tcg.players.strategy_right_flank import RightFlankExpansionist
from tcg.players.strategy_aggressive_center import AggressiveCenterStrategy 

def mask_fn(env: DefensiveTCGEnv) -> list[bool]:
    return env.action_masks()

def train_defensive():
    # Set number of threads to 1 for CPU efficiency in parallel environments
    torch.set_num_threads(1)

    # Create log dir
    log_dir = "logs_defensive/"
    os.makedirs(log_dir, exist_ok=True)

    # Define the opponents
    # We want TrainedCounterPlayer to be selected 30% of the time, and others 10% each.
    others = [
        RightFlankAggressive,
        SecureHomeAggressive,
        AntiMLPlayer,
        EconomistAggressive,
        RightHeavyAggressive,
        RightFlankExpansionist,
        AggressiveCenterStrategy
    ]
    
    opponent_classes = [TrainedCounterPlayer] * 3 + others
    
    print(f"Training against (Weighted): {[p.__name__ for p in opponent_classes]}")

    # Create the environment
    def make_env():
        # Set number of threads to 1 for subprocesses
        import torch
        torch.set_num_threads(1)
        
        # Use the DefensiveTCGEnv with shaped rewards
        env = DefensiveTCGEnv(opponent_classes)
        env = ActionMasker(env, mask_fn)
        return env

    # Use 8 parallel environments for speed (CPU count is 8)
    from stable_baselines3.common.vec_env import SubprocVecEnv
    env = make_vec_env(make_env, n_envs=8, vec_env_cls=SubprocVecEnv)

    # Initialize the agent
    print("Starting training from scratch (Defensive Strategy).")
    policy_kwargs = dict(net_arch=[256, 256])
    model = MaskablePPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        tensorboard_log=log_dir,
        learning_rate=0.0001,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        policy_kwargs=policy_kwargs
    )

    # Save checkpoints
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=log_dir,
        name_prefix="defensive_model"
    )

    print("Starting training...")
    # Train for a reasonable amount of steps
    model.learn(total_timesteps=50000000, callback=checkpoint_callback)
    
    # Save final model
    model.save("defensive_final")
    print("Training complete. Model saved to defensive_final.zip")

if __name__ == "__main__":
    train_defensive()
