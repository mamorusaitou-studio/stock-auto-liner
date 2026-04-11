def build_flex():
    rows = []

    for ticker, name in INDICES.items():
        data = get_price(ticker)

        if not data:
            # ← データ取れなくても表示する（これ重要）
            rows.append({
                "type": "text",
                "text": f"{name}: error",
                "size": "sm"
            })
            continue

        now, prev, ytd = data
        rows.append(make_row(name, now, prev, ytd, ticker))
        time.sleep(0.3)

    # ← rowsが空対策（超重要）
    if not rows:
        rows.append({
            "type": "text",
            "text": "データ取得失敗",
            "size": "sm",
            "color": "#ff0000"
        })

    return {
        "type": "flex",
        "altText": "米国市場",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "US MARKET",
                        "weight": "bold",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": datetime.now().strftime("%m/%d %H:%M"),
                        "size": "xs",
                        "color": "#999999"
                    },
                    {"type": "separator", "margin": "md"},
                    *rows  # ← ここが超重要
                ]
            }
        }
    }
