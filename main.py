name: Daily Stock Scan with History

on:
  schedule:
    - cron: '0 7 * * *'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions: # 書き込み権限を追加
      contents: write
      
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          pip install yfinance pandas lxml requests
          
      - name: Run script
        env:
          LINE_TOKEN: ${{ secrets.LINE_TOKEN }}
          USER_ID: ${{ secrets.USER_ID }}
        run: python main.py

      - name: Commit and Push changes # ここで履歴ファイルを保存する
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add history.md
          git commit -m "Add scan history [skip ci]" || exit 0
          git push
