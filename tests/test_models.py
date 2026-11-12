"""モデル固定・API キー保存・エラーヒントのテスト（API は呼ばない）。"""

import os
import stat

import gemini_client
from gemini_client import MODEL, error_hint, save_api_key


def test_model_is_fixed_to_free_tier_flash_lite():
    assert MODEL == "gemini-3.1-flash-lite"


def test_generation_uses_fixed_model(app, monkeypatch):
    used = []

    def fake_stream(api_key, model, contents, system=None, temperature=0.7):
        used.append(model)
        yield "ok"

    import ui

    monkeypatch.setattr(ui, "stream_text", fake_stream)
    theme = next(w for w in app.main.text_input if w.label == "記事のテーマ *")
    theme.input("テスト").run()
    next(b for b in app.main.button if b.proto.type == "primary").click().run()
    assert used == [MODEL]


def test_save_api_key_writes_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("OTHER=1\nGEMINI_API_KEY=old\n", encoding="utf-8")
    monkeypatch.setattr(gemini_client, "ENV_FILE", env)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    save_api_key(" new-key\n")

    assert env.read_text(encoding="utf-8") == "OTHER=1\nGEMINI_API_KEY=new-key\n"
    assert stat.S_IMODE(env.stat().st_mode) == 0o600
    assert os.environ["GEMINI_API_KEY"] == "new-key"
    assert gemini_client.find_api_key() == "new-key"


def test_error_hint_for_429():
    hint = error_hint(Exception("429 RESOURCE_EXHAUSTED. limit: 0"))
    assert MODEL in hint
    assert error_hint(Exception("400 INVALID_ARGUMENT")) == ""
