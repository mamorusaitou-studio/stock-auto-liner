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
            # データ取得
            df = yf.download(ticker, start=f"{current_year}-01-01", progress=False, auto_adjust=True)
            if df.empty:
                df = yf.download(ticker, period="5d", progress=False, auto_adjust=True)

            if df.empty:
                perf_text += f"\n◆ {name}\n   データ取得不能\n"
                continue

            # ---【最強のエラー対策】表から「純粋な数字」だけを引っこ抜く ---
            # 1. どんな形式で来ても「Close」列（または最初の列）を取得
            if 'Close' in df.columns:
                target_col = df['Close']
            else:
                target_col = df.iloc[:, 0]
            
            # 2. 表（Series）から純粋な値だけのリストに変換し、最後と最初を取得
            prices = target_col.values.flatten() # これでただの数字の羅列になる
            
            close_now = float(prices[-1])
            close_prev = float(prices[-2]) if len(prices) >= 2 else close_now
            close_ytd = float(prices)
            # ---------------------------------------------------------

            # 計算（ここでもし万が一エラーが出ても止まらないようにする）
            day_pct = ((close_now - close_prev) / close_prev * 100) if close_prev != 0 else 0
            ytd_pct = ((close_now - close_ytd) / close_ytd * 100) if close_ytd != 0 else 0
            
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
            # エラーが出た場合、その内容を極力短く表示
            err_msg = str(e)[:15]
            perf_text += f"\n◆ {name}\n   計算エラー({err_msg})\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
