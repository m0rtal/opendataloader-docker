#!/usr/bin/env python3
import os, signal, subprocess, sys, time, threading, requests

def reap(signum, frame):
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
        except ChildProcessError:
            break

signal.signal(signal.SIGCHLD, reap)

env = os.environ.copy()
env["OMP_NUM_THREADS"] = "4"
env["MKL_NUM_THREADS"] = "4"
env["OPENBLAS_NUM_THREADS"] = "4"
env["TESSDATA_PREFIX"] = "/usr/share/tesseract-ocr/4.00/tessdata"

backend_cmd = [
    "opendataloader-pdf-hybrid",
    "--port", "5002",
    "--ocr-engine", "tesseract",
    "--ocr-lang", "rus,eng",
    "--device", "cpu"
]

proxy_cmd = [
    "python3", "-m", "uvicorn", "wrapper:app",
    "--host", "0.0.0.0", "--port", "8080"
]

backend = subprocess.Popen(backend_cmd, env=env, stdout=sys.stdout, stderr=sys.stderr)
time.sleep(10)

proxy = subprocess.Popen(proxy_cmd, cwd="/app", stdout=sys.stdout, stderr=sys.stderr)

def _backend_alive() -> bool:
    try:
        r = requests.get("http://localhost:5002/v1/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def _restart_backend():
    global backend
    print("HEALTHCHECK: Backend unresponsive, killing and restarting...", flush=True)
    try:
        backend.kill()
        backend.wait(timeout=5)
    except Exception:
        pass
    backend = subprocess.Popen(backend_cmd, env=env, stdout=sys.stdout, stderr=sys.stderr)
    time.sleep(5)
    print(f"HEALTHCHECK: Backend restarted (pid={backend.pid})", flush=True)

def _get_cpu_time(pid):
    """Return cumulative CPU time (user+system) in seconds from /proc/pid/stat."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().split()
        # utime is field 14, stime is field 15 (0-indexed: 13, 14)
        clk_tck = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        utime = int(parts[13])
        stime = int(parts[14])
        return (utime + stime) / clk_tck
    except Exception:
        return None

def hang_monitor():
    """Watchdog: if backend CPU time stalls for 60s while process stays alive, kill it."""
    stall_seconds = 0
    last_cpu = None
    while True:
        time.sleep(10)
        pid = backend.pid
        cpu = _get_cpu_time(pid)
        if cpu is None:
            stall_seconds = 0
            last_cpu = None
            continue
        if last_cpu is not None and cpu == last_cpu:
            stall_seconds += 10
            if stall_seconds >= 60:
                print(f"HANG DETECTED: backend pid={pid} CPU stalled for {stall_seconds}s, killing...", flush=True)
                _restart_backend()
                stall_seconds = 0
                last_cpu = None
        else:
            stall_seconds = 0
            last_cpu = cpu

hang_thread = threading.Thread(target=hang_monitor, daemon=True)
hang_thread.start()

def health_monitor():
    failures = 0
    while True:
        time.sleep(30)
        if _backend_alive():
            failures = 0
            continue
        failures += 1
        print(f"HEALTHCHECK: Backend not responding (failure {failures}/3)", flush=True)
        if failures >= 3:
            _restart_backend()
            failures = 0

monitor = threading.Thread(target=health_monitor, daemon=True)
monitor.start()

while True:
    backend_status = backend.poll()
    proxy_status = proxy.poll()
    
    if backend_status is not None:
        print(f"Backend exited with {backend_status}, restarting...", flush=True)
        backend = subprocess.Popen(backend_cmd, env=env, stdout=sys.stdout, stderr=sys.stderr)
        time.sleep(5)
    
    if proxy_status is not None:
        print(f"Proxy exited with {proxy_status}, exiting...", flush=True)
        sys.exit(proxy_status or 1)
    
    time.sleep(5)
