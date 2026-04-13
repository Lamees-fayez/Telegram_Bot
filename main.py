import time
import logging
import os

from database import JobsDatabase
from MostaqlScraper import MostaqlScraper
from KhamsatScraper import KhamsatScraper
from telegram_bot import TelegramBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_bot():
    db = JobsDatabase()

    mostaql = MostaqlScraper()
    khamsat = KhamsatScraper()

    # ✅ خد التوكن من Render
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    telegram = TelegramBot(token=BOT_TOKEN, db=db)

    while True:
        try:
            logger.info("🚀 Starting scraping...")

            mostaql_jobs = mostaql.search_jobs()
            khamsat_jobs = khamsat.search_jobs()

            all_jobs = mostaql_jobs + khamsat_jobs

            logger.info(f"📊 Total collected: {len(all_jobs)}")

            new_jobs = db.get_new_jobs(all_jobs)

            logger.info(f"🔥 New jobs: {len(new_jobs)}")

            if new_jobs:
                telegram.send_jobs(new_jobs)

            logger.info("===== RUN END =====")

        except Exception as e:
            logger.error(f"❌ Error: {e}")

        logger.info("⏳ Waiting 60 seconds...")
        time.sleep(60)


if __name__ == "__main__":
    run_bot()
