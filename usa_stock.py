import yfinance as yf
import requests
import json
import os
import numpy as np
import pandas as pd
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
            # 1. 1銘柄ずつ個別に、生データに近い形式でダウンロード
            df = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
            
            if df.empty:
                perf_text += f"\n◆ {name}\n   データ取得不能\n"
                continue

            # 2. 【ここが最重要】
            # 表形式（DataFrame）を .to_numpy() で完全に「ただの数字の塊」に分解します。
            # これにより、TypeError の原因だった「銘柄名ラベル」を物理的に消滅させます。
            # 終値（Close）の列を狙い撃ちし、flatten（平坦化）してリスト化します。
            
            # Close列が存在するかチェックし、無ければ一番右端を代用
            col_target = 'Close' if 'Close' in df.columns else df.columns[-1]
            raw_prices = df[col_target].to_numpy().flatten()
            
            # 純粋な数値(float)だけを抽出（NaNやゴミを排除）
            prices = [float(x) for x in raw_prices if np.isscalar(x) and not np.isnan(x)]
            
            if len(prices) < 2:
                perf_text += f"\n◆ {name}\n   データ不足\n"
                continue

            close_now = prices[-1]
            close_prev = prices[-2]
            
            # 年初来の特定（今年のデータだけを同様の手順で抽出）
            ytd_raw = df[df.index.year >= current_year][col_target].to_numpy().flatten()
            ytd_prices = [float(x) for x in ytd_raw if np.isscalar(x) and not np.isnan(x)]
            close_ytd = ytd_prices if ytd_prices else close_now

            # 3. 計算
            day_pct = ((close_now - close_prev) / close_prev * 100)
            ytd_pct = ((close_now - close_ytd) / close_ytd * 100)
            
            # 4. 表示補正
            val = close_now
            is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
            
            # 金利の表示補正（yfinanceの単位バラツキ対策）
            if ticker in ["^TNX", "^US2Y"] and val > 15:
                val = val / 10
            
            unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
            
            if day_pct > 0:
                day_arrow = "📈" if is_warn else "🚀"
            else:
                day_arrow = "📉" if is_warn else "💦"
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"

        except Exception:
            # 最終防衛ライン：エラー時は項目を飛ばしてLINE送信全体は維持する
            perf_text += f"\n◆ {name}\n   データ処理エラー\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
