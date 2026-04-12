import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
from typing import List, Dict
from urllib.parse import urljoin, urlparse

from config import MAX_RESULTS_PER_SITE

logger = logging.getLogger(__name__)


class MostaqlScraper:
    BASE_URL = "https://mostaql.com"
    PROJECTS_URL = "https://mostaql.com/projects"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://mostaql.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        self.weighted_keywords = {
            # Excel / Sheets
            "excel": 5,
            "microsoft excel": 5,
            "spreadsheet": 4,
            "spreadsheets": 4,
            "google sheets": 4,
            "google sheet": 4,
            "sheet": 2,
            "sheets": 2,
            "اكسل": 5,
            "إكسل": 5,
            "اكسيل": 5,
            "شيت": 2,
            "شيتات": 2,
            "جوجل شيت": 4,
            "جوجل شيتس": 4,

            # Power BI / Dashboard
            "power bi": 5,
            "powerbi": 5,
            "dashboard": 5,
            "dash board": 5,
            "interactive dashboard": 5,
            "data visualization": 4,
            "visualization": 3,
            "لوحة تحكم": 5,
            "لوحه تحكم": 5,
            "داشبورد": 5,
            "داش بورد": 5,
            "تقارير تفاعلية": 4,
            "تقرير تفاعلي": 4,
            "dashboard excel": 5,
            "excel dashboard": 5,
            "power bi dashboard": 5,
            "excel report": 4,
            "تقارير excel": 4,

            # Data analysis / reporting
            "data analysis": 4,
            "data analytics": 4,
            "data analyst": 3,
            "eda": 4,
            "analysis": 2,
            "report": 2,
            "reports": 2,
            "reporting": 2,
            "kpi": 3,
            "kpis": 3,
            "data": 2,
            "تحليل بيانات": 4,
            "تحليل الداتا": 4,
            "تحليل": 2,
            "تقارير": 2,
            "تقرير": 2,
            "مؤشرات الاداء": 3,
            "مؤشر اداء": 3,

            # Data work / ETL
            "etl": 3,
            "data cleaning": 3,
            "cleaning data": 3,
            "data processing": 3,
            "power query": 4,
            "sql": 2,
            "python": 2,
            "database": 2,
            "automation": 2,
            "api": 2,
            "csv": 2,
            "xlsx": 2,
            "تنظيف بيانات": 3,
            "معالجة بيانات": 3,
            "باور كويري": 4,
            "قاعدة بيانات": 2,

            # Scraping / extraction
            "web scraping": 5,
            "scraping": 4,
            "scraper": 4,
            "data extraction": 4,
            "crawl": 3,
            "crawler": 3,
            "سحب بيانات": 5,
            "استخراج بيانات": 5,
            "جمع بيانات": 4,
            "ويب سكرابينج": 5,
            "سكرابينج": 4,
        }

        self.strong_keywords = {
            "excel", "microsoft excel", "اكسل", "إكسل", "اكسيل",
            "power bi", "powerbi",
            "dashboard", "dash board", "داشبورد", "داش بورد",
            "لوحة تحكم", "لوحه تحكم",
            "web scraping", "scraping", "data extraction",
            "سحب بيانات", "استخراج بيانات", "جمع بيانات",
            "تحليل بيانات", "data analysis",
            "google sheets", "جوجل شيت", "power query", "باور كويري",
            "excel dashboard", "dashboard excel", "power bi dashboard"
        }

        self.min_score = 2

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""

        text = text.lower().strip()

        arabic_map = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"
        }
        for old, new in arabic_map.items():
            text = text.replace(old, new)

        text = re.sub(r"[\u0617-\u061A\u064B-\u0652]", "", text)
        text = re.sub(r"[^\w\s\+\#]", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

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

    def is_relevant(self, title: str, card_text: str, description: str):
        full_text = self.normalize_text(f"{title} {card_text} {description}")
        score, matched = self.score_text(full_text)

        normalized_matched = [self.normalize_text(x) for x in matched]
        strong_hit = any(self.normalize_text(k) in normalized_matched for k in self.strong_keywords)

        is_ok = strong_hit or score >= self.min_score

        logger.info(
            f"🔎 Mostaql match check | strong_hit={strong_hit} | score={score} | matched={matched}"
        )
        return is_ok, score, matched

    def fix_url(self, href: str) -> str:
        if not href:
            return self.PROJECTS_URL
        return urljoin(self.BASE_URL, href)

    def canonicalize_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return clean_url.rstrip("/")

    def extract_project_id(self, href: str) -> str:
        match = re.search(r"/project/(\d+)", href or "")
        return match.group(1) if match else ""

    def extract_price_from_text(self, text: str) -> str:
        if not text:
            return "غير محدد"

        patterns = [
            r'(\d[\d,\.]*\s*-\s*\d[\d,\.]*\s*\$)',
            r'(\d[\d,\.]*\s*\$)',
            r'(\$\s*\d[\d,\.]*\s*-\s*\d[\d,\.]*)',
            r'(\$\s*\d[\d,\.]*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return "غير محدد"

    def extract_best_description(self, soup: BeautifulSoup) -> str:
        candidates = []

        selectors = ["article", "main", "section", "div", "p"]

        for tag_name in selectors:
            for block in soup.find_all(tag_name):
                txt = block.get_text(" ", strip=True)
                txt = re.sub(r"\s+", " ", txt).strip()

                if len(txt) < 80:
                    continue

                bad_words = [
                    "مشاريع مشابهة", "أضف عرضك الآن", "تسجيل الدخول",
                    "حسابي", "الرئيسية", "المساعدة", "سياسة الخصوصية"
                ]
                if any(word in txt for word in bad_words):
                    continue

                candidates.append(txt)

        if not candidates:
            return ""

        candidates.sort(key=lambda x: len(x), reverse=True)

        for txt in candidates:
            if 120 <= len(txt) <= 2500:
                return txt[:1500]

        return candidates[0][:1500]

    def get_project_details(self, url: str) -> Dict:
        result = {
            "description": "",
            "price": "غير محدد"
        }

        try:
            time.sleep(random.uniform(0.7, 1.3))
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text(" ", strip=True)

            result["price"] = self.extract_price_from_text(page_text)
            result["description"] = self.extract_best_description(soup)

        except Exception as e:
            logger.warning(f"تعذر قراءة تفاصيل المشروع: {url} | {e}")

        return result

    def collect_projects_from_page(self, page_url: str) -> List[Dict]:
        projects = []

        try:
            response = self.session.get(page_url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all("a", href=re.compile(r"/project/\d+"))
            seen_ids = set()

            logger.info(f"📄 {page_url} | raw links found = {len(links)}")

            for link in links:
                try:
                    href = (link.get("href") or "").strip()
                    if not href:
                        continue

                    full_url = self.canonicalize_url(self.fix_url(href))
                    project_id = self.extract_project_id(full_url)

                    if not project_id or project_id in seen_ids:
                        continue
                    seen_ids.add(project_id)

                    title = (
                        link.get_text(" ", strip=True)
                        or link.get("title", "")
                        or link.get("aria-label", "")
                        or ""
                    ).strip()

                    card = link.find_parent(["div", "article", "li", "section"])
                    card_text = card.get_text(" ", strip=True) if card else ""
                    card_price = self.extract_price_from_text(card_text) if card_text else "غير محدد"

                    if len(title) < 5 and card:
                        h_tag = card.find(["h1", "h2", "h3", "h4"])
                        if h_tag:
                            title = h_tag.get_text(" ", strip=True)

                    if len(title) < 5:
                        continue

                    projects.append({
                        "job_id": project_id,
                        "title": title,
                        "url": full_url,
                        "card_text": card_text,
                        "card_price": card_price
                    })

                except Exception as e:
                    logger.warning(f"collect project item error: {e}")
                    continue

        except Exception as e:
            logger.error(f"خطأ أثناء قراءة صفحة مستقل: {page_url} | {e}")

        return projects

    def search_jobs(self) -> List[Dict]:
        logger.info("✅ MOSTAQL REQUESTS SCRAPER IS RUNNING")
        logger.info("🔍 البحث في مستقل...")

        collected = []

        page_urls = [
            self.PROJECTS_URL,
            f"{self.PROJECTS_URL}?page=2",
            f"{self.PROJECTS_URL}?page=3",
            f"{self.PROJECTS_URL}?page=4",
        ]

        for page_url in page_urls:
            logger.info(f"📄 قراءة صفحة: {page_url}")
            page_projects = self.collect_projects_from_page(page_url)
            logger.info(f"📌 تم العثور على {len(page_projects)} مشروع مبدئي")
            collected.extend(page_projects)
            time.sleep(random.uniform(0.8, 1.5))

        logger.info(f"📌 total collected before dedupe = {len(collected)}")

        unique_map = {}
        for item in collected:
            job_id = item.get("job_id")
            if job_id and job_id not in unique_map:
                unique_map[job_id] = item

        all_projects = list(unique_map.values())
        all_projects.sort(key=lambda x: int(x.get("job_id", 0)), reverse=True)

        logger.info(f"📌 total unique projects = {len(all_projects)}")
        for item in all_projects[:5]:
            logger.info(
                f"🧪 sample project: job_id={item.get('job_id')} | title={item.get('title')} | url={item.get('url')}"
            )

        matched_jobs = []

        for item in all_projects:
            try:
                details = self.get_project_details(item["url"])
                description = details.get("description", "")
                price = details.get("price") or item.get("card_price") or "غير محدد"

                ok, score, matched = self.is_relevant(
                    title=item.get("title", ""),
                    card_text=item.get("card_text", ""),
                    description=description
                )

                if not ok:
                    logger.info(
                        f"⏭️ not matched: {item.get('title', '')[:70]} | score={score} | matched={matched}"
                    )
                    continue

                job = {
                    "job_id": item["job_id"],
                    "title": f"🆕 مشروع مستقل: {item['title'][:120]}",
                    "url": item["url"],
                    "link": item["url"],
                    "price": price,
                    "description": description[:500],
                    "posted_date": time.strftime("%Y-%m-%d %H:%M")
                }

                matched_jobs.append(job)
                logger.info(
                    f"✅ مطابق من مستقل: {item['title'][:70]} | score={score} | matched={matched}"
                )

                if len(matched_jobs) >= MAX_RESULTS_PER_SITE:
                    break

            except Exception as e:
                logger.warning(f"تخطي مشروع بسبب خطأ: {e}")
                continue

        logger.info(f"🎯 تم جلب {len(matched_jobs)} مشروع من مستقل")
        return matched_jobs
