
import random
from tcg.controller import Controller
from tcg.config import fortress_limit, fortress_cool

class SmartExpansionist(Controller):
    """
    マップ支配戦略 (Map Control Strategy):
    - 「質より量」：要塞のレベルアップよりも、要塞の数を増やすことを最優先します。
    - 計算上、2つのLv1要塞(クールダウン60*2)の方が、1つのLv5要塞(クールダウン35)よりも生産効率が高いためです。
    - 最小限の防衛戦力を残しつつ、中立要塞を次々と占領して総生産力を高めます。
    """
    def team_name(self) -> str:
        return "MapControl"

    def update(self, info):
        team_id, state, moving_pawns, spawning_pawns, done = info
        
        my_fortresses = [i for i, s in enumerate(state) if s[0] == 1]
        
        # 攻撃/移動のターゲット候補を探す
        actions = []
        
        for i in my_fortresses:
            pawn_count = state[i][3]
            
            # 最低限の守備兵を残す (例: 5体)
            if pawn_count < 5:
                continue
                
            neighbors = state[i][5]
            
            # ターゲットの優先順位:
            # 1. 占領可能な中立要塞 (兵数が少ない)
            # 2. 占領可能な敵要塞
            # 3. 味方への増援 (満杯でない場合)
            
            neutrals = [n for n in neighbors if state[n][0] == 0]
            enemies = [n for n in neighbors if state[n][0] == 2]
            allies = [n for n in neighbors if state[n][0] == 1]
            
            # 中立要塞への攻撃判断
            for n in neutrals:
                # 相手の兵数
                target_troops = state[n][3]
                # 送る兵数 (現在の半分)
                sending = pawn_count // 2
                # ダメージ計算 (Kind 0: 0.65, Kind 1: 0.95)
                # 自分の要塞の種類を確認
                my_kind = state[i][1]
                damage_rate = 0.95 if my_kind == 1 else 0.65
                damage = sending * damage_rate
                
                # 1回で占領できる、または相手を大幅に削れるなら攻撃
                # 占領コストが低いところを優先
                score = 100 - target_troops
                if damage > target_troops:
                    score += 50 # 占領ボーナス
                
                actions.append((score, 1, i, n))

            # 敵要塞への攻撃判断
            for n in enemies:
                target_troops = state[n][3]
                sending = pawn_count // 2
                my_kind = state[i][1]
                damage_rate = 0.95 if my_kind == 1 else 0.65
                damage = sending * damage_rate
                
                # 敵がアップグレード中ならチャンス
                if state[n][4] != -1:
                    actions.append((200, 1, i, n))
                # 倒せるなら攻撃
                elif damage > target_troops:
                    actions.append((150, 1, i, n))
                # 敵が少なければハラスメント
                elif target_troops < 5:
                    actions.append((50, 1, i, n))

            # 味方への増援 (前線へ送るなど)
            # ここでは単純に、兵数が少ない味方へ送る
            for n in allies:
                if state[n][3] < fortress_limit[state[n][2]] * 0.5:
                    actions.append((20, 1, i, n))

            # アップグレード判断
            # 拡張できる場所がなく、兵が溢れそうならアップグレード
            limit = fortress_limit[state[i][2]]
            if pawn_count >= limit * 0.9 and state[i][2] < 5 and state[i][4] == -1:
                 actions.append((10, 2, i, 0))

        # 最もスコアの高い行動を選択
        if actions:
            actions.sort(key=lambda x: x[0], reverse=True)
            return actions[0][1], actions[0][2], actions[0][3]

        return 0, 0, 0
