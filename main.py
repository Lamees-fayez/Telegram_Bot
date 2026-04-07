import os
import json
import time
import logging
import threading
from dotenv import load_dotenv

from config import TELEGRAM_TOKEN, SCRAPE_INTERVAL_SECONDS
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

        github_actions = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"
        polling_enabled = not github_actions

        self.bot = TelegramBot(
            TELEGRAM_TOKEN,
            self.db,
            polling_enabled=polling_enabled
        )

        self.scrapers = {
            "mostaql": MostaqlScraper(),
            "khamsat_requests": KhamsatScraper(),
        }

        self.state_file = "jobs_state.json"
        self.sent_jobs = self.load_state()
        self.scrape_interval = SCRAPE_INTERVAL_SECONDS
        self.stop_event = threading.Event()

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
                json.dump(sorted(list(self.sent_jobs)), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"save_state error: {e}")

    def build_unique_key(self, platform: str, job: dict) -> str:
        job_id = (job.get("job_id") or "").strip()
        url = (job.get("url") or job.get("link") or "").strip()

        if job_id:
            return f"{platform}:{job_id}"
        return f"{platform}:{url}"

    def scrape_all(self):
        logger.info("=" * 80)
        logger.info("بدء البحث في كل المواقع")

        total_new = 0

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"فحص المصدر: {name}")
                jobs = scraper.search_jobs() or []
                logger.info(f"{name}: {len(jobs)} results")

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
                            self.bot.notify_subscribers(job)

                    except Exception as e:
                        logger.exception(f"job processing error in {name}: {e}")

            except Exception as e:
                logger.exception(f"scraper error in {name}: {e}")

        logger.info(f"إجمالي الجديد = {total_new}")
        logger.info("=" * 80)

    def scraping_loop(self):
        logger.info(f"Scraping loop started every {self.scrape_interval} seconds")

        while not self.stop_event.is_set():
            try:
                self.scrape_all()
            except Exception as e:
                logger.exception(f"scraping_loop error: {e}")

            if self.stop_event.wait(self.scrape_interval):
                break

    def run_github_actions_mode(self, cycles=5, sleep_seconds=60):
        logger.info("GitHub Actions mode started")

        for i in range(cycles):
            logger.info(f"Cycle {i + 1}/{cycles}")
            self.scrape_all()
            if i < cycles - 1:
                time.sleep(sleep_seconds)

    def run_polling_mode(self):
        logger.info("Polling mode started")

        scraper_thread = threading.Thread(target=self.scraping_loop, daemon=True)
        scraper_thread.start()

        self.bot.run()

    def stop(self):
        self.stop_event.set()


if __name__ == "__main__":
    bot = JobsBot()
    github_actions = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"

    try:
        if github_actions:
            bot.run_github_actions_mode(cycles=5, sleep_seconds=60)
        else:
            bot.run_polling_mode()
    except KeyboardInterrupt:
        bot.stop()
        logger.info("تم إيقاف البوت")
    except Exception as e:
        bot.stop()
        logger.exception(f"Fatal error: {e}")
        raise
