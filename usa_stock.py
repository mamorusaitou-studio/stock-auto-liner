import yfinance as yf
import requests
import json
import os
from datetime import datetime, timedelta

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
            # 1. 銘柄ごとに個別に、確実にデータを取得
            t = yf.Ticker(ticker)
            # 年初来を計算するため、1年分を確保
            df = t.history(period="1y", auto_adjust=True)

            if df.empty or len(df) < 2:
                perf_text += f"\n◆ {name}\n   データ取得失敗\n"
                continue

            # 2. 最新値と前日値を取得（確実にClose列から）
            close_now = float(df['Close'].iloc[-1])
            close_prev = float(df['Close'].iloc[-2])
            
            # 3. 年初来（今年の最初の営業日）の値を特定
            ytd_df = df[df.index >= f"{current_year}-01-01"]
            if ytd_df.empty:
                close_ytd = close_now
            else:
                close_ytd = float(ytd_df['Close'].iloc)

            # 4. 騰落率の計算
            day_pct = ((close_now - close_prev) / close_prev) * 100
            ytd_pct = ((close_now - close_ytd) / close_ytd) * 100
            
            # 金利の表示補正（10倍表示対策）
            val = close_now
            if ticker == "^TNX" and val > 10:
                val = val / 10
            unit = "%" if ticker == "^TNX" else ""
            
            day_arrow = "🚀" if day_pct > 0 else "💦"
            if ticker == "^TNX": day_arrow = "📈" if day_pct > 0 else "📉"
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            # 5. 表示
            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"
            perf_text += f"   └ {desc}\n"

        except Exception:
            perf_text += f"\n◆ {name}\n   計算エラー（調整中）\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
    
