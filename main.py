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

def get_jp_market_summary():
    # 日本市場の重要指標（コードをより安定したものに修正）
    indices = {
        "^N225": ("日経平均", "日本を代表する225社の平均値。"),
        "^TOPX": ("TOPIX", "東証全体の動き。市場の地合いを表す。"),
        "^MOSS": ("グロース250", "新興市場。個人投資家の意欲を映す。"),
        "^TREIT": ("東証REIT", "不動産市場。金利上昇には弱い。"),
        "^JNIV": ("日経VIX", "恐怖指数。25を超えるとパニック警戒。")
    }
    
    perf_text = "【📊国内市場・指数解説】\n"
    
    for ticker, (name, desc) in indices.items():
        try:
            # 安定して2日分取得するための設定
            idx_data = yf.download(ticker, period="5d", progress=False)
            if len(idx_data) >= 2:
                close_now = idx_data['Close'].iloc[-1].item()
                close_prev = idx_data['Close'].iloc[-2].item()
                diff = ((close_now - close_prev) / close_prev) * 100
                
                mark = "📈" if diff >= 0 else "📉"
                if name == "日経VIX":
                    mark = "🛡️" if diff < 0 else "⚠️"
                
                perf_text += f"{mark}{name}: {diff:+.2f}%\n"
                
                if name == "日経VIX":
                    if close_now < 20: status = "✅相場は平穏。個別株を攻めやすい。"
                    elif 20 <= close_now < 25: status = "🟡やや荒れ模様。急落に注意。"
                    else: status = "🚨リスク回避。キャッシュ比率アップを。"
                    perf_text += f"   └{status}\n"
                else:
                    view = "好調" if diff > 0.5 else "軟調" if diff < -0.5 else "横ばい"
                    perf_text += f"   └{desc}({view})\n"
            else:
                perf_text += f"⚠️{name}: データ不足\n"
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
        try: worksheet = sh.worksheet("国内株")
        except: worksheet = sh.get_worksheet(0)
        worksheet.append_rows(data_list)
    except Exception as e:
        print(f"Spreadsheet Error: {e}")

# 銘柄リスト取得 (TOPIX 500)
name_map = {}
try:
    urls = ["https://ja.wikipedia.org/wiki/TOPIX_Core30", "https://ja.wikipedia.org/wiki/TOPIX_Large70", "https://ja.wikipedia.org/wiki/TOPIX_Mid400"]
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

index_summary = get_jp_market_summary()
target_list_line = []
target_list_sheet = []
now_str = datetime.now().strftime('%Y/%m/%d %H:%M')

print("国内株スキャン開始...")
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
            target_list_line.append(f"🔥{name}({ticker}) RSI:{current_rsi:.1f} 出来高:{vol_ratio:.0f}%")
            target_list_sheet.append([now_str, name, ticker, round(current_rsi, 1), f"{vol_ratio:.0f}%"])
        time.sleep(0.05)
    except: continue

ss_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
if target_list_sheet:
    update_spreadsheet(target_list_sheet)
    msg = f"【🎯国内：チャンス到来】\n{now_str}\n\n{index_summary}\n\n" + "\n".join(target_list_line[:8]) + f"\n\n📊スプシ:\n{ss_url}"
else:
    msg = f"【🍵国内：定期報告】\n{now_str}\n\n{index_summary}\n個別銘柄に合致はありませんでした。"

send_line(msg)
