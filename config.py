import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
NEEDS_REVIEW_DIR = DATA_DIR / "needs_review"
OUTPUT_DIR = BASE_DIR / "output"

EXCEL_FILE = OUTPUT_DIR / "work_orders.xlsx"
LOG_FILE = BASE_DIR / "automation.log"
PROCESSED_LOG_FILE = BASE_DIR / "processed_log.json"

# Google Gemini settings
# gemini-2.5-flash was retired for new users (404 "no longer available");
# gemini-3.5-flash is the current stable flash model with vision support.
GEMINI_MODEL = "gemini-3.5-flash"


def get_api_key():
    """Read the API key from the environment at call time, not import time."""
    return os.environ.get("GEMINI_API_KEY", "").strip()

# To set your API key on Windows, open a Command Prompt and run:
#   setx GEMINI_API_KEY "your-key-here"
# Then close and reopen the terminal / restart run.bat so the key is picked up.

# File stability check: wait until the file size is unchanged for this many seconds
STABILITY_CHECK_SECONDS = 1.0

# Excel file locked: retry for up to this many times, waiting EXCEL_RETRY_DELAY between tries
EXCEL_MAX_RETRIES = 10
EXCEL_RETRY_DELAY_SECONDS = 3.0

# How long the watcher waits between polling checks (seconds)
POLL_INTERVAL_SECONDS = 1.0

EXCEL_HEADERS = ["Sr No", "Work Order", "Item Code", "Description", "Qty", "Cat", "Status"]

for d in (DATA_DIR, PROCESSED_DIR, NEEDS_REVIEW_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)
