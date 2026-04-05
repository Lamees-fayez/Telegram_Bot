import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "45"))
MAX_RESULTS_PER_SITE = int(os.getenv("MAX_RESULTS_PER_SITE", "10"))

HEADLESS = os.getenv("HEADLESS", "true").strip().lower() == "true"

KEYWORDS = [
    "excel",
    "اكسل",
    "power bi",
    "powerbi",
    "dashboard",
    "dash board",
    "داشبورد",
    "داش بورد",
    "web scraping",
    "scraping",
    "scraper",
    "سحب بيانات",
    "استخراج بيانات",
    "data entry",
    "تنظيف بيانات",
    "cleaning data",
    "etl"
]

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is missing. Please set it in environment variables or .env")
