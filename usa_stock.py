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
    "^GSPC": ("S&P 500", "米国株の体温計。"),
    "^NDX": ("Nasdaq 100", "ハイテク株の象徴。"),
    "^SOX": ("SOX指数", "半導体セクターの勢い。"),
    "^RUT": ("ラッセル2000", "米国の小型株。"),
    "GC=F": ("ゴールド", "安全資産。金。"),
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
    try:
        requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
    except: pass

def get_finance_data(ticker):
    """
    ChatGPTの成功パターンをベースに、階層エラーを完全に修正したロジック
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return None
        
        data = res.json()
        
        # 階層の取得をリスト/辞書の型に合わせて安全に行う
        result = data['chart']['result']
        timestamps = result.get('timestamp', [])
        indicators = result.get('indicators', {})
        quote = indicators.get('quote', [{}]) # ここが修正ポイント
        prices = quote.get('close', [])

        # 有効なデータのみ抽出
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
    except:
        return None

def get_market_summary():
    report_time = datetime.now().strftime('%Y/%m/%d %H:%M')
    text = f"【🧭 米国市場レポート】\n{report_time}\n"
    
    for ticker, (name, desc) in INDICES.items():
        res = get_finance_data(ticker)
        if not res:
            text += f"\n◆ {name}\n   データ取得失敗\n"
            continue
            
        now, prev, ytd = res
        day_pct = (now - prev) / prev * 100
        ytd_pct = (now - ytd) / ytd * 100
        
        # 10倍表示補正（金利のみ）
        val = now
        if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10
        unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
        
        # アイコン判定
        if ticker == "^VIX":
            day_icon = "😱" if day_pct > 0 else "😌"
        elif ticker in ["^TNX", "^US2Y"]:
            day_icon = "📈" if day_pct > 0 else "📉"
        else:
            day_icon = "🚀" if day_pct > 0 else "💦"
        
        ytd_icon = "🔥" if ytd_pct > 0 else "❄️"

        text += f"\n◆ {name}\n"
        text += f"   {val:,.2f}{unit} ({day_icon} {day_pct:+.2f}%)\n"
        text += f"   ┗ 年初来: {ytd_icon} {ytd_pct:+.2f}%\n"
        text += f"   └ {desc}\n"
        time.sleep(0.3)

    return text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
