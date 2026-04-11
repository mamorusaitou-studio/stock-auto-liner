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

# 監視銘柄リスト
INDICES = {
    "^GSPC": ("S&P 500", "米国株の体温計。主要500社の動き。"),
    "^NDX": ("Nasdaq 100", "ハイテク株の象徴。金利上昇に弱い。"),
    "^SOX": ("SOX指数", "半導体セクターの勢い。景気の先行指標。"),
    "^RUT": ("ラッセル2000", "米国の小型株。景気に敏感に反応。"),
    "GC=F": ("ゴールド", "安全資産。有事やインフレ時に買われる。"),
    "CL=F": ("WTI原油", "エネルギー価格。ガソリン代や物価に直結。"),
    "^TNX": ("米国10年金利", "長期金利。これが高いと株価の重石に。"),
    "^US2Y": ("米国2年金利", "短期金利。FRBの動きを反映。"),
    "^VIX": ("VIX指数", "恐怖指数。市場の警戒感。")
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
            # 1. 銘柄ごとに個別にダウンロード（一括ダウンロードを避ける）
            # group_by='column'を指定することで、銘柄名などの余計な層を排除
            df = yf.download(ticker, period="1y", progress=False, group_by='column', auto_adjust=True)
            
            if df.empty:
                perf_text += f"\n◆ {name}\n   データ取得不能\n"
                continue

            # 2. 【最重要】Close列の中身を強制的に「ただの数字のリスト」へ変換
            # これで MultiIndex による TypeError を物理的に回避します
            prices = df['Close'].dropna().values.flatten().tolist()
            
            if len(prices) < 2:
                perf_text += f"\n◆ {name}\n   データ不足\n"
                continue

            close_now = float(prices[-1])
            close_prev = float(prices[-2])
            
            # 年初来価格の特定
            ytd_df = df[df.index.year >= current_year]
            ytd_prices = ytd_df['Close'].dropna().values.flatten().tolist()
            close_ytd = float(ytd_prices) if ytd_prices else close_now

            # 3. 騰落率の計算
            day_pct = ((close_now - close_prev) / close_prev) * 100
            ytd_pct = ((close_now - close_ytd) / close_ytd) * 100
            
            # 4. 表示調整
            val = close_now
            is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
            
            # 金利の表示補正
            if ticker in ["^TNX", "^US2Y"] and val > 10:
                val = val / 10
            
            unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
            
            # アイコン出し分け（金利/VIXは上がると📉、他は🚀）
            if day_pct > 0:
                day_arrow = "📈" if is_warn else "🚀"
            else:
                day_arrow = "📉" if is_warn else "💦"
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"
            perf_text += f"   └ {desc}\n"

        except:
            # どんな想定外が起きても、LINE送信全体を止めないためのガード
            perf_text += f"\n◆ {name}\n   計算エラー\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
