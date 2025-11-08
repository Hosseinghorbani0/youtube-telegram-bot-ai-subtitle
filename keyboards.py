# -*- coding: utf-8 -*-
"""
کیبوردهای ربات
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from database import get_sponsors

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """ کیبورد اصلی ربات """
    keyboard = [
        [KeyboardButton(text="📥 دانلود یوتیوب"), KeyboardButton(text="⭐ وضعیت اعتبار")],
        [KeyboardButton(text="🔗 دریافت لینک زیرمجموعه"), KeyboardButton(text="💳 خرید اشتراک")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_quality_keyboard() -> InlineKeyboardMarkup:
    """ کیبورد انتخاب کیفیت """
    keyboard = [
        [InlineKeyboardButton(text="🎵 MP3 (صوت)", callback_data="q_audio")],
        [
            InlineKeyboardButton(text="480p 📹", callback_data="q_480"),
            InlineKeyboardButton(text="720p 📹", callback_data="q_720"),
        ],
        [InlineKeyboardButton(text="1080p 📹", callback_data="q_1080")],
        [InlineKeyboardButton(text="❌ لغو", callback_data="q_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subtitle_choice_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🎬 بدون زیرنویس", callback_data="sub_none")],
        [InlineKeyboardButton(text="📝 با زیرنویس", callback_data="sub_yes")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="sub_back_quality")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subtitle_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="sub_lang_fa"), InlineKeyboardButton(text="🇺🇸 English", callback_data="sub_lang_en")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="sub_back_choice")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """ کیبورد پنل ادمین """
    keyboard = [
        [InlineKeyboardButton(text="🎁 ساخت ریدیم کد", callback_data="admin_gen_code")],
        [InlineKeyboardButton(text="📢 مدیریت اسپانسرها", callback_data="admin_manage_sponsors")],
        [InlineKeyboardButton(text="🔒 خروج از پنل", callback_data="admin_logout")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_sponsors_menu_keyboard() -> InlineKeyboardMarkup:
    """ کیبورد مدیریت اسپانسرها """
    sponsors = get_sponsors()
    keyboard = []
    
    if sponsors:
        keyboard.append([InlineKeyboardButton(text="--- اسپانسرهای فعلی ---", callback_data="ignore")])
        for sponsor in sponsors:
            keyboard.append([InlineKeyboardButton(
                text=f"📢 {sponsor['handle']}", 
                url=sponsor['link']
            )])
    else:
        keyboard.append([InlineKeyboardButton(
            text="هیچ اسپانسری ثبت نشده", 
            callback_data="ignore"
        )])
    
    keyboard.append([InlineKeyboardButton(text="➕ افزودن اسپانسر", callback_data="sponsor_add")])
    
    if sponsors:
        keyboard.append([InlineKeyboardButton(
            text="➖ حذف اسپانسر", 
            callback_data="sponsor_remove_select"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="🔙 بازگشت به پنل اصلی", 
        callback_data="admin_main_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_buy_subscription_keyboard() -> InlineKeyboardMarkup:
    """ کیبورد خرید اشتراک """
    keyboard = [[InlineKeyboardButton(
        text="🔑 وارد کردن کد ریدیم", 
        callback_data="buy_redeem_start"
    )]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_force_join_keyboard(channels_to_join):
    """ کیبورد عضویت اجباری """
    keyboard = []
    for channel in channels_to_join:
        name = channel['handle'].replace('@', '')
        keyboard.append([InlineKeyboardButton(
            text=f"⬅️ {name}", 
            url=channel['link']
        )])
    keyboard.append([InlineKeyboardButton(
        text="✅ جوین شدم (بررسی مجدد)", 
        callback_data="force_join_check"
    )])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

