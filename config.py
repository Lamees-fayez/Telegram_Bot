import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

MAX_RESULTS_PER_SITE = int(os.getenv("MAX_RESULTS_PER_SITE", "10"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
SCRAPE_INTERVAL_SECONDS = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "60"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing")

if not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID is missing")
