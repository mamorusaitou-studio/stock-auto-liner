import yfinance as yf
import requests
import json
import os
import numpy as np
import pandas as pd
from datetime import datetime

# ==========================================
# 設定エリア (GitHubのSecretsを使用)
# ==========================================
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

# 【完全版】米国市場銘柄リスト
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
            # 1. 履歴を取得
            t = yf.Ticker(ticker)
            df = t.history(period="1y", auto_adjust=True)

            if df.empty:
                perf_text += f"\n◆ {name}\n   データ取得失敗\n"
                continue

            # 2. 【エラー回避の決定打】ラベルをすべて剥がし、純粋な数値の塊にする
            # どんな構造の DataFrame でも 'Close' 列を抜き出し、強制的に 1次元配列へ
            raw_close = df['Close'].to_numpy().flatten()
            
            # 3. NaN(空)を除外した純粋な数値リストを作成
            prices = [float(x) for x in raw_close if np.isscalar(x) and not np.isnan(x)]
            
            if len(prices) < 2:
                perf_text += f"\n◆ {name}\n   データ不足\n"
                continue

            close_now = prices[-1]
            close_prev = prices[-2]
            
            # 4. 年初来の取得 (インデックスの「年」でフィルタ)
            ytd_prices = df[df.index.year >= current_year]['Close'].to_numpy().flatten()
            valid_ytd = [float(x) for x in ytd_prices if np.isscalar(x) and not np.isnan(x)]
            close_ytd = valid_ytd if valid_ytd else close_now

            # 5. 騰落率の計算
            day_pct = ((close_now - close_prev) / close_prev * 100)
            ytd_pct = ((close_now - close_ytd) / close_ytd * 100)
            
            # 表示補正（金利の10倍対策）
            val = close_now
            if ticker in ["^TNX", "^US2Y"] and val > 10:
                val = val / 10
            
            unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
            
            # アイコン出し分け
            is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
            day_arrow = ("📈" if day_pct > 0 else "📉") if is_warn else ("🚀" if day_pct > 0 else "💦")
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"
            perf_text += f"   └ {desc}\n"

        except Exception as e:
            # どんなエラーが起きても止まらないようにし、種類を表示
            perf_text += f"\n◆ {name}\n   計算エラー({type(e).__name__})\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
