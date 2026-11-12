"""各機能で共通して使う出力エリア・履歴などの UI 部品。"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from gemini_client import error_hint, stream_text

HISTORY_FILE = Path(__file__).parent / "data" / "history.json"

BASE_SYSTEM = (
    "あなたは日本語の文章作成を得意とするプロのライター兼編集者です。"
    "指示された条件を厳密に守り、前置きや「承知しました」などの余計な説明は書かず、"
    "成果物だけを Markdown で出力してください。"
)


def init_state() -> None:
    st.session_state.setdefault("results", {})  # feature_key -> 最新の出力
    st.session_state.setdefault("last_req", {})  # feature_key -> (prompt, system)
    st.session_state.setdefault("pending", {})  # feature_key -> 修正用プロンプト
    if "history" not in st.session_state:
        st.session_state.history = load_history()
    st.session_state.setdefault("chat_messages", [])


def load_history() -> list[dict]:
    """JSON ファイルから履歴を読み込む（無い・壊れている場合は空）。"""
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, OSError) as e:
        # 上書きで中身を失わないよう、壊れたファイルは退避しておく
        backup = HISTORY_FILE.with_name(f"history_broken_{datetime.now():%Y%m%d_%H%M%S}.json")
        try:
            HISTORY_FILE.rename(backup)
            st.warning(f"履歴ファイルを読み込めなかったため `{backup.name}` に退避しました: {e}")
        except OSError:
            st.warning(f"履歴ファイルを読み込めませんでした: {e}")
        return []


def save_history() -> None:
    """履歴を JSON ファイルに保存する（一時ファイル経由で安全に書き込み）。"""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = HISTORY_FILE.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(st.session_state.history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, HISTORY_FILE)
    except OSError as e:
        st.error(f"履歴の保存に失敗しました: {e}")


def settings() -> dict:
    return st.session_state["settings"]


def build_system(extra: str = "", use_style: bool = True) -> str:
    parts = [BASE_SYSTEM, extra]
    style = settings().get("my_style", "").strip()
    if use_style and style:
        parts.append(f"【ユーザーの文体・好み（可能な範囲で反映）】\n{style}")
    return "\n\n".join(p for p in parts if p)


def add_history(feature: str, prompt: str, output: str) -> None:
    st.session_state.history.insert(
        0,
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "feature": feature,
            "prompt": prompt,
            "output": output,
        },
    )
    save_history()


def _generate(key: str, label: str, prompt: str, system: str) -> None:
    s = settings()
    try:
        text = st.write_stream(stream_text(s["api_key"], s["model"], prompt, system, s["temperature"]))
    except Exception as e:  # API エラーは画面に表示
        st.error(f"生成中にエラーが発生しました: {e}{error_hint(e)}")
        return
    if isinstance(text, list):
        text = "".join(map(str, text))
    st.session_state.results[key] = text
    st.session_state.last_req[key] = (prompt, system)
    add_history(label, prompt, text)


def _queue_refine(key: str) -> None:
    instruction = st.session_state.get(f"refine_{key}", "").strip()
    if not instruction or key not in st.session_state.last_req:
        return
    prompt, system = st.session_state.last_req[key]
    current = st.session_state.results.get(key, "")
    refine_prompt = (
        f"以下は先ほどの依頼と、あなたが作成した成果物です。\n\n"
        f"### 元の依頼\n{prompt}\n\n### 作成した成果物\n{current}\n\n"
        f"### 修正指示\n{instruction}\n\n"
        "修正指示を反映した成果物の完成版のみを出力してください。"
    )
    st.session_state.pending[key] = (refine_prompt, system)
    st.session_state[f"refine_{key}"] = ""


def output_area(key: str, label: str, prompt: str | None = None, system: str | None = None) -> None:
    """生成結果の表示エリア。prompt が渡されたら生成を実行する。"""
    st.divider()
    pending = st.session_state.pending.pop(key, None)

    if prompt is not None and system is not None:
        _generate(key, label, prompt, system)
    elif pending:
        _generate(key, f"{label}（修正）", *pending)
    elif key in st.session_state.results:
        st.markdown(st.session_state.results[key])
    else:
        return

    text = st.session_state.results.get(key)
    if not text:
        return

    st.caption(f"文字数: {len(text):,} 文字")
    with st.expander("📋 コピー用（右上のアイコンでコピー）"):
        st.code(text, language=None, wrap_lines=True)

    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    with c1:
        st.text_input(
            "✏️ 修正指示",
            key=f"refine_{key}",
            placeholder="例: もっとカジュアルに / 導入を短く / 具体例を追加して",
        )
    with c2:
        st.button(
            "修正する",
            key=f"refine_btn_{key}",
            on_click=_queue_refine,
            args=(key,),
            use_container_width=True,
        )
    st.download_button(
        "⬇️ Markdown でダウンロード",
        data=text,
        file_name=f"{key}_{datetime.now():%Y%m%d_%H%M}.md",
        mime="text/markdown",
        key=f"dl_{key}",
    )


def require_text(value: str, name: str) -> bool:
    if not value.strip():
        st.warning(f"「{name}」を入力してください。")
        return False
    return True
