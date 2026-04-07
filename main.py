import os
import json
import logging
from dotenv import load_dotenv

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
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
        self.bot = TelegramBot(TELEGRAM_BOT_TOKEN, self.db)

        self.scrapers = {
            "mostaql": MostaqlScraper(),
            "khamsat": KhamsatScraper(),
        }

        self.state_file = "jobs_state.json"
        self.sent_jobs = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
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

    def build_key(self, platform, job):
        return (job.get("url") or job.get("link") or "").strip()

    def run(self):
        logger.info("===== BOT START =====")
        logger.info(f"Token exists: {'YES' if TELEGRAM_BOT_TOKEN else 'NO'}")
        logger.info(f"Chat ID exists: {'YES' if TELEGRAM_CHAT_ID else 'NO'}")

        try:
            chat_id = int(TELEGRAM_CHAT_ID)

            me = self.bot.bot.get_me()
            logger.info(f"Bot username: @{me.username}")
            logger.info(f"Bot id: {me.id}")

            self.bot.bot.send_message(
                chat_id=chat_id,
                text="✅ Bot is running from GitHub Actions"
            )
            logger.info("TEST MESSAGE SENT SUCCESSFULLY")

        except Exception as e:
            logger.exception(f"TEST SEND FAILED: {e}")
            raise

        total = 0

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"checking scraper: {name}")
                jobs = scraper.search_jobs() or []
                logger.info(f"{name}: jobs found = {len(jobs)}")

                for job in jobs:
                    try:
                        job["platform"] = name
                        key = self.build_key(name, job)

                        if not key:
                            logger.warning("job skipped: no key")
                            continue

                        if key in self.sent_jobs:
                            logger.info("job skipped: already sent")
                            continue

                        saved = self.db.save_job(name, job)
                        logger.info(f"save_job returned: {saved}")

                        if saved:
                            self.sent_jobs.add(key)
                            self.save_state()
                            self.bot.notify_subscribers(job)
                            total += 1
                            logger.info(f"new job notified: {job.get('title', '')[:70]}")

                    except Exception as e:
                        logger.exception(f"job processing error in {name}: {e}")

            except Exception as e:
                logger.exception(f"{name} scraper error: {e}")

        logger.info(f"done. new jobs: {total}")
        logger.info("===== BOT END =====")


if __name__ == "__main__":
    bot = JobsBot()
    bot.run()
