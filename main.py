import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import json
import urllib.request
import os
import gspread
from google.oauth2.service_account import Credentials
import time

# 設定の読み込み
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GCP_JSON = os.environ.get("GCP_JSON")

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, data=json.dumps(data))

def update_spreadsheet(data_list):
    if not data_list: return
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_info(json.loads(GCP_JSON), scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(SPREADSHEET_ID)
        
        # 【ここを修正】「国内株」という名前のシートに書き込む
        try:
            worksheet = sh.worksheet("国内株")
        except:
            # もし「国内株」という名前がなければ、一番左のシートに書く
            worksheet = sh.get_worksheet(0)
            
        worksheet.append_rows(data_list)
    except Exception as e:
        print(f"Spreadsheet Error: {e}")

# ターゲットリスト取得 (TOPIX 500)
name_map = {}
try:
    urls = [
        "https://ja.wikipedia.org/wiki/TOPIX_Core30",
        "https://ja.wikipedia.org/wiki/TOPIX_Large70",
        "https://ja.wikipedia.org/wiki/TOPIX_Mid400"
    ]
    for url in urls:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            tables = pd.read_html(response.read())
            df = tables[1] if "Core30" in url else tables[2]
            for _, row in df.iterrows():
                code = str(row['コード']) + ".T"
                name = row.get('コンポーネント') or row.get('銘柄名') or row.get('社名')
                name_map[code] = name
except:
    name_map = {"8306.T": "三菱UFJ", "7203.T": "トヨタ"}

target_list_line = []
target_list_sheet = []
now_str = datetime.now().strftime('%Y/%m/%d %H:%M')

print(f"国内株スキャン開始...")

for ticker, name in name_map.items():
    try:
        data = yf.download(ticker, period="8mo", progress=False)
        if len(data) < 75: continue
        ma25 = data['Close'].rolling(window=25).mean()
        ma75 = data['Close'].rolling(window=75).mean()
        is_gc = (ma25.iloc[-1].item() > ma75.iloc[-1].item()) and (ma25.iloc[-2].item() <= ma75.iloc[-2].item())
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        current_rsi = rsi.iloc[-1].item()
        avg_volume = data['Volume'].iloc[-6:-1].mean()
        today_volume = data['Volume'].iloc[-1].item()
        vol_ratio = (today_volume / avg_volume) * 100

        if is_gc and (current_rsi < 70) and (vol_ratio >= 120):
            target_list_line.append(f"🔥【500特選】{name} ({ticker})\n   ├ RSI: {current_rsi:.1f}\n   └ 出来高: {vol_ratio:.0f}%")
            target_list_sheet.append([now_str, name, ticker, round(current_rsi, 1), f"{vol_ratio:.0f}%"])
        time.sleep(0.05)
    except:
        continue

ss_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"

if target_list_sheet:
    update_spreadsheet(target_list_sheet)
    summary = "\n".join(target_list_line[:8])
    msg = f"【🎯国内株：スキャン完了】\n{now_str}\n\n{summary}\n\n📊スプシで確認:\n{ss_url}"
else:
    msg = f"【🎯国内株スキャン】\n{now_str}\n\n条件に合う銘柄はありませんでした。"

send_line(msg)
