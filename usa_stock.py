import requests
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
# データ取得（完全修正版）
# ==========================================
def get_price(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            print(f"HTTP ERROR {ticker}: {res.status_code}")
            return None

        data = res.json()

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]

        # None除外
        clean = [(t, p) for t, p in zip(timestamps, closes) if p is not None]

        if len(clean) < 2:
            return None

        # ← 正しく値取得
        _, now = clean[-1]
        _, prev = clean[-2]

        # 年初来
        year = datetime.now(timezone.utc).year
        ytd = now

        for t, p in clean:
            if datetime.fromtimestamp(t, timezone.utc).year >= year:
                ytd = p
                break

        return now, prev, ytd

    except Exception as e:
        print(f"ERROR {ticker}: {e}")
        return None

# ==========================================
# 1行（Flex用）
# ==========================================
def make_row(name, now, prev, ytd, ticker):
    day = (now - prev) / prev * 100
    ytdp = (now - ytd) / ytd * 100

    # 色設定
    color = "#00C853" if day > 0 else "#D50000"

    # VIXだけ特別
    if ticker == "^VIX":
        color = "#FF6D00" if day > 0 else "#00C853"

    return {
        "type": "box",
        "layout": "baseline",
        "spacing": "sm",
        "contents": [
            {"type": "text", "text": name, "size": "sm", "flex": 3},
            {"type": "text", "text": f"{now:.1f}", "size": "sm", "flex": 2, "align": "end"},
            {"type": "text", "text": f"{day:+.1f}%", "size": "sm", "flex": 2, "align": "end", "color": color},
            {"type": "text", "text": f"{ytdp:+.1f}%", "size": "sm", "flex": 2, "align": "end"}
        ]
    }

# ==========================================
# Flexメッセージ構築
# ==========================================
def build_flex():
    rows = []

    for ticker, name in INDICES.items():
        data = get_price(ticker)

        if not data:
            rows.append({
                "type": "text",
                "text": f"{name}: error",
                "size": "sm",
                "color": "#ff0000"
            })
            continue

        now, prev, ytd = data
        rows.append(make_row(name, now, prev, ytd, ticker))

        time.sleep(0.4)

    # 空対策
    if not rows:
        rows.append({
            "type": "text",
            "text": "データ取得失敗",
            "size": "sm",
            "color": "#ff0000"
        })

    return {
        "type": "flex",
        "altText": "米国市場レポート",
        "contents": {
            "type": "bubble",
            "size": "giga",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "US MARKET",
                        "weight": "bold",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "size": "xs",
                        "color": "#888888"
                    },
                    {
                        "type": "separator"
                    },
                    *rows
                ]
            }
        }
    }

# ==========================================
# LINE送信
# ==========================================
def send_line():
    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": USER_ID,
        "messages": [build_flex()]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text)
    except Exception as e:
        print("LINE ERROR:", e)

# ==========================================
# 実行
# ==========================================
if __name__ == "__main__":
    send_line()
