import requests
import json
import os
import time
from datetime import datetime, timezone

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
    "CL=F": ("WTI原油", "エネルギー価格。物価に直結。"),
    "^TNX": ("米国10年金利", "長期金利。株価の重石。"),
    "^US2Y": ("米国2年金利", "短期金利。FRBの動きを反映。"),
    "^VIX": ("VIX指数", "恐怖指数。市場の警戒感。")
}

# ==========================================
# LINE送信
# ==========================================
def send_line(message):
    if not LINE_TOKEN or not USER_ID:
        print("LINE設定が未設定")
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

    try:
        res = requests.post(url, headers=headers, data=json.dumps(data))
        if res.status_code != 200:
            print(f"LINE送信失敗: {res.text}")
    except Exception as e:
        print(f"LINE送信エラー: {e}")

# ==========================================
# データ取得
# ==========================================
def get_finance_data(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            print(f"[ERROR] {ticker}: HTTP {res.status_code}")
            return None

        data = res.json()

        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        prices = result['indicators']['quote'][0]['close']

        # データ整形
        clean_data = [
            (t, p) for t, p in zip(timestamps, prices) if p is not None
        ]

        if len(clean_data) < 2:
            return None

        # 正しい取得（←バグ修正ポイント）
        t_now, close_now = clean_data[-1]
        t_prev, close_prev = clean_data[-2]

        # 年初来
        current_year = datetime.now(timezone.utc).year
        close_ytd = close_now

        for t, p in clean_data:
            if datetime.fromtimestamp(t, tz=timezone.utc).year >= current_year:
                close_ytd = p
                break

        return close_now, close_prev, close_ytd

    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        return None

# ==========================================
# コメント生成（プロっぽいやつ）
# ==========================================
def generate_comment(ticker, ytd):
    if ticker == "^VIX":
        return "市場不安が増大中" if ytd > 0 else "市場は比較的落ち着き"

    if ytd > 15:
        return "強い上昇トレンド"
    elif ytd > 5:
        return "堅調な推移"
    elif ytd > -5:
        return "横ばい圏"
    elif ytd > -15:
        return "やや弱気"
    else:
        return "弱気トレンド注意"

# ==========================================
# メインレポート
# ==========================================
def get_market_summary():
    text = f"【🧭 米国市場レポート】\n{datetime.now().strftime('%Y/%m/%d %H:%M')}\n"

    for ticker, (name, desc) in INDICES.items():
        res = get_finance_data(ticker)

        if not res:
            text += f"\n◆ {name}\n   データ取得失敗\n"
            continue

        now, prev, ytd = res

        # 騰落率
        day_pct = ((now - prev) / prev * 100)
        ytd_pct = ((now - ytd) / ytd * 100)

        # 表示調整
        val = now
        if ticker in ["^TNX", "^US2Y"] and val > 15:
            val /= 10

        unit = "pt" if ticker == "^VIX" else ("%" if ticker in ["^TNX", "^US2Y"] else "")

        # アイコン
        if ticker == "^VIX":
            day_icon = "😱" if day_pct > 0 else "😌"
        elif ticker in ["^TNX", "^US2Y"]:
            day_icon = "📈" if day_pct > 0 else "📉"
        else:
            day_icon = "🚀" if day_pct > 0 else "💦"

        ytd_icon = "🔥" if ytd_pct > 0 else "❄️"

        comment = generate_comment(ticker, ytd_pct)

        text += f"\n◆ {name}\n"
        text += f"   {val:,.2f}{unit} ({day_icon} {day_pct:+.2f}%)\n"
        text += f"   ┗ 年初来: {ytd_icon} {ytd_pct:+.2f}%\n"
        text += f"   ┗ {comment}\n"
        text += f"   └ {desc}\n"

        time.sleep(0.4)

    return text

# ==========================================
# 実行
# ==========================================
if __name__ == "__main__":
    message = get_market_summary()
    print(message)  # ログ確認用
    send_line(message)
