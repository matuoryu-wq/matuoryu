"""バックアップを1回実行する(Windows タスクスケジューラからの日次実行用)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import backup, db  # noqa: E402
from app.config import load_settings  # noqa: E402

s = load_settings()
if not s.backup_dir:
    sys.exit("BACKUP_DIR が .env に設定されていません")
conn = db.connect(s.db_path)
db.init_db(conn)
conn.close()
try:
    print("バックアップ完了:", backup.run_backup(s.db_path, s.backup_dir, s.backup_keep))
except Exception as e:  # noqa: BLE001
    backup.record_failure(s.db_path, e)
    sys.exit(f"バックアップ失敗: {e}")
