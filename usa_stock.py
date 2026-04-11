import requests
import json
import os
import time
from datetime import datetime, timezone

# --- 設定 (GitHub Secrets) ---
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
    """
    階層構造を1段階ずつ、型を確認しながら確実に掘り進める防弾ロジック
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return None
        
        data = res.json()
        
        # 1. 'chart' -> 'result' (リスト) を取得
        chart_data = data.get('chart', {})
        result_list = chart_data.get('result')
        if not result_list or not isinstance(result_list, list): return None
        
        # 2. 0番目の要素にアクセス
        main_result = result_list
        timestamps = main_result.get('timestamp', [])
        
        # 3. 'indicators' -> 'quote' (リスト) を取得
        indicators = main_result.get('indicators', {})
        quote_list = indicators.get('quote')
        
        # 4. 【エラーの元】quote_list がリストであることを確認し、0番目を取り出す
        if not quote_list or not isinstance(quote_list, list) or len(quote_list) == 0:
            return None
        
        # ここでリストから「辞書」を取り出してから get を使う
        actual_data_dict = quote_list
        if not isinstance(actual_data_dict, dict): return None
        
        prices = actual_data_dict.get('close', [])
        
        # 5. 有効データ(None以外)を抽出
        clean_data = [(t, p) for t, p in zip(timestamps, prices) if p is not None]
        if len(clean_data) < 2: return None

        now = clean_data[-1]
        prev = clean_data[-2]
        
        # 年初来価格の特定
        current_year = datetime.now(timezone.utc).year
        ytd_val = now
        for t, p in clean_data:
            if datetime.fromtimestamp(t, tz=timezone.utc).year >= current_year:
                ytd_val = p
                break
        return now, prev, ytd_val

    except Exception as e:
        # エラーが出た場合、ログに詳細を残す（検証用）
        print(f"DEBUG: {ticker} failed with {type(e).__name__}: {e}")
        return None

def get_market_summary():
    report_time = datetime.now().strftime('%Y/%m/%d %H:%M')
    text = f"【🧭 米国市場レポート】\n{report_time}\n"
    
    success_count = 0
    for ticker, (name, desc) in INDICES.items():
        res = get_finance_data(ticker)
        if not res:
            text += f"\n◆ {name}\n   データ取得失敗\n"
            continue
            
        success_count += 1
        now, prev, ytd = res
        day_pct = (now - prev) / prev * 100
        ytd_pct = (now - ytd) / ytd * 100
        
        val = now
        if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10
        unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
        
        # アイコン判定
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
    if message:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
        payload = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        print(f"LINE Result Status: {res.status_code}")
