#!/usr/bin/env python3
"""Fix cloud server: unblock IPs, create owner, restart app."""
import os
import sys
import json
import paramiko

HOST = os.environ.get("VPS_HOST", "80.78.245.66")
PASSWORD = os.environ.get("VPS_PASSWORD", "")
INSTALL = "/root/AI_team_takura"

OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "takura.anigatsuki@gmail.com")
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "")
OWNER_NAME = os.environ.get("OWNER_NAME", "Takura")

# Also ensure yandex admin
YANDEX_EMAIL = "takura.anigatsuki@yandex.ru"


def run(c, cmd, t=120):
    print(f"$ {cmd[:100]}")
    _, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    code = o.channel.recv_exit_status()
    if out:
        print(out[-4000:])
    if code:
        print("ERR:", err[-1000:] if err else code)
        if code != 0:
            raise SystemExit(code)
    return out


def main():
    if not PASSWORD or not OWNER_PASSWORD:
        sys.exit("Set VPS_PASSWORD and OWNER_PASSWORD")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)

    # Clear blocked IPs
    run(c, f"""python3 - <<'PY'
import json, os
p = "{INSTALL}/data/blocked_ips.json"
os.makedirs(os.path.dirname(p), exist_ok=True)
with open(p, "w", encoding="utf-8") as f:
    json.dump({{}}, f)
print("blocked_ips cleared")
PY""")

    # Create owners
    run(c, (
        f"cd {INSTALL} && docker compose exec -T ai-team-room python scripts/create_owner.py "
        f"--email '{OWNER_EMAIL}' --password '{OWNER_PASSWORD}' --name '{OWNER_NAME}'"
    ))
    run(c, (
        f"cd {INSTALL} && docker compose exec -T ai-team-room python scripts/create_owner.py "
        f"--email '{YANDEX_EMAIL}' --password '{OWNER_PASSWORD}' --name 'Takura'"
    ))

    # Patch security: don't auto-block on probe for /api/ paths (in container)
    patch = r"""
import re
path = '/app/middleware/security.py'
try:
    with open(path) as f:
        s = f.read()
    old = 'if monitor.is_blocked(ip):'
    new = '''# Skip block check for health/auth endpoints
        if path in ("/api/health", "/api/auth/login", "/api/auth/register", "/api/auth/me") and monitor.is_blocked(ip):
            try:
                from room.security_monitor import get_monitor
                get_monitor()._blocks.pop(ip, None)
                get_monitor()._save_blocks()
            except Exception:
                pass
        if monitor.is_blocked(ip):'''
    if old in s and new not in s:
        s = s.replace(old, new)
        with open(path, 'w') as f:
            f.write(s)
        print('security patch applied')
    else:
        print('security patch skip')
except Exception as e:
    print('patch err', e)
"""
    # Simpler: patch security_monitor to not block on probe severity - clear is enough + fix THREAT pattern in uploaded code

    run(c, f"cd {INSTALL} && docker compose restart ai-team-room")
    import time
    time.sleep(25)

    run(c, "curl -sf http://127.0.0.1/api/health")
    run(c, f"cd {INSTALL} && docker compose exec -T ai-team-room python -c \"import json; print(json.load(open('data/blocked_ips.json')))\" 2>/dev/null || echo '{{}}'")

    # Test login API
    run(c, f"""curl -s -X POST http://127.0.0.1/api/auth/login -H 'Content-Type: application/json' -d '{{"email":"{OWNER_EMAIL}","password":"{OWNER_PASSWORD}"}}' | head -c 200""")

    c.close()
    print("\n=== FIXED ===")
    print(f"Login: {OWNER_EMAIL}")
    print(f"Site: http://{HOST}/app")


if __name__ == "__main__":
    main()
