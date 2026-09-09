# -*- coding: utf-8 -*-
"""
مدیریت دانلود یوتیوب

نکته مهم:
- قراردادهای عمومی ماژول حفظ شده‌اند.
- نام و امضای توابع اصلی تغییر نکرده است.
- کلیدهای FSM، callback format و خروجی‌های کاربر حفظ شده‌اند.
- منطق انتخاب کیفیت، اعتبار، دانلود، آپلود و cleanup عمداً تغییر نکرده است.
"""

import asyncio
import glob
import logging
import os
import random
import re
import time
import urllib.request
from typing import Optional, Tuple

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from config import DOWNLOAD_DIR, MAX_DURATION, MAX_FILE_SIZE
from credits import check_and_consume_credit
from keyboards import get_quality_keyboard
from pyrogram_client import get_pyrogram_client
from states import DownloadStates
from user_agents import USER_AGENTS


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Compatibility / public constants
# ---------------------------------------------------------------------------

class DownloadState:
    """Compatibility alias؛ state اصلی از DownloadStates مدیریت می‌شود."""

    waiting_for_quality = "waiting_for_quality"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YOUTUBE_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)"
    r"([a-zA-Z0-9_-]{11})"
)

YOUTUBE_THUMBNAIL_TEMPLATE = "https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

DOWNLOAD_RETRIES = 2
RETRY_DELAY_SECONDS = 1.0
PYROGRAM_THRESHOLD_BYTES = 49 * 1024 * 1024

AUDIO_FORMATS = (
    "bestaudio[ext=m4a]",
    "bestaudio[ext=mp3]",
    "bestaudio",
    "worstaudio",
)

VIDEO_FALLBACK_FORMATS = (
    "22/18/136/137/248",
    "best",
    "worst",
)

FSM_DATA_KEYS = (
    "video_url",
    "video_title",
    "video_id",
    "thumbnail_url",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_download_dir() -> None:
    """اطمینان از وجود پوشه دانلود."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _remove_file_safely(file_path: str) -> None:
    """حذف امن یک فایل بدون ایجاد خطا در مسیر اصلی."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError as exc:
        logger.debug("حذف فایل ناموفق بود (%s): %s", file_path, exc)


def _cleanup_video_files(video_id: str) -> None:
    """فایل‌های قبلی مربوط به همان ویدیو را پاک می‌کند."""
    _ensure_download_dir()

    for file_name in os.listdir(DOWNLOAD_DIR):
        if file_name.startswith(video_id):
            _remove_file_safely(os.path.join(DOWNLOAD_DIR, file_name))


def _find_downloaded_file(video_id: str) -> Optional[str]:
    """اولین فایل خروجی مربوط به video_id را پیدا می‌کند."""
    pattern = os.path.join(DOWNLOAD_DIR, f"{video_id}.*")
    files = glob.glob(pattern)
    return files[0] if files else None


def _is_file_size_valid(file_path: str) -> bool:
    """بررسی می‌کند فایل از محدودیت حجم بیشتر نباشد."""
    try:
        return os.path.getsize(file_path) <= MAX_FILE_SIZE
    except OSError:
        return False


def _build_video_formats(quality: str) -> Tuple[str, ...]:
    """لیست فرمت‌های قابل تلاش را بدون تغییر قرارداد قبلی می‌سازد."""
    if quality == "audio":
        return AUDIO_FORMATS

    return (
        f"best[height<={quality}]/22/18",
        *VIDEO_FALLBACK_FORMATS,
    )


def _restore_download_state(
    state,
    video_url: str,
    video_title: str,
    video_id: str,
    thumbnail_url: str,
):
    """بازگرداندن داده‌های FSM در صورت شکست عملیات."""
    return state.set_state(DownloadStates.waiting_for_quality)


async def _set_download_state(
    state,
    video_url: str,
    video_title: str,
    video_id: str,
    thumbnail_url: str,
) -> None:
    """ثبت اطلاعات ویدیو در FSM."""
    await state.set_state(DownloadStates.waiting_for_quality)
    await state.update_data(
        video_url=video_url,
        video_title=video_title,
        video_id=video_id,
        thumbnail_url=thumbnail_url,
    )


async def _restore_download_state(
    state,
    video_url: str,
    video_title: str,
    video_id: str,
    thumbnail_url: str,
) -> None:
    """بازگردانی کامل FSM پس از خطای اعتبار یا دانلود."""
    await _set_download_state(
        state,
        video_url,
        video_title,
        video_id,
        thumbnail_url,
    )


async def _edit_caption_safely(message, caption: str, **kwargs) -> bool:
    """ویرایش کپشن بدون شکستن جریان اصلی در صورت خطای تلگرام."""
    try:
        await message.edit_caption(caption=caption, **kwargs)
        return True
    except Exception as exc:
        logger.warning("خطا در ویرایش کپشن: %s", exc)
        return False


async def _send_small_file(bot, chat_id: int, file_path: str, title: str, quality: str) -> None:
    """ارسال فایل با aiogram؛ قرارداد ارسال قبلی حفظ شده است."""
    file_input = FSInputFile(file_path)

    if quality == "audio":
        await bot.send_audio(
            chat_id=chat_id,
            audio=file_input,
            caption=title,
            title=title,
        )
        return

    await bot.send_video(
        chat_id=chat_id,
        video=file_input,
        caption=f"{title} - {quality}p",
        supports_streaming=True,
    )


async def _send_large_file(
    bot,
    chat_id: int,
    file_path: str,
    title: str,
    quality: str,
) -> None:
    """ارسال فایل بزرگ با Pyrogram و fallback به aiogram."""
    pyro_client = await get_pyrogram_client()

    if pyro_client:
        if quality == "audio":
            await pyro_client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                caption=title,
            )
        else:
            await pyro_client.send_video(
                chat_id=chat_id,
                video=file_path,
                caption=f"{title} - {quality}p",
                supports_streaming=True,
            )
        return

    # Fallback اصلی پروژه حفظ شده است.
    await _send_small_file(bot, chat_id, file_path, title, quality)


