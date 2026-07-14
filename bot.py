"""
Video İndirme Telegram Botu
----------------------------
Kullanıcı YouTube, Instagram, TikTok veya Twitter (X) linki gönderdiğinde
videoyu indirip Telegram üzerinden geri gönderir.

Gereksinimler: requirements.txt
Kurulum ve kullanım için README.md dosyasına bakın.
"""

import os
import re
import logging
import asyncio
import tempfile
import shutil
from pathlib import Path

import yt_dlp
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --------------------------------------------------------------------------
# AYARLAR
# --------------------------------------------------------------------------

# Botunuzun tokenini buraya YAZMAYIN. Ortam değişkeni olarak verin:
#   export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Telegram Bot API üzerinden (resmi/bulut API) gönderilebilecek maksimum
# dosya boyutu ~50 MB'dir. Daha büyük dosyalar için kendi Local Bot API
# Server'ınızı kurmanız gerekir (README'de anlatılıyor).
MAX_FILE_SIZE_MB = 50

# Desteklenen platformları basitçe tanımak için (bilgi amaçlı; yt-dlp
# zaten linki tanımayı kendisi hallediyor)
URL_REGEX = re.compile(r"https?://\S+")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# --------------------------------------------------------------------------

def download_video(url: str, out_dir: str) -> str:
    """
    Verilen URL'deki videoyu out_dir içine indirir ve dosya yolunu döner.
    Hata durumunda yt_dlp.utils.DownloadError fırlatır.
    """
    output_template = str(Path(out_dir) / "%(title).80s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        # 50MB sınırını aşmamak için mp4/h264 öncelikli, mantıklı bir kalite seç
        "format": (
            "best[ext=mp4][filesize<50M]/"
            "best[filesize<50M]/"
            "best[ext=mp4]/best"
        ),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        # Bazı siteler (Instagram gibi) için user-agent gerekebilir
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # merge_output_format mp4 olsa da uzantı bazen farklı gelebilir,
        # gerçek dosyayı klasörden bulalım
        if not os.path.exists(filename):
            candidates = list(Path(out_dir).glob("*"))
            if candidates:
                filename = str(candidates[0])
        return filename


# --------------------------------------------------------------------------
# TELEGRAM HANDLER'LARI
# --------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Merhaba! 👋\n\n"
        "Bana YouTube, Instagram, TikTok veya Twitter (X) linki gönder, "
        "videoyu indirip sana geri göndereyim.\n\n"
        f"Not: Telegram bot API sınırı nedeniyle {MAX_FILE_SIZE_MB}MB'tan "
        "büyük videoları gönderemiyorum."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    match = URL_REGEX.search(text)

    if not match:
        await update.message.reply_text(
            "Lütfen geçerli bir video linki gönder (YouTube, Instagram, "
            "TikTok, Twitter/X)."
        )
        return

    url = match.group(0)
    status_msg = await update.message.reply_text("⏳ Video indiriliyor, biraz bekle...")

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO
    )

    tmp_dir = tempfile.mkdtemp(prefix="videobot_")
    try:
        loop = asyncio.get_running_loop()
        # yt-dlp senkron çalıştığı için thread pool'da çalıştırıyoruz
        filepath = await loop.run_in_executor(None, download_video, url, tmp_dir)

        if not filepath or not os.path.exists(filepath):
            await status_msg.edit_text("❌ Video indirilemedi. Link geçersiz olabilir.")
            return

        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"❌ Video çok büyük ({size_mb:.1f}MB). "
                f"Telegram Bot API limiti {MAX_FILE_SIZE_MB}MB.\n"
                "Daha büyük dosyalar için Local Bot API Server kurulumu "
                "gerekiyor (README.md'ye bakın)."
            )
            return

        await status_msg.edit_text("📤 Gönderiliyor...")
        with open(filepath, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="✅ İşte videon!",
                supports_streaming=True,
                read_timeout=120,
                write_timeout=120,
                connect_timeout=60,
            )
        await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        logger.error("Download error: %s", e)
        await status_msg.edit_text(
            "❌ Video indirilemedi. Link desteklenmiyor olabilir ya da "
            "içerik özel/kısıtlı olabilir."
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Beklenmeyen hata")
        await status_msg.edit_text(f"❌ Bir hata oluştu: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# --------------------------------------------------------------------------
# ANA GİRİŞ NOKTASI
# --------------------------------------------------------------------------

def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN ortam değişkeni bulunamadı.\n"
            'Örnek: export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."'
        )

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot başlatılıyor...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
