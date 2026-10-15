@echo off
rem 案件管理サーバーを起動する(127.0.0.1 のみで待受)
chcp 65001 > nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 初回セットアップ: 仮想環境を作成します
  py -3 -m venv .venv || python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -r requirements-optional.txt
)
rem 依存ライブラリの更新(導入済みなら数秒で終わる)
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if not exist ".env" (
  echo .env がありません。.env.example をコピーして APP_TOKEN 等を設定してください。
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run.py
pause
