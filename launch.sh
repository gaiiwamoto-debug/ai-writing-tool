#!/bin/bash
# AI ライティングツールを起動してブラウザで開く。すでに起動中なら開くだけ。
# デスクトップの「AIライティングツール.app」から呼ばれる。
cd "$(dirname "$0")" || exit 1
PORT=8501
URL="http://localhost:$PORT"
LOG="$HOME/Library/Logs/ai-writing-tool.log"

if ! curl -sf "$URL/_stcore/health" >/dev/null 2>&1; then
    nohup .venv/bin/streamlit run app.py --server.headless true --server.address localhost --server.port "$PORT" >"$LOG" 2>&1 &
    for _ in $(seq 1 30); do
        curl -sf "$URL/_stcore/health" >/dev/null 2>&1 && break
        sleep 1
    done
fi

if curl -sf "$URL/_stcore/health" >/dev/null 2>&1; then
    open "$URL"
else
    osascript -e "display alert \"AI ライティングツールを起動できませんでした\" message \"ログ: $LOG\""
fi
