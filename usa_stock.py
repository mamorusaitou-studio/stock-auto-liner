import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import json
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

def get_usa_index_performance():
    indices = {"^GSPC": "S&P500", "^SOX": "SOX指数"}
    perf_text = "【📊米国概況】\n"
    for ticker, name in indices.items():
        try:
            idx_data = yf.download(ticker, period="2d", progress=False)
            if len(idx_data) >= 2:
                close_now = idx_data['Close'].iloc[-1].item()
                close_prev = idx_data['Close'].iloc[-2].item()
                diff = ((close_now - close_prev) / close_prev) * 100
                mark = "🇺🇸" if diff >= 0 else "📉"
                perf_text += f"{mark}{name}: {diff:+.2f}%\n"
        except:
            perf_text += f"⚠️{name}: 取得失敗\n"
    return perf_text

def update_spreadsheet(data_list):
    if not data_list: return
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_info(json.loads(GCP_JSON), scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(SPREADSHEET_ID)
        try: worksheet = sh.worksheet("米国株")
        except: worksheet = sh.get_worksheet(0)
        worksheet.append_rows(data_list)
    except Exception as e:
        print(f"Spreadsheet Error: {e}")

usa_stocks = {"SOXL": "半導体ブル3倍", "SOXS": "半導体ベア3倍", "TQQQ": "ナス100ブル3倍", "NVDA": "エヌビディア", "TSLA": "テスラ", "AAPL": "アップル"}

index_summary = get_usa_index_performance()
target_list_line = []
target_list_sheet = []
now_str = datetime.now().strftime('%Y/%m/%d %H:%M')

print("米国株スキャンの実行中...")
for ticker, name in usa_stocks.items():
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

        if is_gc and (current_rsi < 75) and (vol_ratio >= 110):
            target_list_line.append(f"🚀{name} ({ticker})\n   RSI:{current_rsi:.1f} 出来高:{vol_ratio:.0f}%")
            target_list_sheet.append([now_str, name, ticker, round(current_rsi, 1), f"{vol_ratio:.0f}%"])
    except: continue

if target_list_sheet:
    update_spreadsheet(target_list_sheet)
    ss_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    msg = f"【🚀米国：チャンス到来】\n{now_str}\n\n{index_summary}\n\n" + "\n".join(target_list_line) + f"\n\n📊詳細:\n{ss_url}"
    send_line(msg)
else:
    send_line(f"【🇺🇸米国：定期報告】\n{now_str}\n\n{index_summary}\nチャンス銘柄はありません。")
