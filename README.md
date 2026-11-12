# AI ライティングツール（個人用）

Python + Streamlit + Gemini API で作った、文章作成系 AI 機能をまとめたツールです。

## 機能
- ✍️ ブログ記事（構成案 / 全文、SEO キーワード、文字数指定）
- 📧 メール作成・返信（関係性・方向性・丁寧さ、複数パターン）
- 📝 要約（ファイル読み込み可、形式・詳しさ指定）
- 🔍 校正・リライト（誤字チェック表、トーン変更、文字数調整）
- 🌐 翻訳（解説付きオプション）
- 📱 SNS 投稿（X / Instagram / Threads / LinkedIn など）
- 💡 タイトル・キャッチコピー案出し
- 🗂️ 議事録・メモ整形
- 💬 ライティング相談チャット
- 📜 履歴（検索・一括ダウンロード）

共通: ストリーミング表示、修正指示での再生成、コピー、Markdown ダウンロード、「私の文体」設定、temperature 切替（モデルは gemini-3.1-flash-lite 固定）

## セットアップ
```bash
cd ~/ai-writing-tool
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # GEMINI_API_KEY を記入
.venv/bin/streamlit run app.py
```
API キーは .env に書かなくても、起動後サイドバーから入力できます。

## 開発
```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q                                      # テスト（API は呼ばない）
.venv/bin/ruff check . --fix && .venv/bin/ruff format .  # リント・整形
```
履歴は `data/history.json` に保存されます。
