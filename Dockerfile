FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng \
    libgl1 libglib2.0-0 \
    libjpeg-dev zlib1g-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    pytesseract pymupdf fastapi uvicorn python-multipart pillow

COPY wrapper.py /app/wrapper.py
COPY start.sh /app/start.sh

EXPOSE 8080

ENV PATH="/usr/local/bin:$PATH"

CMD ["sh", "/app/start.sh"]
