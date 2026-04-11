import yfinance as yf
import requests
import json
import os
import pandas as pd
from datetime import datetime

# ==========================================
# 設定エリア (GitHubのSecretsを使用)
# ==========================================
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

# 【米国市場専用】銘柄リスト
INDICES = {
    "^GSPC": ("S&P 500", "米国株の体温計。主要500社の動き。"),
    "^NDX": ("Nasdaq 100", "ハイテク株の象徴。金利上昇に弱い。"),
    "^SOX": ("SOX指数", "半導体セクターの勢い。景気の先行指標。"),
    "^RUT": ("ラッセル2000", "米国の小型株。景気に敏感に反応。"),
    "GC=F": ("ゴールド", "安全資産。有事やインフレ時に買われる。"),
    "CL=F": ("WTI原油", "エネルギー価格。ガソリン代や物価に直結。"),
    "^TNX": ("米国10年金利", "長期金利。これが高いと株価の重石に。"),
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
            # 最新のyfinance仕様対策: 確実に1次元の数値として取得する
            # group_by='ticker' を外して取得し、末尾の数値を取り出す
            data = yf.download(ticker, start=f"{current_year}-01-01", progress=False)
            
            if data.empty:
                data = yf.download(ticker, period="5d", progress=False)

            if data.empty:
                perf_text += f"\n◆ {name}\n   データ取得不能\n"
                continue

            # --- 最強の数値抽出処理 ---
            # どんな多重構造になっていても、一番右端の「Close」列を数値として引っこ抜く
            df_close = data['Close'].dropna()
            
            # Seriesの末尾から純粋な値(float)として取得
            prices = df_close.values.tolist()
            if isinstance(prices, list): # 二重リスト対策
                prices = [p for p in prices]
                
            close_now = float(prices[-1])
            close_prev = float(prices[-2]) if len(prices) >= 2 else close_now
            close_ytd = float(prices)
            # -------------------------

            day_pct = ((close_now - close_prev) / close_prev) * 100
            ytd_pct = ((close_now - close_ytd) / close_ytd) * 100
            
            val = close_now / 10 if ticker == "^TNX" else close_now
            unit = "%" if ticker == "^TNX" else ""
            
            day_arrow = "🚀" if day_pct > 0 else "💦"
            if ticker == "^TNX": day_arrow = "📈" if day_pct > 0 else "📉"
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"
            perf_text += f"   └ {desc}\n"

        except Exception as e:
            # 何が起きたか特定するためにエラー名を出す設定
            perf_text += f"\n◆ {name}\n   計算中...(エラー:{type(e).__name__})\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
