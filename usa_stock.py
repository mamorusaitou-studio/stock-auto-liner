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
}

def get_price(ticker):
    print("START:", ticker)

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}

        res = requests.get(url, headers=headers, timeout=10)

        print("STATUS:", res.status_code)

        data = res.json()

        print("DATA CHECK:", "chart" in data)

        if not data.get("chart") or not data["chart"].get("result"):
            print("NO DATA:", ticker)
            return None

        result = data["chart"]["result"][0]

        timestamps = result.get("timestamp", [])
        closes = result.get("indicators", {}).get("quote", [])[0].get("close", [])

        print("DATA LENGTH:", len(closes))

        clean = [(t, p) for t, p in zip(timestamps, closes) if p is not None]

        if len(clean) < 2:
            print("NOT ENOUGH DATA:", ticker)
            return None

        _, now = clean[-1]
        _, prev = clean[-2]

        print("SUCCESS:", ticker)

        return now, prev, now

    except Exception as e:
        print("ERROR:", ticker, e)
        return None


def main():
    for ticker in INDICES:
        get_price(ticker)
        time.sleep(1)

    print("DONE")


if __name__ == "__main__":
    main()
