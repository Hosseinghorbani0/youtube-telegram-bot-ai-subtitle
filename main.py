# - - coding: utf-8 - -

import os
import logging
import asyncio
import sys
import traceback
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from states import AdminStates, SponsorStates, RedeemStates, DownloadStates

import config
from database import initialize_database
from keyboards import get_main_keyboard
from credits import (
    handle_referral_logic, get_referral_link, show_credits_status, 
    buy_subscription_menu
)
from admin import (
    admin_login_entry, handle_username, handle_password,
    admin_logout, admin_gen_code, start_redeem_callback, handle_redeem_code_input
)
from sponsor import (
    sponsor_add_start, sponsor_receive_handle, sponsor_receive_link,
    sponsor_remove_select, sponsor_remove_confirm
)
from download import process_youtube_link, handle_quality_callback, DownloadState, handle_subtitle_choice_callback, handle_subtitle_language_callback
from force_join import force_join_handler, force_join_check_button

logging.basicConfig(
    level=getattr(logging, config.LOGGING_LEVEL),
    format=config.LOGGING_FORMAT
)
logger = logging.getLogger(__name__)

if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    logger.critical("خطای بحرانی: متغیر محیطی BOT_TOKEN تنظیم نشده است.")
    logger.critical("1. یک فایل به نام .env بسازید.")
    logger.critical("2. داخل آن بنویسید: BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN")
    sys.exit(1)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# مجموعه کاربران احراز هویت شده (ادمین‌ها)
authenticated_users = set()

# پوشه دانلود
os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

# --- State Classes ---

# State classes are now defined in states.py

# --- Commands ---

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """ دستور /start """
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    # بررسی پارامتر زیرمجموعه‌گیری: پشتیبانی از /start 123 و /start=123 و /start ref=123
    referrer_id = None
    if message.text:
        try:
            parts = message.text.split()
            if len(parts) > 1:
                payload = parts[1]
                if payload.startswith("ref=") or payload.startswith("start="):
                    payload = payload.split("=", 1)[1]
                referrer_id = int(payload)
        except Exception:
            referrer_id = None
    
    # ثبت کاربر و نمایش پیام خوش‌آمدگویی
    welcome_text = await handle_referral_logic(bot, user_id, username, referrer_id)
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """ دستور /admin """
    result = await admin_login_entry(message, state, authenticated_users)
    return result

# --- Admin Panel Handlers ---

@router.callback_query(F.data == "admin_logout")
async def cb_admin_logout(query: CallbackQuery):
    """ خروج از پنل """
    await admin_logout(query, authenticated_users)

@router.callback_query(F.data == "admin_gen_code")
async def cb_admin_gen_code(query: CallbackQuery):
    """ ساخت کد ریدیم """
    await admin_gen_code(query)

@router.callback_query(F.data == "admin_manage_sponsors")
async def cb_admin_manage_sponsors(query: CallbackQuery):
    """ مدیریت اسپانسرها """
    await query.answer()
    from keyboards import get_sponsors_menu_keyboard
    await query.message.edit_text(
        "مدیریت اسپانسرها:",
        reply_markup=get_sponsors_menu_keyboard()
    )

@router.callback_query(F.data == "admin_main_menu")
async def cb_admin_main_menu(query: CallbackQuery):
    """ بازگشت به منوی اصلی """
    await query.answer()
    from keyboards import get_admin_main_keyboard
    users_count = get_users_count()
    await query.message.edit_text(
        f"پنل مدیریت:\n\n👥 تعداد کاربران ثبت‌شده: {users_count}",
        reply_markup=get_admin_main_keyboard()
    )


# --- Sponsor Handlers ---

@router.callback_query(F.data == "sponsor_add")
async def cb_sponsor_add(query: CallbackQuery, state: FSMContext):
    """ افزودن اسپانسر """
    result = await sponsor_add_start(query, state)
    return result

@router.callback_query(F.data == "sponsor_remove_select")
async def cb_sponsor_remove_select(query: CallbackQuery):
    """ انتخاب اسپانسر برای حذف """
    await sponsor_remove_select(query)

@router.callback_query(F.data.startswith("sponsor_remove_confirm_"))
async def cb_sponsor_remove_confirm(query: CallbackQuery):
    """ تایید حذف اسپانسر """
    await sponsor_remove_confirm(query)

# --- Sponsor Conversation Handlers ---

@router.message(AdminStates.username)
async def msg_username(message: Message, state: FSMContext):
    """ دریافت نام کاربری """
    result = await handle_username(message, state)
    return result

