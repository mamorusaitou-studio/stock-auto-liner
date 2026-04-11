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

# 監視銘柄（2年金利とVIXを確実に追加）
INDICES = {
    "^GSPC": ("S&P 500", "米国株の体温計。"),
    "^NDX": ("Nasdaq 100", "ハイテク株の象徴。"),
    "^SOX": ("SOX指数", "半導体セクター。"),
    "^RUT": ("ラッセル2000", "米国小型株。"),
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
            # 1つずつ個別にダウンロード。
            # group_by='ticker'をあえて外して取得し、構造を単純化します。
            df = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
            
            if df.empty:
                perf_text += f"\n◆ {name}\n   データ取得不能\n"
                continue

            # 【防弾処理】どんな多重構造が来ても、強制的に「Close」列の数値リストに変換
            # flatten()で全ての層を無視して「ただの数字の列」にします
            if 'Close' in df.columns:
                close_values = df['Close'].dropna().values.flatten().tolist()
            else:
                # Closeが見当たらない場合、一番右端（通常は終値）を数値化
                close_values = df.iloc[:, -1].dropna().values.flatten().tolist()
            
            if len(close_values) < 2:
                perf_text += f"\n◆ {name}\n   データ不足\n"
                continue

            close_now = float(close_values[-1])
            close_prev = float(close_values[-2])
            
            # 年初来の取得
            ytd_df = df[df.index.year >= current_year]
            if not ytd_df.empty:
                if 'Close' in ytd_df.columns:
                    ytd_vals = ytd_df['Close'].dropna().values.flatten().tolist()
                else:
                    ytd_vals = ytd_df.iloc[:, -1].dropna().values.flatten().tolist()
                close_ytd = float(ytd_vals) if ytd_vals else close_now
            else:
                close_ytd = close_now

            # 騰落率計算
            day_pct = ((close_now - close_prev) / close_prev * 100)
            ytd_pct = ((close_now - close_ytd) / close_ytd * 100)
            
            # 表示調整
            val = close_now
            is_warn = ticker in ["^TNX", "^US2Y", "^VIX"]
            
            # 金利の10倍表示補正（yfinanceの仕様対策）
            if ticker in ["^TNX", "^US2Y"] and val > 15:
                val = val / 10
            
            unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
            
            # アイコン選択
            if day_pct > 0:
                day_arrow = "📈" if is_warn else "🚀"
            else:
                day_arrow = "📉" if is_warn else "💦"
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"

        except Exception:
            perf_text += f"\n◆ {name}\n   データ処理エラー\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
