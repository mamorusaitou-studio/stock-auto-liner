import yfinance as yf
import requests
import json
import os
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
            # 1. データを取得
            df = yf.download(ticker, start=f"{current_year}-01-01", progress=False)
            if df.empty:
                df = yf.download(ticker, period="5d", progress=False)

            # 2. 【究極のエラー対策】名前を無視して「数値」だけをリスト化
            # .values で純粋な配列にし、.flatten() で1次元にしてから、
            # float以外（見出し等）を徹底排除して「数字だけの列」を作る
            raw_data = df.values.flatten()
            prices = []
            for val in raw_data:
                try:
                    p = float(val)
                    if p == p: # NaN（空データ）チェック
                        prices.append(p)
                except:
                    continue

            if len(prices) < 2:
                perf_text += f"\n◆ {name}\n   データ不足\n"
                continue

            # 3. yfinanceの多重構造(Open, High, Low, Close...)を考慮し、
            # 1日あたりのデータ数（通常6個か8個）で最新と年初を特定する
            cols_count = len(df.columns)
            close_now = prices[-1] # 一番最後が最新の終値
            close_prev = prices[-(1 + cols_count)] # 1行分前が前日の終値
            close_ytd = prices[cols_count - 1] # 最初の行の最後が年初の終値

            # 4. 騰落率の計算
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

        except Exception:
            perf_text += f"\n◆ {name}\n   計算エラー（対策中）\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