@router.message(AdminStates.password)
async def msg_password(message: Message, state: FSMContext):
    """ دریافت رمز عبور """
    result = await handle_password(message, state, authenticated_users)
    return result

@router.message(SponsorStates.handle)
async def msg_sponsor_handle(message: Message, state: FSMContext):
    """ دریافت یوزرنیم اسپانسر """
    result = await sponsor_receive_handle(message, state)
    return result

@router.message(SponsorStates.link)
async def msg_sponsor_link(message: Message, state: FSMContext):
    """ دریافت لینک اسپانسر """
    result = await sponsor_receive_link(message, state)
    return result

# --- Redeem Code Handler ---

@router.callback_query(F.data == "buy_redeem_start")
async def cb_buy_redeem_start(query: CallbackQuery, state: FSMContext):
    """ شروع وارد کردن کد ریدیم """
    result = await start_redeem_callback(query, state)
    return result

@router.message(RedeemStates.awaiting_redeem_code)
async def msg_redeem_code(message: Message, state: FSMContext):
    """ دریافت کد ریدیم """
    result = await handle_redeem_code_input(message, state)
    return result

# --- YouTube Download Handlers ---

@router.message(F.text.regexp(r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})'))
async def msg_youtube_link(message: Message, state: FSMContext):
    """ پردازش لینک یوتیوب """
    # چک عضویت اجباری
    result = await force_join_handler(message, authenticated_users)
    if result:
        return
    
    await process_youtube_link(message, state)

@router.callback_query(lambda c: c.data.startswith("q_"))
async def cb_quality(query: CallbackQuery, state: FSMContext):
    """ مدیریت انتخاب کیفیت """
    await handle_quality_callback(query, state)

@router.callback_query(lambda c: c.data in ("sub_yes","sub_none","sub_back_quality"))
async def cb_subtitle_choice(query: CallbackQuery, state: FSMContext):
    await handle_subtitle_choice_callback(query, state)

@router.callback_query(lambda c: c.data in ("sub_lang_fa","sub_lang_en","sub_back_choice"))
async def cb_subtitle_lang(query: CallbackQuery, state: FSMContext):
    await handle_subtitle_language_callback(query, state)

# --- Credits Handlers ---

@router.message(F.text == "⭐ وضعیت اعتبار")
async def msg_status_credits(message: Message):
    """ نمایش وضعیت اعتبار """
    await show_credits_status(message)

@router.message(F.text == "🔗 دریافت لینک زیرمجموعه")
async def msg_referral_link(message: Message):
    """ ارسال لینک زیرمجموعه‌گیری """
    await get_referral_link(bot, message.from_user.id)

@router.message(F.text == "💳 خرید اشتراک")
async def msg_buy_subscription(message: Message):
    """ نمایش منوی خرید اشتراک """
    await buy_subscription_menu(message)

@router.message(F.text == "📥 دانلود یوتیوب")
async def msg_download_youtube(message: Message):
    """ راهنمای دانلود یوتیوب """
    await message.answer(
        " دانلود یوتیوب\n\n"
        "لطفاً لینک یوتیوب را برای من ارسال کنید.\n\n"
        "⚠️ توجه: ویدیوها باید کمتر از 30 دقیقه باشند."
    )

# --- Force Join Handler ---

@router.callback_query(F.data == "force_join_check")
async def cb_force_join_check(query: CallbackQuery):
    """ بررسی مجدد عضویت """
    await force_join_check_button(query, authenticated_users)

# --- سایر پیام‌ها ---

@router.message()
async def handle_other_messages(message: Message, state: FSMContext):
    """ پاسخ به سایر پیام‌ها """
    # چک عضویت اجباری
    result = await force_join_handler(message, authenticated_users)
    if result:
        return
    
    await message.answer("لطفاً از دکمه‌های منو استفاده کنید یا لینک یوتیوب ارسال کنید.")

# --- تابع اصلی ---

async def main():
    """ تابع اصلی اجرای ربات """
    
    # آماده‌سازی دیتابیس
    initialize_database()
    
    # ثبت روتر
    dp.include_router(router)
    
    logger.info("ربات در حال شروع به کار است...")
    
    # حذف آپدیت‌های قدیمی
    await bot.delete_webhook(drop_pending_updates=True)
    
    # شروع Polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"خطای بحرانی در Polling: {e}")
        logger.critical(traceback.format_exc())
    finally:
        await bot.session.close()
        logger.info("ربات متوقف شد.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("درخواست توقف ربات...")

