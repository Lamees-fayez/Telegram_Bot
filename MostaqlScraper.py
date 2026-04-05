import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
from typing import List, Dict
from urllib.parse import urljoin

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
        logger.info(f"🔎 Mostaql matched keywords: {matched} | score={score}")
        return score >= self.min_score

    def fix_url(self, href: str) -> str:
        if not href:
            return self.PROJECTS_URL
        return urljoin(self.BASE_URL, href)

    def extract_project_id(self, href: str) -> int:
        match = re.search(r"/project/(\d+)", href or "")
        return int(match.group(1)) if match else 0

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

    def get_project_details(self, url: str) -> Dict:
        result = {
            "description": "",
            "price": "غير محدد"
        }

        try:
            time.sleep(random.uniform(0.8, 1.5))
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text(" ", strip=True)

            result["price"] = self.extract_price_from_text(page_text)

            best_text = ""
            blocks = soup.find_all(["p", "div", "section", "article"])

            for block in blocks:
                block_text = block.get_text(" ", strip=True)
                if len(block_text) > len(best_text):
                    best_text = block_text

            if best_text:
                result["description"] = best_text[:1500]

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
            seen = set()

            logger.info(f"📄 {page_url} | raw links found = {len(links)}")

            for link in links:
                try:
                    href = (link.get("href") or "").strip()
                    if not href:
                        continue

                    full_url = self.fix_url(href)
                    if full_url in seen:
                        continue
                    seen.add(full_url)

                    title = (
                        link.get_text(" ", strip=True)
                        or link.get("title", "")
                        or link.get("aria-label", "")
                        or ""
                    ).strip()

                    card = link.find_parent(["div", "article", "li", "section"])
                    card_text = card.get_text(" ", strip=True) if card else ""
                    card_price = self.extract_price_from_text(card_text) if card_text else "غير محدد"

                    if len(title) < 5:
                        h_tag = None
                        if card:
                            h_tag = card.find(["h1", "h2", "h3", "h4"])
                        if h_tag:
                            title = h_tag.get_text(" ", strip=True)

                    if len(title) < 5:
                        continue

                    project_id = self.extract_project_id(href)

                    projects.append({
                        "id": project_id,
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
        logger.info("🔍 البحث في مستقل...")
        collected = []

        page_urls = [
            self.PROJECTS_URL,
            f"{self.PROJECTS_URL}?page=2",
            f"{self.PROJECTS_URL}?page=3",
        ]

        for page_url in page_urls:
            logger.info(f"📄 قراءة صفحة: {page_url}")
            page_projects = self.collect_projects_from_page(page_url)
            logger.info(f"📌 تم العثور على {len(page_projects)} مشروع مبدئي")
            collected.extend(page_projects)
            time.sleep(random.uniform(1, 2))

        logger.info(f"📌 total collected before dedupe = {len(collected)}")

        unique_map = {}
        for item in collected:
            if item["url"] not in unique_map:
                unique_map[item["url"]] = item

        all_projects = list(unique_map.values())
        all_projects.sort(key=lambda x: x["id"], reverse=True)

        logger.info(f"📌 total unique projects = {len(all_projects)}")
        for item in all_projects[:5]:
            logger.info(f"🧪 sample project: title={item.get('title')} | url={item.get('url')}")

        matched_jobs = []

        for item in all_projects:
            try:
                details = self.get_project_details(item["url"])
                full_text = f"{item.get('title', '')} {item.get('card_text', '')} {details.get('description', '')}"

                score, matched = self.score_text(full_text)

                if score < self.min_score:
                    logger.info(f"⏭️ not matched: {item.get('title', '')[:60]} | score={score} | matched={matched}")
                    continue

                price = details.get("price") or item.get("card_price") or "غير محدد"
                description = details.get("description", "")

                job = {
                    "title": f"🆕 مشروع مستقل: {item['title'][:120]}",
                    "url": item["url"],
                    "price": price,
                    "description": description[:500],
                    "posted_date": time.strftime("%Y-%m-%d %H:%M")
                }

                matched_jobs.append(job)
                logger.info(f"✅ مطابق من مستقل: {item['title'][:70]} | score={score} | matched={matched}")

                if len(matched_jobs) >= MAX_RESULTS_PER_SITE:
                    break

            except Exception as e:
                logger.warning(f"تخطي مشروع بسبب خطأ: {e}")
                continue

        logger.info(f"🎯 تم جلب {len(matched_jobs)} مشروع من مستقل")
        return matched_jobs