async def _send_downloaded_file(
    query,
    file_path: str,
    video_title: str,
    quality: str,
) -> None:
    """انتخاب مسیر آپلود بر اساس حجم فایل."""
    file_size = os.path.getsize(file_path)
    chat_id = query.message.chat.id

    if file_size > PYROGRAM_THRESHOLD_BYTES:
        await _send_large_file(
            query.bot,
            chat_id,
            file_path,
            video_title,
            quality,
        )
        return

    await _send_small_file(
        query.bot,
        chat_id,
        file_path,
        video_title,
        quality,
    )


async def _send_thumbnail_with_fallback(
    message,
    thumbnail_url: str,
    fallback_thumbnail_url: str,
    caption: str,
) -> None:
    """ارسال thumbnail با fallback همانند منطق قبلی."""
    try:
        await message.bot.send_photo(
            chat_id=message.chat.id,
            photo=thumbnail_url,
            caption=caption,
            reply_markup=get_quality_keyboard(),
        )
        return

    except TelegramBadRequest as exc:
        error_text = str(exc).lower()

        if "wrong type of the web page content" not in error_text:
            raise

        # تلاش دوم با thumbnail استاندارد یوتیوب.
        if thumbnail_url != fallback_thumbnail_url:
            try:
                await message.bot.send_photo(
                    chat_id=message.chat.id,
                    photo=fallback_thumbnail_url,
                    caption=caption,
                    reply_markup=get_quality_keyboard(),
                )
                return
            except Exception as fallback_exc:
                logger.debug(
                    "ارسال thumbnail جایگزین ناموفق بود: %s",
                    fallback_exc,
                )

        # آخرین fallback: دانلود thumbnail روی دیسک.
        thumb_path = os.path.join(
            DOWNLOAD_DIR,
            f"{message.text and _extract_video_id(message.text) or 'youtube'}_thumb.jpg",
        )

        try:
            urllib.request.urlretrieve(fallback_thumbnail_url, thumb_path)
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=FSInputFile(thumb_path),
                caption=caption,
                reply_markup=get_quality_keyboard(),
            )
        except Exception as local_exc:
            logger.warning(
                "ارسال thumbnail محلی ناموفق بود؛ ارسال متن: %s",
                local_exc,
            )
            await message.bot.send_message(
                chat_id=message.chat.id,
                text=caption,
                reply_markup=get_quality_keyboard(),
            )
        finally:
            _remove_file_safely(thumb_path)


