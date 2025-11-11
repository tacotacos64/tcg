Territory Conquering Game
=========================
この実験では、陣取りゲームのAIプレイヤーを開発します。 

## 実験の準備

1. まずuvをインストールします。[uv](https://docs.astral.sh/uv/getting-started/installation/)を参考にしましょう。

2. リポジトリをクローンし、必要なライブラリをインストール:
```bash
git clone https://github.com/matt76k/tcg
cd tcg
uv sync
```

3. ゲームの実行:
```bash
uv run python src/main.py
```

## 実験内容

1. src/main.pyを開き、RandomPlayerクラスを参考にして独自のAIプレイヤーを実装してください。

2. 以下の点を考慮してAIを設計しましょう:
- タイルの配置をどのように評価するか
- どの方向に動かすのが最適か
- 何手先まで読むか

3. 実装したAIの性能を評価し、改善を試みてください。