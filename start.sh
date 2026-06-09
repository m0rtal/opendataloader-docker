#!/bin/sh
cd /app
exec python3 -m uvicorn wrapper:app --host 0.0.0.0 --port 8080
