"""履歴の JSON 保存・読み込み・削除のテスト。"""

from __future__ import annotations

import json

from conftest import APP_PATH, go, primary_button
from streamlit.testing.v1 import AppTest

import ui


def _generate_blog(at, times=1):
    for _ in range(times):
        next(w for w in at.main.text_input if w.label == "記事のテーマ *").input("テーマ").run()
        primary_button(at).click().run()


def _saved():
    return json.loads(ui.HISTORY_FILE.read_text(encoding="utf-8"))


def test_history_saved_and_reloaded(app):
    _generate_blog(app, times=2)
    assert len(_saved()) == 2

    fresh = AppTest.from_file(APP_PATH, default_timeout=30).run()  # 再起動相当
    assert len(fresh.session_state.history) == 2


def test_delete_one_and_clear_all(app):
    _generate_blog(app, times=2)
    go(app, "📜")
    next(b for b in app.main.button if b.label == "この履歴を削除").click().run()
    assert len(_saved()) == 1

    next(b for b in app.main.button if b.label == "消去する").click().run()
    assert _saved() == []


def test_broken_file_is_backed_up(calls):
    ui.HISTORY_FILE.write_text("{broken", encoding="utf-8")
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert not at.exception
    assert at.session_state.history == []
    backups = list(ui.HISTORY_FILE.parent.glob("history_broken_*.json"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == "{broken"
