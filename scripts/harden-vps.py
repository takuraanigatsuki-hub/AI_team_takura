#!/usr/bin/env python3
"""Apply docker-compose override + firewall + cron on VPS."""
import os
import sys
import time
import paramiko

HOST = "80.78.245.66"
PASSWORD = os.environ.get("VPS_PASSWORD", "")
INSTALL = "/root/AI_team_takura"


def run(c, cmd, t=600):
    print(f"$ {cmd[:90]}")
    _, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    code = o.channel.recv_exit_status()
    if out:
        print(out[-3000:])
    if code:
        print("ERR:", err[-800:] if err else code)
        raise SystemExit(code)
    return out


def main():
    if not PASSWORD:
        sys.exit("VPS_PASSWORD required")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)

    run(c, f"test -f {INSTALL}/docker-compose.override.yml || echo 'override missing'")
    run(c, f"cd {INSTALL} && docker compose up -d --build", t=900)
    time.sleep(10)

    run(c, """bash -lc '
export DEBIAN_FRONTEND=noninteractive
command -v ufw >/dev/null || apt-get install -y -qq ufw
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
echo y | ufw enable
ufw status numbered
'""")

    run(c, f"(crontab -l 2>/dev/null | grep -v backup-data; echo '0 3 * * * cd {INSTALL} && bash scripts/backup-data.sh >> backups/cron.log 2>&1') | crontab -")
    run(c, "curl -sf http://127.0.0.1/api/health || curl -sf http://127.0.0.1:8000/api/health")
    run(c, f"cd {INSTALL} && docker compose ps")
    c.close()
    print("\nOK http://80.78.245.66/app")


if __name__ == "__main__":
    main()
