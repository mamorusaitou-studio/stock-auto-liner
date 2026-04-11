import yfinance as yf
import requests
import json
import os
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
            # 最新の仕様に合わせてデータをダウンロード
            df = yf.download(ticker, start=f"{current_year}-01-01", progress=False, auto_adjust=True)
            
            if df.empty or len(df) < 1:
                df = yf.download(ticker, period="5d", progress=False, auto_adjust=True)

            if df.empty:
                perf_text += f"\n◆ {name}\n   データ取得不能\n"
                continue

            # 【重要】yfinanceのマルチインデックス対策（平坦化）
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 確実に数値として取得
            close_now = float(df['Close'].iloc[-1])
            
            # 前日比の計算
            day_pct = 0.0
            day_arrow = "―"
            if len(df) >= 2:
                close_prev = float(df['Close'].iloc[-2])
                day_pct = ((close_now - close_prev) / close_prev) * 100
                day_arrow = "🚀" if day_pct > 0 else "💦"
                if ticker == "^TNX": day_arrow = "📈" if day_pct > 0 else "📉"

            # 年初来の計算
            close_ytd = float(df['Close'].iloc)
            ytd_pct = ((close_now - close_ytd) / close_ytd) * 100
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            # 表示調整（金利）
            val = close_now / 10 if ticker == "^TNX" else close_now
            unit = "%" if ticker == "^TNX" else ""

            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"
            perf_text += f"   └ {desc}\n"

        except Exception as e:
            # 何が起きたか特定するためにエラー内容を少し出す
            perf_text += f"\n◆ {name}\n   計算エラー({type(e).__name__})\n"
            
    return perf_text

# エラー対策で pandas もインポート
import pandas as pd

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
