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

# 通知したい銘柄リスト
# ^TNX: 米国10年債利回り, ^IRX: 米国13週債利回り
INDICES = {
    "^GSPC": "S&P 500",
    "^NDX": "Nasdaq 100",
    "^N225": "日経平均",
    "GC=F": "ゴールド",
    "CL=F": "WTI原油",
    "^TNX": "米国10年金利",
    "^IRX": "米国短期金利"
}

def send_line(message):
    """
    LINE Messaging APIを使用してメッセージを送信する
    """
    if not LINE_TOKEN or not USER_ID:
        print("エラー: LINE_TOKEN または USER_ID が設定されていません。")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    data = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(f"LINE送信ステータス: {response.status_code}")

def get_market_summary():
    """
    各銘柄のデータを取得してメッセージを作成する
    """
    perf_text = "【🧭 お宝市場レポート】\n"
    
    for ticker, name in INDICES.items():
        try:
            # 最新の2日分データを取得
            idx_data = yf.download(ticker, period="5d", progress=False)
            if not idx_data.empty:
                closes = idx_data['Close'].dropna()
                if len(closes) >= 2:
                    close_now = closes.iloc[-1].item()
                    close_prev = closes.iloc[-2].item()
                    diff_pct = ((close_now - close_prev) / close_prev) * 100
                    
                    # 金利(^TNX)は yfinanceでは10倍の値(4.5%が45.0)で入るため調整
                    if ticker == "^TNX":
                        display_val = close_now / 10
                        unit = "%"
                    elif ticker == "^IRX":
                        display_val = close_now
                        unit = "%"
                    else:
                        display_val = close_now
                        unit = ""

                    # 上昇・下落の絵文字
                    if diff_pct > 0:
                        arrow = "📈" if ticker in ["^TNX", "^IRX"] else "🚀"
                    else:
                        arrow = "📉" if ticker in ["^TNX", "^IRX"] else "💦"

                    perf_text += f"\n◆ {name}\n   {display_val:.2f}{unit} ({arrow} {diff_pct:+.2f}%)\n"

        except Exception as e:
            perf_text += f"\n× {name}: 取得エラー\n"
            
    return perf_text

if __name__ == "__main__":
    # レポート作成
    message = get_market_summary()
    # 送信
    send_line(message)
