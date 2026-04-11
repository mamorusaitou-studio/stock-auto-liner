import requests
import json
import os
import time
from datetime import datetime, timezone

# ==========================================
# 設定
# ==========================================
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

INDICES = {
    "^GSPC": "S&P500",
    "^NDX": "NASDAQ100",
    "^SOX": "SOX",
    "^RUT": "RUSSELL2000",
    "GC=F": "GOLD",
    "CL=F": "WTI",
    "^TNX": "10Y",
    "^US2Y": "2Y",
    "^VIX": "VIX"
}

# ==========================================
# LINE送信（UTF-8完全対応）
# ==========================================
def send_line(message):
    if not LINE_TOKEN or not USER_ID:
        print("LINE未設定")
        return

    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8"
    }

    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": message}]
    }

    try:
        res = requests.post(
            url,
            headers=headers,
            json=payload  # ← ここ重要（dataじゃなくjson）
        )

        if res.status_code != 200:
            print("LINE送信失敗:", res.text)

    except Exception as e:
        print("LINE送信エラー:", e)

# ==========================================
# データ取得
# ==========================================
def get_price(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        res = requests.get(url, timeout=10)

        data = res.json()
        result = data["chart"]["result"][0]

        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]

        clean = [(t, p) for t, p in zip(timestamps, closes) if p]

        if len(clean) < 2:
            return None

        # ← 修正済
        _, now = clean[-1]
        _, prev = clean[-2]

        # 年初
        year = datetime.now(timezone.utc).year
        ytd = now

        for t, p in clean:
            if datetime.fromtimestamp(t, timezone.utc).year >= year:
                ytd = p
                break

        return now, prev, ytd

    except Exception as e:
        print(f"{ticker} error:", e)
        return None

# ==========================================
# フォーマット（LINE最適化）
# ==========================================
def format_line(name, now, prev, ytd, ticker):
    day = (now - prev) / prev * 100
    ytdp = (now - ytd) / ytd * 100

    # シンプル化（崩れ防止）
    icon = "+" if day > 0 else "-"
    
    # VIX特別
    if ticker == "^VIX":
        icon = "!!" if day > 0 else "OK"

    return f"{name}: {now:.2f} ({icon}{day:+.2f}%) YTD:{ytdp:+.1f}%"

# ==========================================
# メイン
# ==========================================
def build_message():
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append(f"[US Market] {now}")

    for ticker, name in INDICES.items():
        data = get_price(ticker)

        if not data:
            lines.append(f"{name}: error")
            continue

        now_p, prev_p, ytd_p = data
        line = format_line(name, now_p, prev_p, ytd_p, ticker)
        lines.append(line)

        time.sleep(0.5)

    # LINE制限対策（長すぎ防止）
    msg = "\n".join(lines)
    return msg[:4900]

# ==========================================
# 実行
# ==========================================
if __name__ == "__main__":
    msg = build_message()
    print(msg)
    send_line(msg)
