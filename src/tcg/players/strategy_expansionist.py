
import random
from tcg.controller import Controller
from tcg.config import fortress_limit

class RapidExpansionist(Controller):
    """
    急速拡大戦略 (Rapid Expansion Strategy):
    - 中立の砦（Neutral Fortresses）の確保を最優先します。
    - 敵よりも早く砦数を増やすことを目指します。
    - 中立砦が隣接している場合、積極的に兵を送ります。
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
            target_pawns = state[n][3]
            
            # 自陣の砦の兵数/2 > 攻撃対象の砦なら攻撃
            if total_attack_force > target_pawns:
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
                    # Reinforce random ally
                    return 1, i, random.choice(allies)
        
        return 0, 0, 0
