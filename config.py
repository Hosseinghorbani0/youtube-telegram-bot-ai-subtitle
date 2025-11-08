
import os
from dotenv import load_dotenv

load_dotenv()

# تنظیمات ربات
BOT_TOKEN = os.getenv('BOT_TOKEN') or "YOUR_BOT_TOKEN_HERE"
BOT_USERNAME = "token"  # نام کاربری ربات

API_ID = os.getenv('API_ID') or "api id"
API_HASH = os.getenv('API_HASH') or "api hash"

# تنظیمات ادمین
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"
ADMIN_CARD_NUMBER = "6037-XXXX-XXXX-XXXX"
ADMIN_PAYMENT_ID = "@ID"
SUBSCRIPTION_PRICE = "50,000 تومان"

# تنظیمات دیتابیس
DB_FILE = "bot_data.db"
DOWNLOAD_DIR = "downloads"

# تنظیمات اعتبار و اشتراک
INITIAL_CREDITS = 5  # اعتبار اولیه
REFERRAL_BONUS_CREDITS = 1  # اعتبار اهدایی
SUBSCRIPTION_DURATION_DAYS = 30  # مدت اشتراک

# تنظیمات دانلود یوتیوب
MAX_FILE_SIZE = 49 * 1024 * 1024  # 49 مگابایت
MAX_DURATION = 1800  # 30 دقیقه

# تنظیمات لاگ
LOGGING_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGGING_LEVEL = 'INFO'

