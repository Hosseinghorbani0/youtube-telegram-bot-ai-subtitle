# -*- coding: utf-8 -*-
"""
کلاینت Pyrogram برای آپلود فایل‌های بزرگ
"""

import logging
from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH

logger = logging.getLogger(__name__)

# کلاینت Pyrogram برای آپلود فایل‌های بزرگ
pyrogram_client = None

async def get_pyrogram_client():
    """ دریافت یا ساخت کلاینت Pyrogram """
    global pyrogram_client
    
    if pyrogram_client is None:
        try:
            pyrogram_client = Client(
                "bot_session",
                api_id=int(API_ID),
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                in_memory=True
            )
            await pyrogram_client.start()
            logger.info("✅ Pyrogram client started successfully")
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی Pyrogram: {e}")
            return None
    
    return pyrogram_client

async def close_pyrogram_client():
    """ بستن کلاینت Pyrogram """
    global pyrogram_client
    if pyrogram_client:
        try:
            await pyrogram_client.stop()
            pyrogram_client = None
            logger.info("Pyrogram client stopped")
        except Exception as e:
            logger.error(f"خطا در بستن Pyrogram: {e}")

