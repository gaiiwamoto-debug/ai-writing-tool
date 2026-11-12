"""AI ライティングツール（個人用） - Streamlit + Gemini API"""

import streamlit as st

import features
from gemini_client import MODEL, find_api_key, save_api_key
from ui import init_state

st.set_page_config(page_title="AI ライティングツール", page_icon="✍️", layout="wide")
init_state()

PAGES = {
    "✍️ ブログ記事": features.blog,
    "📧 メール作成・返信": features.email,
    "📝 要約": features.summarize,
    "🔍 校正・リライト": features.rewrite,
    "🌐 翻訳": features.translate,
    "📱 SNS 投稿": features.sns,
    "💡 タイトル・コピー": features.titles,
    "🗂️ 議事録・メモ整形": features.minutes,
    "💬 相談チャット": features.chat,
    "📜 履歴": features.history,
}

with st.sidebar:
    st.title("✍️ AI ライティング")
    page = st.radio("機能", list(PAGES), label_visibility="collapsed")

    st.divider()
    st.subheader("⚙️ 設定")
    api_key = find_api_key()
    if not api_key:
        api_key = st.text_input(
            "Gemini API キー", type="password", help="下のボタンで保存すると、次回から入力不要になります"
        )
        if api_key and st.button("🔒 このキーを保存（次回から入力不要）"):
            save_api_key(api_key)
            st.rerun()
    else:
        st.caption("✅ API キー読み込み済み")

    model = MODEL
    st.caption(f"🤖 モデル: {MODEL}（固定）")
    temperature = st.slider("創造性（temperature）", 0.0, 2.0, 0.7, 0.1, help="低いほど堅実、高いほど自由な発想")
    with st.expander("🖋️ 私の文体・好み"):
        my_style = st.text_area(
            "全機能に反映されます（要約・翻訳・校正チェック・議事録を除く）",
            key="my_style_input",
            placeholder="例: 一人称は「僕」。です・ます調。難しい言葉は避け、具体例を多めに。",
            height=120,
        )

st.session_state["settings"] = {
    "api_key": api_key,
    "model": model,
    "temperature": temperature,
    "my_style": my_style,
}

if not api_key:
    st.info(
        "👈 サイドバーで Gemini API キーを入力してください。キーは [Google AI Studio](https://aistudio.google.com/apikey) で無料で取得できます。"
    )
    st.stop()

PAGES[page]()
