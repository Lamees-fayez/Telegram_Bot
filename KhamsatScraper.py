import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import random
from typing import List, Dict
from urllib.parse import urlparse

from config import MAX_RESULTS_PER_SITE

logger = logging.getLogger(__name__)


class KhamsatScraper:
    BASE_URL = "https://khamsat.com"
    REQUESTS_URL = "https://khamsat.com/community/requests"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": self.REQUESTS_URL,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        self.weighted_keywords = {
            "excel": 4,
            "اكسل": 4,
            "power bi": 4,
            "powerbi": 4,
            "dashboard": 4,
            "dash board": 4,
            "داشبورد": 4,
            "داش بورد": 4,
            "web scraping": 4,
            "scraping": 4,
            "scraper": 4,
            "سحب بيانات": 4,
            "استخراج بيانات": 4,
            "data entry": 3,
            "تنظيف بيانات": 3,
            "cleaning data": 3,
            "etl": 3,
            "python": 1,
            "sql": 1,
            "analysis": 1,
            "data analysis": 2,
            "تحليل بيانات": 2,
            "report": 1,
            "reports": 1,
            "تقارير": 1,
        }

        self.min_score = 4

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""

        text = text.lower().strip()
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ة", "ه")
        text = text.replace("ى", "ي")
        text = re.sub(r"\s+", " ", text)
        return text

    def score_text(self, text: str):
        text = self.normalize_text(text)
        score = 0
        matched = []

        for keyword, weight in self.weighted_keywords.items():
            nk = self.normalize_text(keyword)
            if nk in text:
                score += weight
                matched.append(keyword)

        return score, matched

    def is_relevant(self, text: str) -> bool:
        score, matched = self.score_text(text)
        logger.info(f"🔎 Khamsat matched keywords: {matched} | score={score}")
        return score >= self.min_score

    def fix_khamsat_url(self, href: str) -> str:
        if not href:
            return self.REQUESTS_URL

        if href.startswith("//"):
            return "https:" + href
        elif href.startswith("/"):
            return self.BASE_URL + href
        elif not href.startswith("http"):
            return self.BASE_URL + "/" + href.lstrip("/")
        else:
            return href

    def get_request_details(self, url: str) -> Dict:
        result = {
            "description": "",
            "price": "طلب مفتوح"
        }

        try:
            time.sleep(random.uniform(0.8, 1.5))
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            best_text = ""
            blocks = soup.find_all(["article", "section", "div", "p"])

            for block in blocks:
                txt = block.get_text(" ", strip=True)
                if len(txt) > len(best_text):
                    best_text = txt

            result["description"] = best_text[:1500]

        except Exception as e:
            logger.warning(f"تعذر قراءة تفاصيل طلب خمسات: {url} | {e}")

        return result

    def search_requests(self) -> List[Dict]:
        jobs = []

        try:
            logger.info("🔍 البحث في خمسات...")
            response = self.session.get(self.REQUESTS_URL, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all("a", href=re.compile(r"^/community/requests/\d+"))
            seen = set()

            logger.info(f"📌 عدد الروابط الأولية من خمسات: {len(links)}")

            for link in links:
                try:
                    href = link.get("href", "").strip()
                    title = link.get_text(" ", strip=True).strip()

                    if not href or not title or len(title) < 4:
                        continue

                    fixed_url = self.fix_khamsat_url(href)

                    if fixed_url in seen:
                        continue
                    seen.add(fixed_url)

                    parsed = urlparse(fixed_url)
                    if "khamsat.com" not in parsed.netloc:
                        continue

                    details = self.get_request_details(fixed_url)
                    full_text = f"{title} {details.get('description', '')}"

                    score, matched = self.score_text(full_text)

                    if score < self.min_score:
                        logger.info(f"⏭️ not matched khamsat: {title[:60]} | score={score} | matched={matched}")
                        continue

                    job = {
                        "title": f"🆕 طلب خمسات: {title[:120]}",
                        "url": fixed_url,
                        "price": "طلب مفتوح",
                        "description": details.get("description", "")[:500],
                        "posted_date": time.strftime("%Y-%m-%d %H:%M")
                    }

                    jobs.append(job)
                    logger.info(f"✅ مطابق من خمسات: {title[:60]} | score={score} | matched={matched}")

                    if len(jobs) >= MAX_RESULTS_PER_SITE:
                        break

                except Exception as e:
                    logger.warning(f"تخطي طلب خمسات بسبب خطأ: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ خطأ في KhamsatScraper: {e}")

        logger.info(f"🎯 عدد الطلبات المطابقة من خمسات = {len(jobs)}")
        return jobs

    def search_jobs(self):
        return self.search_requests()
