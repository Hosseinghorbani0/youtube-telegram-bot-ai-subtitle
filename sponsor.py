# -*- coding: utf-8 -*-
"""
مدیریت اسپانسرها
"""

import logging
from database import get_sponsors, add_sponsor, remove_sponsor
from keyboards import get_sponsors_menu_keyboard, get_admin_main_keyboard

logger = logging.getLogger(__name__)

from states import SponsorStates

async def sponsor_add_start(query, state):
    """ شروع فرآیند افزودن اسپانسر """
    await query.answer()
    sponsors = get_sponsors()
    
    if len(sponsors) >= 6:
        await query.message.edit_text(
            "ظرفیت اسپانسرها پر است (حداکثر 6 مورد).",
            reply_markup=get_sponsors_menu_keyboard()
        )
        return None
    
    await query.message.edit_text(
        "لطفاً یوزرنیم کانال اسپانسر را وارد کنید (مثلاً: @MyChannel یا MyChannel):"
    )
    await state.set_state(SponsorStates.handle)
    return None

async def sponsor_receive_handle(message, state):
    """ دریافت یوزرنیم اسپانسر """
    handle = message.text
    if not handle.startswith('@'):
        handle = f"@{handle}"
    
    await state.update_data(sponsor_handle=handle)
    await message.answer(
        f"یوزرنیم {handle} دریافت شد. حالا لینک کامل کانال را ارسال کنید (مثلاً: https://t.me/MyChannel):"
    )
    await state.set_state(SponsorStates.link)
    return None

async def sponsor_receive_link(message, state):
    """ دریافت لینک اسپانسر """
    handle = (await state.get_data()).get('sponsor_handle')
    link = message.text
    
    if not link.startswith("https://t.me/"):
        await message.answer(
            "لینک نامعتبر است. باید با https://t.me/ شروع شود. لطفاً دوباره تلاش کنید."
        )
        await state.set_state(SponsorStates.link)
        return None
    
    success, msg = add_sponsor(handle, link)
    
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")
    
    await message.answer("مدیریت اسپانسرها:", reply_markup=get_sponsors_menu_keyboard())
    await state.clear()
    return None

async def sponsor_remove_select(query):
    """ انتخاب اسپانسر برای حذف """
    await query.answer()
    
    sponsors = get_sponsors()
    if not sponsors:
        await query.message.edit_text(
            "هیچ اسپانسری برای حذف وجود ندارد.",
            reply_markup=get_sponsors_menu_keyboard()
        )
        return
    
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = []
    keyboard.append([InlineKeyboardButton(
        text="--- کدام اسپانسر حذف شود؟ ---",
        callback_data="ignore"
    )])
    for sponsor in sponsors:
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {sponsor['handle']}",
                callback_data=f"sponsor_remove_confirm_{sponsor['handle']}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 لغو و بازگشت",
            callback_data="admin_manage_sponsors"
        )
    ])
    
    await query.message.edit_text(
        "لطفاً اسپانسری که می‌خواهید حذف شود را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def sponsor_remove_confirm(query):
    """ تایید حذف اسپانسر """
    await query.answer()
    
    handle = query.data.split("sponsor_remove_confirm_")[-1]
    success, msg = remove_sponsor(handle)
    
    if success:
        await query.message.edit_text(
            f"✅ {msg}",
            reply_markup=get_sponsors_menu_keyboard()
        )
    else:
        await query.message.edit_text(
            f"❌ {msg}",
            reply_markup=get_sponsors_menu_keyboard()
        )

