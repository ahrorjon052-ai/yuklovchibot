# 1. Python-ning yengil versiyasidan foydalanamiz
FROM python:3.10-slim

# 2. Tizim paketlarini yangilaymiz va FFmpeg-ni o'rnatamiz
# Bu qism videodan MP3 ajratish uchun JUDA MUHIM
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. Ishchi katalogni belgilaymiz
WORKDIR /app

# 4. Kerakli kutubxonalar ro'yxatini nusxalaymiz va o'rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Bot kodlarini konteyner ichiga nusxalaymiz
COPY . .

# 6. Yuklamalar uchun papka ochamiz
RUN mkdir -p downloads

# 7. Portni ochamiz (Render uchun)
EXPOSE 8080

# 8. Botni ishga tushiramiz
CMD ["python", "yuklabot.py"]
