# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

個人用の AI ライティングツール。ブログ記事、メール返信、要約、校正・リライト、翻訳、SNS 投稿、タイトル案、議事録整形、相談チャットの機能を持つ。Python + Streamlit + Gemini API で作っており、Gemini には `google-genai` SDK（`from google import genai`）を使う。

データベースとログイン機能は意図的に持たせていない。頼まれない限り追加しないこと。

画面の文言も AI へのプロンプトも日本語。ユーザーへの返答や説明も日本語で行う。

## コマンド

```bash
.venv/bin/pip install -r requirements-dev.txt   # 本体＋pytest・ruff（.venv は作成済み、Python 3.14）
.venv/bin/streamlit run app.py                  # http://localhost:8501
./launch.sh                                     # 未起動なら裏で起動してブラウザで開く（~/Desktop/AIライティングツール.app から呼ばれる。ログは ~/Library/Logs/ai-writing-tool.log）

.venv/bin/pytest -q                                              # 全テスト
.venv/bin/pytest -q tests/test_features.py::test_blog_style_and_length   # 単体テスト
.venv/bin/pytest -q -k history                                   # 名前で絞り込み

.venv/bin/ruff check . --fix && .venv/bin/ruff format .          # リント＋フォーマット
```

pytest と ruff の設定は `pyproject.toml` にある。ruff は `BLE001`（広い except）を無視する設定にしている。API エラーを画面に表示するため、意図的に `except Exception` を使っているからである。

API キーは `GEMINI_API_KEY`（または `GOOGLE_API_KEY`）を、`.env`・環境変数・`st.secrets` の順で探す。どこにも無ければ、サイドバーに入力欄と「このキーを保存」ボタンが出る。ボタンを押すと `save_api_key` が `.env`（`.gitignore` 済み、権限 600）に書き込み、次回から入力不要になる。

モデルは `gemini_client.MODEL`（`gemini-3.1-flash-lite`、無料枠対応）に固定しており、サイドバーでは選べない。

## アーキテクチャ

### `app.py`（エントリーポイント）

サイドバー（機能の選択、API キー、モデル表示（固定）、temperature、「私の文体」）の値を `st.session_state["settings"]` にまとめてから、`PAGES` 辞書で選ばれたページ関数を呼ぶ。

機能を追加するときは、`features.py` に関数を作って `PAGES` に登録し、`tests/test_features.py` の `GENERATING_PAGES` にもその機能を足す。

### `features.py`（各機能の画面とプロンプト）

1機能＝1関数。入力欄を描画し、プロンプトとシステムプロンプトを組み立ててから `_run(key, label, clicked, ok, prompt, system)` を呼ぶ。

例外は `chat()` で、複数ターンの `contents`（`role` は `user` / `model`）を使い、自分で直接ストリーミングする。

### `ui.py`（共通部品）

#### `build_system(extra, use_style)`

`BASE_SYSTEM` に、機能ごとのペルソナと「私の文体」を足してシステムプロンプトを作る。要約・翻訳・校正チェック・議事録では `use_style=False` にして、ユーザーの文体を混ぜない。

#### `output_area(key, label, prompt?, system?)`

- prompt を渡すと、`st.write_stream` で生成して、結果を `session_state.results[key]` と `last_req[key]` に保存する。
- prompt を渡さないと、保存済みの結果を表示し直す。
- どちらの場合も、コピー・ダウンロード・「修正指示」欄をあわせて描画する。

#### 修正の流れ

1. 修正ボタンの `on_click` コールバック（`_queue_refine`）が、修正用のプロンプトを組み立てて `session_state.pending[key]` に入れる。
2. 次の再実行で、`output_area` がそれを取り出して生成する。

コールバックを使っているのは、ウィジェットを描画したあとではその値を変更できないため。

#### 履歴

- `data/history.json` に保存する（`.gitignore` 済み）。中身はユーザー自身が書いた文章なので、外部に送ったりコミットしたりしない。
- セッションごとに一度だけ、`init_state()` で読み込む。
- `add_history()` のたび、および `features.history()` で削除・全消去したときに `save_history()` で保存する。書き込みは一時ファイルに書いて `os.replace` で置き換える方式。
- 読めないファイルは上書きせず、`history_broken_<日時>.json` という名前に変えて退避する。

### `gemini_client.py`（Gemini API との通信）

- `get_client`：`st.cache_resource` でキャッシュする。
- `MODEL`：使うモデル（固定）。
- `save_api_key`：API キーを `.env` に保存し、`os.environ` にも入れる。
- `stream_text`：生成されたテキストを少しずつ返すジェネレーター。
- `error_hint`：429 / RESOURCE_EXHAUSTED のとき、無料枠の上限に達した旨と対処を返す。

### session_state のキー

| キー | 役割 |
| --- | --- |
| `settings` | サイドバーの設定（`api_key` / `model` / `temperature` / `my_style`） |
| `results` | 機能ごとの最新の生成結果 |
| `last_req` | 機能ごとに直前に送った `(prompt, system)`（修正に使う） |
| `pending` | 次の再実行で生成する修正用の `(prompt, system)` |
| `history` | 生成履歴（新しい順）。中身は `history.json` と同じ |
| `chat_messages` | 相談チャットの会話。ファイルには保存しない |

`results` / `last_req` / `pending` は、`features.py` の `_run` に渡す機能 key（`blog`、`email` など）で引く。

## 実装の約束ごと・注意点

- コールバックをまたいで値を残したいウィジェットには、明示的に key を付ける。例：ブログの文字数は、number_input の `blog_length` と segmented_control の `blog_len_preset` に分けている。プリセットの `on_change` が `blog_length` に値を書き込む。
- プロンプトでは「前置きを書かず、成果物だけを Markdown で出力する」よう指示している。機能を追加するときもこの方針に合わせる。
- `st.segmented_control`、`st.popover`、`st.code(wrap_lines=...)` など、比較的新しい Streamlit の API を使っている。そのため `requirements.txt` の Streamlit は `>=1.40` にしている。

## テスト

`tests/` にあるテストは `streamlit.testing.v1.AppTest` でアプリ全体を動かす。Gemini API は呼ばない。

`tests/conftest.py` の `calls` フィクスチャが、次の準備をする。

- `gemini_client` の `find_api_key` / `stream_text` をモックに差し替える。
- `ui.stream_text` と `features.stream_text` も差し替える。どちらも名前で import しているので、`gemini_client` 側だけ差し替えても効かない。
- `ui.HISTORY_FILE` を `tmp_path` に向けて、本物の `data/history.json` に書き込まないようにする。
- Gemini に送られた `(contents, system)` を記録したリストを返す。テストではこれを見て、プロンプトに何が入ったかを確かめる。

`app` フィクスチャは起動済みの AppTest を返す。`go()`、`primary_button()`、`output_shown()` が補助関数。

テストを書くときの注意：

- `AppTest.from_file()` は相対パスを呼び出し元ファイルを基準に解決するので、`conftest.APP_PATH`（絶対パス）を使う。
- `at.selectbox` や `at.radio` にはサイドバーのウィジェットも含まれる。メインエリアのウィジェットは `at.main.*` で取り、ラベルか key で絞り込む。
- 再起動したときの動きを確かめるには、同じテストの中で `AppTest.from_file()` を作り直す（新しいセッションになる）。
