import yfinance as yf
import requests
import json
import os
import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================
# 設定エリア (GitHubのSecrets)
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
            # 1つずつ個別にダウンロード
            df = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
            
            if df.empty:
                perf_text += f"\n◆ {name}\n   データ取得失敗\n"
                continue

            # 【究極の防弾処理】
            # Close列を狙うが、万が一見つからなくても「一番最後の列」を数値として引っこ抜く。
            # values.flatten() でラベルや階層を粉砕して「ただの数字の列」に変換。
            target_col = df['Close'] if 'Close' in df.columns else df.iloc[:, -1]
            raw_prices = target_col.values.flatten()
            
            # 純粋な数値(float)だけを抽出
            prices = [float(x) for x in raw_prices if np.isscalar(x) and not np.isnan(x)]
            
            if len(prices) < 2:
                perf_text += f"\n◆ {name}\n   データ不足\n"
                continue

            close_now = prices[-1]
            close_prev = prices[-2]
            
            # 年初来データの特定（同じく力ずくで抽出）
            ytd_df = df[df.index.year >= current_year]
            if not ytd_df.empty:
                ytd_target = ytd_df['Close'] if 'Close' in ytd_df.columns else ytd_df.iloc[:, -1]
                ytd_raw = ytd_target.values.flatten()
                ytd_prices = [float(x) for x in ytd_raw if np.isscalar(x) and not np.isnan(x)]
                close_ytd = ytd_prices
            else:
                close_ytd = close_now

            # 計算
            day_pct = ((close_now - close_prev) / close_prev * 100)
            ytd_pct = ((close_now - close_ytd) / close_ytd * 100)
            
            # 表示補正
            val = close_now
            is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
            if ticker in ["^TNX", "^US2Y"] and val > 15: val /= 10 # 10倍表示対策
            
            unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
            day_arrow = ("📈" if day_pct > 0 else "📉") if is_warn else ("🚀" if day_pct > 0 else "💦")
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"

        except Exception:
            perf_text += f"\n◆ {name}\n   データ更新待ち\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
    
