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
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = res.json()
        
        # 確実に数字を取るための最短ルート
        result = data['chart']['result']
        prices = result['indicators']['quote']['close']
        # Noneを除去
        valid_prices = [p for p in prices if p is not None]
        
        if len(valid_prices) >= 2:
            now = valid_prices[-1]
            prev = valid_prices[-2]
            return now, prev
        return None
    except:
        return None

def main():
    report_time = datetime.now().strftime('%m/%d %H:%M')
    msg = f"【🧭 米国市場】\n{report_time}\n"
    
    for ticker, name in INDICES.items():
        res = get_data(ticker)
        if res:
            now, prev = res
            diff = ((now - prev) / prev) * 100
            
            # 表示調整
            val = now
            if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10
            unit = "%" if ticker in ["^TNX", "^US2Y"] else ("pt" if ticker == "^VIX" else "")
            
            icon = "🚀" if diff > 0 else "💦"
            if ticker == "^VIX": icon = "😱" if diff > 0 else "😌"
            
            msg += f"\n◆ {name}\n   {val:,.2f}{unit} ({icon} {diff:+.2f}%)"
        
        time.sleep(0.5)

    if LINE_TOKEN and USER_ID:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
        payload = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
        requests.post(url, headers=headers, json=payload, timeout=10)

if __name__ == "__main__":
    main()
