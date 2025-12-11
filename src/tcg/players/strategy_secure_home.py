
import random
import math
from tcg.controller import Controller
from tcg.config import fortress_limit, pos_fortress, fortress_cool

class SecureHomeExpansionist(Controller):
    """
    自陣確保・拡大戦略 (Secure Home Expansion Strategy):
    - Expansionistをベースにする。
    - 開幕、自陣の3つの砦（Home Base）の確保を最優先する。
    - 自陣の3つを確保したら、Expansionistと同様に中立砦の確保と拡大を行う。
    """
    def team_name(self) -> str:
        return "SecureHome"

    # 要塞の重要度（接続数と位置に基づく）
    # 上側(0,1,2)が自陣の場合の重要度
    FORTRESS_IMPORTANCE_UPPER = {
        0: 14, 1: 15, 2: 14,      # 上側エリア
        3: 10, 4: 12, 5: 10,     # 中央上
        6: 6, 7: 8, 8: 6,     # 中央下
        9: 3, 10: 4, 11: 3     # 下側エリア
    }
    
    # 下側(9,10,11)が自陣の場合の重要度（反転）
    FORTRESS_IMPORTANCE_LOWER = {
        0: 3, 1: 4, 2: 3,      # 上側エリア
        3: 6, 4: 8, 5: 6,     # 中央上
        6: 10, 7: 12, 8: 10,     # 中央下
        9: 14, 10: 15, 11: 14     # 下側エリア
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
        team, kind, level, pawn_number, _, _ = state[fort_id]
        limit = fortress_limit[level]
        
        # If it's neutral (team 0) or enemy (team 2), it produces pawns
        # Note: In this controller, we are always team 1.
        if team == 1:
            return pawn_number 
            
        cool = fortress_cool[kind][level]
        produced = steps // cool
        return min(limit, pawn_number + produced)

    def get_capture_time_estimate(self, my_idx, target_idx, state, upgrade=False):
        # My stats
        my_team, my_kind, my_level, my_pawns, my_upgrade_timer, _ = state[my_idx]
        
        # Target stats
        tgt_team, tgt_kind, tgt_level, tgt_pawns, _, _ = state[target_idx]
        
        limit_l = fortress_limit[my_level]
        cool_l = fortress_cool[my_kind][my_level]
        
        tgt_limit = fortress_limit[tgt_level]
        tgt_cool = fortress_cool[tgt_kind][tgt_level]
        
        dist_steps = self.estimate_travel_steps(my_idx, target_idx)
        
        current_time = 0
        sim_my_pawns = my_pawns
        sim_my_level = my_level
        sim_limit = limit_l
        sim_cool = cool_l
        
        # If upgrading
        if upgrade:
            if my_level >= 5:
                return float('inf')
            
            upgrade_cost = limit_l // 2
            
            # Time to start upgrade
            if sim_my_pawns < upgrade_cost:
                wait_steps = int((upgrade_cost - sim_my_pawns) * sim_cool)
                current_time += wait_steps
                sim_my_pawns = upgrade_cost 
            
            # Perform upgrade
            current_time += 200
            # Pawns produced during upgrade
            produced = 200 // sim_cool
            sim_my_pawns = (sim_my_pawns - upgrade_cost) + produced
            
            # Level up
            sim_my_level += 1
            sim_limit = fortress_limit[sim_my_level]
            sim_cool = fortress_cool[my_kind][sim_my_level]
            
        # Iterate to find earliest win time
        # We simulate pawn growth up to limit
        for p in range(int(sim_my_pawns), sim_limit + 1):
            wait_steps = int((p - sim_my_pawns) * sim_cool)
            arrival_time = current_time + wait_steps + dist_steps
            
            # Target prediction
            pred_tgt = min(tgt_limit, tgt_pawns + arrival_time // tgt_cool)
            
            if p // 2 > pred_tgt:
                return current_time + wait_steps
        
        return float('inf')

    def update(self, info):
        team_id, state, moving_pawns, spawning_pawns, done = info
        
        # Determine my side (Upper or Lower)
        upper_count = sum(1 for i in [0, 1, 2] if state[i][0] == 1)
        lower_count = sum(1 for i in [9, 10, 11] if state[i][0] == 1)
        
        if upper_count > lower_count:
            my_side = "upper"
            home_ids = [0, 1, 2]
        else:
            my_side = "lower"
            home_ids = [9, 10, 11]

        # --- Phase 1: Secure Home Base ---
        
        # 1.1 Secure missing home fortresses
        missing_home = [i for i in home_ids if state[i][0] != 1]
        if missing_home:
            # Try to attack missing home fortresses
            for target in missing_home:
                neighbors = state[target][5]
                my_neighbors = [m for m in neighbors if state[m][0] == 1]
                
                if not my_neighbors:
                    continue
                
                # 1. Check if we can attack NOW with coordinated force
                total_attack_force = sum(state[m][3] // 2 for m in my_neighbors)
                max_steps = max(self.estimate_travel_steps(m, target) for m in my_neighbors)
                target_future_pawns = self.predict_future_pawns(target, max_steps, state)
                
                if total_attack_force > target_future_pawns:
                    # Attack!
                    my_neighbors.sort(key=lambda x: state[x][3], reverse=True)
                    attacker = my_neighbors[0]
                    if state[attacker][3] > 1:
                        return 1, attacker, target
                
                # 2. If we cannot attack now, decide whether to Wait or Upgrade
                # We check the primary neighbor (most troops)
                my_neighbors.sort(key=lambda x: state[x][3], reverse=True)
                primary = my_neighbors[0]
                
                time_wait = self.get_capture_time_estimate(primary, target, state, upgrade=False)
                time_upgrade = self.get_capture_time_estimate(primary, target, state, upgrade=True)
                
                if time_upgrade < time_wait:
                    # Upgrade is faster (or necessary if wait is infinite)
                    limit = fortress_limit[state[primary][2]]
                    upgrade_cost = limit // 2
                    if state[primary][3] >= upgrade_cost and state[primary][4] == -1:
                        return 2, primary, 0
                    else:
                        # Wait for resources to upgrade
                        return 0, 0, 0
                else:
                    # Wait is faster (or both infinite)
                    # If both infinite, we might need coordinated wait, so we wait.
                    return 0, 0, 0

        # --- Phase 2: Standard Expansionist Logic ---
        
        # 2.1 Priority: Capture Neutrals with Coordinated Attack
        neutrals = [i for i, s in enumerate(state) if s[0] == 0 and i not in home_ids] # Exclude home_ids as we handled them
        # Sort by importance (desc), then pawn count (asc)
        neutrals.sort(key=lambda x: (-self.get_importance(x, my_side), state[x][3]))
        
        for n in neutrals:
            neighbors = state[n][5]
            my_neighbors = [m for m in neighbors if state[m][0] == 1]
            
            if not my_neighbors:
                continue
                
            # Calculate total available attacking force
            total_attack_force = sum(state[m][3] // 2 for m in my_neighbors)
            
            max_steps = max(self.estimate_travel_steps(m, n) for m in my_neighbors)
            target_future_pawns = self.predict_future_pawns(n, max_steps, state)
            
            if total_attack_force > target_future_pawns:
                # Attack!
                my_neighbors.sort(key=lambda x: state[x][3], reverse=True)
                attacker = my_neighbors[0]
                
                if state[attacker][3] > 1:
                    return 1, attacker, n

        # 2.2 Secondary: Upgrade or other actions
        my_fortresses = [i for i, s in enumerate(state) if s[0] == 1]
        random.shuffle(my_fortresses)
        
        for i in my_fortresses:
            pawn_count = state[i][3]
            level = state[i][2]
            limit = fortress_limit[level]
            upgrade_cost = limit // 2
            is_upgrading = state[i][4] != -1
            
            # Upgrade if cheap and safe
            if level < 5 and not is_upgrading and pawn_count >= upgrade_cost:
                 return 2, i, 0

            # 2.3 Tertiary: Attack Weak Enemies or Reinforce
            neighbors = state[i][5]
            enemies = [n for n in neighbors if state[n][0] == 2]
            allies = [n for n in neighbors if state[n][0] == 1]
            
            # 兵力が溢れそうな場合は敵を攻撃または味方を支援
            if pawn_count > limit * 0.8:
                if enemies:
                    # Attack weakest enemy
                    enemies.sort(key=lambda x: state[x][3])
                    return 1, i, enemies[0]
                elif allies:
                    # Reinforce ally
                    # Priority 1: Allies under attack
                    under_attack = set()
                    for p in moving_pawns:
                        if p[0] == 2 and p[3] in allies:
                            under_attack.add(p[3])
                    
                    front_line = [a for a in allies if any(state[n][0] == 2 for n in state[a][5])]
                    
                    target = None
                    if under_attack:
                        target = min(under_attack, key=lambda x: state[x][3])
                    elif front_line:
                        target = min(front_line, key=lambda x: state[x][3])
                    else:
                        target = random.choice(allies)
                        
                    return 1, i, target
        
        return 0, 0, 0
