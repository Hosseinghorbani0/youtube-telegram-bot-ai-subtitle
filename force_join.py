# -*- coding: utf-8 -*-
"""
مدیریت عضویت اجباری در کانال‌ها
"""

import logging
from database import get_sponsors, get_user_data, is_subscribed
from keyboards import get_force_join_keyboard

logger = logging.getLogger(__name__)

async def check_user_membership(bot, user_id: int):
    """ بررسی عضویت کاربر در کانال‌های اسپانسر """
    sponsors = get_sponsors()
    if not sponsors:
        return []

    not_joined = []
    for sponsor in sponsors:
        try:
            handle = sponsor['handle']
            if not handle.startswith('@') and not handle.startswith('-100'):
                handle = f"@{handle}"

            # تلاش برای دریافت وضعیت عضویت کاربر در کانال
            try:
                member_status = await bot.get_chat_member(chat_id=handle, user_id=user_id)
                status = member_status.status
                
                # اگر کاربر عضو نیست
                if status not in ['member', 'administrator', 'creator', 'restricted']:
                    not_joined.append(sponsor)
            except Exception as member_error:
                # اگر خطای "member list is inaccessible" یا خطای مشابه باشد
                error_str = str(member_error).lower()
                if 'member list is inaccessible' in error_str or 'rights' in error_str:
                    # اگر ربات admin نیست، کاربر را نیاز عضویت در نظر می‌گیریم
                    logger.warning(f"ربات در کانال {sponsor['handle']} admin نیست یا لیست members دردسترس نیست. کاربر را نیاز به عضویت در نظر می‌گیریم.")
                    not_joined.append(sponsor)
                else:
                    logger.error(f"خطا در بررسی عضویت کانال {sponsor['handle']}: {member_error}")
                
        except Exception as e:
            logger.error(f"خطای کلی در بررسی کانال {sponsor['handle']}: {e}")
            # در صورت خطا، احتیاط می‌کنیم و کاربر را نیاز عضویت در نظر می‌گیریم
            not_joined.append(sponsor)
            
    return not_joined

async def force_join_handler(message, authenticated_users):
    """ هندلر اصلی عضویت اجباری """
    user_id = message.from_user.id
    
    # ادمین‌ها چک نمی‌شوند
    if user_id in authenticated_users:
        return None  # ادامه به هندلرهای بعدی
    
    # چک اشتراک کاربر - اگر اشتراک فعال باشد، اجازه عبور
    user_data = get_user_data(user_id)
    if user_data and is_subscribed(user_data['subscription_end']):
        return None  # کاربر اشتراک دارد، اجازه عبور بدون چک عضویت
    
    # بررسی عضویت
    channels_to_join = await check_user_membership(message.bot, user_id)
    
    if channels_to_join:
        logger.info(f"کاربر {user_id} عضو کانال‌ها نیست.")
        keyboard = get_force_join_keyboard(channels_to_join)
        await message.answer(
            "سلام! 👋\nبرای استفاده از ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید و سپس دکمه «جوین شدم» را بزنید:",
            reply_markup=keyboard
        )
        return True  # جلوی اجرای سایر هندلرها را بگیر
    
    return None  # کاربر عضو است، اجازه عبور بده

async def force_join_check_button(query, authenticated_users):
    """ مدیریت دکمه «جوین شدم» """
    user_id = query.from_user.id
    
    channels_to_join = await check_user_membership(query.bot, user_id)
    
    if channels_to_join:
        await query.answer("❌ شما هنوز در همه کانال‌ها عضو نشده‌اید!", show_alert=True)
        keyboard = get_force_join_keyboard(channels_to_join)
        try:
            await query.message.edit_text(
                "هنوز در کانال‌های زیر عضو نیستید. لطفاً عضو شوید و دوباره دکمه را بزنید:",
                reply_markup=keyboard
            )
        except Exception:
            pass
    else:
        await query.answer("✅ عضویت شما تایید شد!", show_alert=False)
        await query.message.delete()
        from keyboards import get_main_keyboard
        await query.bot.send_message(
            chat_id=user_id,
            text="🎉 عالیه! عضویت شما تایید شد. حالا می‌توانید از ربات استفاده کنید.",
            reply_markup=get_main_keyboard()
        )

