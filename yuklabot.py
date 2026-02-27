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

# Instagram cookies (sizning cookie'laringiz)
INSTAGRAM_COOKIES = {
    'sessionid': '75312399240%3ASsjTaBaMIMjYWN%3A0%3AAYg2uWWAZT0XjZlXkqqqyh5lqlPo8b13IQQ9Or_kjQ',
    'ds_user_id': '75312399240',
    'csrftoken': 'ygLScyAyFAyC-zjc2JrwSQ',
}

# Cookies faylini yaratish
def create_cookie_file():
    """Instagram cookies faylini yaratish"""
    cookie_content = """# Netscape HTTP Cookie File
.instagram.com	TRUE	/	TRUE	1735689600	sessionid	{sessionid}
.instagram.com	TRUE	/	TRUE	1735689600	ds_user_id	{ds_user_id}
.instagram.com	TRUE	/	TRUE	1735689600	csrftoken	{csrftoken}
""".format(**INSTAGRAM_COOKIES)
    
    with open('instagram_cookies.txt', 'w') as f:
        f.write(cookie_content)
    
    logging.info("Instagram cookies fayli yaratildi")

def download_media(url, mode='video'):
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    # Cookies faylini yaratish
    create_cookie_file()
    
    # Asosiy sozlamalar
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': False,  # Xatoliklarni ko'rish uchun False
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 5,
        'cookiefile': 'instagram_cookies.txt',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # Platformaga qarab sozlamalar
    if 'instagram.com' in url:
        # Instagram uchun maxsus sozlamalar
        ydl_opts.update({
            'format': 'best',
            'extract_flat': False,
            'force_generic_extractor': False,
            'instagram_use_web_archive': True,  # Instagram web archive dan foydalanish
        })
    elif 'youtube.com' in url or 'youtu.be' in url:
        # YouTube uchun sozlamalar
        ydl_opts.update({
            'format': 'best[height<=720][ext=mp4]/best[height<=720]' if mode == 'video' else 'bestaudio/best',
            'youtube_include_dash_manifest': False,
            'youtube_skip_dash': True,
        })
    else:
        # Boshqa platformalar
        ydl_opts.update({
            'format': 'best[ext=mp4]/best' if mode == 'video' else 'bestaudio/best',
        })
    
    # Audio uchun sozlamalar
    if mode == 'audio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.info(f"Yuklab olish boshlandi: {url}")
            
            # Ma'lumotni olish
            info = ydl.extract_info(url, download=True)
            
            # Fayl nomini tayyorlash
            filename = ydl.prepare_filename(info)
            
            if mode == 'audio':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            logging.info(f"Yuklab olish tugadi: {filename}")
            return filename
            
    except Exception as e:
        logging.error(f"Download error: {str(e)}", exc_info=True)
        raise

# Qo'llab-quvvatlanadigan platformalar
SUPPORTED_SITES = {
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'instagram.com': 'Instagram',
    'facebook.com': 'Facebook',
    'tiktok.com': 'TikTok',
    'vm.tiktok.com': 'TikTok',
    'fb.watch': 'Facebook',
}

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    sites_list = "\n".join([f"• {name}" for name in set(SUPPORTED_SITES.values())])
    await message.reply(
        "👋 *Salom! Men video yuklovchi botman*\n\n"
        "📥 Menga video linkini yuboring, men uni yuklab beraman.\n\n"
        "*Qo'llab-quvvatlanadigan platformalar:*\n"
        f"{sites_list}\n\n"
        "🔗 *Masalan:* `https://www.instagram.com/reel/XXXXX/`\n"
        "📌 *Eslatma:* Instagram reels va postlar ishlaydi",
        parse_mode='Markdown'
    )