def _extract_video_id(text: Optional[str]) -> Optional[str]:
    """استخراج شناسه 11 کاراکتری ویدیو از متن."""
    if not text:
        return None

    match = YOUTUBE_URL_PATTERN.search(text)
    return match.group(1) if match else None


def _format_duration(duration) -> str:
    """فرمت مدت زمان با رفتار قبلی."""
    try:
        seconds = int(duration or 0)
    except (TypeError, ValueError):
        seconds = 0

    return f"{seconds // 60}:{seconds % 60:02d}"


# ---------------------------------------------------------------------------
# yt-dlp configuration
# ---------------------------------------------------------------------------

def get_download_opts(format_str):
    """تنظیمات yt-dlp."""
    _ensure_download_dir()

    return {
        "format": format_str,
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "http_headers": {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "quiet": True,
        "no_warnings": True,
        "logger": logger,
        "retries": 10,
        "fragment_retries": 10,
        "no_check_certificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"],
            },
        },
        "cookies": "cookies.txt",
    }


# ---------------------------------------------------------------------------
# Download engine
# ---------------------------------------------------------------------------

def download_video_sync(url: str, video_id: str, quality: str):
    """
    دانلود ویدیو با yt-dlp به‌صورت synchronous.

    خروجی دقیقاً همان قرارداد قبلی است:
        (file_path, None)
        یا
        (None, error_message)
    """
    _ensure_download_dir()
    _cleanup_video_files(video_id)

    formats = _build_video_formats(quality)

    for fmt in formats:
        for attempt in range(1, DOWNLOAD_RETRIES + 2):
            try:
                logger.info(
                    "شروع دانلود: video_id=%s format=%s attempt=%s",
                    video_id,
                    fmt,
                    attempt,
                )

                with YoutubeDL(get_download_opts(fmt)) as ydl:
                    ydl.download([url])

                file_path = _find_downloaded_file(video_id)

                if file_path:
                    if _is_file_size_valid(file_path):
                        logger.info(
                            "دانلود موفق: video_id=%s path=%s",
                            video_id,
                            file_path,
                        )
                        return file_path, None

                    logger.warning(
                        "فایل بیشتر از MAX_FILE_SIZE است: %s",
                        file_path,
                    )
                    _remove_file_safely(file_path)

                # در صورت خروجی نامعتبر، همین format را دوباره بی‌جهت ادامه نده.
                break

            except DownloadError as exc:
                logger.warning(
                    "yt-dlp خطا داد (video_id=%s, fmt=%s, attempt=%s): %s",
                    video_id,
                    fmt,
                    attempt,
                    exc,
                )

            except Exception as exc:
                logger.exception(
                    "خطای غیرمنتظره در دانلود "
                    "(video_id=%s, fmt=%s, attempt=%s): %s",
                    video_id,
                    fmt,
                    attempt,
                    exc,
                )

            if attempt <= DOWNLOAD_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    logger.error("دانلود نهایی ناموفق بود: video_id=%s", video_id)
    return None, "نمی‌توانم ویدیو را دانلود کنم."


# ---------------------------------------------------------------------------
# YouTube link processing
# ---------------------------------------------------------------------------

async def process_youtube_link(message, state):
    """پردازش لینک یوتیوب."""
    status_msg = None

    try:
        video_id = _extract_video_id(message.text)

        if not video_id:
            await message.answer("لینک یوتیوب نامعتبر است.")
            return

        clean_url = f"https://www.youtube.com/watch?v={video_id}"
        status_msg = await message.answer("🚀")

        # دریافت اطلاعات ویدیو
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "logger": logger,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
        except Exception as exc:
            logger.warning(
                "yt-dlp نتوانست اطلاعات را بخواند "
                "(video_id=%s): %s",
                video_id,
                exc,
            )
            await status_msg.edit_text(
                "خطا در خواندن اطلاعات ویدیو. ممکن است ویدیو خصوصی یا حذف شده باشد."
            )
            return

        title = info.get("title", "بدون عنوان")
        fallback_thumbnail = YOUTUBE_THUMBNAIL_TEMPLATE.format(video_id=video_id)
        thumbnail_url = info.get("thumbnail") or fallback_thumbnail
        duration = info.get("duration", 0)

        # بررسی محدودیت زمان
        if duration > MAX_DURATION:
            await status_msg.edit_text(
                f"❌ ویدیو ({duration // 60} دقیقه) "
                f"طولانی‌تر از حد مجاز (30 دقیقه) است."
            )
            return

        # ذخیره اطلاعات در FSM
        await _set_download_state(
            state,
            video_url=clean_url,
            video_title=title,
            video_id=video_id,
            thumbnail_url=thumbnail_url,
        )

        caption = (
            f"<b>{title}</b>\n\n"
            f"⏱️ مدت زمان: {_format_duration(duration)}\n\n"
            "لطفاً کیفیت مورد نظر را انتخاب کنید:"
        )

        await _send_thumbnail_with_fallback(
            message,
            thumbnail_url,
            fallback_thumbnail,
            caption,
        )

        if status_msg:
            try:
                await status_msg.delete()
            except Exception as exc:
                logger.debug("حذف status message ناموفق بود: %s", exc)

    except Exception as exc:
        logger.exception("خطا در پردازش لینک یوتیوب: %s", exc)

        try:
            await message.answer(f"خطای ناشناخته: {str(exc)}")
        except Exception:
            logger.exception("ارسال پیام خطای نهایی نیز ناموفق بود.")


