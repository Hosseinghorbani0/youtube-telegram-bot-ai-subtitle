# -*- coding: utf-8 -*-
"""
مدیریت دانلود یوتیوب
"""

import os
import re
import asyncio
import urllib.request
import logging
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest
from config import DOWNLOAD_DIR, MAX_FILE_SIZE, MAX_DURATION
from user_agents import USER_AGENTS
import random
import glob
from keyboards import get_quality_keyboard
from states import DownloadStates
from credits import check_and_consume_credit
from pyrogram_client import get_pyrogram_client

logger = logging.getLogger(__name__)

class DownloadState:
    waiting_for_quality = "waiting_for_quality"  # باقی مانده برای سازگاری؛ از DownloadStates استفاده می‌کنیم


def get_download_opts(format_str):
    """ تنظیمات yt-dlp """
    return {
        'format': format_str,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'http_headers': {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9'
        },
        'quiet': True,
        'no_warnings': True,
        'logger': logger,
        'retries': 10,
        'fragment_retries': 10,
        'no_check_certificate': True,
        'extractor_args': {
            'youtube': {'player_client': ['android', 'ios']}
        },
     
        'cookies': 'cookies.txt'
    }

# def get_download_opts(format_str):
#     """ تنظیمات yt-dlp """
#     return {
#         'format': format_str,            
#         'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
#         'http_headers': {
#             'User-Agent': random.choice(USER_AGENTS),
#             'Accept': '*/*',
#             'Accept-Language': 'en-US,en;q=0.9'
#         },
#         'quiet': True,
#         'no_warnings': True,
#         'logger': logger,
#         'retries': 10,
#         'fragment_retries': 10,
#         'no_check_certificate': True,
#         'extractor_args': {
#             'youtube': {'player_client': ['android', 'ios']}
#         },
#     }

def download_video_sync(url: str, video_id: str, quality: str):
    """ دانلود ویدیو با yt-dlp (همگام) با مدیریت خطا و retry محدود """
    import time

    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(video_id):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, f))
            except Exception:
                pass

    # تنظیم فرمت‌ها
    formats = (
        ['bestaudio[ext=m4a]', 'bestaudio[ext=mp3]', 'bestaudio', 'worstaudio']
        if quality == "audio"
        else [
            f"best[height<={quality}]/22/18",
            "22/18/136/137/248",
            "best",
            "worst"
        ]
    )

    # حداکثر تعداد تلاش‌ها برای هر فرمت
    max_retries_per_fmt = 2

    # تلاش دانلود با فرمت‌های مختلف
    for fmt in formats:
        retries = 0
        while retries <= max_retries_per_fmt:
            try:
                with YoutubeDL(get_download_opts(fmt)) as ydl:
                    ydl.download([url])
                # پیدا کردن فایل دانلود شده
                files = glob.glob(os.path.join(DOWNLOAD_DIR, f'{video_id}.*'))
                if files:
                    file_path = files[0]
                    try:
                        size_ok = os.path.getsize(file_path) <= MAX_FILE_SIZE
                    except Exception:
                        size_ok = False
                    if size_ok:
                        return file_path, None
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                break
            except DownloadError as de:
                logger.warning(f"yt-dlp خطا داد (fmt={fmt}): {de}")
                retries += 1
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"خطای غیرمنتظره در دانلود (fmt={fmt}): {e}")
                retries += 1
                time.sleep(1.0)

    return None, "نمی‌توانم ویدیو را دانلود کنم."

async def process_youtube_link(message, state):
    """ پردازش لینک یوتیوب """
    try:
        # استخراج URL
        url_match = re.search(
            r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})',
            message.text
        )
        if not url_match:
            await message.answer("لینک یوتیوب نامعتبر است.")
            return
        
        video_id = url_match.group(1)
        clean_url = f"https://www.youtube.com/watch?v={video_id}"
        
        status_msg = await message.answer("🚀")
        
        # دریافت اطلاعات ویدیو
        ydl_opts = {'quiet': True, 'no_warnings': True, 'logger': logger}
        info = {}
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
        except Exception as e:
            logger.warning(f"yt-dlp نتوانست اطلاعات را بخواند: {e}")
            await status_msg.edit_text(
                "خطا در خواندن اطلاعات ویدیو. ممکن است ویدیو خصوصی یا حذف شده باشد."
            )
            return
        
        title = info.get('title', 'بدون عنوان')
        yt_thumb = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        thumbnail_url = info.get('thumbnail') or yt_thumb
        duration = info.get('duration', 0)
        
        # بررسی محدودیت زمان
        if duration > MAX_DURATION:
            await status_msg.edit_text(
                f"❌ ویدیو ({duration // 60} دقیقه) طولانی‌تر از حد مجاز (30 دقیقه) است."
            )
            return
        
        # ذخیره اطلاعات در FSM
        await state.set_state(DownloadStates.waiting_for_quality)
        await state.update_data(
            video_url=clean_url,
            video_title=title,
            video_id=video_id,
            thumbnail_url=thumbnail_url
        )
        
        # ارسال عکس و دکمه‌ها
        caption = (
            f"<b>{title}</b>\n\n"
            f"⏱️ مدت زمان: {duration // 60}:{duration % 60:02d}\n\n"
            "لطفاً کیفیت مورد نظر را انتخاب کنید:"
        )
        
        # تلاش برای ارسال عکس
        try:
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=thumbnail_url,
                caption=caption,
                reply_markup=get_quality_keyboard()
            )
        except TelegramBadRequest as tbre:
            err_text = str(tbre).lower()
            if 'wrong type of the web page content' in err_text:
                try:
                    if thumbnail_url != yt_thumb:
                        await message.bot.send_photo(
                            chat_id=message.chat.id,
                            photo=yt_thumb,
                            caption=caption,
                            reply_markup=get_quality_keyboard()
                        )
                    else:
                        raise Exception('skip')
                except Exception:
                    # دانلود و ارسال عکس محلی
                    thumb_path = os.path.join(DOWNLOAD_DIR, f"{video_id}_thumb.jpg")
                    try:
                        urllib.request.urlretrieve(yt_thumb, thumb_path)
                        await message.bot.send_photo(
                            chat_id=message.chat.id,
                            photo=FSInputFile(thumb_path),
                            caption=caption,
                            reply_markup=get_quality_keyboard()
                        )
                    except Exception:
                        await message.bot.send_message(
                            chat_id=message.chat.id,
                            text=caption,
                            reply_markup=get_quality_keyboard()
                        )
                    finally:
                        if os.path.exists(thumb_path):
                            try:
                                os.remove(thumb_path)
                            except:
                                pass
            else:
                raise
        
        await status_msg.delete()
    
    except Exception as e:
        logger.error(f"خطا در پردازش لینک: {e}")
        await message.answer(f"خطای ناشناخته: {str(e)}")

