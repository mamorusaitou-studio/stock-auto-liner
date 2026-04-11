import requests
import json
import os
import time
from datetime import datetime

# ==========================================
# 設定エリア
# ==========================================
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

def send_line(message):
    if not LINE_TOKEN or not USER_ID: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, data=json.dumps(data))

def get_raw_finance_data(ticker):
    """ライブラリを使わず、Yahoo Financeから生の数字を直接引っこ抜く"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # 生の数字のリスト（終値）を取得
        prices = data['chart']['result']['indicators']['quote']['close']
        # 年初来を特定するためにタイムスタンプを取得
        timestamps = data['chart']['result']['timestamp']
        
        # 欠損値(None)を排除
        valid_data = [(t, p) for t, p in zip(timestamps, prices) if p is not None]
        return valid_prices_only(valid_data)
    except:
        return None

def valid_prices_only(data_list):
    if not data_list: return None
    current_year = datetime.now().year
    
    # 最新と前日
    close_now = data_list[-1]
    close_prev = data_list[-2] if len(data_list) >= 2 else close_now
    
    # 年初来
    ytd_price = close_now
    for t, p in data_list:
        if datetime.fromtimestamp(t).year >= current_year:
            ytd_price = p
            break
            
    return close_now, close_prev, ytd_price

def get_market_summary():
    perf_text = f"【🧭 米国：お宝市場レポート】\n{datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
    
    for ticker, (name, desc) in INDICES.items():
        result = get_raw_finance_data(ticker)
        
        if not result:
            perf_text += f"\n◆ {name}\n   データ取得失敗\n"
            continue
            
        now, prev, ytd = result
        
        # 騰落率計算
        day_pct = ((now - prev) / prev * 100)
        ytd_pct = ((now - ytd) / ytd * 100)
        
        # 表示調整
        val = now
        is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
        if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10 # 10倍表示補正
        
        unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
        day_arrow = ("📈" if day_pct > 0 else "📉") if is_warn else ("🚀" if day_pct > 0 else "💦")
        ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

        perf_text += f"\n◆ {name}\n"
        perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
        perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"
        
        time.sleep(0.5) # サーバー負荷対策

    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
