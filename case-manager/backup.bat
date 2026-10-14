@echo off
rem 日次バックアップ(タスクスケジューラ用)
chcp 65001 > nul
cd /d "%~dp0"
if not exist data mkdir data
".venv\Scripts\python.exe" scripts\backup_now.py >> data\backup.log 2>&1
