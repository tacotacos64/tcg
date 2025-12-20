import os
import sys
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import VecNormalize

from tcg.counter_gym_env import CounterTCGEnv
from tcg.players.player_kishida_mlppo import MLPlayer
from tcg.players.player_kishida_counter import ONCT
from tcg.players.strategy_right_flank_aggressive import RightFlankAggressive
from tcg.players.strategy_secure_home_aggressive import SecureHomeAggressive
from tcg.players.anti_ml_player import AntiMLPlayer
from tcg.players.strategy_economist_aggressive import EconomistAggressive
from tcg.players.strategy_right_heavy_aggressive import RightHeavyAggressive
from tcg.players.strategy_right_flank import RightFlankExpansionist
from tcg.players.strategy_aggressive_center import AggressiveCenterStrategy 
from tcg.players.strategy_economist import DefensiveEconomist
from tcg.players.strategy_secure_home import SecureHomeExpansionist

def mask_fn(env: CounterTCGEnv) -> list[bool]:
    return env.action_masks()

def linear_schedule(initial_value: float):
    """
    Linear learning rate schedule.
    :param initial_value: Initial learning rate.
    :return: schedule function.
    """
    def func(progress_remaining: float):
        """
        Progress will decrease from 1 (beginning) to 0.
        :param progress_remaining:
        :return: current learning rate
        """
        return progress_remaining * initial_value
    return func

def train_counter():
    # Set number of threads to 1 for CPU efficiency in parallel environments
    torch.set_num_threads(1)

    # Create log dir
    log_dir = "logs_counter/"
    os.makedirs(log_dir, exist_ok=True)

    # Define the opponents
    # We want ML_PPO to be selected 30% of the time, and others 10% each.
    # Since gym_env uses random.choice(list), we can achieve this by adding MLPlayer multiple times.
    # Total 10 slots: 3 MLPlayer, 1 of each of the other 7.
    others = [
        RightFlankAggressive,
        SecureHomeAggressive,
        AntiMLPlayer,
        EconomistAggressive,
        RightHeavyAggressive,
        RightFlankExpansionist,
        AggressiveCenterStrategy,
        DefensiveEconomist,
        SecureHomeExpansionist
    ]
    
    opponent_classes = [MLPlayer] * 2 + [ONCT] * 2 + others
    
    print(f"Training against (Weighted): {[p.__name__ for p in opponent_classes]}")

    # Create the environment
    def make_env():
        # Set number of threads to 1 for subprocesses
        import torch
        torch.set_num_threads(1)
        
        # Use the CounterTCGEnv with shaped rewards
        env = CounterTCGEnv(opponent_classes)
        env = ActionMasker(env, mask_fn)
        return env

    # Use 8 parallel environments for speed (CPU count is 8)
    from stable_baselines3.common.vec_env import SubprocVecEnv
    env = make_vec_env(make_env, n_envs=8, vec_env_cls=SubprocVecEnv)
    
    # ★追加: 報酬と観測の正規化 (PPOの学習効率が劇的に上がることが多いです)
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)

    # Initialize the agent
    print("Starting training from scratch.")
    policy_kwargs = dict(net_arch=[512, 512, 512])
    model = MaskablePPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        tensorboard_log=log_dir,
        learning_rate=linear_schedule(0.0003),
        n_steps=8192,
        batch_size=512, # Reduced from 2048 to prevent generalization issues
        n_epochs=5,
        gamma=0.9,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.02,
        policy_kwargs=policy_kwargs
    )

    # Save checkpoints
    checkpoint_callback = CheckpointCallback(
        save_freq=100000, # Save every 100k steps
        save_path=log_dir,
        name_prefix="counter_ml_model"
    )

    print("Starting training (Fine-tuning)...")
    # Train for a reasonable amount of steps
    # 50M steps is a good start
    model.learn(total_timesteps=50000000, callback=checkpoint_callback)
    
    # Save final model
    model.save("counter_ml_final_ver4")
    print("Training complete. Model saved to counter_ml_final_ver4.zip")

if __name__ == "__main__":
    train_counter()
