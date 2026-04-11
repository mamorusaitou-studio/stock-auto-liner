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

        _, now = clean[-1]
        _, prev = clean[-2]

        year = datetime.now(timezone.utc).year
        ytd = now

        for t, p in clean:
            if datetime.fromtimestamp(t, timezone.utc).year >= year:
                ytd = p
                break

        return now, prev, ytd

    except Exception as e:
        print("ERROR:", ticker, e)
        return None


def build_message():
    lines = []
    lines.append("US MARKET\n")

    for ticker, name in INDICES.items():
        data = get_price(ticker)

        if not data:
            lines.append(f"{name}: error")
            continue

        now, prev, ytd = data

        day = (now - prev) / prev * 100
        ytdp = (now - ytd) / ytd * 100

        lines.append(f"{name}: {now:.1f} ({day:+.1f}%) YTD:{ytdp:+.1f}%")

        time.sleep(0.3)

    return "\n".join(lines)


def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }

    res = requests.post(url, headers=headers, json=payload)
    print(res.status_code, res.text)


if __name__ == "__main__":
    msg = build_message()
    send_line(msg)
