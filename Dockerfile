FROM eclipse-temurin:17-jre

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /app/venv
RUN /app/venv/bin/pip install --upgrade pip
RUN /app/venv/bin/pip install "opendataloader-pdf[hybrid]" fastapi uvicorn python-multipart

COPY wrapper.py /app/wrapper.py
COPY start.sh /app/start.sh

EXPOSE 8080 5002

ENV PATH="/app/venv/bin:$PATH"
ENV HYBRID_PORT=5002
ENV HYBRID_OCR_LANG=ru,en

CMD ["sh", "/app/start.sh"]
