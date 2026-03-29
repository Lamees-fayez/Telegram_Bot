import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

SCRAPE_INTERVAL = 1  # كل 10 دقايق عشان تجرب

KEYWORDS = [
    'power bi', 'داشبورد', 'dashboard', 'excel', 'اكسل',
    'تحليل بيانات', 'data analysis', 'بيانات','Excel','تصميم داش بورد','Microsoft Excel','web scrapping','سحب بيانات'
]