name: USA Stock Scan

on:
  schedule:
    - cron: '30 22 * * 1-5' # 日本時間 朝7:30 (火〜土)
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install yfinance pandas lxml requests gspread google-auth

      - name: Run USA script
        env:
          LINE_TOKEN: ${{ secrets.LINE_TOKEN }}
          USER_ID: ${{ secrets.USER_ID }}
          SPREADSHEET_ID: ${{ secrets.SPREADSHEET_ID }}
          GCP_JSON: ${{ secrets.GCP_JSON }}
        run: python usa_stock.py
