import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from scraper import scrape_dlu

DEFAULT_STATE_FILE = ".auto_scrape_state.json"
DEFAULT_INTERVAL_DAYS = 3
DEFAULT_CHECK_SECONDS = 60 * 60


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def is_scrape_due(last_success, now=None, interval_days=DEFAULT_INTERVAL_DAYS):
    now = now or datetime.now()
    last_success_at = parse_datetime(last_success)
    if last_success_at is None:
        return True
    return now - last_success_at >= timedelta(days=interval_days)


def load_state(state_path=DEFAULT_STATE_FILE):
    path = Path(state_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state, state_path=DEFAULT_STATE_FILE):
    path = Path(state_path)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def run_if_due(
    state_path=DEFAULT_STATE_FILE,
    scrape_func=scrape_dlu,
    now=None,
    interval_days=DEFAULT_INTERVAL_DAYS,
):
    now = now or datetime.now()
    state = load_state(state_path)
    if not is_scrape_due(state.get("last_success"), now=now, interval_days=interval_days):
        return {"ran": False, "success": None, "reason": "not_due"}

    success = bool(scrape_func())
    state["last_attempt"] = now.isoformat()
    state["last_success"] = now.isoformat() if success else state.get("last_success", "")
    state["last_result"] = "success" if success else "failed"
    save_state(state, state_path)
    return {"ran": True, "success": success}


def scheduler_loop(
    state_path=DEFAULT_STATE_FILE,
    scrape_func=scrape_dlu,
    interval_days=DEFAULT_INTERVAL_DAYS,
    check_seconds=DEFAULT_CHECK_SECONDS,
):
    while True:
        run_if_due(
            state_path=state_path,
            scrape_func=scrape_func,
            interval_days=interval_days,
        )
        time.sleep(check_seconds)


def start_background_scheduler():
    if os.getenv("VERCEL") or os.getenv("DISABLE_AUTO_SCRAPE") == "1":
        return None

    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    return thread
