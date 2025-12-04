
import os
import sys
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import CheckpointCallback

from tcg.gym_env import TCGEnv
from tcg.players.strategy_economist import DefensiveEconomist
from tcg.players.sample_random import RandomPlayer
from tcg.players.strategy_rusher import AggressiveRusher

def train():
    # Create log dir
    log_dir = "logs/"
    os.makedirs(log_dir, exist_ok=True)

    # Define the opponent. 
    # Ideally, we should mix opponents or use self-play.
    # For now, let's train against the strongest static strategy: Economist.
    # Or maybe start with Random to learn basics?
    # Let's use Economist as it is the target to beat.
    opponent_class = DefensiveEconomist

    # Create the environment
    # We wrap it in a DummyVecEnv for performance (though single env here)
    env = make_vec_env(lambda: TCGEnv(opponent_class), n_envs=1)

    # Initialize the agent
    model = PPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        tensorboard_log=log_dir,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
    )

    # Save a checkpoint every 10000 steps
    checkpoint_callback = CheckpointCallback(
        save_freq=10000, save_path='./models/', name_prefix='tcg_ppo'
    )

    print("Starting training...")
    # Train for a certain number of timesteps
    # 1 game is max 50000 steps, but with frame skip 40, it's 1250 steps per game.
    # 100,000 steps = approx 80 games.
    # 1,000,000 steps = approx 800 games.
    total_timesteps = 100000 
    
    model.learn(total_timesteps=total_timesteps, callback=checkpoint_callback)

    # Save the final model
    model.save("tcg_ppo_final")
    print("Training finished. Model saved to tcg_ppo_final.zip")

if __name__ == "__main__":
    train()
