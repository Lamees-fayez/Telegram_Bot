import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

# عدد الثواني بين كل فحص
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "45"))

# عدد النتائج القصوى من كل موقع في كل دورة
MAX_RESULTS_PER_SITE = int(os.getenv("MAX_RESULTS_PER_SITE", "10"))

# timeout للطلبات
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))

# الكلمات المفتاحية
DEFAULT_KEYWORDS = [
    "excel", "اكسل",
    "power bi", "powerbi",
    "dashboard", "dash board", "داشبورد", "داش بورد",
    "data analysis", "data analyst", "تحليل بيانات", "تحليل", "بيانات",
    "web scraping", "scraping", "scraper", "سحب بيانات", "استخراج بيانات",
    "data entry", "تنظيف بيانات", "cleaning data",
    "sql", "python", "automation", "etl", "report", "reports", "تقارير"
]


def load_keywords(file_path: str = "keywords.txt"):
    if not os.path.exists(file_path):
        return DEFAULT_KEYWORDS

    keywords = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            kw = line.strip()
            if kw:
                keywords.append(kw)

    return keywords if keywords else DEFAULT_KEYWORDS
