"""
Standalone Cron Job Worker for CA Onboarding Live Email Synchronization.
Can be executed periodically via Linux crontab or Windows Task Scheduler.

Usage:
    python backend/cron_sync.py

Example Crontab on AWS EC2 (runs every 5 minutes):
    */5 * * * * /var/www/ca-onboarding/venv/bin/python /var/www/ca-onboarding/backend/cron_sync.py >> /var/log/ca-sync.log 2>&1
"""
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.config import config_by_name
from app.extensions import get_db_connection
from app.services.ingestion_service import IngestionService

def run_sync():
    env = os.environ.get("FLASK_ENV", "default")
    config = config_by_name.get(env, config_by_name["default"])
    db_path = config.DB_PATH
    upload_dir = config.UPLOAD_DIR
    
    conn = get_db_connection(db_path)
    try:
        res = IngestionService.sync_live_inbox(conn, upload_dir)
        msg = res.get('message') or res.get('error', '')
        print(f"[CRON SYNC] Status: {res.get('ok')} | Processed: {res.get('processed', 0)} | {msg}")
    except Exception as e:
        print(f"[CRON ERROR] Sync failed: {e}", file=sys.stderr)
    finally:
        conn.close()

if __name__ == "__main__":
    run_sync()
