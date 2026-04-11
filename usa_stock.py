print("★★★ THIS FILE IS RUNNING ★★★")
def get_price(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}

        res = requests.get(url, headers=headers, timeout=10)

        data = res.json()

        if not data.get("chart") or not data["chart"].get("result"):
            return None

        result = data["chart"]["result"][0]

        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]

        clean = [(t, p) for t, p in zip(timestamps, closes) if p is not None]

        if len(clean) < 2:
            return None

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
        print("ERROR:", ticker, e)
        return None
