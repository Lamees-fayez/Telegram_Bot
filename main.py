import os
import logging
from dotenv import load_dotenv

from config import TELEGRAM_TOKEN
from database import JobsDatabase
from telegram_bot import TelegramBot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN مش موجود")

    db = JobsDatabase()

    bot = TelegramBot(
        TELEGRAM_TOKEN,
        db,
        polling_enabled=True  # أهم سطر
    )

    bot.run()


if __name__ == "__main__":
    main()
