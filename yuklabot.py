import os
import logging
import asyncio
import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Sozlamalar
API_TOKEN = "8530462813:AAFxPrAjZyDG6Fgv_JMqy0XwMgnCKQp1Zv4"
# Render URL: masalan https://loyiha.onrender.com
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL") 
WEBHOOK_PATH = f'/webhook/{API_TOKEN}'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Yuklash funksiyasi
def download_media(url, mode='video'):
    ydl_opts = {
        'format': 'best[ext=mp4]/best' if mode == 'video' else 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
    }
    if mode == 'audio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info) if mode == 'video' else ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Salom! Menga ijtimoiy tarmoqdan video linkini yuboring.")

@dp.message_handler(regexp='http')
async def handle_message(message: types.Message):
    status_msg = await message.answer("Video tayyorlanmoqda...")
    url = message.text

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, 'video')
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎵 Musiqasini yuklash", callback_data=f"mp3_{url}"))
        
        with open(file_path, 'rb') as video:
            await message.answer_video(video, caption="Tayyor!", reply_markup=keyboard)
        
        os.remove(file_path) # Joyni tejash
        await status_msg.delete()
    except Exception as e:
        await message.answer(f"Xato: {str(e)}")

@dp.callback_query_handler(lambda c: c.data.startswith('mp3_'))
async def process_callback_mp3(callback_query: types.CallbackQuery):
    url = callback_query.data.replace('mp3_', '')
    await bot.answer_callback_query(callback_query.id, "Musiqa yuklanmoqda...")
    
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, 'audio')
        
        with open(file_path, 'rb') as audio:
            await bot.send_audio(callback_query.from_user.id, audio)
        os.remove(file_path)
    except Exception as e:
        await bot.send_message(callback_query.from_user.id, "Musiqa yuklashda xato bo'ldi.")

# Render uchun Webhook sozlamalari
async def on_startup(dp):
    if not os.path.exists('downloads'): os.makedirs('downloads')
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == '__main__':
    # Render PORT beradi, agar bo'lmasa 8080 ishlatiladi
    port = int(os.environ.get("PORT", 8080))
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host='0.0.0.0',
        port=port,
    )
