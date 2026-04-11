import requests
import json
import os
import time
from datetime import datetime, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

INDICES = {"^GSPC": "S&P 500", "^VIX": "VIX指数"} # テスト用に絞ってもOKです

def get_finance_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        
        # 【デバッグ用ログ】中身をすべて出力して、失敗の原因を特定する
        print(f"--- DEBUG [{ticker}] ---")
        print(f"Status: {res.status_code}")
        
        if res.status_code != 200:
            return None

        data = res.json()
        # ここでデータの深い階層をチェック
        if 'chart' in data and data['chart']['result'] is not None:
            result = data['chart']['result']
            prices = result['indicators']['quote'].get('close', [])
            clean_prices = [p for p in prices if p is not None]
            
            print(f"Data length: {len(clean_prices)}") # 何件取れたか表示
            
            if len(clean_prices) >= 2:
                return clean_prices[-1], clean_prices[-2]
        else:
            print(f"Error: {data.get('chart', {}).get('error')}")
            
        return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

if __name__ == "__main__":
    # まずは1銘柄だけテスト実行
    ticker = "^GSPC"
    res = get_finance_data(ticker)
    
    if res:
        now, prev = res
        diff = ((now - prev) / prev) * 100
        message = f"【テスト】{ticker}\n現在: {now:,.2f}\n前日比: {diff:+.2f}%"
        print("Success:", message)
        # ログで成功を確認したら、LINE送信も実行
        # requests.post(...) # LINE送信コードをここに
    else:
        print("Final Result: Failed to fetch data.")
