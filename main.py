import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import json
import urllib.request
import os

# GitHubの秘密設定（Secrets）から鍵を読み込む設定
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, data=json.dumps(data))

# 日経225スキャン
name_map = {}
try:
    url = "https://ja.wikipedia.org/wiki/%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87%E6%A0%AA%E4%BE%A1"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        tables = pd.read_html(response.read())
    target_table = tables[1]
    name_map = {str(row['コード']) + ".T": row['社名'] for _, row in target_table.iterrows()}
except:
    name_map = {"8306.T": "三菱UFJ", "7203.T": "トヨタ", "9984.T": "ソフトバンクG"}

target_list = []
for ticker, name in name_map.items():
    try:
        data = yf.download(ticker, period="8mo", progress=False)
        ma25 = data['Close'].rolling(window=25).mean()
        ma75 = data['Close'].rolling(window=75).mean()
        if (ma25.iloc[-1].item() > ma75.iloc[-1].item()) and (ma25.iloc[-2].item() <= ma75.iloc[-2].item()):
            target_list.append(f"★ {name} ({ticker})")
    except:
        continue

now_str = datetime.now().strftime('%m/%d %H:%M')
msg = f"【🔥爆上予報：GC発生】\n{now_str}\n\n" + "\n".join(target_list) if target_list else f"【通知】{now_str}\n本日の発生はありません。"
send_line(msg)
