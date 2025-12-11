#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

# -------------------------------
# AUTO DETECT PROJECT PATHS
# -------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PATH = PROJECT_ROOT / ".venv" / "bin"
PYTHON_PATH = VENV_PATH / "python"
GUNICORN_PATH = VENV_PATH / "gunicorn"



# -------------------------------
# AUTO DETECT DJANGO MODULE
# -------------------------------

def detect_django_module():
    for item in PROJECT_ROOT.iterdir():
        if item.is_dir() and (item / "settings.py").exists():
            return item.name
    raise RuntimeError("❌ Could not detect Django module (settings.py not found).")

DJANGO_MODULE = detect_django_module()
WSGI_MODULE = f"{DJANGO_MODULE}.wsgi:application"

print(f"[+] Django module detected as: {DJANGO_MODULE}")
print(f"[+] Using Linux user: ubuntu")

# -------------------------------
# SYSTEMD SERVICE FILES
# -------------------------------

GUNICORN_SERVICE = f"""
[Unit]
Description=Gunicorn Service for Django
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory={PROJECT_ROOT}
Environment="PATH={VENV_PATH}"
ExecStart={GUNICORN_PATH} \\
  --workers 4 \\
  --threads 2 \\
  --preload \\
  --timeout 120 \\
  --bind unix:/run/gunicorn/gunicorn.sock \
  {WSGI_MODULE}

Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

WORKER_SERVICE = f"""
[Unit]
Description=Celery Worker
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory={PROJECT_ROOT}
Environment="PATH={VENV_PATH}"
ExecStart={PYTHON_PATH} -m celery \\
  -A {DJANGO_MODULE} worker \\
  --loglevel=INFO \\
  --concurrency=2 \\
  --prefetch-multiplier=1

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

BEAT_SERVICE = f"""
[Unit]
Description=Celery Beat Scheduler
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory={PROJECT_ROOT}
Environment="PATH={VENV_PATH}"
ExecStart={PYTHON_PATH} -m celery \\
  -A {DJANGO_MODULE} beat \\
  --loglevel=INFO

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

# -------------------------------
# HELPERS
# -------------------------------

def write_service(name, content):
    path = Path(f"/etc/systemd/system/{name}.service")
    with open(path, "w") as f:
        f.write(content.strip() + "\n")
    print(f"[+] Created {path}")

def run(cmd):
    subprocess.run(cmd, check=False)

def reload_systemd():
    run(["sudo", "systemctl", "daemon-reload"])
    run(["sudo", "systemctl", "reset-failed"])

def enable_services():
    for svc in ["gunicorn", "worker", "beat"]:
        run(["sudo", "systemctl", "enable", svc])

def start_services():
    for svc in ["gunicorn", "worker", "beat"]:
        run(["sudo", "systemctl", "start", svc])

def stop_services():
    for svc in ["gunicorn", "worker", "beat"]:
        run(["sudo", "systemctl", "stop", svc])

def restart_services():
    for svc in ["gunicorn", "worker", "beat"]:
        run(["sudo", "systemctl", "restart", svc])

def status_services():
    for svc in ["gunicorn", "worker", "beat"]:
        print(f"\n--- {svc.upper()} STATUS ---")
        run(["sudo", "systemctl", "status", svc])

# -------------------------------
# COMMAND HANDLER
# -------------------------------

def setup():
    print("[*] Writing systemd service files...")
    write_service("gunicorn", GUNICORN_SERVICE)
    write_service("worker", WORKER_SERVICE)
    write_service("beat", BEAT_SERVICE)

    print("[*] Reloading systemd...")
    reload_systemd()

    print("[*] Enabling services...")
    enable_services()

    print("[✅] Setup completed. Now run: ./setup_systemd.py start")

def start():n
    print("[*] Starting services...")
    start_services()
    print("[✅] Services started.")

def stop():
    print("[*] Stopping services...")
    stop_services()
    print("[✅] Services stopped.")

def restart():
    print("[*] Restarting services...")
    restart_services()
    print("[✅] Services restarted.")

def status():
    status_services()

# -------------------------------
# ENTRY POINT
# -------------------------------

if len(sys.argv) != 2:
    print("""
Usage:
  ./setup_systemd.py setup    → create + enable services
  ./setup_systemd.py start    → start services
  ./setup_systemd.py stop     → stop services
  ./setup_systemd.py restart  → restart services
  ./setup_systemd.py status   → show status
""")
    sys.exit(1)

cmd = sys.argv[1].lower()

if cmd == "setup":
    setup()
elif cmd == "start":
    start()
elif cmd == "stop":
    stop()
elif cmd == "restart":
    restart()
elif cmd == "status":
    status()
else:
    print("❌ Unknown command:", cmd)
    sys.exit(1)
