import logging
import asyncio
import yt_dlp
import os
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
def download_media(url, mode='video'):
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best' if mode == 'video' else 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    if mode == 'audio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if mode == 'audio':
            return filename.rsplit('.', 1)[0] + '.mp3'
        return filename

# --- BOT HANDLERLARI ---
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Salom! Menga video linkini yuboring, men uni yuklab beraman. 📥")

@dp.message_handler(regexp=r'(https?://[^\s]+)')
async def handle_video_request(message: types.Message):
    url = message.text
    status_msg = await message.answer("Jarayon boshlandi... ⏳")
    
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, 'video')

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎵 Musiqasini yuklash (MP3)", callback_data=f"mp3_{url}"))

        with open(file_path, 'rb') as video:
            await message.answer_video(video, caption="Tayyor! ✅", reply_markup=keyboard)

        if os.path.exists(file_path):
            os.remove(file_path)
        await status_msg.delete()
        
    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("Kechirasiz, ushbu videoni yuklab bo'lmadi. Link noto'g'ri yoki serverda cheklov bor.")

@dp.callback_query_handler(lambda c: c.data.startswith('mp3_'))
async def process_callback_mp3(callback_query: types.CallbackQuery):
    url = callback_query.data.replace('mp3_', '')
    await bot.answer_callback_query(callback_query.id, "Musiqa tayyorlanmoqda... 🎧")

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, 'audio')

        with open(file_path, 'rb') as audio:
            await bot.send_audio(callback_query.from_user.id, audio, caption="Siz so'ragan musiqa 🎵")
        
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        await bot.send_message(callback_query.from_user.id, "Musiqani yuklashda xatolik bo'ldi.")

# --- ISHGA TUSHIRISH ---
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

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
