"""各ライティング機能の画面とプロンプト。"""

from __future__ import annotations

import json

import streamlit as st

from gemini_client import error_hint, stream_text
from ui import HISTORY_FILE, build_system, output_area, require_text, save_history, settings

TONES = ["丁寧・誠実", "親しみやすい", "カジュアル", "専門的・論理的", "熱量高め", "ユーモアあり"]


def _run(key: str, label: str, clicked: bool, ok: bool, prompt: str, system: str) -> None:
    if clicked and ok:
        output_area(key, label, prompt, system)
    else:
        output_area(key, label)


def _read_upload(file) -> str:
    if file is None:
        return ""
    return file.getvalue().decode("utf-8", errors="ignore")


# ---------------------------------------------------------------- ブログ記事
BLOG_STYLES = {
    "です・ます調": "敬体（です・ます調）で統一する。",
    "だ・である調": "常体（だ・である調）で統一する。",
    "話し言葉風（語りかけ）": "読者に話しかけるような口語体。「〜ですよね」「〜なんです」などを自然に使う。",
    "体験談・エッセイ風": "一人称視点で、自分の体験や感情を交えたエッセイ調。",
    "解説・教科書風": "客観的で論理的な説明文。定義→理由→具体例の順で丁寧に解説する。",
    "ニュース・レポート風": "事実を簡潔に伝える報道調。結論を先に書く。",
    "おまかせ（私の文体設定に従う）": "",
}


def _apply_len_preset() -> None:
    preset = st.session_state.get("blog_len_preset")
    if preset:
        st.session_state.blog_length = preset


def blog() -> None:
    st.header("✍️ ブログ記事作成")
    theme = st.text_input("記事のテーマ *", placeholder="例: 初心者向け Python 学習ロードマップ")
    c1, c2 = st.columns(2)
    reader = c1.text_input("想定読者", placeholder="例: プログラミング未経験の社会人")
    keywords = c2.text_input("SEO キーワード（カンマ区切り）", placeholder="例: Python, 独学, 初心者")
    c3, c4, c5 = st.columns(3)
    style = c3.selectbox("文体", list(BLOG_STYLES))
    tone = c4.selectbox("トーン", TONES, index=1)
    mode = c5.radio("出力", ["記事全文", "構成案のみ"], horizontal=True)

    length = 0
    if mode == "記事全文":
        l1, l2 = st.columns([1, 2], vertical_alignment="bottom")
        st.session_state.setdefault("blog_length", 3000)
        length = l1.number_input("記事の長さ（文字数）", min_value=300, max_value=20000, step=100, key="blog_length")
        l2.segmented_control(
            "よく使う長さ",
            [1000, 2000, 3000, 5000, 8000],
            format_func=lambda n: f"{n:,}字",
            key="blog_len_preset",
            on_change=_apply_len_preset,
        )
    points = st.text_area("盛り込みたい内容・自分の体験（任意）", height=100)
    opts = st.multiselect(
        "追加オプション",
        ["メタディスクリプション", "タイトル案を3つ", "まとめ・CTA", "FAQ セクション", "表を活用"],
        default=["メタディスクリプション", "まとめ・CTA"],
    )

    if mode == "構成案のみ":
        task = (
            "記事の構成案（タイトル案、リード文の要旨、H2/H3 の見出しと各見出しで書く内容の要点）を作成してください。"
        )
    else:
        task = (
            f"本文が約{length:,}文字（±10%以内）のブログ記事を、H2/H3 の見出しを使った Markdown で執筆してください。"
            f"文字数は必ず守り、短すぎる場合は具体例や解説を増やして調整してください。"
        )

    prompt = f"""{task}

- テーマ: {theme}
- 想定読者: {reader or "指定なし"}
- SEO キーワード: {keywords or "指定なし"}（自然な形で含める）
- 文体: {style}{"（" + BLOG_STYLES[style] + "この指定を最優先）" if BLOG_STYLES[style] else ""}
- トーン: {tone}
- 盛り込みたい内容: {points or "特になし"}
- 追加で含めるもの: {", ".join(opts) or "なし"}

読者の悩みに寄り添う導入、具体例、読みやすい段落分けを意識してください。"""
    system = build_system("あなたは SEO にも詳しい人気ブロガーです。")
    label = f"約{length:,}文字で記事を生成" if mode == "記事全文" else "構成案を生成"
    clicked = st.button(label, type="primary")
    _run("blog", "ブログ記事", clicked, clicked and require_text(theme, "記事のテーマ"), prompt, system)


