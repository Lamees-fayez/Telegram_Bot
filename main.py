import os
import time
from dotenv import load_dotenv

from database import JobsDatabase
from telegram_bot import TelegramBot
from MostaqlScraper import MostaqlScraper
from KhamsatScraper import KhamsatScraper

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))


def main():
    db = JobsDatabase()
    bot = TelegramBot(TOKEN, db)

    scrapers = [
        MostaqlScraper(),
        KhamsatScraper()
    ]

    print("🚀 Bot Started")

    while True:
        for scraper in scrapers:
            jobs = scraper.search_jobs()

            for job in jobs:
                key = f"{job['platform']}:{job['job_id']}"

                if db.exists(key):
                    continue

                db.add(key)
                bot.notify_subscribers(job)
                time.sleep(1)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
