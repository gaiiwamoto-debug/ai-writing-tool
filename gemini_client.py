"""Gemini API との通信をまとめたモジュール。"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parent / ".env")

# 使うモデル（固定）。無料枠で使えるテキスト生成モデル。
# 参考: https://aistudio.google.com/docs/pricing （2026-11 時点で Free Tier「Free of charge」）
MODEL = "gemini-3.1-flash-lite"

ENV_FILE = Path(__file__).resolve().parent / ".env"


def find_api_key() -> str | None:
    """環境変数 / .env / Streamlit secrets から API キーを探す。"""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


def save_api_key(key: str) -> None:
    """API キーを .env に保存し、このプロセスでもすぐ使えるようにする（.env は .gitignore 済み）。"""
    key = "".join(key.split())  # 改行や空白が混ざって .env が壊れないように
    ENV_FILE.touch(mode=0o600, exist_ok=True)
    ENV_FILE.chmod(0o600)
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    lines = [line for line in lines if not line.startswith("GEMINI_API_KEY=")]
    lines.append(f"GEMINI_API_KEY={key}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ["GEMINI_API_KEY"] = key


@st.cache_resource(show_spinner=False)
def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def stream_text(
    api_key: str,
    model: str,
    contents: str | list[dict],
    system: str | None = None,
    temperature: float = 0.7,
) -> Iterator[str]:
    """テキストをストリーミング生成する。"""
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
    )
    for chunk in get_client(api_key).models.generate_content_stream(model=model, contents=contents, config=config):
        if chunk.text:
            yield chunk.text


def error_hint(e: Exception) -> str:
    """API エラーに、ユーザー向けの対処のヒントを付ける。"""
    msg = str(e)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return (
            f"\n\n💡 無料枠の利用上限に達しました（モデル: {MODEL}）。"
            "1分ほど待つか、1日の上限の場合は翌日に試してください。"
        )
    return ""
