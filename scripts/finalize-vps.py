#!/usr/bin/env python3
"""Finalize VPS: security, firewall, backup cron, optional HTTPS prod."""
import io
import os
import sys
import tarfile
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get("VPS_HOST", "80.78.245.66")
PASSWORD = os.environ.get("VPS_PASSWORD", "")
APP_DOMAIN = os.environ.get("APP_DOMAIN", "").strip()
USE_PROD = os.environ.get("USE_PROD", "0") == "1"
INSTALL = "/root/AI_team_takura"

COMPOSE_OVERRIDE = """services:
  ai-team-room:
    ports:
      - "127.0.0.1:8000:8000"
  postgres:
    ports: []
  redis:
    ports: []
"""

CADDY_IP = """:80 {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
"""


def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
    return c


def run(c, cmd, timeout=600):
    sys.stdout.write(f"\n$ {cmd[:100]}\n")
    sys.stdout.flush()
    _, o, e = c.exec_command(cmd, timeout=timeout)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    code = o.channel.recv_exit_status()
    if out:
        sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
        sys.stdout.write("\n")
    if code and err:
        sys.stdout.write(err[-1500:] + "\n")
    if code:
        raise RuntimeError(f"exit {code}: {cmd[:60]}")
    return out


def upload_file(c, remote: str, content: str):
    sftp = c.open_sftp()
    sftp.putfo(io.BytesIO(content.encode()), remote)
    sftp.close()


def main():
    if not PASSWORD:
        sys.exit("Set VPS_PASSWORD")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    c = connect()
    print(f"Connected {HOST}")

    # SSH deploy key
    pub = Path.home() / ".ssh" / "ai_team_regru.pub"
    if pub.exists():
        key = pub.read_text(encoding="utf-8").strip().replace("'", "'\\''")
        run(c, f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && grep -Fq 'ai-team-regru' ~/.ssh/authorized_keys 2>/dev/null || echo '{key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys")

    upload_file(c, f"{INSTALL}/docker-compose.override.yml", COMPOSE_OVERRIDE)

    if USE_PROD and APP_DOMAIN:
        run(c, f"sed -i 's/^APP_DOMAIN=.*/APP_DOMAIN={APP_DOMAIN}/' {INSTALL}/.env")
        figma_uri = f"https://{APP_DOMAIN}/api/figma/callback"
        run(c, f"grep -q '^FIGMA_REDIRECT_URI=' {INSTALL}/.env && sed -i 's|^FIGMA_REDIRECT_URI=.*|FIGMA_REDIRECT_URI={figma_uri}|' {INSTALL}/.env || echo 'FIGMA_REDIRECT_URI={figma_uri}' >> {INSTALL}/.env")
        run(c, f"cd {INSTALL} && docker compose -f docker-compose.prod.yml build --pull", timeout=1200)
        run(c, f"cd {INSTALL} && docker compose -f docker-compose.prod.yml up -d", timeout=600)
    else:
        upload_file(c, "/etc/caddy/Caddyfile", CADDY_IP)
        run(c, "apt-get install -y -qq caddy 2>/dev/null || (apt-get update -qq && apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null; apt-get install -y -qq caddy 2>/dev/null || true)")
        run(c, "systemctl enable caddy 2>/dev/null; systemctl restart caddy 2>/dev/null || true")
        run(c, f"cd {INSTALL} && docker compose up -d", timeout=300)

    # Firewall
    run(c, """export DEBIAN_FRONTEND=noninteractive
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
echo y | ufw enable
ufw status
""")

    # Backup cron daily 3am
    run(c, f"(crontab -l 2>/dev/null | grep -v backup-data; echo '0 3 * * * cd {INSTALL} && bash scripts/backup-data.sh >> backups/cron.log 2>&1') | crontab -")

    # Health
    import time
    time.sleep(8)
    run(c, "curl -sf http://127.0.0.1:8000/api/health || curl -sf http://127.0.0.1/api/health")
    run(c, f"cd {INSTALL} && docker compose ps")

    c.close()
    print("\n=== DONE ===")
    if USE_PROD and APP_DOMAIN:
        print(f"https://{APP_DOMAIN}/app")
    else:
        print(f"http://{HOST}/app")
        print(f"http://{HOST}:8000/app")


if __name__ == "__main__":
    main()
