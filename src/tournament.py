"""
Tournament Script

src/tcg/players/ ディレクトリ内の全AIプレイヤーを自動検出して総当たり戦を実行します。

実行方法:
    cd src
    uv run python tournament.py

オプション:
    - ウィンドウ表示: src/tcg/config.py の ON_window を True に設定
    - 試合数: MATCHES_PER_PAIR を変更
"""

from collections import defaultdict
from itertools import combinations

import pygame

from tcg.config import ON_window
from tcg.controller import Controller
from tcg.game import Game
from tcg.players import discover_players

# トーナメント設定
MATCHES_PER_PAIR = 3  # 各対戦カードで実行する試合数


def run_match(player1: Controller, player2: Controller, match_id: int = 1) -> dict:
    """
    1試合を実行して結果を返す

    Args:
        player1: プレイヤー1（青/下側）
        player2: プレイヤー2（赤/上側）
        match_id: 試合番号

    Returns:
        dict: 試合結果
            - winner: "Blue" | "Red" | "Both"
            - blue_fortresses: 青チームの要塞数
            - red_fortresses: 赤チームの要塞数
            - steps: 総ステップ数
    """
    game = Game(player1, player2)
    game.run()

    result = {
        "winner": game.win_team,
        "blue_fortresses": game.Blue_fortress,
        "red_fortresses": game.Red_fortress,
        "steps": game.step,
    }

    if not ON_window:
        print(
            f"  Match {match_id}: {game.win_team} Win! "
            f"(Blue: {game.Blue_fortress}, Red: {game.Red_fortress}, Steps: {game.step})"
        )

    return result


def run_tournament(players: list[type[Controller]], matches_per_pair: int = 3):
    """
    総当たり戦トーナメントを実行

    Args:
        players: プレイヤークラスのリスト
        matches_per_pair: 各対戦で実行する試合数
    """
    if len(players) < 2:
        print("エラー: 最低2人のプレイヤーが必要です")
        print(f"現在のプレイヤー数: {len(players)}")
        return

    print("=" * 70)
    print("要塞征服ゲーム トーナメント")
    print("=" * 70)
    print(f"\n参加プレイヤー: {len(players)}人")
    for i, player_class in enumerate(players, 1):
        player = player_class()
        print(f"  {i}. {player.team_name()} ({player_class.__name__})")

    print(f"\n各対戦: {matches_per_pair}試合")
    print(f"総試合数: {len(list(combinations(range(len(players)), 2))) * matches_per_pair * 2}試合")
    print(f"ビジュアライゼーション: {'ON' if ON_window else 'OFF'}")
    print("=" * 70)

    # 統計情報を記録
    stats = defaultdict(
        lambda: {"wins": 0, "losses": 0, "draws": 0, "total_fortresses": 0, "matches": 0}
    )

    # 総当たり戦
    match_count = 0
    for i, j in combinations(range(len(players)), 2):
        player1_class = players[i]
        player2_class = players[j]

        player1_name = player1_class().team_name()
        player2_name = player2_class().team_name()

        print(f"\n【{player1_name} vs {player2_name}】")

        # 先攻・後攻を入れ替えて実行
        for round_num in range(1, matches_per_pair + 1):
            # プレイヤー1が青（下側/先攻）
            print(f"  Round {round_num}A: {player1_name}(Blue) vs {player2_name}(Red)")
            result = run_match(player1_class(), player2_class(), match_count + 1)
            match_count += 1

            # 統計更新
            stats[player1_name]["matches"] += 1
            stats[player2_name]["matches"] += 1
            stats[player1_name]["total_fortresses"] += result["blue_fortresses"]
            stats[player2_name]["total_fortresses"] += result["red_fortresses"]

            if result["winner"] == "Blue":
                stats[player1_name]["wins"] += 1
                stats[player2_name]["losses"] += 1
            elif result["winner"] == "Red":
                stats[player2_name]["wins"] += 1
                stats[player1_name]["losses"] += 1
            else:
                stats[player1_name]["draws"] += 1
                stats[player2_name]["draws"] += 1

            # プレイヤー2が青（下側/先攻）
            print(f"  Round {round_num}B: {player2_name}(Blue) vs {player1_name}(Red)")
            result = run_match(player2_class(), player1_class(), match_count + 1)
            match_count += 1

            # 統計更新
            stats[player1_name]["matches"] += 1
            stats[player2_name]["matches"] += 1
            stats[player1_name]["total_fortresses"] += result["red_fortresses"]
            stats[player2_name]["total_fortresses"] += result["blue_fortresses"]

            if result["winner"] == "Blue":
                stats[player2_name]["wins"] += 1
                stats[player1_name]["losses"] += 1
            elif result["winner"] == "Red":
                stats[player1_name]["wins"] += 1
                stats[player2_name]["losses"] += 1
            else:
                stats[player1_name]["draws"] += 1
                stats[player2_name]["draws"] += 1

    # 結果表示
    print("\n" + "=" * 70)
    print("トーナメント結果")
    print("=" * 70)

    # スコア計算（勝ち=3点、引き分け=1点、負け=0点）
    rankings = []
    for player_name, data in stats.items():
        score = data["wins"] * 3 + data["draws"] * 1
        win_rate = data["wins"] / data["matches"] * 100 if data["matches"] > 0 else 0
        avg_fortresses = data["total_fortresses"] / data["matches"] if data["matches"] > 0 else 0
        rankings.append(
            {
                "name": player_name,
                "score": score,
                "wins": data["wins"],
                "draws": data["draws"],
                "losses": data["losses"],
                "matches": data["matches"],
                "win_rate": win_rate,
                "avg_fortresses": avg_fortresses,
            }
        )

    # スコア順にソート
    rankings.sort(key=lambda x: (x["score"], x["wins"], x["avg_fortresses"]), reverse=True)

    # ランキング表示
    print(
        f"\n{'順位':<4} {'プレイヤー名':<20} {'スコア':<6} {'勝':<4} {'分':<4} {'敗':<4} "
        f"{'勝率':<8} {'平均要塞数':<10}"
    )
    print("-" * 70)
    for rank, player in enumerate(rankings, 1):
        print(
            f"{rank:<4} "
            f"{player['name']:<20} "
            f"{player['score']:<6} "
            f"{player['wins']:<4} "
            f"{player['draws']:<4} "
            f"{player['losses']:<4} "
            f"{player['win_rate']:>6.1f}% "
            f"{player['avg_fortresses']:>10.2f}"
        )

    print("\n" + "=" * 70)
    print(f"総試合数: {match_count}試合")
    print("=" * 70)


def main():
    """メイン関数"""
    # プレイヤーを収集
    players = []

    # src/tcg/players/ から自動検出
    discovered_players = discover_players()
    players.extend(discovered_players)
    print(f"発見したプレイヤー: {len(discovered_players)}人")

    if len(players) == 0:
        print("\nエラー: プレイヤーが見つかりませんでした")
        print("src/tcg/players/ ディレクトリに player_*.py ファイルを作成してください")
        print("詳細は src/tcg/players/README.md を参照")
        return

    # トーナメント実行
    run_tournament(players, matches_per_pair=MATCHES_PER_PAIR)

    # Pygameの終了処理
    if ON_window:
        pygame.quit()


if __name__ == "__main__":
    main()
