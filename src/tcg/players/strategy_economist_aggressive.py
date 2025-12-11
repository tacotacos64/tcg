import random
import math
from tcg.controller import Controller
from tcg.config import fortress_limit, pos_fortress, fortress_cool

class EconomistAggressive(Controller):
    """
    Economist + Aggressive Snipe
    """
    def team_name(self) -> str:
        return "EconomistAggressive"

    def estimate_travel_steps(self, from_id, to_id):
        p1 = pos_fortress[from_id]
        p2 = pos_fortress[to_id]
        dist = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        travel_dist = max(0, dist - 87)
        return int(travel_dist / 1.5)

    def predict_future_pawns(self, fort_id, steps, state):
        team, kind, level, pawn_number, _, _ = state[fort_id]
        limit = fortress_limit[level]
        if team == 1: return pawn_number 
        cool = fortress_cool[kind][level]
        produced = steps // cool
        return min(limit, pawn_number + produced)

    def update(self, info):
        team_id, state, moving_pawns, spawning_pawns, done = info
        
        # --- Aggressive Snipe Logic (Added) ---
        my_fortresses = [i for i, s in enumerate(state) if s[0] == 1]
        random.shuffle(my_fortresses)
        for i in my_fortresses:
            neighbors = state[i][5]
            enemies = [n for n in neighbors if state[n][0] == 2]
            for enemy in enemies:
                steps = self.estimate_travel_steps(i, enemy)
                pred_enemy = self.predict_future_pawns(enemy, steps, state)
                if pred_enemy < 5 and (state[i][3] // 2) > (pred_enemy + 2):
                    return 1, i, enemy

        # Standard Economist Logic
        my_fortresses = [i for i, s in enumerate(state) if s[0] == 1]
        random.shuffle(my_fortresses)
        
        for i in my_fortresses:
            level = state[i][2]
            pawn_count = state[i][3]
            limit = fortress_limit[level]
            upgrade_cost = limit // 2
            is_upgrading = state[i][4] != -1
            
            # 1. Try to upgrade if not max level and not currently upgrading
            if level < 5 and not is_upgrading:
                if pawn_count >= upgrade_cost:
                    return 2, i, 0
            
            # 2. If full (or close to full), attack/expand
            if pawn_count >= limit * 0.9:
                neighbors = state[i][5]
                enemies = [n for n in neighbors if state[n][0] == 2]
                neutrals = [n for n in neighbors if state[n][0] == 0]
                allies = [n for n in neighbors if state[n][0] == 1]
                
                target = None
                if enemies:
                    enemies.sort(key=lambda x: state[x][3])
                    target = enemies[0]
                elif neutrals:
                    neutrals.sort(key=lambda x: state[x][3])
                    target = neutrals[0]
                elif allies:
                    allies.sort(key=lambda x: state[x][3] / fortress_limit[state[x][2]])
                    target = allies[0]
                
                if target is not None:
                    return 1, i, target

        return 0, 0, 0
