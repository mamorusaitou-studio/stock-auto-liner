import yfinance as yf
import requests
import json
import os
import pandas as pd
from datetime import datetime

# ==========================================
# 設定エリア
# ==========================================
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

# 参照する銘柄
INDICES = {
    "^GSPC": ("S&P 500", "米国株の体温計。"),
    "^NDX": ("Nasdaq 100", "ハイテク株の象徴。"),
    "^SOX": ("SOX指数", "半導体セクター。"),
    "^RUT": ("ラッセル2000", "小型株。"),
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

def get_market_summary():
    current_year = datetime.now().year
    perf_text = f"【🧭 米国：お宝市場レポート】\n{datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
    
    for ticker, (name, desc) in INDICES.items():
        try:
            # 1つずつ個別にダウンロードし、余計なIndex（銘柄名）を列に入れない設定にする
            df = yf.download(ticker, period="1y", progress=False, group_by='ticker', auto_adjust=True)
            
            if df.empty:
                perf_text += f"\n◆ {name}\n   取得失敗\n"
                continue

            # 【ここが重要】参照先を「一番シンプルな数列」に固定
            # これで yfinance の仕様変更（MultiIndex）の影響を完全に遮断します
            prices = df['Close'].dropna().values.flatten().tolist()
            
            if len(prices) < 2:
                perf_text += f"\n◆ {name}\n   データ不足\n"
                continue

            close_now = float(prices[-1])
            close_prev = float(prices[-2])
            
            # 年初来を特定
            ytd_df = df[df.index.year >= current_year]
            ytd_prices = ytd_df['Close'].dropna().values.flatten().tolist()
            close_ytd = float(ytd_prices) if ytd_prices else close_now

            # 計算
            day_pct = ((close_now - close_prev) / close_prev * 100)
            ytd_pct = ((close_now - close_ytd) / close_ytd * 100)
            
            # 金利の表示補正
            val = close_now
            if ticker in ["^TNX", "^US2Y"] and val > 10:
                val = val / 10
            
            unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
            is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
            day_arrow = ("📈" if day_pct > 0 else "📉") if is_warn else ("🚀" if day_pct > 0 else "💦")
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"

        except:
            perf_text += f"\n◆ {name}\n   計算エラー\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
