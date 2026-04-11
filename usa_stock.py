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

# 【完全版】米国市場銘柄リスト（2年金利・VIX追加）
INDICES = {
    "^GSPC": ("S&P 500", "米国株の体温計。主要500社の動き。"),
    "^NDX": ("Nasdaq 100", "ハイテク株の象徴。金利上昇に弱い。"),
    "^SOX": ("SOX指数", "半導体セクターの勢い。景気の先行指標。"),
    "^RUT": ("ラッセル2000", "米国の小型株。景気に敏感に反応。"),
    "GC=F": ("ゴールド", "安全資産。有事やインフレ時に買われる。"),
    "CL=F": ("WTI原油", "エネルギー価格。ガソリン代や物価に直結。"),
    "^TNX": ("米国10年金利", "長期金利。これが高いと株価の重石に。"),
    "^US2Y": ("米国2年金利", "短期金利。FRBの利上げ・利下げを反映。"),
    "^VIX": ("VIX指数", "恐怖指数。市場の警戒感（20超えで注意）。")
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
            t = yf.Ticker(ticker)
            df = t.history(period="1y")

            if df.empty:
                perf_text += f"\n◆ {name}\n   データ取得失敗\n"
                continue

            # 【エラー対策1】yfinanceの仕様変更による多重構造(MultiIndex)を平坦化
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if 'Close' not in df.columns:
                perf_text += f"\n◆ {name}\n   データ取得失敗\n"
                continue

            # 【エラー対策2】DataFrameになってしまった場合、最初の列（Series）を取り出す
            close_col = df['Close']
            if isinstance(close_col, pd.DataFrame):
                series_close = close_col.iloc[:, 0]
            else:
                series_close = close_col

            series_close = series_close.dropna()
            if len(series_close) < 2:
                perf_text += f"\n◆ {name}\n   データ不足\n"
                continue

            # 【エラー対策3】日付フォーマットの違いによるエラーを強制修正
            series_close.index = pd.to_datetime(series_close.index, utc=True)

            close_now = float(series_close.iloc[-1])
            close_prev = float(series_close.iloc[-2])
            
            # 年初来の取得
            ytd_df = series_close[series_close.index.year >= current_year]
            close_ytd = float(ytd_df.iloc) if not ytd_df.empty else close_now

            # 騰落率の計算
            day_pct = ((close_now - close_prev) / close_prev) * 100
            ytd_pct = ((close_now - close_ytd) / close_ytd) * 100
            
            val = close_now
            is_yield_or_vix = ticker in ["^TNX", "^US2Y", "^VIX"]
            
            # 金利の表示補正（yfinanceの10倍表示対策）
            if ticker in ["^TNX", "^US2Y"] and val > 10:
                val = val / 10
                
            unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")
            
            # 絵文字の出し分け（金利とVIXは上がると警戒📈、下がると安心📉）
            if day_pct > 0:
                day_arrow = "📈" if is_yield_or_vix else "🚀"
            else:
                day_arrow = "📉" if is_yield_or_vix else "💦"
                
            ytd_arrow = "🔥" if ytd_pct > 0 else "❄️"

            # 表示の組み立て
            perf_text += f"\n◆ {name}\n"
            perf_text += f"   {val:,.2f}{unit} ({day_arrow} {day_pct:+.2f}%)\n"
            perf_text += f"   ┗ 年初来: {ytd_arrow} {ytd_pct:+.2f}%\n"
            perf_text += f"   └ {desc}\n"

        except Exception as e:
            # エラー発生時も最小限の行数で理由を記載
            perf_text += f"\n◆ {name}\n   計算エラー({type(e).__name__})\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
