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
        worksheet = sh.get_worksheet(0)
        worksheet.append_rows(data_list)
    except Exception as e:
        print(f"Spreadsheet Error: {e}")

# --- 銘柄リスト取得 (TOPIX 500) ---
name_map = {}
try:
    # WikipediaのTOPIX Large70 / Mid400 のページから取得
    urls = [
        "https://ja.wikipedia.org/wiki/TOPIX_Core30",
        "https://ja.wikipedia.org/wiki/TOPIX_Large70",
        "https://ja.wikipedia.org/wiki/TOPIX_Mid400"
    ]
    for url in urls:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            tables = pd.read_html(response.read())
            # 各ページの構成に合わせてテーブルを抽出
            df = tables[1] if "Core30" in url else tables[2]
            for _, row in df.iterrows():
                code = str(row['コード']) + ".T"
                name = row.get('コンポーネント') or row.get('銘柄名') or row.get('社名')
                name_map[code] = name
except Exception as e:
    print(f"List Fetch Error: {e}")
    name_map = {"8306.T": "三菱UFJ", "7203.T": "トヨタ"} # バックアップ

target_list_line = []
target_list_sheet = []
now_str = datetime.now().strftime('%Y/%m/%d %H:%M')

print(f"スキャン開始: {len(name_map)} 銘柄を調査中...")

# --- スキャン実行 ---
for i, (ticker, name) in enumerate(name_map.items()):
    try:
        # 進捗ログ（GitHubのログで見れるようにする）
        if i % 50 == 0: print(f"{i}銘柄目スキャン中...")

        data = yf.download(ticker, period="8mo", progress=False)
        if len(data) < 75: continue

        # 1. GC判定
        ma25 = data['Close'].rolling(window=25).mean()
        ma75 = data['Close'].rolling(window=75).mean()
        is_gc = (ma25.iloc[-1].item() > ma75.iloc[-1].item()) and (ma25.iloc[-2].item() <= ma75.iloc[-2].item())
        
        # 2. RSI判定
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        current_rsi = rsi.iloc[-1].item()
        
        # 3. 出来高判定
        avg_volume = data['Volume'].iloc[-6:-1].mean()
        today_volume = data['Volume'].iloc[-1].item()
        vol_ratio = (today_volume / avg_volume) * 100

        # 条件合致！ (RSI 70未満 かつ 出来高120%以上)
        if is_gc and (current_rsi < 70) and (vol_ratio >= 120):
            rsi_comment = "最高！" if current_rsi <= 55 else "勢いアリ"
            vol_comment = "本気買い" if vol_ratio >= 200 else "注目増"
            
            target_list_line.append(f"🔥【500特選】{name} ({ticker})\n   ├ RSI: {current_rsi:.1f} ({rsi_comment})\n   └ 出来高: {vol_ratio:.0f}% ({vol_comment})")
            target_list_sheet.append([now_str, name, ticker, round(current_rsi, 1), f"{vol_ratio:.0f}%"])
            
        # 負荷対策（銘柄数が多いので必須）
        time.sleep(0.05)
            
    except:
        continue

# --- 結果の送信・記録 ---
ss_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"

if target_list_sheet:
    update_spreadsheet(target_list_sheet)
    # LINEは長すぎると送れないので、5件以上ある場合はスプシ誘導を強調
    summary = "\n".join(target_list_line[:8]) # 最大8件まで表示
    if len(target_list_line) > 8:
        summary += f"\n\n...ほか {len(target_list_line) - 8} 銘柄がヒット！"
    
    msg = f"【🎯TOPIX500：スキャン完了】\n{now_str}\n\n{summary}\n\n📊全データはスプシで確認:\n{ss_url}"
else:
    msg = f"【🎯TOPIX500】\n{now_str}\n\n本日、500銘柄の中に条件合致はありませんでした。"

send_line(msg)
