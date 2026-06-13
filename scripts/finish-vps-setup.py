#!/usr/bin/env python3
import os, sys, time
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOST = "80.78.245.66"
PASSWORD = os.environ.get("VPS_PASSWORD", "")
EMAIL = "takura.anigatsuki@yandex.ru"
APP_PW = os.environ.get("OWNER_PASSWORD", PASSWORD)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)

def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    code = o.channel.recv_exit_status()
    print(out)
    if err and code:
        print("ERR:", err[:500])
    return code, out

time.sleep(15)
print("=== health")
run("curl -s http://127.0.0.1:8000/api/health")
print("=== owner")
run(f"cd /root/AI_team_takura && docker compose exec -T ai-team-room python scripts/create_owner.py --email '{EMAIL}' --password '{APP_PW}' --name Owner")
print("=== firewall")
run("ufw allow 8000/tcp 2>/dev/null; ufw allow 80/tcp 2>/dev/null; ufw allow 443/tcp 2>/dev/null; true")
print("=== ps")
run("cd /root/AI_team_takura && docker compose ps")
c.close()
print(f"\nDONE: http://{HOST}:8000/app")
