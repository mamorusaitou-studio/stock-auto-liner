import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import json
import urllib.request
import os
import gspread
from google.oauth2.service_account import Credentials

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
        # Google認証
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_info(json.loads(GCP_JSON), scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.get_worksheet(0)
        # データの追記
        worksheet.append_rows(data_list)
    except Exception as e:
        print(f"Spreadsheet Error: {e}")

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

target_list_line = []
target_list_sheet = []
now_str = datetime.now().strftime('%Y/%m/%d %H:%M')

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
            rsi_comment = "最高！" if current_rsi <= 55 else "勢いアリ"
            vol_comment = "本気買い" if vol_ratio >= 200 else "注目増"
            
            target_list_line.append(f"🔥【極選】{name} ({ticker})\n   ├ RSI: {current_rsi:.1f} ({rsi_comment})\n   └ 出来高: {vol_ratio:.0f}% ({vol_comment})")
            target_list_sheet.append([now_str, name, ticker, round(current_rsi, 1), f"{vol_ratio:.0f}%"])
            
    except:
        continue

# スプレッドシートのURLを作成
ss_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"

# 記録・送信
if target_list_sheet:
    update_spreadsheet(target_list_sheet)
    msg = f"【🎯お宝：スプシ記帳完了】\n{now_str}\n\n" + "\n".join(target_list_line) + f"\n\n📊詳細データはこちら:\n{ss_url}"
else:
    msg = f"【🎯鉄板シグナル判定】\n{now_str}\n\n本日、鉄板条件に合う銘柄はありませんでした。"

send_line(msg)
