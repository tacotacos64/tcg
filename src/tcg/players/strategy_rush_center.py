"""
Rush Center Strategy Player

波状攻撃と後方支援を活用して中央の砦（砦7と砦4）の制圧を目指す戦略
"""

from tcg.config import fortress_limit, A_coordinate
from tcg.controller import Controller


class RushCenterPlayer(Controller):
    """
    Rush Center Strategy (Advanced):
    - 連続攻撃：同じ目標に複数回攻撃（兵数2以上あれば攻撃）
    - 波状攻撃：複数の隣接砦から同時集中攻撃
    - 後方支援：非隣接砦から隣接砦へ兵を送り、兵力回復を加速
    """

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.current_target = None      # 現在攻撃中の目標砦
        self.attack_sources = []        # 攻撃参加中の砦リスト（波状攻撃用）
        self.support_mode = False       # 後方支援モード

    def team_name(self):
        return "RushCenter"

    def update(self, info) -> tuple[int, int, int]:
        self.team, self.state, self.moving_pawns, self.spawning_pawns, self.done = info
        self.step += 1

        # 自分の砦と敵の砦を特定
        my_fortresses = [i for i in range(12) if self.state[i][0] == self.team]
        enemy_fortresses = [i for i in range(12) if self.state[i][0] != 0 and self.state[i][0] != self.team]
        neutral_fortresses = [i for i in range(12) if self.state[i][0] == 0]
        
        if not my_fortresses:
            return 0, 0, 0

        # 波状攻撃の継続チェック
        if self.current_target is not None:
            # 目標が制圧されたか確認
            if self.state[self.current_target][0] == self.team:
                self.current_target = None
                self.attack_sources = []
                self.support_mode = False
            else:
                # 波状攻撃：隣接する全ての砦から攻撃
                for fort in my_fortresses:
                    if fort in self.attack_sources or A_coordinate[fort][self.current_target] != 0:
                        if self.state[fort][3] >= 2:
                            return 1, fort, self.current_target
                
                # 後方支援：目標に隣接する自分の砦へ兵を送る
                if self.support_mode:
                    adjacent_my_forts = [f for f in my_fortresses if A_coordinate[f][self.current_target] != 0]
                    if adjacent_my_forts:
                        # 一番兵が少ない隣接砦を探す
                        target_support = min(adjacent_my_forts, key=lambda f: self.state[f][3])
                        # 隣接していない砦から支援を送る
                        for fort in my_fortresses:
                            if fort not in adjacent_my_forts and self.state[fort][3] >= 10:
                                # target_supportに隣接しているか確認
                                if A_coordinate[fort][target_support] != 0:
                                    return 1, fort, target_support
                
                # どこからも攻撃できない場合、目標リセット
                self.current_target = None
                self.attack_sources = []
                self.support_mode = False

        # 目標砦の状態確認
        fortress_7_owned = self.state[7][0] == self.team
        fortress_4_owned = self.state[4][0] == self.team
        
        # 自分の総戦力を計算
        total_power = sum(self.state[f][3] for f in my_fortresses)
        
        # Phase 0: 初期ブースト - 最初の砦を強化して生産力を上げる
        if len(my_fortresses) == 1:
            fort = my_fortresses[0]
            level = self.state[fort][2]
            pawns = self.state[fort][3]
            upgrade_time = self.state[fort][4]
            
            # 部隊が20以上溜まったら攻撃開始（連続攻撃で制圧）
            if pawns >= 20:
                neighbors = self.state[fort][5]
                # Lv1の中立砦を優先
                for neighbor in neighbors:
                    if neighbor in neutral_fortresses and self.state[neighbor][2] == 1:
                        self.current_target = neighbor
                        self.attack_sources = [fort]
                        return 1, fort, neighbor
                
                # Lv2の中立砦も攻撃対象（30部隊以上で）
                if pawns >= 30:
                    for neighbor in neighbors:
                        if neighbor in neutral_fortresses:
                            self.current_target = neighbor
                            self.attack_sources = [fort]
                            return 1, fort, neighbor
            
            # 攻撃できる相手がいない、またはまだ兵が足りない場合、アップグレード
            # Lv2→Lv3へアップグレード（コスト10）
            if level == 2 and upgrade_time == -1 and pawns >= 15:
                return 2, fort, fort
            
            # Lv3→Lv4へアップグレード（コスト15）
            if level == 3 and upgrade_time == -1 and pawns >= 20:
                return 2, fort, fort
            
            # それ以外は待機（部隊を溜める）
            return 0, 0, 0
        
        # Phase 1: 序盤 - 経済基盤を拡大（波状攻撃）
        # 砦数が2個以下、または総戦力が50未満の場合のみ
        if len(my_fortresses) <= 2 or total_power < 50:
            # まず、低レベルの自分の砦をアップグレード
            for fort in my_fortresses:
                level = self.state[fort][2]
                pawns = self.state[fort][3]
                upgrade_time = self.state[fort][4]
                
                # Lv3以下の砦を優先的にアップグレード
                if level <= 3 and upgrade_time == -1:
                    cost = fortress_limit[level] // 2
                    # アップグレード後も10部隊以上残るなら実行
                    if pawns >= cost + 10:
                        return 2, fort, fort
            
            # 中立砦への波状攻撃を準備
            # 各中立砦に対して、隣接する自分の砦の数と総兵力をチェック
            best_target = None
            best_attackers = []
            best_total_power = 0
            
            for neutral in neutral_fortresses:
                adjacent_attackers = [f for f in my_fortresses if A_coordinate[f][neutral] != 0 and self.state[f][3] >= 10]
                if adjacent_attackers:
                    total_attack_power = sum(self.state[f][3] for f in adjacent_attackers)
                    # 複数の砦から攻撃できる目標を優先
                    if len(adjacent_attackers) > len(best_attackers) or \
                       (len(adjacent_attackers) == len(best_attackers) and total_attack_power > best_total_power):
                        best_target = neutral
                        best_attackers = adjacent_attackers
                        best_total_power = total_attack_power
            
            # 波状攻撃を開始
            if best_target is not None and best_total_power >= 20:
                self.current_target = best_target
                self.attack_sources = best_attackers
                self.support_mode = True  # 後方支援も有効化
                # 最も兵が多い砦から攻撃開始
                best_attacker = max(best_attackers, key=lambda f: self.state[f][3])
                return 1, best_attacker, best_target
        
        # Phase 2: 中盤 - 砦7への積極的攻撃（速攻重視）
        elif not fortress_7_owned:
            # 砦7に隣接する砦: 3, 4, 5, 6, 9, 10, 11
            adjacent_to_7 = [3, 4, 5, 6, 9, 10, 11]
            my_adjacent = [f for f in my_fortresses if f in adjacent_to_7]
            
            # 波状攻撃：低い閾値で即座に攻撃開始（速攻重視）
            attackers = [f for f in my_adjacent if self.state[f][3] >= 10]
            total_attack_power = sum(self.state[f][3] for f in attackers)
            
            # 総兵力20以上で攻撃開始（大幅に閾値を下げる）
            if total_attack_power >= 20:
                self.current_target = 7
                self.attack_sources = attackers
                self.support_mode = True
                # 最も兵が多い砦から攻撃開始
                best_attacker = max(attackers, key=lambda f: self.state[f][3])
                return 1, best_attacker, 7
            
            # 後方支援：隣接砦へ兵を送って攻撃力を上げる
            if my_adjacent:
                weakest_adjacent = min(my_adjacent, key=lambda f: self.state[f][3])
                # 隣接していない砦から支援
                for fort in my_fortresses:
                    if fort not in my_adjacent and self.state[fort][3] >= 12:
                        if A_coordinate[fort][weakest_adjacent] != 0:
                            return 1, fort, weakest_adjacent
            
            # 隣接砦を確保（砦7攻略と並行して進める）
            for neutral in [n for n in neutral_fortresses if n in adjacent_to_7]:
                attackers = [f for f in my_fortresses if A_coordinate[f][neutral] != 0 and self.state[f][3] >= 8]
                if attackers:
                    self.current_target = neutral
                    self.attack_sources = attackers
                    self.support_mode = False  # 隣接砦確保時は支援なし（速度重視）
                    best_attacker = max(attackers, key=lambda f: self.state[f][3])
                    return 1, best_attacker, neutral
            
            # アップグレードは最小限に（速攻重視）
            for fort in my_adjacent:
                level = self.state[fort][2]
                pawns = self.state[fort][3]
                upgrade_time = self.state[fort][4]
                
                # Lv2以下の砦のみアップグレード
                if level <= 2 and upgrade_time == -1:
                    cost = fortress_limit[level] // 2
                    if pawns >= cost + 8:
                        return 2, fort, fort
            
            # 周辺の弱い砦を確保（最小限）
            for fort in my_fortresses:
                if self.state[fort][3] >= 12:
                    neighbors = self.state[fort][5]
                    for neighbor in neighbors:
                        if neighbor in neutral_fortresses and self.state[neighbor][2] == 1:
                            self.current_target = neighbor
                            self.attack_sources = [fort]
                            return 1, fort, neighbor
        
        # Phase 3: 砦7確保後、砦4への波状攻撃と後方支援
        elif fortress_7_owned and not fortress_4_owned:
            # 砦4に隣接する砦: 0, 1, 2, 3, 5, 6, 7, 8
            adjacent_to_4 = [0, 1, 2, 3, 5, 6, 7, 8]
            my_adjacent = [f for f in my_fortresses if f in adjacent_to_4]
            
            # 後方支援：隣接砦へ兵を送る
            if my_adjacent:
                weakest_adjacent = min(my_adjacent, key=lambda f: self.state[f][3])
                # 隣接していない砦から支援
                for fort in my_fortresses:
                    if fort not in my_adjacent and self.state[fort][3] >= 15:
                        if A_coordinate[fort][weakest_adjacent] != 0:
                            return 1, fort, weakest_adjacent
            
            # 波状攻撃：複数の隣接砦から同時攻撃
            attackers = [f for f in my_adjacent if self.state[f][3] >= 15]
            total_attack_power = sum(self.state[f][3] for f in attackers)
            
            if total_attack_power >= 30:
                self.current_target = 4
                self.attack_sources = attackers
                self.support_mode = True
                best_attacker = max(attackers, key=lambda f: self.state[f][3])
                return 1, best_attacker, 4
            
            # まだ戦力が足りない場合、アップグレード
            for fort in my_adjacent:
                level = self.state[fort][2]
                pawns = self.state[fort][3]
                upgrade_time = self.state[fort][4]
                
                if level < 4 and upgrade_time == -1:
                    cost = fortress_limit[level] // 2
                    if pawns >= cost + 10:
                        return 2, fort, fort
        
        # Phase 4: 両方確保したら、防衛・アップグレード・拡張
        else:
            # 中央砦（7, 4）を最高レベルまでアップグレード
            for fort in [7, 4]:
                if fort in my_fortresses:
                    level = self.state[fort][2]
                    pawns = self.state[fort][3]
                    upgrade_time = self.state[fort][4]
                    
                    if level < 5 and upgrade_time == -1:
                        cost = fortress_limit[level] // 2
                        if pawns >= cost:
                            return 2, fort, fort
            
            # 他の砦もアップグレード
            for fort in my_fortresses:
                level = self.state[fort][2]
                pawns = self.state[fort][3]
                upgrade_time = self.state[fort][4]
                
                if level < 5 and upgrade_time == -1:
                    cost = fortress_limit[level] // 2
                    if pawns >= cost + 5:
                        return 2, fort, fort
            
            # 敵砦への波状攻撃
            for enemy in enemy_fortresses:
                attackers = [f for f in my_fortresses if A_coordinate[f][enemy] != 0 and self.state[f][3] >= 15]
                total_attack_power = sum(self.state[f][3] for f in attackers)
                
                if total_attack_power >= 30:
                    self.current_target = enemy
                    self.attack_sources = attackers
                    self.support_mode = True
                    best_attacker = max(attackers, key=lambda f: self.state[f][3])
                    return 1, best_attacker, enemy
            
            # 残りの中立砦を確保（波状攻撃）
            for neutral in neutral_fortresses:
                attackers = [f for f in my_fortresses if A_coordinate[f][neutral] != 0 and self.state[f][3] >= 10]
                if attackers:
                    self.current_target = neutral
                    self.attack_sources = attackers
                    self.support_mode = True
                    best_attacker = max(attackers, key=lambda f: self.state[f][3])
                    return 1, best_attacker, neutral

        # デフォルト：待機
        return 0, 0, 0