# ---------------------------------------------------------------------------
# Quality callback
# ---------------------------------------------------------------------------

async def handle_quality_callback(query, state):
    """مدیریت انتخاب کیفیت."""
    user_data = await state.get_data()

    video_url = user_data.get("video_url")
    video_title = user_data.get("video_title")
    video_id = user_data.get("video_id")
    thumbnail_url = user_data.get("thumbnail_url")

    await state.clear()

    if not video_url:
        await query.answer("این دکمه منقضی شده است.", show_alert=True)

        try:
            await query.message.delete()
        except Exception as exc:
            logger.debug("حذف پیام منقضی‌شده ناموفق بود: %s", exc)

        return

    # عمداً ساختار callback قبلی حفظ شده است.
    quality = query.data.split("_")[1]

    if quality == "cancel":
        await query.answer("عملیات لغو شد.")

        try:
            await query.message.delete()
        except Exception as exc:
            logger.debug("حذف پیام لغو ناموفق بود: %s", exc)

        return

    await query.answer(f"درخواست شما برای {quality} ثبت شد...")

    await _edit_caption_safely(
        query.message,
        f"<b>{video_title}</b>\n\n"
        f"⏳ در حال آماده‌سازی فایل ({quality})...",
    )

    # ------------------------------------------------------------------
    # Credit
    # ------------------------------------------------------------------
    user_id = query.from_user.id
    success, result = await check_and_consume_credit(user_id)

    if not success:
        await query.message.edit_caption(
            caption=(
                f"<b>{video_title}</b>\n\n"
                f"❌ {result}\n\n"
                "لطفاً دوباره تلاش کنید:"
            ),
            reply_markup=get_quality_keyboard(),
        )

        await _restore_download_state(
            state,
            video_url,
            video_title,
            video_id,
            thumbnail_url,
        )
        return

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------
    loop = asyncio.get_event_loop()

    file_path, error_msg = await loop.run_in_executor(
        None,
        download_video_sync,
        video_url,
        video_id,
        quality,
    )

    if error_msg or not file_path:
        await query.message.edit_caption(
            caption=(
                f"<b>{video_title}</b>\n\n"
                f"❌ {error_msg or 'فایل پیدا نشد'}\n\n"
                "لطفاً دوباره تلاش کنید:"
            ),
            reply_markup=get_quality_keyboard(),
        )

        await _restore_download_state(
            state,
            video_url,
            video_title,
            video_id,
            thumbnail_url,
        )
        return

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    try:
        await query.message.edit_caption(
            caption=(
                f"<b>{video_title}</b>\n\n"
                f"📤 در حال آپلود فایل ({quality})..."
            )
        )

        await _send_downloaded_file(
            query,
            file_path,
            video_title,
            quality,
        )

        await query.message.delete()

    except Exception as send_error:
        logger.exception("خطا در ارسال فایل: %s", send_error)

        await query.message.edit_caption(
            caption=(
                f"<b>{video_title}</b>\n\n"
                f"❌ خطا در آپلود: {send_error}"
            ),
            reply_markup=get_quality_keyboard(),
        )

    finally:
        # Cleanup قطعی؛ حتی در صورت شکست آپلود.
        _remove_file_safely(file_path)