@dp.message_handler(regexp=r'(https?://[^\s]+)')
async def handle_video_request(message: types.Message):
    url = message.text.strip()
    
    # Platformani tekshirish
    platform = None
    for site, name in SUPPORTED_SITES.items():
        if site in url:
            platform = name
            break
    
    if not platform:
        await message.answer("❌ *Bu platforma qo'llab-quvvatlanmaydi*", parse_mode='Markdown')
        return
    
    status_msg = await message.answer(f"⏳ *{platform}* videosi yuklanmoqda...\n\nBu bir necha soniya vaqt olishi mumkin.", parse_mode='Markdown')
    
    try:
        # Yuklab olish
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, 'video')

        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            # Fayl hajmini tekshirish (50MB dan kichik)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            if file_size_mb > 50:
                await message.answer(f"❌ Video hajmi juda katta ({file_size_mb:.1f} MB). Telegram 50 MB dan katta fayllarni qabul qilmaydi.")
                os.remove(file_path)
                await status_msg.delete()
                return
            
            # Keyboard yaratish
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🎵 Musiqasini yuklash (MP3)", callback_data=f"mp3_{url}"))

            # Videoni yuborish
            with open(file_path, 'rb') as video:
                await message.answer_video(
                    video, 
                    caption=f"✅ *{platform}* videosi tayyor!\n\n📹 Hajmi: {file_size_mb:.1f} MB", 
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )

            # Faylni o'chirish
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await status_msg.delete()
        else:
            raise Exception("Yuklab olingan fayl bo'sh yoki mavjud emas")
        
    except Exception as e:
        error_text = str(e)
        logging.error(f"Xato: {error_text}")
        
        # Xatolik turiga qarab habar berish
        if "login" in error_text.lower() or "rate-limit" in error_text.lower():
            await message.answer(
                f"❌ *{platform}* da cheklov mavjud.\n\n"
                "📌 *Sabablari:*\n"
                "• Ko'p so'rov yuborilgan\n"
                "• Video shaxsiy (private)\n"
                "• Video o'chirilgan\n\n"
                "Iltimos, keyinroq urinib ko'ring.",
                parse_mode='Markdown'
            )
        elif "Video unavailable" in error_text:
            await message.answer("❌ *Video mavjud emas yoki o'chirilgan*", parse_mode='Markdown')
        else:
            await message.answer(
                f"❌ *{platform}* videosini yuklab bo'lmadi.*\n\n"
                "📌 *Sabablari:*\n"
                "• Video juda uzun\n"
                "• Mualliflik huquqi bilan himoyalangan\n"
                "• Noma'lum xatolik",
                parse_mode='Markdown'
            )
        
        await status_msg.delete()

@dp.callback_query_handler(lambda c: c.data.startswith('mp3_'))
async def process_callback_mp3(callback_query: types.CallbackQuery):
    url = callback_query.data.replace('mp3_', '')
    await bot.answer_callback_query(callback_query.id, "🎵 Musiqa tayyorlanmoqda...")

    status_msg = await bot.send_message(callback_query.from_user.id, "⏳ *Musiqa yuklanmoqda...*\n\nBu bir necha soniya vaqt olishi mumkin.", parse_mode='Markdown')

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, 'audio')

        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            # Fayl hajmini tekshirish
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            if file_size_mb > 50:
                await bot.send_message(callback_query.from_user.id, f"❌ Audio hajmi juda katta ({file_size_mb:.1f} MB)")
                os.remove(file_path)
                await status_msg.delete()
                return
            
            # Audioni yuborish
            with open(file_path, 'rb') as audio:
                await bot.send_audio(
                    callback_query.from_user.id, 
                    audio, 
                    caption=f"🎵 *Siz so'ragan musiqa*\n\n📀 Hajmi: {file_size_mb:.1f} MB",
                    parse_mode='Markdown'
                )
            
            # Faylni o'chirish
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await status_msg.delete()
        else:
            raise Exception("Audio fayl yuklanmadi")
            
    except Exception as e:
        logging.error(f"Audio xato: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ *Musiqani yuklashda xatolik bo'ldi.*", parse_mode='Markdown')
        await status_msg.delete()

# --- ISHGA TUSHIRISH ---
async def on_startup(dp):
    # Webhook o'rnatish
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
    
    # Cookies faylini yaratish
    create_cookie_file()
    
    # Bot ishga tushganini bildirish
    logging.info("Bot ishga tushdi!")

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
