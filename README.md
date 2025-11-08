# 🎬 YouTube Downloader Telegram Bot with AI Subtitle Generator

<div align="center">

[![English](https://img.shields.io/badge/English-🇺🇸-blue?style=for-the-badge)](README.md)
[![فارسی](https://img.shields.io/badge/فارسی-🇮🇷-green?style=for-the-badge)](README_FA.md)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://telegram.org/)
[![YouTube](https://img.shields.io/badge/YouTube-Downloader-red.svg)](https://youtube.com/)

**🚀 Professional Telegram Bot for YouTube Video & Audio Download with AI-Powered Subtitle Generation**

</div>

---

## 📖 Overview

A powerful, feature-rich **Telegram bot** for downloading **YouTube videos** and **audio files** with **AI-powered subtitle generation**. Built with Python and aiogram, this bot offers a complete solution for YouTube content management with advanced features like credit system, referral program, subscription management, and automatic subtitle creation using **faster-whisper** and **WhisperX**.

**👨‍💻 Created by [Hossein Ghorbani](https://github.com/hosseinghorbani0)**

### 🎯 Key Highlights

- ⚡ **Fast & Reliable** - Download YouTube videos in multiple quality options
- 🎵 **Audio Extraction** - Convert videos to MP3 format
- 🤖 **AI Subtitle Generator** - Automatic subtitle generation in Persian and English
- 💳 **Credit System** - Flexible credit-based usage model
- 🔗 **Referral Program** - Built-in referral system for user growth
- 💎 **Subscription System** - Monthly unlimited access plans
- 🛡️ **Admin Panel** - Complete admin dashboard for bot management
- 📢 **Sponsor Management** - Force join channel functionality

---

## ✨ Features

### 🎥 For End Users

#### YouTube Download
- ✅ **Multiple Quality Options** - Download in 480p, 720p, 1080p
- ✅ **Audio Extraction** - Extract audio as MP3 files
- ✅ **YouTube Shorts Support** - Download YouTube Shorts videos
- ✅ **Duration Limit** - Maximum 30 minutes per video
- ✅ **Smart Format Selection** - Automatic best quality selection
- ✅ **Large File Support** - Pyrogram integration for files >49MB

#### AI Subtitle Generation
- ✅ **Automatic Transcription** - AI-powered speech-to-text conversion
- ✅ **Multi-Language Support** - Persian (Farsi) and English subtitles
- ✅ **Word-Level Alignment** - Precise timing with WhisperX
- ✅ **SRT Format Export** - Standard subtitle file format
- ✅ **GPU Acceleration** - Fast processing with CUDA support (optional)

#### Credit & Subscription System
- ✅ **Free Credits** - Initial credits for new users
- ✅ **Referral Rewards** - Earn credits by inviting friends
- ✅ **Unlimited Subscription** - Monthly subscription plans
- ✅ **Redeem Codes** - One-time redeem codes for subscriptions
- ✅ **Credit Tracking** - Real-time credit status monitoring

### 👨‍💼 For Administrators

#### Admin Dashboard
- ✅ **Secure Login** - Username and password authentication
- ✅ **User Statistics** - Total registered users count
- ✅ **Redeem Code Generator** - Create subscription codes
- ✅ **Code Management** - Track code usage and expiration

#### Sponsor Management
- ✅ **Channel Management** - Add/remove sponsor channels (max 6)
- ✅ **Force Join System** - Require channel membership
- ✅ **Automatic Verification** - Check user membership status
- ✅ **Bypass Options** - Admins and subscribers bypass force join

---

## 🏗️ Project Structure

```
├── main.py                  # Main bot entry point
├── config.py                # Configuration settings
├── database.py              # SQLite database management
├── download.py              # YouTube download handler
├── pyrogram_client.py       # Large file upload handler
├── keyboards.py             # Inline & reply keyboards
├── states.py                # FSM states for conversations
├── admin.py                 # Admin panel functionality
├── api_security.py          # API security functions
├── audio_to_subtitle.py     # AI subtitle generation
├── credits.py               # Credit & referral system
├── force_join.py            # Force join channel handler
├── sponsor.py               # Sponsor management
├── user_agents.py           # User-Agent rotation list
├── requirements.txt         # Main dependencies
└── requirements-optional.txt # Optional dependencies
```

---

## 📋 Requirements

### System Requirements

- **Python** 3.8 or higher
- **FFmpeg** (for audio/video processing)
- **SQLite3** (included with Python)

### Python Dependencies

**Core Dependencies:**
```bash
aiogram==3.13.1          # Modern Telegram Bot Framework
yt-dlp==2024.11.16       # YouTube downloader
python-dotenv==1.0.1     # Environment variables
```

**Optional Dependencies (for subtitle generation):**
```bash
faster-whisper          # Fast speech recognition
whisperx                # Word-level alignment
torch                   # PyTorch for GPU acceleration
googletrans==4.0.0-rc1  # Translation service
```

---

## 🚀 Quick Start Guide

### Step 1: Clone Repository

```bash
git clone https://github.com/hosseinghorbani0/youtube-telegram-bot-ai-subtitle.git
cd youtube-telegram-bot-ai-subtitle
```

### Step 2: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install optional dependencies (for subtitle generation)
pip install -r requirements-optional.txt
```

### Step 3: Install FFmpeg

**Windows:**
- Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- Add to system PATH

**Linux:**
```bash
sudo apt-get install ffmpeg
# or
sudo yum install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### Step 4: Configure Environment

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token_here
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
```

**How to get credentials:**

1. **BOT_TOKEN:** Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. **API_ID & API_HASH:** Get from [my.telegram.org](https://my.telegram.org/apps)

### Step 5: Configure Settings

Edit `config.py`:

```python
# Bot Settings
BOT_USERNAME = "your_bot_username"  # Without @

# Admin Settings
ADMIN_USERNAME = "your_admin_username"
ADMIN_PASSWORD = "your_admin_password"
ADMIN_CARD_NUMBER = "your_card_number"
ADMIN_PAYMENT_ID = "@your_telegram_id"

# Subscription Settings
SUBSCRIPTION_PRICE = "50,000 تومان"

# Credit Settings
INITIAL_CREDITS = 5
REFERRAL_BONUS_CREDITS = 1

# Download Settings
MAX_FILE_SIZE = 49 * 1024 * 1024  # 49 MB
MAX_DURATION = 1800  # 30 minutes
```

### Step 6: Run the Bot

```bash
python main.py
```

The database (`bot_data.db`) will be created automatically on first run.

---

## 📚 Technical Documentation

### Core Components

#### 1. `main.py` - Bot Entry Point

Main bot initialization and handler registration.

**Key Handlers:**
- `cmd_start()` - Handles `/start` command with referral link support
- `cmd_admin()` - Admin panel access
- `msg_youtube_link()` - YouTube URL processing
- `cb_quality()` - Quality selection callback handler

**State Management:**
- Uses `aiogram.fsm` for conversation state management
- States defined in `states.py`

#### 2. `database.py` - Database Management

SQLite database operations for users, credits, subscriptions, redeem codes, and sponsors.

**Database Schema:**

```sql
-- Users Table
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    referrer_id INTEGER,
    credits INTEGER DEFAULT 5,
    subscription_end REAL DEFAULT 0
)

-- Redeem Codes Table
CREATE TABLE redeem_codes (
    code TEXT PRIMARY KEY NOT NULL,
    is_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    used_by_id INTEGER
)

-- Sponsors Table
CREATE TABLE sponsors (
    channel_handle TEXT PRIMARY KEY NOT NULL,
    channel_link TEXT NOT NULL
)
```

**Key Functions:**
- `initialize_database()` - Creates all tables
- `add_user()` - Registers new user
- `add_credits()` / `deduct_credits()` - Credit management
- `is_subscribed()` - Checks subscription status
- `create_and_store_redeem_code()` - Generates redeem codes
- `get_sponsors()` / `add_sponsor()` / `remove_sponsor()` - Sponsor management

#### 3. `download.py` - YouTube Download Handler

YouTube video/audio downloading using `yt-dlp`.

**Key Functions:**
- `process_youtube_link()` - Extracts video info and shows quality options
- `handle_quality_callback()` - Processes quality selection and downloads
- `download_video_sync()` - Synchronous download with retry logic
- `get_download_opts()` - Configures yt-dlp options

**Features:**
- Random User-Agent rotation to bypass rate limiting
- Multiple format fallback for reliability
- Pyrogram integration for large files (>49MB)
- Automatic file cleanup after upload

#### 4. `audio_to_subtitle.py` - AI Subtitle Generator

Advanced subtitle generation using faster-whisper and optional WhisperX alignment.

**Key Functions:**
- `transcribe_pipeline()` - Main subtitle generation function
- `transcribe_with_faster_whisper()` - Speech-to-text conversion
- `align_with_whisperx()` - Word-level alignment (optional)
- `build_subtitles()` - Formats subtitles into SRT format

**Configuration:**
- Model selection based on language (Persian/English)
- GPU acceleration support (CUDA)
- Configurable via environment variables

#### 5. `credits.py` - Credit & Referral System

Manages user credits, referrals, and subscriptions.

**Credit Flow:**
1. New users receive `INITIAL_CREDITS` (default: 5)
2. Each download consumes 1 credit (if no active subscription)
3. Referrers receive `REFERRAL_BONUS_CREDITS` (default: 1) per referral
4. Subscribed users have unlimited downloads

#### 6. `admin.py` - Admin Panel

Complete admin functionality for bot management.

**Features:**
- Secure login system
- User statistics
- Redeem code generation
- Session-based authentication

#### 7. `force_join.py` - Force Join System

Enforces channel membership before allowing bot usage.

**Bypass Conditions:**
- Admins (authenticated users)
- Users with active subscriptions

---

## 🎮 Usage

### User Commands

- `/start` - Start the bot
  - Supports referral links: `/start 123456` or `/start ref=123456`

### Menu Buttons

- **📥 دانلود یوتیوب** - Download YouTube video
- **⭐ وضعیت اعتبار** - View credit status
- **🔗 دریافت لینک زیرمجموعه** - Get referral link
- **💳 خرید اشتراک** - Buy subscription

### Admin Commands

- `/admin` - Access admin panel

**Admin Panel Features:**
- **🎁 ساخت ریدیم کد** - Generate redeem codes
- **📢 مدیریت اسپانسرها** - Manage sponsor channels
- **🔒 خروج از پنل** - Logout from admin panel

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token | ✅ Yes |
| `API_ID` | Telegram API ID | ✅ Yes |
| `API_HASH` | Telegram API Hash | ✅ Yes |

### Config.py Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `INITIAL_CREDITS` | 5 | Initial credits for new users |
| `REFERRAL_BONUS_CREDITS` | 1 | Credits per referral |
| `SUBSCRIPTION_DURATION_DAYS` | 30 | Subscription duration |
| `MAX_FILE_SIZE` | 49 MB | Maximum file size |
| `MAX_DURATION` | 1800 seconds | Maximum video duration |

---

## 🐛 Troubleshooting

### Common Issues

**1. Bot not starting**
- Verify `BOT_TOKEN` is set in `.env` file
- Check token validity

**2. Download fails**
- Check internet connection
- Verify YouTube link format
- Ensure video is accessible (not private/restricted)

**3. Database errors**
- Check write permissions in project directory
- Ensure `bot_data.db` is not locked

**4. Subtitle generation not working**
- Install optional dependencies: `pip install -r requirements-optional.txt`
- Ensure FFmpeg is installed and in PATH
- Check GPU availability (optional)

---

## 📝 License

This project is licensed under the **MIT License**.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

**How to contribute:**
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📧 Support

For questions, issues, or support:
- Open an issue on [GitHub Issues](https://github.com/hosseinghorbani0/youtube-telegram-bot-ai-subtitle/issues)
- Check existing issues and discussions

---

## 🙏 Acknowledgments

Special thanks to the open-source community:

- [aiogram](https://github.com/aiogram/aiogram) - Modern Telegram Bot Framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloader
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Fast speech recognition
- [WhisperX](https://github.com/m-bain/whisperX) - Word-level alignment

---

## ⚠️ Disclaimer

This bot is for **educational purposes** only. Please respect YouTube's Terms of Service and copyright laws. Users are responsible for ensuring they have the right to download content.

---

## 🌟 Star History

If you find this project useful, please consider giving it a ⭐ on GitHub!

---

<div align="center">

[![English](https://img.shields.io/badge/English-🇺🇸-blue?style=for-the-badge)](README.md)
[![فارسی](https://img.shields.io/badge/فارسی-🇮🇷-green?style=for-the-badge)](README_FA.md)

**Made with ❤️ for the Telegram community**

[![GitHub stars](https://img.shields.io/github/stars/hosseinghorbani0/youtube-telegram-bot-ai-subtitle?style=social)](https://github.com/hosseinghorbani0/youtube-telegram-bot-ai-subtitle)
[![GitHub forks](https://img.shields.io/github/forks/hosseinghorbani0/youtube-telegram-bot-ai-subtitle?style=social)](https://github.com/hosseinghorbani0/youtube-telegram-bot-ai-subtitle)

---

## 👨‍💻 Author

**Hossein Ghorbani**

- 🌐 Website: [hosseinghorbani0.ir](https://hosseinghorbani0.ir)
- GitHub: [@hosseinghorbani0](https://github.com/hosseinghorbani0)
- Telegram: [@nicot_10](https://t.me/nicot_10)

</div>
