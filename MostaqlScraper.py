import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
from typing import List, Dict
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class MostaqlScraper:
    BASE_URL = "https://mostaql.com"
    PROJECTS_URL = "https://mostaql.com/projects"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://mostaql.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        self.keywords = [
            "excel", "microsoft excel", "اكسل", "اكسيل", "إكسل",
            "power bi", "powerbi",
            "dashboard", "dash board", "داشبورد", "داش بورد",
            "لوحه تحكم", "لوحة تحكم",
            "تحليل بيانات", "data analysis", "data analytics",
            "sql", "python", "power query", "باور كويري",
            "web scraping", "scraping", "data extraction",
            "سحب بيانات", "استخراج بيانات", "جمع بيانات",
            "google sheets", "google sheet", "جوجل شيت", "جوجل شيتس",
            "eda", "automation", "csv", "xlsx",
            "data", "analysis", "report", "reports", "reporting",
            "kpi", "kpis", "تقارير", "تقرير", "تحليل",
            "database", "قاعده بيانات", "قاعدة بيانات"
        ]

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""

        text = text.lower().strip()

        arabic_map = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ة": "ه", "ى": "ي
