"""各機能ページの描画と生成フローのテスト。"""

from __future__ import annotations

import pytest
from conftest import go, output_shown, primary_button

# (ページ名の先頭, 必須入力のウィジェット種別, そのラベル)
GENERATING_PAGES = [
    ("✍️", "text_input", "記事のテーマ *"),
    ("📧", "text_area", "受信したメール *"),
    ("📝", "text_area", "要約したい文章 *"),
    ("🔍", "text_area", "対象の文章 *"),
    ("🌐", "text_area", "翻訳したい文章 *"),
    ("📱", "text_area", "投稿したい内容・伝えたいこと *"),
    ("💡", "text_area", "内容・商品・記事の概要 *"),
    ("🗂️", "text_area", "会議メモ・文字起こし *"),
]


def _fill(at, kind, label, value="テスト入力"):
    widget = next(w for w in getattr(at.main, kind) if w.label == label)
    widget.input(value).run()


@pytest.mark.parametrize(("prefix", "kind", "label"), GENERATING_PAGES)
def test_page_generates(app, calls, prefix, kind, label):
    go(app, prefix)
    _fill(app, kind, label)
    primary_button(app).click().run()
    assert not app.exception, app.exception
    assert output_shown(app)
    assert len(calls) == 1
    assert len(app.session_state.history) == 1


@pytest.mark.parametrize(("prefix", "kind", "label"), GENERATING_PAGES)
def test_required_input_warns(app, calls, prefix, kind, label):
    go(app, prefix)
    primary_button(app).click().run()
    assert app.main.warning, "必須入力が空なら警告が出るはず"
    assert calls == []


def test_refine_uses_previous_result(app, calls):
    _fill(app, "text_input", "記事のテーマ *", "Python入門")
    primary_button(app).click().run()
    app.text_input(key="refine_blog").input("もっと短く").run()
    app.button(key="refine_btn_blog").click().run()
    assert not app.exception, app.exception
    assert len(calls) == 2
    refine_prompt = calls[-1][0]
    assert "もっと短く" in refine_prompt and "生成結果テキスト" in refine_prompt
    assert app.session_state.history[0]["feature"].endswith("（修正）")


def test_blog_style_and_length(app, calls):
    _fill(app, "text_input", "記事のテーマ *", "Python入門")
    next(s for s in app.main.selectbox if s.label == "文体").select("だ・である調").run()
    app.button_group(key="blog_len_preset").set_value(5000).run()
    assert app.number_input(key="blog_length").value == 5000
    app.number_input(key="blog_length").set_value(4200).run()
    button = primary_button(app)
    assert button.label == "約4,200文字で記事を生成"
    button.click().run()
    prompt = calls[-1][0]
    assert "約4,200文字" in prompt and "だ・である調" in prompt


def test_blog_outline_mode_hides_length(app):
    next(r for r in app.main.radio if r.label == "出力").set_value("構成案のみ").run()
    assert primary_button(app).label == "構成案を生成"
    assert not [n for n in app.main.number_input if n.key == "blog_length"]


def test_my_style_is_applied_only_where_intended(app, calls):
    app.sidebar.text_area(key="my_style_input").input("一人称は僕").run()
    _fill(app, "text_input", "記事のテーマ *", "テーマ")
    primary_button(app).click().run()
    assert "一人称は僕" in calls[-1][1]

    go(app, "🌐")
    _fill(app, "text_area", "翻訳したい文章 *")
    primary_button(app).click().run()
    assert "一人称は僕" not in calls[-1][1]


def test_chat_keeps_conversation(app, calls):
    go(app, "💬")
    app.chat_input[0].set_value("こんにちは").run()
    app.chat_input[0].set_value("続けて").run()
    assert not app.exception, app.exception
    assert [m["role"] for m in app.session_state.chat_messages] == ["user", "assistant", "user", "assistant"]
    contents = calls[-1][0]
    assert [c["role"] for c in contents] == ["user", "model", "user"]
