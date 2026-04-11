import requests
import os
import time
from datetime import datetime

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

INDICES = {
    "^GSPC": "S&P 500",
    "^NDX": "Nasdaq 100",
    "^SOX": "SOX指数",
    "^RUT": "ラッセル2000",
    "GC=F": "ゴールド",
    "CL=F": "WTI原油",
    "^TNX": "米国10年金利",
    "^US2Y": "米国2年金利",
    "^VIX": "VIX指数"
}

def get_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            return f"HTTP {res.status_code}"

        data = res.json()
        
        # ChatGPTが指摘した「」を確実に使う構造
        chart = data.get('chart', {})
        result_list = chart.get('result', [])
        if not result_list: return "No Result"
        
        main_result = result_list
        indicators = main_result.get('indicators', {})
        quote_list = indicators.get('quote', [])
        if not quote_list: return "No Quote"
        
        prices = quote_list.get('close', [])
        valid_prices = [p for p in prices if p is not None]
        
        if len(valid_prices) < 2: return "No Data"
        
        return valid_prices[-1], valid_prices[-2]
    except Exception as e:
        return str(e)

def main():
    report_time = datetime.now().strftime('%m/%d %H:%M')
    msg = f"【🧭 米国市場：検証報告】\n{report_time}\n"
    
    for ticker, name in INDICES.items():
        res = get_data(ticker)
        
        if isinstance(res, tuple):
            now, prev = res
            diff = ((now - prev) / prev) * 100
            val = now
            if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10
            msg += f"\n◆ {name}\n   {val:,.2f} ({diff:+.2f}%)"
        else:
            # 取得失敗した場合、その理由（エラー名）をLINEに載せる
            msg += f"\n◆ {name}\n   取得失敗: {res}"
        
        time.sleep(0.3)

    if LINE_TOKEN and USER_ID:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
        payload = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
        requests.post(url, headers=headers, json=payload, timeout=10)

if __name__ == "__main__":
    main()
