import os
import logging
from typing import Dict, List

from telegram import Bot
from database import JobsDatabase

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, db: JobsDatabase):
        self.token = token
        self.db = db
        self.bot = Bot(token=token)

    def format_job_message(self, job: Dict) -> str:
        title = str(job.get("title", "فرصة جديدة")).strip()
        url = str(job.get("url") or job.get("link") or "").strip()
        price = str(job.get("price", "غير محدد")).strip()

        platform = str(
            job.get("platform") or job.get("source") or "unknown"
        ).replace("_", " ").title()

        posted_date = str(
            job.get("posted_date", job.get("scraped_date", ""))
        )[:16].strip()

        description = str(job.get("description", "")).strip()
        if len(description) > 250:
            description = description[:250] + "..."

        parts = [
            "🚨 فرصة جديدة نزلت!",
            "",
            f"📌 {title}",
            f"💰 {price}",
            f"🌐 {platform}",
        ]

        if posted_date:
            parts.append(f"📅 {posted_date}")

        if description:
            parts.extend(["", f"📝 {description}"])

        if url:
            parts.extend(["", f"🔗 {url}"])

        return "\n".join(parts)

    def get_target_chat_ids(self) -> List[int]:
        subscribers = []

        # من قاعدة البيانات
        try:
            if hasattr(self.db, "get_subscribers"):
                subscribers = self.db.get_subscribers() or []
        except Exception as e:
            logger.warning(f"تعذر قراءة المشتركين من الداتابيز: {e}")

        # fallback من Environment
        fallback_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

        if not subscribers and fallback_chat_id:
            try:
                subscribers = [int(fallback_chat_id)]
            except ValueError:
                logger.warning("TELEGRAM_CHAT_ID غير صالح")

        # إزالة التكرار
        unique_ids = []
        seen = set()
        for chat_id in subscribers:
            try:
                cid = int(chat_id)
                if cid not in seen:
                    seen.add(cid)
                    unique_ids.append(cid)
            except Exception:
                continue

        return unique_ids

    def notify_subscribers(self, job: Dict):
        chat_ids = self.get_target_chat_ids()

        if not chat_ids:
            logger.info("لا يوجد مشتركين أو TELEGRAM_CHAT_ID غير موجود")
            return

        msg = self.format_job_message(job)

        for chat_id in chat_ids:
            try:
                self.bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    disable_web_page_preview=False
                )
                logger.info(f"✅ sent to {chat_id}")
            except Exception as e:
                logger.error(f"❌ error sending to {chat_id}: {e}")

    def send_jobs(self, jobs: List[Dict]):
        if not jobs:
            logger.info("لا توجد وظائف لإرسالها")
            return

        for job in jobs:
            self.notify_subscribers(job)
