import re
import logging
from typing import List, Dict
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class KhamsatScraper:
    BASE_URL = "https://khamsat.com/community/requests"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    }

    KEYWORDS = [
        "excel", "microsoft excel", "power bi", "powerbi",
        "dashboard", "dash board", "داش بورد", "داشبورد",
        "اكسل", "إكسل",
        "تحليل بيانات", "data analysis", "data analytics", "eda",
        "sql", "python", "automation",
        "scraping", "web scraping", "data extraction",
        "سحب بيانات", "استخراج بيانات", "جمع بيانات",
        "google sheets", "google sheet", "جوجل شيت", "جوجل شيتس",
        "power query", "باور كويري"
    ]

    def _normalize(self, text: str) -> str:
        text = (text or "").strip().lower()

        arabic_map = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"
        }
        for old, new in arabic_map.items():
            text = text.replace(old, new)

        text = re.sub(r"[\u0617-\u061A\u064B-\u0652]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _matches_keywords(self, title: str, desc: str = "") -> bool:
        haystack = self._normalize(f"{title} {desc}")
        return any(self._normalize(k) in haystack for k in self.KEYWORDS)

    def _extract_job_id(self, url: str) -> str:
        match = re.search(r"/community/requests/(\d+)", url or "")
        return match.group(1) if match else ""

    def _canonicalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    def search_jobs(self) -> List[Dict]:
        jobs: List[Dict] = []

        try:
            logger.info("✅ KHAMSAT REQUESTS SCRAPER IS RUNNING")
            logger.info("جلب صفحة خمسات...")

            response = requests.get(self.BASE_URL, headers=self.HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.select("a[href*='/community/requests/']")

            seen_ids = set()

            for link in links:
                try:
                    href = (link.get("href") or "").strip()
                    title = link.get_text(" ", strip=True)

                    if not href or not title:
                        continue

                    if not href.startswith("http"):
                        href = "https://khamsat.com" + href

                    href = self._canonicalize_url(href)
                    job_id = self._extract_job_id(href)

                    if not job_id or job_id in seen_ids:
                        continue

                    seen_ids.add(job_id)

                    if not self._matches_keywords(title):
                        logger.info(f"⏭️ not matched: {title}")
                        continue

                    jobs.append({
                        "job_id": str(job_id),
                        "title": str(title),
                        "url": str(href),
                        "link": str(href),
                        "description": "",
                        "price": "غير محدد",
                        "posted_date": "",
                        "platform": "khamsat"
                    })

                except Exception as e:
                    logger.warning(f"تخطي عنصر من خمسات بسبب خطأ: {e}")
                    continue

            logger.info(f"🎯 Khamsat jobs found = {len(jobs)}")

        except Exception as e:
            logger.error(f"Khamsat scraper error: {e}")

        return jobs
