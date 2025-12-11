
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
        # Check ownership of starting fortresses to guess side
        # Upper starts at 0,1,2. Lower starts at 9,10,11.
        # But in this game, usually Player 1 is Bottom (Lower) and Player 2 is Top (Upper)?
        # Let's check based on current ownership of "home base" areas if possible, 
        # or just assume based on team_id if we knew the map layout.
        # However, the map is symmetric. Let's infer from initial state or current state.
        # If I own any of 9,10,11, I'm likely Lower side. If I own 0,1,2, I'm Upper.
        # If I own both, it's mixed. Let's count.
        
        upper_count = sum(1 for i in [0, 1, 2] if state[i][0] == 1)
        lower_count = sum(1 for i in [9, 10, 11] if state[i][0] == 1)
        
        if upper_count > lower_count:
            my_side = "upper"
        else:
            my_side = "lower" # Default to lower if equal or more lower

        # My fortresses
        my_fortresses = [i for i, s in enumerate(state) if s[0] == 1]
        random.shuffle(my_fortresses) # Randomize order to avoid bias
        
        for i in my_fortresses:
            pawn_count = state[i][3]
            neighbors = state[i][5]
            
            # Identify targets
            neutrals = [n for n in neighbors if state[n][0] == 0]
            enemies = [n for n in neighbors if state[n][0] == 2]
            allies = [n for n in neighbors if state[n][0] == 1]
            
            level = state[i][2]
            limit = fortress_limit[level]
            upgrade_cost = limit // 2
            is_upgrading = state[i][4] != -1

            # 1. Priority: Capture Neutrals
            if neutrals:
                best_target = None
                # 重要度が高い順、次に兵数が少ない順にソート
                # Sort key: (-importance, pawn_count)
                neutrals.sort(key=lambda x: (-self.get_importance(x, my_side), state[x][3]))
                
                for n in neutrals:
                    target_pawns = state[n][3]
                    # 攻撃に行けるのは砦にいる兵士の半分
                    # 自陣の砦の兵数/2 > 攻撃対象の砦なら攻撃
                    if (pawn_count // 2) > target_pawns:
                        best_target = n
                        break
                
                if best_target is not None:
                    return 1, i, best_target
                
                # 攻撃できない場合はレベルアップに努める
                if level < 5 and not is_upgrading and pawn_count >= upgrade_cost:
                    return 2, i, 0
                
                # 中立砦があるが攻撃もアップグレードもできない場合は待機
                continue
            
            # 2. Secondary: Upgrade if cheap and safe (No neutrals nearby)
            if level < 5 and not is_upgrading and pawn_count >= upgrade_cost:
                 return 2, i, 0

            # 3. Tertiary: Attack Weak Enemies or Reinforce
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
