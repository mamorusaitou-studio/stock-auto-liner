import requests
import json
import os
import time
from datetime import datetime, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

INDICES = {
    "^GSPC": ("S&P 500", "米国株の体温計。"),
    "^NDX": ("Nasdaq 100", "ハイテク株の象徴。"),
    "^SOX": ("SOX指数", "半導体セクター。"),
    "^RUT": ("ラッセル2000", "米国小型株。"),
    "GC=F": ("ゴールド", "安全資産。"),
    "CL=F": ("WTI原油", "エネルギー価格。"),
    "^TNX": ("米国10年金利", "長期金利。"),
    "^US2Y": ("米国2年金利", "短期金利。"),
    "^VIX": ("VIX指数", "恐怖指数。")
}

def get_finance_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return None
        
        data = res.json()
        
        # 1. 階層を一つずつ変数に代入して確実に掘る
        chart = data.get('chart', {})
        results = chart.get('result', [])
        if not results: return None
        
        main_result = results
        timestamps = main_result.get('timestamp', [])
        
        indicators = main_result.get('indicators', {})
        quote_list = indicators.get('quote', [])
        
        # 2. 【ここが修正の核心】
        # quote_listはリストなので、まず0番目の辞書を取り出す
        if not quote_list or not isinstance(quote_list, list): return None
        actual_data_dict = quote_list 
        
        # 3. 辞書から 'close' リストを取得
        prices = actual_data_dict.get('close', [])
        
        # 有効な数字のみ抽出
        clean_data = [(t, p) for t, p in zip(timestamps, prices) if p is not None]
        if len(clean_data) < 2: return None

        now = clean_data[-1]
        prev = clean_data[-2]
        
        # 年初来価格
        current_year = datetime.now(timezone.utc).year
        ytd_val = now
        for t, p in clean_data:
            if datetime.fromtimestamp(t, tz=timezone.utc).year >= current_year:
                ytd_val = p
                break
        return now, prev, ytd_val

    except Exception as e:
        # 失敗した場合はログに出すが、LINE送信は止めない
        print(f"DEBUG: {ticker} failed with {type(e).__name__}: {e}")
        return None

def get_market_summary():
    report_time = datetime.now().strftime('%Y/%m/%d %H:%M')
    text = f"【🧭 米国市場レポート】\n{report_time}\n"
    
    success_count = 0
    for ticker, (name, desc) in INDICES.items():
        res = get_finance_data(ticker)
        if not res:
            text += f"\n◆ {name}\n   データ更新待ち\n"
            continue
            
        success_count += 1
        now, prev, ytd = res
        day_pct = (now - prev) / prev * 100
        ytd_pct = (now - ytd) / ytd * 100
        
        val = now
        if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10
        unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
        
        is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
        day_arrow = ("📈" if day_pct > 0 else "📉") if is_warn else ("🚀" if day_pct > 0 else "💦")
        if ticker == "^VIX": day_arrow = "😱" if day_pct > 0 else "😌"

        text += f"\n◆ {name}\n"
        text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
        text += f"   ┗ 年初来: {'🔥' if ytd_pct > 0 else '❄️'} {ytd_pct:+.2f}%\n"
        time.sleep(0.3)

    return text if success_count > 0 else None

if __name__ == "__main__":
    message = get_market_summary()
    if message and LINE_TOKEN and USER_ID:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
        payload = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        print(f"LINE Result Status: {res.status_code}")
