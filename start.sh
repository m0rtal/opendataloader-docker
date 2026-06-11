#!/bin/sh
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Start backend in background
opendataloader-pdf-hybrid --port 5002 --ocr-engine tesseract --ocr-lang "rus,eng" --device cpu &
BACKEND_PID=$!

# Reap zombie children
python3 -c "
import os, signal, time

def reap(signum, frame):
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
        except ChildProcessError:
            break

signal.signal(signal.SIGCHLD, reap)

# Watchdog: if backend dies, restart
while True:
    try:
        os.kill($BACKEND_PID, 0)
    except OSError:
        print('Backend died, restarting...')
        os.system('opendataloader-pdf-hybrid --port 5002 --ocr-engine tesseract --ocr-lang \"rus,eng\" --device cpu &')
        import subprocess
        # Get new PID
        result = subprocess.run(['pgrep', '-f', 'opendataloader-pdf-hybrid'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = [int(p) for p in result.stdout.strip().split('\n') if p.strip()]
            if pids:
                global BACKEND_PID
                BACKEND_PID = max(pids)
    time.sleep(5)
" &

sleep 10

cd /app
exec python3 -m uvicorn wrapper:app --host 0.0.0.0 --port 8080