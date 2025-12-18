
import random
import math
from tcg.controller import Controller
from tcg.config import fortress_limit, pos_fortress, fortress_cool

class AntiMLPlayer(Controller):
    """
    Strategy designed to beat MLPlayer based on RightFlankAggressive.
    Key features:
    1. Right Flank Focus (proven effective).
    2. Aggressive Snipe on weak enemies.
    3. Opportunistic Attack on Upgrading enemies (ML might be upgrading greedily).
    """
    def team_name(self) -> str:
        return "AntiMLPlayer"

    # Importance Map (Right Flank Focus)
    FORTRESS_IMPORTANCE_UPPER = {
        0: 2, 1: 4, 2: 12,     # Top
        3: 4, 4: 12, 5: 12,    # Mid-Top
        6: 4, 7: 12, 8: 12,    # Mid-Bottom
        9: 2, 10: 4, 11: 12    # Bottom
    }
    
    FORTRESS_IMPORTANCE_LOWER = {
        0: 2, 1: 4, 2: 12,
        3: 4, 4: 12, 5: 12,
        6: 4, 7: 12, 8: 12,
        9: 2, 10: 4, 11: 12
    }

    def get_importance(self, fort_id, my_side):
        if my_side == "upper":
            return self.FORTRESS_IMPORTANCE_UPPER[fort_id]
        else:
            return self.FORTRESS_IMPORTANCE_LOWER[fort_id]

    def estimate_travel_steps(self, from_id, to_id):
        p1 = pos_fortress[from_id]
        p2 = pos_fortress[to_id]
        dist = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        travel_dist = max(0, dist - 87)
        return int(travel_dist / 1.5)

    def predict_future_pawns(self, fort_id, steps, state):
        team, kind, level, pawn_number, upgrade_timer, _ = state[fort_id]
        limit = fortress_limit[level]
        
        if team == 1: # My team (shouldn't happen for enemy prediction but ok)
            return pawn_number 
            
        # If upgrading, they don't produce troops until upgrade finishes
        if upgrade_timer != -1:
            remaining_upgrade = upgrade_timer
            if steps < remaining_upgrade:
                return pawn_number # No production
            else:
                # Upgrade finishes, then production starts at new level
                # This is complex, simplified: assume no production during upgrade
                # and production at current level after (underestimate enemy strength is risky, but ok for aggression)
                # Better: assume production resumes after upgrade
                steps_after = steps - remaining_upgrade
                # New level
                new_level = level + 1
                if new_level > 5: new_level = 5 # Should not happen if upgrading
                new_cool = fortress_cool[kind][new_level]
                new_limit = fortress_limit[new_level]
                produced = steps_after // new_cool
                return min(new_limit, pawn_number + produced)
        
        cool = fortress_cool[kind][level]
        produced = steps // cool
        return min(limit, pawn_number + produced)

    def update(self, info):
        team_id, state, moving_pawns, spawning_pawns, done = info
        
        # Determine my side
        upper_count = sum(1 for i in [0, 1, 2] if state[i][0] == 1)
        lower_count = sum(1 for i in [9, 10, 11] if state[i][0] == 1)
        
        if upper_count > lower_count:
            my_side = "upper"
        else:
            my_side = "lower"
            
        # --- Aggressive Snipe & Anti-Upgrade Logic ---
        my_fortresses = [i for i, s in enumerate(state) if s[0] == 1]
        # Sort my fortresses by pawn count (desc) to use strongest first
        my_fortresses.sort(key=lambda x: state[x][3], reverse=True)
        
        for i in my_fortresses:
            neighbors = state[i][5]
            enemies = [n for n in neighbors if state[n][0] == 2]
            
            for enemy in enemies:
                steps = self.estimate_travel_steps(i, enemy)
                pred_enemy = self.predict_future_pawns(enemy, steps, state)
                
                my_pawns = state[i][3]
                attack_force = my_pawns // 2
                
                # 1. Attack Upgrading Enemies (High Priority)
                if state[enemy][4] != -1:
                    # If we can beat them, attack immediately!
                    if attack_force > pred_enemy + 1:
                        return 1, i, enemy
                        
                # 2. Attack Weak Enemies (Snipe)
                # Threshold: Enemy has < 5 troops (or < 10 if we are very strong)
                if pred_enemy < 8 and attack_force > (pred_enemy + 3):
                    return 1, i, enemy

        # --- Standard Expansion (Right Flank Focus) ---
        
        # Identify targets (Neutrals or Enemies)
        targets = [i for i, s in enumerate(state) if s[0] != 1]
        # Sort by importance
        targets.sort(key=lambda x: self.get_importance(x, my_side), reverse=True)
        
        for t in targets:
            neighbors = state[t][5]
            my_neighbors = [m for m in neighbors if state[m][0] == 1]
            
            if not my_neighbors:
                continue
                
            # Check if we can capture with coordinated attack
            total_force = sum(state[m][3] // 2 for m in my_neighbors)
            max_steps = max(self.estimate_travel_steps(m, t) for m in my_neighbors)
            pred_target = self.predict_future_pawns(t, max_steps, state)
            
            if total_force > pred_target + 2: # +2 buffer
                # Attack with strongest neighbor
                my_neighbors.sort(key=lambda x: state[x][3], reverse=True)
                attacker = my_neighbors[0]
                if state[attacker][3] > 1:
                    return 1, attacker, t
                    
        # --- Upgrade Logic ---
        # Only upgrade if safe and rich
        for i in my_fortresses:
            level = state[i][2]
            pawn_count = state[i][3]
            limit = fortress_limit[level]
            upgrade_cost = limit // 2
            is_upgrading = state[i][4] != -1
            
            # Prioritize upgrading important fortresses
            importance = self.get_importance(i, my_side)
            
            if level < 5 and not is_upgrading and pawn_count >= upgrade_cost:
                # If important, upgrade sooner
                if importance >= 12 or pawn_count >= limit * 0.8:
                    return 2, i, 0
                    
        # --- Reinforce / Attack Weakest ---
        for i in my_fortresses:
            pawn_count = state[i][3]
            limit = fortress_limit[state[i][2]]
            
            if pawn_count > limit * 0.8:
                neighbors = state[i][5]
                enemies = [n for n in neighbors if state[n][0] == 2]
                if enemies:
                    enemies.sort(key=lambda x: state[x][3])
                    return 1, i, enemies[0]
                
                # Reinforce front line
                allies = [n for n in neighbors if state[n][0] == 1]
                front_line = [a for a in allies if any(state[n][0] == 2 for n in state[a][5])]
                if front_line:
                    return 1, i, front_line[0]

        return 0, 0, 0
