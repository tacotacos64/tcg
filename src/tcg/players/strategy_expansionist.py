
import random
import math
from tcg.controller import Controller
from tcg.config import fortress_limit, pos_fortress, fortress_cool

class RapidExpansionist(Controller):
    """
    急速拡大戦略 (Rapid Expansion Strategy):
    - 中立の砦（Neutral Fortresses）の確保を最優先します。
    - 敵よりも早く砦数を増やすことを目指します。
    - 中立砦が隣接している場合、積極的に兵を送ります。
    - 攻撃時は相手の生産速度も考慮して、確実に勝てる場合のみ攻撃します。
    - 支援時は攻撃を受けている砦や前線を優先します。
    """
    def team_name(self) -> str:
        return "Expansionist"

    # 要塞の重要度（接続数と位置に基づく）
    # 上側(0,1,2)が自陣の場合の重要度
    FORTRESS_IMPORTANCE_UPPER = {
        0: 14, 1: 15, 2: 14,      # 上側エリア
        3: 10, 4: 12, 5: 10,     # 中央上
        6: 6, 7: 8, 8: 9,     # 中央下
        9: 3, 10: 4, 11: 3     # 下側エリア
    }
    
    # 下側(9,10,11)が自陣の場合の重要度（反転）
    FORTRESS_IMPORTANCE_LOWER = {
        0: 3, 1: 4, 2: 3,      # 上側エリア
        3: 9, 4: 8, 5: 6,     # 中央上
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
        # Speed is 1.5. Start offset 42, End offset 45.
        # Travel distance approx dist - 87.
        # But let's be conservative and just use dist / 1.5
        # Actually, game logic:
        # Spawn at 42 from center. Arrive at 45 from center.
        # So travel is roughly dist - 87.
        travel_dist = max(0, dist - 87)
        return int(travel_dist / 1.5)

    def predict_future_pawns(self, fort_id, steps, state):
        team, kind, level, pawn_number, _, _ = state[fort_id]
        limit = fortress_limit[level]
        
        # If it's neutral (team 0) or enemy (team 2), it produces pawns
        # Note: In this controller, we are always team 1.
        if team == 1:
            return pawn_number # Should not happen for attack target
            
        cool = fortress_cool[kind][level]
        produced = steps // cool
        return min(limit, pawn_number + produced)

    def update(self, info):
        team_id, state, moving_pawns, spawning_pawns, done = info
        
        # Determine my side (Upper or Lower)
        upper_count = sum(1 for i in [0, 1, 2] if state[i][0] == 1)
        lower_count = sum(1 for i in [9, 10, 11] if state[i][0] == 1)
        
        if upper_count > lower_count:
            my_side = "upper"
        else:
            my_side = "lower"

        # 1. Priority: Capture Neutrals with Coordinated Attack
        neutrals = [i for i, s in enumerate(state) if s[0] == 0]
        # Sort by importance (desc), then pawn count (asc)
        neutrals.sort(key=lambda x: (-self.get_importance(x, my_side), state[x][3]))
        
        for n in neutrals:
            neighbors = state[n][5]
            my_neighbors = [m for m in neighbors if state[m][0] == 1]
            
            if not my_neighbors:
                continue
                
            # Calculate total available attacking force from all connected friendly fortresses
            total_attack_force = sum(state[m][3] // 2 for m in my_neighbors)
            
            # Calculate max travel time to ensure we beat the production
            max_steps = 0
            if my_neighbors:
                max_steps = max(self.estimate_travel_steps(m, n) for m in my_neighbors)
            
            target_future_pawns = self.predict_future_pawns(n, max_steps, state)
            
            # 自陣の砦の兵数/2 > 攻撃対象の砦(将来)なら攻撃
            if total_attack_force > target_future_pawns:
                # Attack!
                # Choose the neighbor with the most troops to attack first
                my_neighbors.sort(key=lambda x: state[x][3], reverse=True)
                attacker = my_neighbors[0]
                
                # Ensure the attacker actually has troops to send
                if state[attacker][3] > 1:
                    return 1, attacker, n

        # 2. Secondary: Upgrade or other actions
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

            # 3. Tertiary: Attack Weak Enemies or Reinforce
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
                        # p: [team, kind, from, to, pos]
                        # If enemy (team 2) is moving to an ally
                        if p[0] == 2 and p[3] in allies:
                            under_attack.add(p[3])
                    
                    # Priority 2: Front-line allies (have enemy neighbors)
                    front_line = [a for a in allies if any(state[n][0] == 2 for n in state[a][5])]
                    
                    target = None
                    if under_attack:
                        # Prioritize the one with lowest troops among those under attack
                        target = min(under_attack, key=lambda x: state[x][3])
                    elif front_line:
                        # Prioritize front line with lowest troops
                        target = min(front_line, key=lambda x: state[x][3])
                    else:
                        # Random ally
                        target = random.choice(allies)
                        
                    return 1, i, target
        
        return 0, 0, 0
