import os
import logging
from aiogram import Bot, Dispatcher, executor, types
import yt_dlp

# 1. Bot va Logging sozlamalari
API_TOKEN = "8530462813:AAFxPrAjZyDG6Fgv_JMqy0XwMgnCKQp1Zv4"
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 2. Yuklash funksiyasi
def download_media(url):
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        # Agar youtube/instagram bloklasa, bu yerga 'cookiefile' qo'shiladi
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# 3. Bot komandalari
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Salom! Video yuklash uchun Instagram yoki YouTube linkini yuboring.")

@dp.message_handler()
async def handle_message(message: types.Message):
    url = message.text
    if "instagram.com" in url or "youtube.com" in url or "youtu.be" in url:
        status_msg = await message.reply("Yuklanmoqda, iltimos kuting...")
        try:
            file_path = download_media(url)
            with open(file_path, 'rb') as video:
                await message.reply_video(video)
            os.remove(file_path) # Faylni o'chirish (joy tejash uchun)
            await status_msg.delete()
        except Exception as e:
            await message.reply(f"Xato yuz berdi: {str(e)}")
    else:
        await message.reply("Iltimos, faqat video havolasini yuboring.")

# 4. BOTNI ISHGA TUSHIRISH (Polling rejimi)
if __name__ == '__main__':
    # Bu qism Render'da webhook xatolarisiz ishlashni ta'minlaydi
    executor.start_polling(dp, skip_updates=True)
