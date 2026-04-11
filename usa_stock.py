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
    "^VIX": "VIX指数"
}

def get_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        
        # 1. 'result' という「リスト」から、0番目の中身（辞書）を取り出す
        res_list = data['chart']['result']
        main_data = res_list # ← ここで を使ってリストを剥く
        
        # 2. 'quote' という「リスト」から、0番目の中身（辞書）を取り出す
        indicators = main_data['indicators']
        quote_list = indicators['quote']
        actual_prices_dict = quote_list # ← ここでも を使ってリストを剥く
        
        # 3. 終値のリストを取得
        prices = actual_prices_dict['close']
        
        # Noneを除いた最新2件
        valid = [p for p in prices if p is not None]
        if len(valid) >= 2:
            return valid[-1], valid[-2]
        return None
    except Exception as e:
        # ログに何がダメだったか出力する（GitHub Actionsで見れます）
        print(f"DEBUG {ticker}: {e}")
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
            val = now
            if ticker == "^TNX" and val > 15: val /= 10
            
            # アイコン
            icon = "🚀" if diff > 0 else "💦"
            if ticker == "^VIX": icon = "😱" if diff > 0 else "😌"
            
            msg += f"\n◆ {name}\n   {val:,.2f} ({icon} {diff:+.2f}%)"
            count += 1
        time.sleep(0.3)

    if count > 0 and LINE_TOKEN and USER_ID:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
        payload = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
        requests.post(url, headers=headers, json=payload, timeout=10)

if __name__ == "__main__":
    main()