async def handle_quality_callback(query, state):
    """ مدیریت انتخاب کیفیت """
    user_data = await state.get_data()
    video_url = user_data.get('video_url')
    video_title = user_data.get('video_title')
    video_id = user_data.get('video_id')
    thumbnail_url = user_data.get('thumbnail_url')
    
    await state.clear()
    
    if not video_url:
        await query.answer("این دکمه منقضی شده است.", show_alert=True)
        await query.message.delete()
        return
    
    quality = query.data.split("_")[1]
    
    if quality == "cancel":
        await query.answer("عملیات لغو شد.")
        await query.message.delete()
        return
    
    await query.answer(f"درخواست شما برای {quality} ثبت شد...")
    
    # ویرایش پیام
    try:
        await query.message.edit_caption(
            caption=f"<b>{video_title}</b>\n\n⏳ در حال آماده‌سازی فایل ({quality})..."
        )
    except Exception as e:
        logger.warning(f"خطا در ویرایش کپشن: {e}")
    
    # بررسی اعتبار
    user_id = query.from_user.id
    success, result = await check_and_consume_credit(user_id)
    
    if not success:
        await query.message.edit_caption(
            caption=f"<b>{video_title}</b>\n\n❌ {result}\n\nلطفاً دوباره تلاش کنید:",
            reply_markup=get_quality_keyboard()
        )
        await state.set_state(DownloadStates.waiting_for_quality)
        await state.update_data(
            video_url=video_url,
            video_title=video_title,
            video_id=video_id,
            thumbnail_url=thumbnail_url
        )
        return
    
    # اجرای دانلود
    loop = asyncio.get_event_loop()
    file_path, error_msg = await loop.run_in_executor(
        None,
        download_video_sync,
        video_url,
        video_id,
        quality
    )
    
    if error_msg or not file_path:
        await query.message.edit_caption(
            caption=f"<b>{video_title}</b>\n\n❌ {error_msg or 'فایل پیدا نشد'}\n\nلطفاً دوباره تلاش کنید:",
            reply_markup=get_quality_keyboard()
        )
        await state.set_state(DownloadStates.waiting_for_quality)
        await state.update_data(
            video_url=video_url,
            video_title=video_title,
            video_id=video_id,
            thumbnail_url=thumbnail_url
        )
        return
    
    # آپلود فایل
    try:
        await query.message.edit_caption(
            caption=f"<b>{video_title}</b>\n\n📤 در حال آپلود فایل ({quality})..."
        )
        
        file_size = os.path.getsize(file_path)
        use_pyrogram = file_size > 49 * 1024 * 1024  # اگر بزرگتر از 49MB باشد
        
        if use_pyrogram:
            # استفاده از Pyrogram برای فایل‌های بزرگ
            pyro_client = await get_pyrogram_client()
            if pyro_client:
                if quality == "audio":
                    await pyro_client.send_audio(
                        chat_id=query.message.chat.id,
                        audio=file_path,
                        caption=video_title
                    )
                else:
                    await pyro_client.send_video(
                        chat_id=query.message.chat.id,
                        video=file_path,
                        caption=f"{video_title} - {quality}p",
                        supports_streaming=True
                    )
            else:
                # اگر Pyrogram در دسترس نبود، با aiogram تلاش می‌کنیم
                file_input = FSInputFile(file_path)
                if quality == "audio":
                    await query.bot.send_audio(
                        chat_id=query.message.chat.id,
                        audio=file_input,
                        caption=video_title,
                        title=video_title
                    )
                else:
                    await query.bot.send_video(
                        chat_id=query.message.chat.id,
                        video=file_input,
                        caption=f"{video_title} - {quality}p",
                        supports_streaming=True
                    )
        else:
            # استفاده از aiogram برای فایل‌های کوچک
            file_input = FSInputFile(file_path)
            if quality == "audio":
                await query.bot.send_audio(
                    chat_id=query.message.chat.id,
                    audio=file_input,
                    caption=video_title,
                    title=video_title
                )
            else:
                await query.bot.send_video(
                    chat_id=query.message.chat.id,
                    video=file_input,
                    caption=f"{video_title} - {quality}p",
                    supports_streaming=True
                )
        
        await query.message.delete()
    
    except Exception as send_error:
        logger.error(f"خطا در ارسال فایل: {send_error}")
        await query.message.edit_caption(
            caption=f"<b>{video_title}</b>\n\n❌ خطا در آپلود: {send_error}",
            reply_markup=get_quality_keyboard()
        )
    
    finally:
        # پاک کردن فایل
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

