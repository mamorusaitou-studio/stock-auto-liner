import requests
import os
import time
from datetime import datetime, timezone

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

        _, now = clean[-1]
        _, prev = clean[-2]

        year = datetime.now(timezone.utc).year
        ytd = now

        for t, p in clean:
            if datetime.fromtimestamp(t, timezone.utc).year >= year:
                ytd = p
                break

        return now, prev, ytd

    except:
        return None

# ==========================================
# 行生成
# ==========================================
def make_row(name, now, prev, ytd, ticker):
    day = (now - prev) / prev * 100
    ytdp = (now - ytd) / ytd * 100

    color = "#00C853" if day > 0 else "#D50000"

    if ticker == "^VIX":
        color = "#FF6D00" if day > 0 else "#00C853"

    return {
        "type": "box",
        "layout": "baseline",
        "contents": [
            {"type": "text", "text": name, "size": "sm", "flex": 2},
            {"type": "text", "text": f"{now:.1f}", "size": "sm", "flex": 2, "align": "end"},
            {"type": "text", "text": f"{day:+.1f}%", "size": "sm", "flex": 2, "align": "end", "color": color},
            {"type": "text", "text": f"{ytdp:+.1f}%", "size": "sm", "flex": 2, "align": "end"}
        ]
    }

# ==========================================
# Flex作成
# ==========================================
def build_flex():
    rows = []

    for ticker, name in INDICES.items():
        data = get_price(ticker)
        if not data:
            continue

        now, prev, ytd = data
        rows.append(make_row(name, now, prev, ytd, ticker))
        time.sleep(0.4)

    return {
        "type": "flex",
        "altText": "米国市場レポート",
        "contents": {
            "type": "bubble",
            "size": "giga",
            "body": {
                "type": "box",
                "layout": "vertical",
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
                        "type": "separator",
                        "margin": "md"
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

    res = requests.post(url, headers=headers, json=payload)
    print(res.status_code, res.text)

# ==========================================
# 実行
# ==========================================
if __name__ == "__main__":
    send_line()
