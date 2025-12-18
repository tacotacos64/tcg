
import os
import sys
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import CheckpointCallback

from tcg.gym_env import TCGEnv
from tcg.players import discover_players

def mask_fn(env: TCGEnv) -> list[bool]:
    return env.action_masks()

def train():
    # Create log dir
    log_dir = "logs/"
    os.makedirs(log_dir, exist_ok=True)

    # Define the opponent. 
    # Use specific strong opponents including the new Aggressive variants
    all_players = discover_players()
    opponent_classes = []
    target_opponents = [
        # New Aggressive Strategies
        "AggressiveCenterStrategy",
        "SecureHomeAggressive",
        "ExpansionistAggressive",
        "RightFlankAggressive",
        "RightHeavyAggressive",
        "EconomistAggressive",
        # Original Strong Strategies
        "SecureHomeExpansionist",
        "RapidExpansionist",
        "RightFlankExpansionist",
        "RightHeavyExpansionist",
        "DefensiveEconomist",
        # Baselines
        "ClaudePlayer", 
        "RandomPlayer"
    ]
    
    for p in all_players:
        if p.__name__ in target_opponents:
            opponent_classes.append(p)
    
    if not opponent_classes:
        print("Warning: No target opponents found! Falling back to all available.")
        for p in all_players:
             if p.__name__ not in ["GymController", "MLPlayer"]:
                 opponent_classes.append(p)

    print(f"Training against {len(opponent_classes)} opponents: {[p.__name__ for p in opponent_classes]}")

    # Create the environment
    def make_env():
        env = TCGEnv(opponent_classes)
        env = ActionMasker(env, mask_fn)
        return env

    env = make_vec_env(make_env, n_envs=1)

    # Check for pretrained model
    pretrained_path = "tcg/players_kishida/tcg_ppo_pretrained.zip"
    # Force start from scratch to adapt to new normalized observation space
    if False and os.path.exists(pretrained_path):
        print(f"Loading pretrained model from {pretrained_path}")
        from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
        model = MaskablePPO.load(
            pretrained_path, 
            env=env,
            custom_objects={
                "policy_class": MaskableActorCriticPolicy,
                "learning_rate": 0.0003, # Reset LR if needed
                "lr_schedule": None # Reset schedule
            },
            print_system_info=True
        )
    else:
        print("No pretrained model found. Starting from scratch.")
        # Initialize the agent
        # Use a larger network architecture
        policy_kwargs = dict(net_arch=[256, 256])
        
        model = MaskablePPO(
            "MlpPolicy", 
            env, 
            verbose=1, 
            tensorboard_log=log_dir,
            learning_rate=0.00005, # Lower LR further
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.1, # More conservative clipping
            max_grad_norm=0.3, # Aggressive gradient clipping
            policy_kwargs=policy_kwargs
        )

    # Save a checkpoint every 50000 steps
    checkpoint_callback = CheckpointCallback(
        save_freq=50000, save_path='./models/', name_prefix='tcg_ppo'
    )

    print("Starting training...")
    # Train for a certain number of timesteps
    # 1 game is max 50000 steps, but with frame skip 40, it's 1250 steps per game.
    # 1,000,000 steps = approx 800-1000 games.
    total_timesteps = 1000000
    
    model.learn(total_timesteps=total_timesteps, callback=checkpoint_callback)

    # Save the final model
    model.save("src/tcg/players/player_kishida_mlppo/tcg_ppo_finetuned")
    print("Training finished. Model saved to tcg/players/player_kishida_mlppo/tcg_ppo_finetuned.zip")

if __name__ == "__main__":
    train()
