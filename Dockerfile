FROM python:3.10-slim

# FFmpeg va kerakli paketlarni o'rnatish
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Ishchi papkani yaratish
WORKDIR /app

# Requirements faylini nusxalash va paketlarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot kodini nusxalash
COPY bot.py .

# Yuklamalar uchun papka yaratish
RUN mkdir -p downloads

# Portni ochish
EXPOSE 8080

# Botni ishga tushirish
CMD ["python", "bot.py"]
