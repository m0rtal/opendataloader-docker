FROM eclipse-temurin:17-jre

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# opendataloader-pdf[hybrid] тянет docling + torch + transformers
# Устанавливаем через venv, чтобы не ломать системный python
RUN python3 -m venv /app/venv
RUN /app/venv/bin/pip install --upgrade pip
RUN /app/venv/bin/pip install "opendataloader-pdf[hybrid]" fastapi uvicorn python-multipart

COPY wrapper.py /app/wrapper.py

# Hybrid backend (docling-fast) + FastAPI sidecar
# Порт 5002 — hybrid backend (внутри контейнера)
# Порт 8080 — FastAPI для скрипта импорта
EXPOSE 8080 5002

ENV PATH="/app/venv/bin:$PATH"
ENV HYBRID_PORT=5002
ENV HYBRID_OCR_LANG=rus,eng

CMD ["sh", "-c", "opendataloader-pdf-hybrid --port ${HYBRID_PORT} --ocr-lang ${HYBRID_OCR_LANG} & sleep 10 && uvicorn wrapper:app --host 0.0.0.0 --port 8080"]
