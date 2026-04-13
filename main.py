import time
import logging
import os

from database import JobsDatabase
from MostaqlScraper import MostaqlScraper
from khamsatScraper import KhamsatScraper
from telegram_bot import TelegramBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_bot():
    db = JobsDatabase()

    mostaql = MostaqlScraper()
    khamsat = KhamsatScraper()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing in environment variables")

    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID is missing in environment variables")

    telegram = TelegramBot(token=bot_token, db=db)

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
                for job in new_jobs:
                    telegram.send_job(chat_id, job)

            logger.info("===== RUN END =====")

        except Exception as e:
            logger.error(f"❌ Error: {e}")

        logger.info("⏳ Waiting 60 seconds...")
        time.sleep(60)


if __name__ == "__main__":
    run_bot()
