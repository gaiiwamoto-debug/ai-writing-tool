"""テスト共通のフィクスチャ。Gemini API は呼ばず、固定の文字列を返すモックに差し替える。"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import features
import gemini_client
import ui

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
FAKE_OUTPUT = "生成結果テキスト"


@pytest.fixture
def calls(monkeypatch, tmp_path):
    """Gemini 呼び出しをモックし、送られた (contents, system) を記録するリストを返す。"""
    recorded: list[tuple] = []

    def fake_stream(api_key, model, contents, system=None, temperature=0.7):
        recorded.append((contents, system))
        yield "生成"
        yield "結果テキスト"

    monkeypatch.setattr(gemini_client, "find_api_key", lambda: "dummy")
    # ui / features は名前で import しているので、それぞれ差し替える必要がある
    monkeypatch.setattr(gemini_client, "stream_text", fake_stream)
    monkeypatch.setattr(ui, "stream_text", fake_stream)
    monkeypatch.setattr(features, "stream_text", fake_stream)
    # 本物の data/history.json に書き込まない
    monkeypatch.setattr(ui, "HISTORY_FILE", tmp_path / "history.json")
    return recorded


@pytest.fixture
def app(calls) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert not at.exception, at.exception
    return at


def go(at: AppTest, page_prefix: str) -> AppTest:
    """サイドバーで指定した機能ページに移動する。"""
    radio = at.sidebar.radio[0]
    page = next(p for p in radio.options if p.startswith(page_prefix))
    radio.set_value(page).run()
    assert not at.exception, at.exception
    return at


def primary_button(at: AppTest):
    return next(b for b in at.main.button if b.proto.type == "primary")


def output_shown(at: AppTest) -> bool:
    return any(FAKE_OUTPUT in m.value for m in at.main.markdown)
