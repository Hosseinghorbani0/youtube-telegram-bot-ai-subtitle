# -*- coding: utf-8 -*-
"""
مدیریت دیتابیس SQLite
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import random
import string
from config import DB_FILE, INITIAL_CREDITS, SUBSCRIPTION_DURATION_DAYS

logger = logging.getLogger(__name__)

def get_db_connection():
    """ اتصال به دیتابیس را برمی‌گرداند. """
    return sqlite3.connect(DB_FILE)

def initialize_database():
    """ دیتابیس و جداول مورد نیاز را ایجاد می‌کند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. جدول کاربران
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        referrer_id INTEGER,
        credits INTEGER DEFAULT {},
        subscription_end REAL DEFAULT 0
    )
    '''.format(INITIAL_CREDITS))
    
    # 2. جدول ریدیم کدها
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS redeem_codes (
        code TEXT PRIMARY KEY NOT NULL,
        is_used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        used_by_id INTEGER
    )
    ''')
    
    # 3. جدول اسپانسرها
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sponsors (
        channel_handle TEXT PRIMARY KEY NOT NULL,
        channel_link TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"دیتابیس '{DB_FILE}' آماده‌سازی شد.")

def get_user_data(user_id):
    """ اطلاعات کاربر را برمی‌گرداند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT credits, subscription_end FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    if data:
        return {"credits": data[0], "subscription_end": data[1]}
    return None

def get_users_count():
    """ تعداد کل کاربران ثبت‌شده را برمی‌گرداند. """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"خطا در شمارش کاربران: {e}")
        return 0

def is_subscribed(subscription_end_timestamp: float) -> bool:
    """ بررسی می‌کند که آیا اشتراک کاربر فعال است یا خیر. """
    import time
    return subscription_end_timestamp > time.time()

def generate_random_code(length=10):
    """ یک رشته تصادفی تولید می‌کند. """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))

def create_and_store_redeem_code():
    """ یک کد ریدیم تولید می‌کند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    while True:
        new_code = generate_random_code()
        created_at = datetime.now()
        expires_at = created_at + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
        
        try:
            cursor.execute(
                "INSERT INTO redeem_codes (code, expires_at) VALUES (?, ?)",
                (new_code, expires_at.strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            conn.close()
            return new_code, expires_at
        except sqlite3.IntegrityError:
            logger.warning(f"کد تکراری {new_code} تولید شد. تلاش مجدد...")
            pass
        except Exception as e:
            logger.error(f"خطا در ساخت کد: {e}")
            conn.close()
            return None, None

def get_sponsors():
    """ لیست اسپانسرهای فعال را برمی‌گرداند. """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_handle, channel_link FROM sponsors")
        sponsors = cursor.fetchall()
        conn.close()
        return [{"handle": handle, "link": link} for handle, link in sponsors]
    except Exception as e:
        logger.error(f"خطا در دریافت اسپانسرها: {e}")
        return []

def add_sponsor(handle, link):
    """ یک اسپانسر اضافه می‌کند. """
    sponsors = get_sponsors()
    if len(sponsors) >= 6:
        return False, "ظرفیت اسپانسرها پر است (حداکثر 6 مورد)."
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sponsors (channel_handle, channel_link) VALUES (?, ?)",
            (handle, link)
        )
        conn.commit()
        conn.close()
        logger.info(f"اسپانسر اضافه شد: {handle}")
        return True, "اسپانسر با موفقیت اضافه شد."
    except sqlite3.IntegrityError:
        return False, "این کانال قبلاً ثبت شده است."
    except Exception as e:
        logger.error(f"خطا در افزودن اسپانسر: {e}")
        return False, f"خطای دیتابیس: {e}"

def remove_sponsor(handle):
    """ یک اسپانسر حذف می‌کند. """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sponsors WHERE channel_handle = ?", (handle,))
        conn.commit()
        conn.close()
        logger.info(f"اسپانسر حذف شد: {handle}")
        return True, "اسپانسر با موفقیت حذف شد."
    except Exception as e:
        logger.error(f"خطا در حذف اسپانسر: {e}")
        return False, f"خطای دیتابیس: {e}"

def get_referrals_count(user_id):
    """ تعداد زیرمجموعه‌های کاربر را برمی‌گرداند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_user(user_id, username, referrer_id):
    """ کاربر جدید اضافه می‌کند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return False  # کاربر قبلاً ثبت شده
    
    cursor.execute(
        "INSERT INTO users (user_id, username, referrer_id, credits) VALUES (?, ?, ?, ?)",
        (user_id, username, referrer_id, INITIAL_CREDITS)
    )
    conn.commit()
    conn.close()
    return True

def add_credits(user_id, amount):
    """ اعتبار به کاربر اضافه می‌کند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET credits = credits + ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()
    conn.close()

def deduct_credits(user_id, amount=1):
    """ اعتبار از کاربر کم می‌کند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET credits = credits - ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    new_credits = cursor.fetchone()[0]
    conn.close()
    return new_credits

def update_subscription(user_id, end_timestamp):
    """ اشتراک کاربر را به‌روزرسانی می‌کند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET subscription_end = ? WHERE user_id = ?",
        (end_timestamp, user_id)
    )
    conn.commit()
    conn.close()

def mark_redeem_code_used(code, user_id):
    """ کد ریدیم را به عنوان استفاده شده علامت می‌زند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE redeem_codes SET is_used = 1, used_by_id = ? WHERE code = ?",
        (user_id, code)
    )
    conn.commit()
    conn.close()

def get_redeem_code_info(code):
    """ اطلاعات کد ریدیم را برمی‌گرداند. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_used, expires_at FROM redeem_codes WHERE code = ?", (code,))
    result = cursor.fetchone()
    conn.close()
    return result