# ---------------------------------------------------------------- メール
def email() -> None:
    st.header("📧 メール作成・返信")
    mode = st.radio("モード", ["返信を作成", "新規メールを作成"], horizontal=True)
    received = ""
    if mode == "返信を作成":
        received = st.text_area("受信したメール *", height=200)
    points = st.text_area(
        "伝えたい要点 *" if mode == "新規メールを作成" else "返信で伝えたい要点",
        height=100,
        placeholder="例: 日程は来週火曜の14時なら可能。資料は前日までに送る。",
    )
    c1, c2, c3 = st.columns(3)
    relation = c1.selectbox("相手との関係", ["社外（取引先・顧客）", "上司・目上", "同僚", "友人・知人"])
    direction = c2.selectbox(
        "方向性", ["おまかせ", "承諾・了承", "丁寧にお断り", "質問・確認", "お礼", "お詫び", "依頼"]
    )
    politeness = c3.select_slider("丁寧さ", ["カジュアル", "標準", "丁寧", "非常に丁寧"], value="丁寧")
    c4, c5 = st.columns(2)
    name = c4.text_input("署名（自分の名前など）")
    variations = c5.number_input("パターン数", 1, 3, 1)

    prompt = f"""{"以下の受信メールへの返信" if received else "新規のメール"}を作成してください。

{f"### 受信メール{chr(10)}{received}{chr(10)}" if received else ""}
### 条件
- 伝えたい要点: {points or "受信内容に合わせて適切に"}
- 相手との関係: {relation}
- 方向性: {direction}
- 丁寧さ: {politeness}
- 署名: {name or "（署名は［名前］のプレースホルダーにする）"}
- パターン数: {variations}（複数の場合はニュアンスを変えて「案1」「案2」と見出しを付ける）

件名（返信の場合は「Re: 」付きで可）と本文を出力してください。"""
    system = build_system("あなたはビジネスメールの達人です。日本のビジネスマナーに沿った自然な文面を書きます。")
    clicked = st.button("メールを生成", type="primary")
    ok = require_text(received, "受信したメール") if mode == "返信を作成" else require_text(points, "伝えたい要点")
    _run("email", "メール", clicked, clicked and ok, prompt, system)


# ---------------------------------------------------------------- 要約
def summarize() -> None:
    st.header("📝 文章の要約")
    file = st.file_uploader("テキストファイルを読み込む（.txt / .md）", type=["txt", "md"])
    text = st.text_area("要約したい文章 *", value=_read_upload(file), height=250)
    st.caption(f"入力: {len(text):,} 文字")
    c1, c2, c3 = st.columns(3)
    style = c1.selectbox(
        "形式", ["3行要約", "箇条書き", "段落の文章", "要点＋アクションアイテム", "一言で（タイトル風）"]
    )
    length = c2.select_slider("詳しさ", ["ごく短く", "短め", "標準", "詳しめ"], value="標準")
    audience = c3.text_input("誰向けに？（任意）", placeholder="例: 忙しい上司")

    prompt = f"""次の文章を要約してください。

- 形式: {style}
- 詳しさ: {length}
- 読み手: {audience or "一般"}
- 原文にない情報は加えないこと。重要な数字・固有名詞は残すこと。

### 原文
{text}"""
    system = build_system("あなたは要点を正確に掴む編集者です。", use_style=False)
    clicked = st.button("要約する", type="primary")
    _run("summary", "要約", clicked, clicked and require_text(text, "要約したい文章"), prompt, system)


# ---------------------------------------------------------------- 校正・リライト
def rewrite() -> None:
    st.header("🔍 校正・リライト")
    text = st.text_area("対象の文章 *", height=250)
    st.caption(f"入力: {len(text):,} 文字")
    mode = st.selectbox(
        "やりたいこと",
        [
            "誤字脱字・文法チェック（修正点を一覧表示）",
            "読みやすくリライト",
            "より丁寧な表現に",
            "カジュアルな表現に",
            "簡潔に短くする",
            "内容を膨らませる",
            "指定文字数に調整",
            "箇条書き ⇔ 文章に変換",
        ],
    )
    target = 0
    if mode == "指定文字数に調整":
        target = st.number_input("目標文字数", 50, 10000, 400, step=50)
    extra = st.text_input("追加の指示（任意）", placeholder="例: 専門用語は残して")

    if mode.startswith("誤字脱字"):
        task = (
            "文章を校正してください。まず「修正箇所」を表（修正前 / 修正後 / 理由）で示し、"
            "その後に「修正後の全文」を出力してください。問題がなければその旨を伝えてください。"
        )
    elif mode == "指定文字数に調整":
        task = f"意味を保ったまま約{target}文字に調整してください。"
    else:
        task = f"文章を「{mode}」という方針で書き直してください。"

    prompt = f"""{task}
追加の指示: {extra or "なし"}

### 対象の文章
{text}"""
    system = build_system("あなたは経験豊富な校正者・編集者です。", use_style=not mode.startswith("誤字脱字"))
    clicked = st.button("実行", type="primary")
    _run("rewrite", f"校正・リライト（{mode}）", clicked, clicked and require_text(text, "対象の文章"), prompt, system)


