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

# 【米国市場専用】銘柄リストと解説
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
    # yfinanceでエラーが出にくいよう、期間指定ではなく「1年分」取得に変更
    perf_text = f"【🧭 米国：お宝市場レポート】\n{datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
    
    for ticker, (name, desc) in INDICES.items():
        try:
            # 確実に年初データを含むよう、期間を1y（1年）で取得
            df = yf.download(ticker, period="1y", progress=False)
            if df.empty or len(df) < 2:
                perf_text += f"\n× {name}: データ不足\n"
                continue
            
            # 今年1月1日以降のデータのみ抽出
            ytd_df = df[df.index >= f"{current_year}-01-01"]
            if ytd_df.empty:
                perf_text += f"\n× {name}: 年初データなし\n"
                continue

            close_now = ytd_df['Close'].iloc[-1].item()
            close_prev = ytd_df['Close'].iloc[-2].item()
            close_ytd = ytd_df['Close'].iloc.item()
            
            day_pct = ((close_now - close_prev) / close_prev) * 100
            ytd_pct = ((close_now - close_ytd) / close_ytd) * 100
            
            # 金利(^TNX)は10倍表示なので調整
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
            perf_text += f"\n× {name}: 取得失敗\n"
            
    return perf_text

if __name__ == "__main__":
    message = get_market_summary()
    send_line(message)
