FROM python:3.10-slim

# FFmpeg ni o'rnatish
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements.txt faylini nusxalash
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot faylini nusxalash (yuklabot.py)
COPY yuklabot.py .

# Yuklamalar uchun papka
RUN mkdir -p downloads

# Portni ochish
EXPOSE 8080

# Botni ishga tushirish
CMD ["python", "yuklabot.py"]
