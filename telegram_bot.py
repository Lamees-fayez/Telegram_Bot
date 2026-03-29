import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from database import JobsDatabase
from typing import Dict

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, db: JobsDatabase):
        self.token = token
        self.db = db
        self.app = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("jobs", self.get_jobs))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دالة /start"""
        await update.message.reply_text("""
🎉 بوت فرص Excel & Power BI!

/jobs - آخر 8 فرصة
/help - مساعدة

إشعارات تلقائية 🚀
        """)
    
    async def get_jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض آخر المشاريع"""
        jobs = self.db.get_new_jobs()
        if not jobs:
            await update.message.reply_text("📭 لا توجد فرص جديدة")
            return
        
        recent = jobs[:8]
        message_lines = [f"📊 آخر {len(recent)} فرصة:\n\n"]
        
        for i, job in enumerate(recent, 1):
            # إصلاح رابط خمسات
            url = job['url']
            if 'khamsat.com' in url and not url.startswith(('http://', 'https://')):
                url = 'https://khamsat.com' + url.lstrip('/')
            
            # التصنيف
            line1 = f"{i}. {job['title']}"
            if 'طلب' in job['title']:
                line1 = f"🆕 {line1}"
            elif '@' in job['title']:
                line1 = f"👤 {line1}"
            
            message_lines.extend([
                line1,
                f"  💰 {job['price']}",
                f"  🌐 {job['platform'].replace('_', ' ').title()}",
                f"  🔗 {url}",
                f"  📅 {job.get('posted_date', job['scraped_date'][:16])}",
                ""
            ])
        
        message = "\n".join(message_lines)
        
        keyboard = [[InlineKeyboardButton("🔄 تحديث", callback_data='refresh_jobs')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            disable_web_page_preview=False
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأزرار"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'refresh_jobs':
            jobs = self.db.get_new_jobs()
            if not jobs:
                await query.edit_message_text("📭 لا فرص جديدة")
                return
            
            recent = jobs[:8]
            lines = [f"📊 محدث - {len(recent)} فرصة:\n\n"]
            
            for i, job in enumerate(recent, 1):
                url = job['url']
                if 'khamsat.com' in url and not url.startswith(('http://', 'https://')):
                    url = 'https://khamsat.com' + url.lstrip('/')
                
                line1 = f"{i}. {job['title']}"
                if 'طلب' in job['title']:
                    line1 = f"🆕 {line1}"
                
                lines.extend([
                    line1,
                    f"💰 {job['price']}",
                    f"🌐 {job['platform']}",
                    f"🔗 {url}",
                    ""
                ])
            
            await query.edit_message_text("\n".join(lines))
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مساعدة"""
        help_text = """
🤖 البوت يبحث في:

- مستقل (مشاريع)
- خمسات طلبات (community/requests)
- خمسات خدمات
- طلبات مستخدمين معينين

المهارات:
✅ Excel / اكسل
✅ Power BI / داشبورد
✅ تحليل بيانات
✅ تنظيف بيانات
✅ Web Scraping

/jogs - آخر الفرص
        """
        await update.message.reply_text(help_text)
    
    async def send_notification(self, user_id: int, job: Dict):
        """إشعار جديد"""
        try:
            msg = f"🚨 فرصة جديدة!\n\n{job['title']}\n{job['url']}"
            await self.app.bot.send_message(user_id, msg)
        except:
            pass
