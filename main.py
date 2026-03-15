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
        data = yf.download(ticker, period="8mo", progress=False)
        if len(data) < 75: continue

        # 1. 移動平均線 (GC判定)
        ma25 = data['Close'].rolling(window=25).mean()
        ma75 = data['Close'].rolling(window=75).mean()
        is_gc = (ma25.iloc[-1].item() > ma75.iloc[-1].item()) and (ma25.iloc[-2].item() <= ma75.iloc[-2].item())
        
        # 2. RSI (過熱感)
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        current_rsi = rsi.iloc[-1].item()
        is_not_overbought = current_rsi < 70

        # 3. 出来高フィルター (エネルギー)
        # 本日の出来高が、過去5日間の平均出来高より20%以上多いか
        avg_volume = data['Volume'].iloc[-6:-1].mean()
        today_volume = data['Volume'].iloc[-1].item()
        is_volume_spike = today_volume > (avg_volume * 1.2)

        # 全条件合致！
        if is_gc and is_not_overbought and is_volume_spike:
            vol_ratio = (today_volume / avg_volume) * 100
            target_list.append(f"🔥極選: {name} ({ticker})\n   ├ RSI: {current_rsi:.1f}\n   └ 出来高: 前日比{vol_ratio:.0f}%")
            
    except:
        continue

now_str = datetime.now().strftime('%Y/%m/%d %H:%M')

# 記録
with open("history.md", "a", encoding="utf-8") as f:
    f.write(f"### {now_str}\n" + ("\n".join(target_list) if target_list else "特選銘柄なし") + "\n\n")

# LINE送信
msg = f"【🎯勝率重視：鉄板シグナル】\n{now_str}\n\n" + ("\n".join(target_list) if target_list else "現在、鉄板条件に合う銘柄はありません。")
send_line(msg)
