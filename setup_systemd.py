#!/usr/bin/env python3
import os
import subprocess
import getpass
from pathlib import Path

PROJECT_NAME = "echome"
APP_MODULE = "ECHOME"
BASE_DIR = Path(__file__).resolve().parent
VENV_PATH = BASE_DIR / ".venv"
USER = getpass.getuser()

GUNICORN_SERVICE = f"""
[Unit]
Description=ECHOME Gunicorn Service
After=network.target

[Service]
User={USER}
Group=www-data
WorkingDirectory={BASE_DIR}
ExecStart={VENV_PATH}/bin/gunicorn \
    --workers 3 \
    --bind unix:{BASE_DIR}/echome.sock \
    {APP_MODULE}.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
"""

CELERY_WORKER_SERVICE = f"""
[Unit]
Description=ECHOME Celery Worker
After=network.target redis.service

[Service]
User={USER}
WorkingDirectory={BASE_DIR}
ExecStart={VENV_PATH}/bin/celery -A {APP_MODULE} worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
"""

CELERY_BEAT_SERVICE = f"""
[Unit]
Description=ECHOME Celery Beat
After=network.target redis.service

[Service]
User={USER}
WorkingDirectory={BASE_DIR}
ExecStart={VENV_PATH}/bin/celery -A {APP_MODULE} beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
"""


def write_service(name, content):
    service_path = f"/etc/systemd/system/{name}"
    print(f"[+] Creating: {service_path}")

    with open("/tmp/temp.service", "w") as f:
        f.write(content)

    subprocess.run(["sudo", "mv", "/tmp/temp.service", service_path], check=True)


def verify_service(name):
    service_path = f"/etc/systemd/system/{name}"
    if os.path.exists(service_path):
        print(f"[✅ VERIFIED] {service_path} exists")
    else:
        print(f"[❌ ERROR] {service_path} NOT FOUND")


def main():
    print("\n🚀 Creating systemd service files for ECHOME (NO START / NO ENABLE)\n")

    write_service("echome_gunicorn.service", GUNICORN_SERVICE)
    write_service("echome_celery.service", CELERY_WORKER_SERVICE)
    write_service("echome_beat.service", CELERY_BEAT_SERVICE)

    print("\n🔎 Verifying service files...\n")

    verify_service("echome_gunicorn.service")
    verify_service("echome_celery.service")
    verify_service("echome_beat.service")

    print("\n✅ Service file creation & verification complete.")
    print("\n⚠️ IMPORTANT: Now run these manually:")
    print("sudo systemctl daemon-reload")
    print("sudo systemctl enable echome_gunicorn echome_celery echome_beat")
    print("sudo systemctl start echome_gunicorn echome_celery echome_beat")


if __name__ == "__main__":
    main()
