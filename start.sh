#!/bin/sh
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

opendataloader-pdf-hybrid --port 5002 --hybrid-mode auto --ocr-lang "rus,eng" --device cpu &
sleep 10

cd /app
exec python3 -m uvicorn wrapper:app --host 0.0.0.0 --port 8080
