import logging
import asyncio
import yt_dlp
import os
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess

# --- SOZLAMALAR ---
API_TOKEN = "8530462813:AAFxPrAjZyDG6Fgv_JMqy0XwMgnCKQp1Zv4"
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL") 
WEBHOOK_PATH = f'/webhook/{API_TOKEN}'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot ishlashda davom etmoqda..."

@app.route('/health')
def health():
    return "OK", 200

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- YUKLASH FUNKSIYASI ---
def check_ffmpeg():
    """FFmpeg mavjudligini tekshirish"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        return True
    except:
        return False

def download_media(url, mode='video'):
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    # FFmpeg mavjudligini tekshirish
    ffmpeg_available = check_ffmpeg()
    if not ffmpeg_available and mode == 'audio':
        logging.warning("FFmpeg topilmadi, audio konvertatsiya qilinmaydi")
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best' if mode == 'video' else 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 5,
        'file_access_retries': 5,
    }
    
    if mode == 'audio' and ffmpeg_available:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif mode == 'audio' and not ffmpeg_available:
        # FFmpeg bo'lmasa, audio sifatida yuklab olish
        ydl_opts['format'] = 'bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # URL ni tekshirish
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise Exception("Video topilmadi")
            
            # Yuklab olish
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if mode == 'audio' and ffmpeg_available:
                return filename.rsplit('.', 1)[0] + '.mp3'
            return filename
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        raise

# --- BOT HANDLERLARI ---
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Salom! Menga video linkini yuboring, men uni yuklab beraman. 📥\n\nMasalan: https://youtube.com/watch?v=...")

@dp.message_handler(regexp=r'(https?://[^\s]+)')
async def handle_video_request(message: types.Message):
    url = message.text.strip()
    status_msg = await message.answer("Jarayon boshlandi... ⏳")
    
    try:
        # Avval linkni tekshirish
        loop = asyncio.get_event_loop()
        
        # Video ma'lumotlarini olish
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            try:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                if not info:
                    raise Exception("Video topilmadi")
            except Exception as e:
                await message.answer(f"❌ Link noto'g'ri yoki video topilmadi: {str(e)[:100]}")
                await status_msg.delete()
                return
        
        # Yuklab olish
        file_path = await loop.run_in_executor(None, download_media, url, 'video')

        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🎵 Musiqasini yuklash (MP3)", callback_data=f"mp3_{url}"))

            with open(file_path, 'rb') as video:
                await message.answer_video(video, caption="✅ Tayyor!", reply_markup=keyboard)

            # Faylni o'chirish
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await status_msg.delete()
        else:
            raise Exception("Yuklab olingan fayl bo'sh yoki mavjud emas")
        
    except Exception as e:
        logging.error(f"Xato: {e}", exc_info=True)
        await message.answer("❌ Kechirasiz, ushbu videoni yuklab bo'lmadi.\n"
                            "Sabablari:\n"
                            "• Link noto'g'ri\n"
                            "• Video juda uzun\n"
                            "• Serverda vaqtinchalik muammo")
        if os.path.exists(file_path) if 'file_path' in locals() else False:
            os.remove(file_path)

@dp.callback_query_handler(lambda c: c.data.startswith('mp3_'))
async def process_callback_mp3(callback_query: types.CallbackQuery):
    url = callback_query.data.replace('mp3_', '')
    await bot.answer_callback_query(callback_query.id, "Musiqa tayyorlanmoqda... 🎧")

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, 'audio')

        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'rb') as audio:
                await bot.send_audio(callback_query.from_user.id, audio, caption="🎵 Siz so'ragan musiqa")
            
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            raise Exception("Audio fayl yuklanmadi")
            
    except Exception as e:
        logging.error(f"Audio xato: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Musiqani yuklashda xatolik bo'ldi.")

# --- ISHGA TUSHIRISH ---
async def on_startup(dp):
    # Webhook o'rnatish
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
    
    # FFmpeg mavjudligini tekshirish
    if check_ffmpeg():
        logging.info("FFmpeg mavjud")
    else:
        logging.warning("FFmpeg topilmadi - audio konvertatsiya ishlamaydi")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        skip_updates=True,
        host='0.0.0.0',
        port=port,
    )
