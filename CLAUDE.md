# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## プロジェクト概要

PygameとPythonで実装された要塞征服ゲームです。2人のプレイヤー（AIエージェントで制御）が、グラフ状の戦場で接続されたノード間で部隊を送り、要塞を奪い合うリアルタイム戦略ゲームです。

## 開発コマンド

### 環境セットアップ
```bash
# Python version: 3.12.3 (.python-versionで指定)
# uvを依存関係管理に使用

# 依存関係のインストール
uv sync

# 仮想環境の有効化
source .venv/bin/activate  # macOS/Linuxの場合
```

### ゲームの実行
```bash
# 依存関係のインストール（初回のみ）
uv sync

# ゲームの実行
cd src && uv run python main.py

# または、仮想環境を有効化してから実行
source .venv/bin/activate
cd src && python main.py

# デフォルトで11試合実行（最初の1試合 + 最後のループで10試合）
```

## アーキテクチャ

### プロジェクト構造

```
src/
├── main.py              # エントリーポイント
└── tcg/
    ├── __init__.py
    ├── config.py        # ゲーム定数と設定
    ├── controller.py    # Controller基底クラス
    ├── game.py          # Gameクラス（メインゲームロジック）
    ├── players.py       # AIプレイヤー実装
    └── utils.py         # ユーティリティ関数
```

### モジュール説明

**src/main.py**
- ゲームのエントリーポイント
- AIプレイヤー同士で11試合実行（最初の1試合 + ループで10試合）

**src/tcg/config.py**
- ゲームの定数（ウィンドウサイズ、速度、色など）
- 要塞の配置と隣接関係
- コマンドリスト
- 要塞の制限値とクールダウン

**src/tcg/controller.py**
- `Controller`基底クラス：全てのプレイヤーが継承
- `Human`クラス：人間プレイヤー用（未実装）

**src/tcg/game.py**
- `Game`クラス：コアゲームループと状態管理
- 12個の要塞をグラフトポロジーで管理
- 要塞のアップグレード、部隊の生成、移動を処理
- Pygameでのビジュアライゼーション

**src/tcg/players.py**
- `RandomPlayer`：ランダムに行動するAI
- `Random_Zako`：弱いランダムAI（50ステップごとにのみ行動）

**src/tcg/utils.py**
- `Swap_team()`：チーム視点の切り替え
- `Swap_up_bottom()`：上下プレイヤーの視点変換
- `create_masking_list()`：有効コマンドのマスク生成

### ゲームメカニクス

**要塞:**
- 12個の要塞で、隣接関係は`A_fortress`行列で定義
- 各要塞の属性：team（0/1/2）、kind（0/1）、level（1-5）、troop count、upgrade timer
- レベルと種類に基づいて時間経過で部隊を生成
- 部隊を消費してアップグレード可能（レベル上限の半分の部隊が必要）

**部隊:**
- 2種類：kind 0（速いが弱い）、kind 1（遅いが強い）
- 要塞から生成され、エッジに沿って目標要塞へ移動
- 攻撃ダメージ：kind 0 = 0.65、kind 1 = 0.95（1部隊あたり）

**コマンド:**
- `(0, *, *)`: 何もしない
- `(1, from, to)`: 要塞の部隊の半分を`from`から`to`へ送る
- `(2, fortress, 0)`: `fortress`をアップグレード（条件を満たす場合）
- 有効なコマンドは`l_command`にリスト化（全64個）

### 重要な定数

- `SPEEDRATE = 40`: フレームあたりのシミュレーションステップ数（ゲーム速度に影響）
- `FPS = 30`: ビジュアライゼーションのフレームレート
- `STEPLIMIT = 50000`: 最大ゲームステップ数
- `fortress_limit = [10,10,20,30,40,50]`: 要塞レベルごとの最大部隊数
- `fortress_cool`: レベルと種類ごとの部隊生成クールダウン

### 状態表現

**ゲーム状態フォーマット:**
```python
[team, kind, level, pawn_number, upgrade_time, [to_set]]
```

**コントローラーに渡される情報:**
```python
[team_id, state, moving_pawns, spawning_pawns, done]
```

- `moving_pawns`: 移動中の部隊リスト
- `spawning_pawns`: 出発待ちの部隊リスト

コントローラーは視点が入れ替わった状態を受け取る（team 2は常に`Swap_up_bottom()`経由で自分を「下側」プレイヤーとして見る）

## 重要な実装の詳細

### 座標系
- 要塞の位置は`pos_fortress`で定義（ピクセル座標）
- 移動ベクトルは`A_coordinate`で定義（正規化された方向タプル）
- グラフの隣接関係は`A_fortress`（対称）と`A_fortress_set`（片方向）
- GNN/グラフ処理用のエッジインデックス表現は`edge_index`

### チーム表現
- Team 0: 中立（初期状態）
- Team 1: 青（下側プレイヤー）
- Team 2: 赤（上側プレイヤー）

### 重要なゲームループ
1. 部隊の移動 (`pawn_move()`)
2. コントローラーの更新（両プレイヤー同時）
3. 命令の実行 (`order()`)
4. 出現ポイントからの部隊出発
5. 部隊の生成 (`pawn_born()`)
6. オーバーフロー処理 (`pawn_over()`)
7. アップグレード進捗チェック
8. 勝利条件チェック

## 新しいAIプレイヤーの作成方法

1. `src/tcg/players.py`に新しいクラスを作成
2. `Controller`クラスを継承
3. `team_name()`メソッドを実装（プレイヤー名を返す）
4. `update(info)`メソッドを実装（ゲーム状態を受け取り、コマンドを返す）

例：
```python
from tcg.controller import Controller

class MyAI(Controller):
    def team_name(self) -> str:
        return "MyAI"

    def update(self, info):
        # info = [team_id, state, moving_pawns, spawning_pawns, done]
        # 戦略を実装
        command, subject, to = 0, 0, 0  # コマンドを決定
        return command, subject, to
```

## ビジュアライゼーション制御

- `ON_window = True/False`: `src/tcg/config.py`でビジュアライゼーションの切り替え
- ウィンドウの表示内容：要塞の状態、部隊数、レベル、アップグレードタイマー
- 背景色は要塞の支配状況に基づいて変化（赤/青のグラデーション）
- フォント: "resources/BestTen-DOT.otf"（存在しない場合は`pygame.font.Font(None, size)`でデフォルトフォントを使用）

## 開発のヒント

- 新しいAIを作成したら、`src/main.py`でインポートして使用する
- ゲーム速度は`config.py`の`SPEEDRATE`と`FPS`で調整
- デバッグ時は`ON_window = False`にして高速実行可能
- GNN用のグラフ表現は`edge_index`と`Edge_dict`を使用
