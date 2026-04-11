import requests
import os
from datetime import datetime

LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def send_line(msg):
    print("TOKEN:", LINE_TOKEN)
    print("USER:", USER_ID)

    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }

    res = requests.post(url, headers=headers, json=payload)

    print("STATUS:", res.status_code)
    print("RESPONSE:", res.text)


def main():
    msg = f"テスト送信 {datetime.now()}"
    send_line(msg)


if __name__ == "__main__":
    main()
