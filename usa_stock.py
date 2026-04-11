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
        # 確実にデータが入っている「1年分」で取得
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = res.json()
        
        # ChatGPTが正解を出した「」を確実に指定する構造
        result = data['chart']['result']
        prices = result['indicators']['quote']['close']
        
        # Noneを除去した最新の2件
        valid_prices = [p for p in prices if p is not None]
        
        if len(valid_prices) >= 2:
            return valid_prices[-1], valid_prices[-2]
        return None
    except:
        return None

def main():
    report_time = datetime.now().strftime('%m/%d %H:%M')
    msg = f"【🧭 米国市場】\n{report_time}\n"
    
    count = 0
    for ticker, name in INDICES.items():
        res = get_data(ticker)
        if res:
            now, prev = res
            diff = ((now - prev) / prev) * 100
            
            # 金利の表示調整
            val = now
            if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10
            
            msg += f"\n◆ {name}\n   {val:,.2f} ({diff:+.2f}%)"
            count += 1
        time.sleep(0.2)

    if count > 0 and LINE_TOKEN and USER_ID:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
        payload = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
        requests.post(url, headers=headers, json=payload, timeout=10)

if __name__ == "__main__":
    main()