# ---------------------------------------------------------------- 翻訳
def translate() -> None:
    st.header("🌐 翻訳")
    text = st.text_area("翻訳したい文章 *", height=220)
    c1, c2 = st.columns(2)
    lang = c1.selectbox(
        "翻訳先", ["英語", "日本語", "中国語（簡体字）", "韓国語", "スペイン語", "フランス語", "ドイツ語"]
    )
    style = c2.selectbox("スタイル", ["自然な意訳", "原文に忠実", "ビジネス向け", "カジュアル"])
    explain = st.checkbox("ニュアンスや訳し分けのポイントも解説する")

    prompt = f"""次の文章を{lang}に翻訳してください。
- スタイル: {style}
{"- 翻訳の後に「解説」見出しで、訳し方のポイントや注意すべきニュアンスを日本語で簡潔に説明してください。" if explain else "- 翻訳文のみを出力してください。"}

### 原文
{text}"""
    system = build_system("あなたはプロの翻訳者です。", use_style=False)
    clicked = st.button("翻訳する", type="primary")
    _run("translate", f"翻訳（→{lang}）", clicked, clicked and require_text(text, "翻訳したい文章"), prompt, system)


# ---------------------------------------------------------------- SNS
SNS_RULES = {
    "X（Twitter）": "全角140文字以内。冒頭で惹きつける。",
    "Instagram": "最初の1〜2行で惹きつけ、改行で読みやすく。ハッシュタグは末尾にまとめる。",
    "Threads": "500文字以内。会話的で親しみやすく。",
    "LinkedIn": "プロフェッショナルなトーン。学びや気づきを中心に。",
    "Facebook": "ストーリー性のある投稿。",
    "note 告知": "記事への誘導文として、読みたくなる要約と一言を添える。",
}


def sns() -> None:
    st.header("📱 SNS 投稿作成")
    content = st.text_area("投稿したい内容・伝えたいこと *", height=150)
    c1, c2, c3 = st.columns(3)
    platform = c1.selectbox("プラットフォーム", list(SNS_RULES))
    purpose = c2.selectbox(
        "目的", ["共感を得たい", "情報を届けたい", "宣伝・告知", "フォロワーを増やしたい", "雑談・日常"]
    )
    count = c3.number_input("案の数", 1, 5, 3)
    c4, c5 = st.columns(2)
    hashtags = c4.checkbox("ハッシュタグを付ける", value=True)
    emoji = c5.checkbox("絵文字を使う", value=True)

    prompt = f"""{platform} 向けの投稿文を{count}案作成してください。

- 内容: {content}
- 目的: {purpose}
- プラットフォームのルール: {SNS_RULES[platform]}
- ハッシュタグ: {"付ける（3〜5個程度）" if hashtags else "付けない"}
- 絵文字: {"適度に使う" if emoji else "使わない"}

各案に「案1」などの見出しを付け、案ごとに切り口を変えてください。"""
    system = build_system("あなたは SNS マーケティングに精通したコピーライターです。")
    clicked = st.button("投稿文を生成", type="primary")
    _run("sns", f"SNS投稿（{platform}）", clicked, clicked and require_text(content, "投稿したい内容"), prompt, system)


# ---------------------------------------------------------------- タイトル・コピー
def titles() -> None:
    st.header("💡 タイトル・キャッチコピー")
    content = st.text_area("内容・商品・記事の概要 *", height=150)
    c1, c2, c3 = st.columns(3)
    kind = c1.selectbox(
        "種類",
        [
            "ブログ記事タイトル",
            "キャッチコピー",
            "メール件名",
            "YouTube 動画タイトル",
            "商品名・サービス名",
            "プレゼン資料タイトル",
        ],
    )
    direction = c2.selectbox(
        "方向性",
        [
            "おまかせ（バラエティ豊かに）",
            "数字を使う",
            "問いかけ型",
            "ベネフィット訴求",
            "意外性・インパクト",
            "シンプル・上品",
        ],
    )
    count = c3.slider("案の数", 3, 20, 10)

    prompt = f"""次の内容に対する「{kind}」を{count}案作成してください。

- 内容: {content}
- 方向性: {direction}

番号付きリストで出力し、最後に「おすすめ TOP3」とその理由を簡潔に添えてください。"""
    system = build_system("あなたは数々のヒットを生んだコピーライターです。")
    clicked = st.button("アイデアを出す", type="primary")
    _run("titles", kind, clicked, clicked and require_text(content, "内容"), prompt, system)


