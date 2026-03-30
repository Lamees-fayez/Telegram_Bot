import logging
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

from database import JobsDatabase

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, db: JobsDatabase):
        self.token = token
        self.db = db
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.setup_handlers()

    def setup_handlers(self):
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("jobs", self.get_jobs))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(CallbackQueryHandler(self.button_callback))

    def start_command(self, update: Update, context: CallbackContext):
        text = """
🎉 بوت فرص Excel & Power BI!

/jobs - آخر 8 فرص
/help - مساعدة

إشعارات تلقائية 🚀
        """
        update.message.reply_text(text)

    def get_jobs(self, update: Update, context: CallbackContext):
        """عرض آخر المشاريع"""
        jobs = self.db.get_new_jobs()

        if not jobs:
            update.message.reply_text("📭 لا توجد فرص جديدة")
            return

        recent = jobs[:8]
        message_lines = [f"📊 آخر {len(recent)} فرصة:\n"]

        for i, job in enumerate(recent, 1):
            url = job.get("url", "")
            if "khamsat.com" in url and not url.startswith(("http://", "https://")):
                url = "https://khamsat.com/" + url.lstrip("/")

            title = job.get("title", "بدون عنوان")
            price = job.get("price", "غير محدد")
            platform = job.get("platform", "unknown").replace("_", " ").title()
            posted_date = job.get("posted_date", job.get("scraped_date", ""))[:16]

            line1 = f"{i}. {title}"
            if "طلب" in title:
                line1 = f"🆕 {line1}"
            elif "@" in title:
                line1 = f"👤 {line1}"

            message_lines.extend([
                line1,
                f"💰 {price}",
                f"🌐 {platform}",
                f"🔗 {url}",
                f"📅 {posted_date}",
                ""
            ])

        message = "\n".join(message_lines)

        keyboard = [[InlineKeyboardButton("🔄 تحديث", callback_data="refresh_jobs")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            message,
            reply_markup=reply_markup,
            disable_web_page_preview=False
        )

    def button_callback(self, update: Update, context: CallbackContext):
        """معالج الأزرار"""
        query = update.callback_query
        query.answer()

        if query.data == "refresh_jobs":
            jobs = self.db.get_new_jobs()

            if not jobs:
                query.edit_message_text("📭 لا توجد فرص جديدة")
                return

            recent = jobs[:8]
            lines = [f"📊 محدث - {len(recent)} فرصة:\n"]

            for i, job in enumerate(recent, 1):
                url = job.get("url", "")
                if "khamsat.com" in url and not url.startswith(("http://", "https://")):
                    url = "https://khamsat.com/" + url.lstrip("/")

                title = job.get("title", "بدون عنوان")
                price = job.get("price", "غير محدد")
                platform = job.get("platform", "unknown").replace("_", " ").title()

                line1 = f"{i}. {title}"
                if "طلب" in title:
                    line1 = f"🆕 {line1}"

                lines.extend([
                    line1,
                    f"💰 {price}",
                    f"🌐 {platform}",
                    f"🔗 {url}",
                    ""
                ])

            keyboard = [[InlineKeyboardButton("🔄 تحديث", callback_data="refresh_jobs")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                text="\n".join(lines),
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )

    def help_command(self, update: Update, context: CallbackContext):
        """مساعدة"""
        help_text = """
🤖 البوت يبحث في:

- مستقل مشاريع
- خمسات طلبات
- خمسات خدمات
- طلبات مستخدمين معينين

المهارات:
✅ Excel / اكسل
✅ Power BI / داشبورد
✅ تحليل بيانات
✅ تنظيف بيانات
✅ Web Scraping

/jobs - آخر الفرص
        """
        update.message.reply_text(help_text)

    def send_notification(self, user_id: int, job: Dict):
        """إشعار جديد"""
        try:
            title = job.get("title", "فرصة جديدة")
            url = job.get("url", "")
            msg = f"🚨 فرصة جديدة!\n\n{title}\n{url}"
            self.updater.bot.send_message(chat_id=user_id, text=msg, disable_web_page_preview=False)
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    def run(self):
        logger.info("Starting Telegram bot...")
        self.updater.start_polling()
        self.updater.idle()
