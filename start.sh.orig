#!/bin/sh
opendataloader-pdf-hybrid --port 5002 --ocr-lang ru,en &
sleep 10
cd /app
exec python3 -m uvicorn wrapper:app --host 0.0.0.0 --port 8080 --reload --reload-dir /app
