import os
import json
import time
import logging
from dotenv import load_dotenv

from config import TELEGRAM_TOKEN
from database import JobsDatabase
from telegram_bot import TelegramBot
from MostaqlScraper import MostaqlScraper
from KhamsatScraper import KhamsatScraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JobsBot:
    def __init__(self):
        self.db = JobsDatabase()

        # 👇 مهم: يحدد هل شغال على GitHub ولا local
        self.github_actions = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"

        # 👇 polling شغال بس لو مش GitHub
        self.bot = TelegramBot(
            TELEGRAM_TOKEN,
            self.db,
            polling_enabled=not self.github_actions
        )

        self.scrapers = {
            "mostaql": MostaqlScraper(),
            "khamsat": KhamsatScraper(),
        }

        self.state_file = "jobs_state.json"
        self.sent_jobs = self.load_state()

    # =====================================================
    # STATE
    # =====================================================
    def load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
        except Exception as e:
            logger.error(f"load_state error: {e}")
        return set()

    def save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(list(self.sent_jobs), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"save_state error: {e}")

    # =====================================================
    # UNIQUE KEY
    # =====================================================
    def build_unique_key(self, platform: str, job: dict) -> str:
        job_id = (job.get("job_id") or "").strip()
        url = (job.get("url") or job.get("link") or "").strip()

        if job_id:
            return f"{platform}:{job_id}"

        return f"{platform}:{url}"

    # =====================================================
    # SCRAPING
    # =====================================================
    def scrape_all(self):
        logger.info("=" * 60)
        logger.info("بدء البحث في الوظائف...")

        total_new = 0

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"فحص المصدر: {name}")

                jobs = scraper.search_jobs() or []
                logger.info(f"{name}: عدد النتائج = {len(jobs)}")

                for job in jobs:
                    try:
                        job["platform"] = name

                        if not job.get("url") and job.get("link"):
                            job["url"] = job["link"]

                        unique_key = self.build_unique_key(name, job)

                        if not unique_key or unique_key.endswith(":"):
                            continue

                        if unique_key in self.sent_jobs:
                            continue

                        saved = self.db.save_job(name, job)

                        self.sent_jobs.add(unique_key)
                        self.save_state()

                        if saved:
                            total_new += 1
                            logger.info(f"وظيفة جديدة: {job.get('title', '')[:60]}")
                            self.bot.notify_subscribers(job)

                    except Exception as e:
                        logger.exception(f"خطأ في وظيفة من {name}: {e}")

            except Exception as e:
                logger.exception(f"خطأ في السكرابر {name}: {e}")

        logger.info(f"إجمالي الجديد = {total_new}")
        logger.info("=" * 60)

    # =====================================================
    # MODES
    # =====================================================
    def run_github_mode(self):
        """
        يستخدم في GitHub Actions
        يشغل مرة واحدة فقط
        """
        logger.info("Running in GitHub Actions mode...")
        self.scrape_all()

    def run_polling_mode(self):
        """
        يستخدم محلي أو على سيرفر
        """
        logger.info("Running in polling mode...")
        self.bot.run()

    # =====================================================
    # RUN
    # =====================================================
    def run(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN مش موجود")

        if self.github_actions:
            self.run_github_mode()
        else:
            self.run_polling_mode()


# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":
    bot = JobsBot()

    try:
        bot.run()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise
