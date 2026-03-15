import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import json
import urllib.request
import os

LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, data=json.dumps(data))

# 日経225取得
name_map = {}
try:
    url = "https://ja.wikipedia.org/wiki/%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87%E6%A0%AA%E4%BE%A1"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        tables = pd.read_html(response.read())
    target_table = tables[1]
    name_map = {str(row['コード']) + ".T": row['社名'] for _, row in target_table.iterrows()}
except:
    name_map = {"8306.T": "三菱UFJ", "7203.T": "トヨタ"}

target_list = []

for ticker, name in name_map.items():
    try:
        # データ取得
        data = yf.download(ticker, period="8mo", progress=False)
        if len(data) < 75: continue

        # 1. 移動平均線の計算
        ma25 = data['Close'].rolling(window=25).mean()
        ma75 = data['Close'].rolling(window=75).mean()
        
        # 2. RSI(14日間)の計算
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1].item()

        # 【判定条件】
        # ① 本日ゴールデンクロス発生
        is_gc = (ma25.iloc[-1].item() > ma75.iloc[-1].item()) and (ma25.iloc[-2].item() <= ma75.iloc[-2].item())
        
        # ② RSIが70未満（まだ過熱しすぎていない）
        is_not_overbought = current_rsi < 70

        if is_gc and is_not_overbought:
            target_list.append(f"★ {name} ({ticker})\n   └ RSI: {current_rsi:.1f} (割安度OK)")
            
    except:
        continue

now_str = datetime.now().strftime('%Y/%m/%d %H:%M')

# 記録
history_file = "history.md"
with open(history_file, "a", encoding="utf-8") as f:
    f.write(f"### {now_str}\n" + ("\n".join(target_list) if target_list else "条件合致なし") + "\n\n")

# LINE送信
msg = f"【🚀厳選：爆上予報】\n{now_str}\n\n" + ("\n".join(target_list) if target_list else "本日、条件に合う銘柄はありません。")
send_line(msg)