# ---------------------------------------------------------------- 議事録
def minutes() -> None:
    st.header("🗂️ 議事録・メモ整形")
    memo = st.text_area(
        "会議メモ・文字起こし *", height=250, placeholder="走り書きのメモや文字起こしをそのまま貼り付けてOK"
    )
    c1, c2, c3 = st.columns(3)
    title = c1.text_input("会議名")
    date = c2.text_input("日時")
    members = c3.text_input("参加者")
    fmt = st.radio("形式", ["議事録（標準）", "要点のみの簡易版", "日報・週報"], horizontal=True)

    prompt = f"""次のメモを「{fmt}」の形式に整理してください。

- 会議名: {title or "メモから推測、なければ空欄"}
- 日時: {date or "不明"}
- 参加者: {members or "メモから推測"}

構成例: 概要 / 議題ごとの議論内容 / 決定事項 / ToDo（担当・期限）/ 次回予定。
メモに書かれていないことは創作せず、不明な点は「要確認」としてください。

### メモ
{memo}"""
    system = build_system("あなたは優秀な秘書です。", use_style=False)
    clicked = st.button("整形する", type="primary")
    _run("minutes", f"議事録（{fmt}）", clicked, clicked and require_text(memo, "会議メモ"), prompt, system)


# ---------------------------------------------------------------- 自由チャット
def chat() -> None:
    st.header("💬 ライティング相談チャット")
    st.caption("文章の相談、アイデア出し、壁打ちなど自由にどうぞ。")
    if st.button("会話をリセット"):
        st.session_state.chat_messages = []
        st.rerun()

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])

    if user_input := st.chat_input("メッセージを入力"):
        st.session_state.chat_messages.append({"role": "user", "text": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        contents = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]}
            for m in st.session_state.chat_messages
        ]
        s = settings()
        system = build_system(
            "あなたはユーザーの文章作成を手伝う頼れる相棒です。会話形式で、必要に応じて質問を返しながら手伝ってください。"
        )
        with st.chat_message("assistant"):
            try:
                reply = st.write_stream(stream_text(s["api_key"], s["model"], contents, system, s["temperature"]))
            except Exception as e:
                st.error(f"エラー: {e}{error_hint(e)}")
                st.session_state.chat_messages.pop()
                return
        st.session_state.chat_messages.append({"role": "assistant", "text": reply})


# ---------------------------------------------------------------- 履歴
def history() -> None:
    st.header("📜 生成履歴")
    st.caption(f"履歴は自動で `{HISTORY_FILE}` に保存され、次回起動時も残ります。")
    items = st.session_state.history
    if not items:
        st.info("まだ履歴はありません。")
        return
    c1, c2, c3 = st.columns(3)
    all_md = "\n\n---\n\n".join(f"## {h['time']} {h['feature']}\n\n{h['output']}" for h in items)
    c1.download_button("⬇️ Markdown でダウンロード", all_md, "history.md", "text/markdown")
    c2.download_button(
        "⬇️ JSON でダウンロード",
        json.dumps(items, ensure_ascii=False, indent=2),
        "history.json",
        "application/json",
    )
    with c3.popover("🗑️ 履歴をすべて消去"):
        st.write("ファイルからも削除され、元に戻せません。")
        if st.button("消去する", type="primary"):
            st.session_state.history = []
            save_history()
            st.rerun()
    query = st.text_input("🔎 検索")
    for i, h in enumerate(items):
        if query and query not in h["output"] and query not in h["feature"]:
            continue
        with st.expander(f"{h['time']}｜{h['feature']}｜{h['output'][:40].replace(chr(10), ' ')}…"):
            st.markdown(h["output"])
            p1, p2 = st.columns([4, 1])
            with p1.popover("入力したプロンプトを見る"):
                st.text(h["prompt"])
            if p2.button("この履歴を削除", key=f"del_{i}_{h['time']}"):
                items.pop(i)
                save_history()
                st.rerun()
