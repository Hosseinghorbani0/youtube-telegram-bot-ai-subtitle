# -- coding: utf-8 --
"""
مدیریت اعتبار و زیرمجموعه‌گیری
"""

import logging
from datetime import datetime
import time
from config import BOT_USERNAME, INITIAL_CREDITS, REFERRAL_BONUS_CREDITS
from database import (
    add_user, add_credits, deduct_credits, is_subscribed, 
    get_user_data, get_referrals_count
)
from keyboards import get_main_keyboard

logger = logging.getLogger(__name__)

async def handle_referral_logic(bot, user_id, username, referrer_id):
    """ منطق ثبت کاربر و اهدای اعتبار """
    created = add_user(user_id, username, referrer_id)
    
    if created:
        # کاربر جدید اضافه شد
        welcome_text = (
            "👋 خوش اومدی به nicot!\n"
            "جایی برای دانلود سریع و آسان ویدئوهای یوتیوب با کیفیت دلخواه و زیرنویس فارسی 🎬\n"
            "بدون دردسر — فقط لینک بده و فایل رو بردار!\n"
            "عضو شو و حرفه‌ای دانلود کن!\n"
            "nicot"
        )
        
        # اهدای اعتبار زیرمجموعه‌گیری
        if referrer_id:
            add_credits(referrer_id, REFERRAL_BONUS_CREDITS)
            welcome_text += "\n✨ شما با لینک اختصاصی یک دوست وارد شدید."
            
            # اطلاع دادن به معرف
            try:
                await bot.send_message(
                    chat_id=referrer_id,
                    text=f"✨ تبریک! یک کاربر جدید وارد شد و شما {REFERRAL_BONUS_CREDITS} اعتبار دریافت کردید."
                )
            except Exception:
                logger.warning(f"Could not notify referrer {referrer_id}.")
        
        return welcome_text
    else:
        return "👋 خوش برگشتی! می‌تونی از ربات استفاده کنی."

async def get_referral_link(bot, user_id):
    """ ساخت و ارسال لینک زیرمجموعه‌گیری """
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    text = (
        "🔗 لینک اختصاصی زیرمجموعه‌گیری شما:\n\n"
        f"با اشتراک‌گذاری این لینک با دوستانتان، به ازای هر نفر {REFERRAL_BONUS_CREDITS} اعتبار دریافت کنید.\n\n"
        f"`{referral_link}`"
    )
    await bot.send_message(user_id, text)

async def show_credits_status(message):
    """ نمایش وضعیت اعتبار کاربر """
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await message.answer("لطفاً ابتدا ربات را /start کنید.")
        return
    
    credits = user_data['credits']
    sub_end_timestamp = user_data['subscription_end']
    
    referrals_count = get_referrals_count(user_id)
    
    status_message = "⭐️ وضعیت حساب شما:\n\n"
    
    if is_subscribed(sub_end_timestamp):
        end_date = datetime.fromtimestamp(sub_end_timestamp).strftime("%Y/%m/%d - %H:%M")
        status_message += (
            f"✅ اشتراک فعال: شما تا تاریخ `{end_date}` محدودیت استفاده ندارید.\n"
            f"   (اعتبار فعلی: {credits})"
        )
    else:
        status_message += f"🎥 اعتبار فعلی دانلود: {credits}\n"
        status_message += "   (هر اعتبار = ۱ ویدیو. برای استفاده نامحدود، اشتراک بخرید.)"
    
    status_message += f"\n\n🔗 زیرمجموعه‌های موفق شما: {referrals_count} نفر"
    
    await message.answer(status_message)

async def check_and_consume_credit(user_id, required_credits: int = 1):
    """ بررسی و مصرف اعتبار (اگر اشتراک نداشته باشد)
    required_credits: تعداد اعتباری که باید کسر شود (۱ برای بدون زیرنویس، ۲ برای با زیرنویس)
    """
    user_data = get_user_data(user_id)
    
    if not user_data:
        return False, "لطفاً ابتدا ربات را /start کنید."
    
    credits = user_data['credits']
    sub_end_timestamp = user_data['subscription_end']
    
    # اگر اشتراک فعال است، اعتبار کسر نمی‌شود
    if is_subscribed(sub_end_timestamp):
        return True, "اشتراک فعال"
    
    # بررسی اعتبار کافی
    if credits >= required_credits:
        new_credits = deduct_credits(user_id, required_credits)
        return True, new_credits
    else:
        return False, f"اعتبار کافی ندارید! برای کسب اعتبار، دوستانتان را دعوت کنید یا اشتراک بخرید."

async def buy_subscription_menu(message):
    """ نمایش منوی خرید اشتراک """
    from config import SUBSCRIPTION_PRICE, ADMIN_CARD_NUMBER, ADMIN_PAYMENT_ID
    from keyboards import get_buy_subscription_keyboard
    
    payment_info = (
        "💳 اطلاعات پرداخت اشتراک یک ماهه\n\n"
        f"مبلغ: {SUBSCRIPTION_PRICE}\n"
        f"شماره کارت: `{ADMIN_CARD_NUMBER}`\n"
        f"شناسه مدیر برای ارسال رسید: {ADMIN_PAYMENT_ID}\n\n"
        "پس از پرداخت و ارسال رسید به مدیر، کد ریدیم یک‌بارمصرف خود را دریافت کنید و دکمه زیر را بزنید."
    )
    
    await message.answer(payment_info, reply_markup=get_buy_subscription_keyboard())

