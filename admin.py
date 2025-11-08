

import logging
from datetime import datetime
from config import ADMIN_USERNAME, ADMIN_PASSWORD
from database import create_and_store_redeem_code, get_redeem_code_info, mark_redeem_code_used, update_subscription, get_users_count
from keyboards import get_admin_main_keyboard

logger = logging.getLogger(__name__)

from states import AdminStates, RedeemStates

async def admin_login_entry(message, state, authenticated_users):
    """ نقطه ورود برای /admin """
    user_id = message.from_user.id
    
    # اگر قبلاً لاگین کرده
    if user_id in authenticated_users:
        users_count = get_users_count()
        await message.answer(
            f"پنل مدیریت:\n\n👥 تعداد کاربران ثبت‌شده: {users_count}",
            reply_markup=get_admin_main_keyboard()
        )
        return None
    
    await message.answer("سلام! برای ورود به پنل مدیریت، لطفاً نام کاربری خود را وارد کنید:")
    await state.set_state(AdminStates.username)
    return None

async def handle_username(message, state):
    """ دریافت نام کاربری """
    await state.update_data(username=message.text)
    await message.answer("نام کاربری دریافت شد. لطفاً رمز عبور را وارد کنید:")
    await state.set_state(AdminStates.password)
    return None

async def handle_password(message, state, authenticated_users):
    """ بررسی رمز عبور و ورود """
    data = await state.get_data()
    username = data.get('username')
    password = message.text
    user_id = message.from_user.id
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        authenticated_users.add(user_id)
        logger.info(f"کاربر {user_id} با موفقیت وارد شد.")
        users_count = get_users_count()
        await message.answer(
            f"✅ ورود موفق!\n\nپنل مدیریت:\n👥 تعداد کاربران ثبت‌شده: {users_count}",
            reply_markup=get_admin_main_keyboard()
        )
        await state.clear()
        return None
    else:
        logger.warning(f"تلاش ناموفق برای ورود با یوزرنیم: {username}")
        await message.answer(
            "❌ نام کاربری یا رمز عبور اشتباه است. لطفاً مجدداً /admin را بزنید."
        )
        await state.clear()
        return None

async def admin_logout(query, authenticated_users):
    """ خروج از پنل ادمین """
    user_id = query.from_user.id
    authenticated_users.discard(user_id)
    logger.info(f"کاربر {user_id} از پنل خارج شد.")
    await query.message.edit_text("شما با موفقیت از پنل خارج شدید.")

async def admin_gen_code(query):
    """ ساخت کد ریدیم جدید """
    await query.answer()
    await query.message.edit_text("⏳ در حال ساخت کد جدید...")
    
    code, expires_at = create_and_store_redeem_code()
    
    if code:
        expiry_date_str = expires_at.strftime("%Y-%m-%d %H:%M")
        reply_text = (
            f"✅ کد جدید با موفقیت ساخته شد:\n\n"
            f"`{code}`\n\n"
            f"💰 این کد به مدت 30 روز (تا تاریخ {expiry_date_str}) معتبر است."
        )
        await query.message.edit_text(reply_text, reply_markup=get_admin_main_keyboard())
    else:
        await query.message.edit_text(
            "❌ خطا در ساخت کد. لطفاً لاگ‌ها را بررسی کنید.",
            reply_markup=get_admin_main_keyboard()
        )

async def start_redeem_callback(query, state):
    """ شروع فرآیند وارد کردن کد ریدیم """
    await query.answer()
    await query.message.edit_text("🔑 لطفاً کد ریدیم یک‌بارمصرفی که از مدیر دریافت کرده‌اید را در پیام بعدی ارسال کنید:")
    await state.set_state(RedeemStates.awaiting_redeem_code)
    return None

async def handle_redeem_code_input(message, state):
    """ پردازش کد ریدیم وارد شده """
    user_id = message.from_user.id
    redeem_code = message.text.strip().upper()
    
    code_result = get_redeem_code_info(redeem_code)
    
    if code_result is None:
        await message.answer("❌ کد ریدیم نامعتبر است.")
        await state.clear()
        return None
        
    is_used, expires_at_str = code_result
    
    if is_used == 1:
        await message.answer("❌ این کد قبلاً استفاده شده است.")
        await state.clear()
        return None
    
    # فعال کردن اشتراک
    end_date = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
    end_timestamp = end_date.timestamp()
    
    update_subscription(user_id, end_timestamp)
    mark_redeem_code_used(redeem_code, user_id)
    
    end_date_str = end_date.strftime("%Y/%m/%d - %H:%M")
    await message.answer(
        f"🎉   تبریک! اشتراک ماهانه شما فعال شد!  \n\n"
        f"شما تا تاریخ `{end_date_str}` به صورت   نامحدود   می‌توانید از ربات استفاده کنید."
    )
    
    await state.clear()
    return None

