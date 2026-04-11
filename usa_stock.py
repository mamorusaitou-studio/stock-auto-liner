import requests
import json
import os
import time
from datetime import datetime, timezone

# ==========================================
# 設定エリア
# ==========================================
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

INDICES = {
    "^GSPC": ("S&P 500", "米国株の体温計。主要500社の動き。"),
    "^NDX": ("Nasdaq 100", "ハイテク株の象徴。金利上昇に弱い。"),
    "^SOX": ("SOX指数", "半導体セクターの勢い。景気の先行指標。"),
    "^RUT": ("ラッセル2000", "米国の小型株。景気に敏感に反応。"),
    "GC=F": ("ゴールド", "安全資産。有事やインフレ時に買われる。"),
    "CL=F": ("WTI原油", "エネルギー価格。物価に直結。"),
    "^TNX": ("米国10年金利", "長期金利。株価の重石。"),
    "^US2Y": ("米国2年金利", "短期金利。FRBの動きを反映。"),
    "^VIX": ("VIX指数", "恐怖指数。市場の警戒感。")
}

def send_line(message):
    if not LINE_TOKEN or not USER_ID: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, data=json.dumps(data))

def get_finance_data(ticker):
    """ライブラリを通さず、生の数字だけを確実に引っこ抜く"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        
        result = data['chart']['result']
        timestamps = result['timestamp']
        prices = result['indicators']['quote']['close']
        
        # 欠損値を除去
        clean_data = [(t, p) for t, p in zip(timestamps, prices) if p is not None]
        if len(clean_data) < 2: return None

        now = clean_data[-1]
        prev = clean_data[-2]
        
        # 年初来を特定
        current_year = datetime.now(timezone.utc).year
        ytd_val = now
        for t, p in clean_data:
            if datetime.fromtimestamp(t, tz=timezone.utc).year >= current_year:
                ytd_val = p
                break
        return now, prev, ytd_val
    except:
        return None

def get_market_summary():
    perf_text = f"【🧭 米国市場：お宝レポート】\n{datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
    
    for ticker, (name, desc) in INDICES.items():
        res = get_finance_data(ticker)
        if not res:
            perf_text += f"\n◆ {name}\n   データ取得失敗\n"
            continue
            
        now, prev, ytd = res
        day_pct = (now - prev) / prev * 100
        ytd_pct = (now - ytd) / ytd * 100
        
        # 金利/VIXの表示調整
        val = now
        if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10
        unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
        
        # アイコン
        is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
        day_arrow = ("📈" if day_pct > 0 else "📉") if is_warn else ("🚀" if day_pct > 0 else "💦")
        ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

        perf_text += f"\n◆ {name}\n"
        perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
        perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"
        perf_text += f"   └ {desc}\n"
        time.sleep(0.3)

    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
