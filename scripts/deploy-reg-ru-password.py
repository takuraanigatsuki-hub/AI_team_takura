#!/usr/bin/env python3
"""One-shot REG.RU deploy via SSH password (run locally, do not commit)."""
import os
import sys
import getpass
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get("VPS_HOST", "80.78.245.66")
USERS = ("root", "ubuntu", "admin")
PASSWORD = os.environ.get("VPS_PASSWORD", "")
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "takura.anigatsuki@yandex.ru")
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "")
APP_DOMAIN = os.environ.get("APP_DOMAIN", "localhost")
USE_PROD = os.environ.get("USE_PROD", "0")


def read_dotenv(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def build_prod_env(local: dict, pg_pass: str) -> str:
    lines = [
        f"APP_DOMAIN={APP_DOMAIN}",
        f"OPENAI_API_KEY={local.get('OPENAI_API_KEY', '')}",
        f"OPENAI_BASE_URL={local.get('OPENAI_BASE_URL', 'https://api.smartaipi.com/v1')}",
        f"LLM_MODEL={local.get('LLM_MODEL', 'gpt-5.4-mini')}",
        f"LLM_ROUTER_MODEL={local.get('LLM_ROUTER_MODEL', 'gpt-5.4-nano')}",
        f"EMBEDDING_MODEL={local.get('EMBEDDING_MODEL', 'text-embedding-3-small')}",
        "POSTGRES_USER=aiteam",
        f"POSTGRES_PASSWORD={pg_pass}",
        "POSTGRES_DB=aiteam",
        f"DATABASE_URL=postgresql://aiteam:{pg_pass}@postgres:5432/aiteam",
        "SQLITE_DB_PATH=data/ai_team.sqlite",
        f"CURSOR_API_KEY={local.get('CURSOR_API_KEY', '')}",
        f"CURSOR_REPO_URL={local.get('CURSOR_REPO_URL', '')}",
        f"GITHUB_TOKEN={local.get('GITHUB_TOKEN', '')}",
        f"FIGMA_CLIENT_ID={local.get('FIGMA_CLIENT_ID', '')}",
        f"FIGMA_CLIENT_SECRET={local.get('FIGMA_CLIENT_SECRET', '')}",
        f"FIGMA_ACCESS_TOKEN={local.get('FIGMA_ACCESS_TOKEN', '')}",
        f"TELEGRAM_BOT_TOKEN={local.get('TELEGRAM_BOT_TOKEN', '')}",
        f"TELEGRAM_CHAT_ID={local.get('TELEGRAM_CHAT_ID', '')}",
        f"TELEGRAM_POLLING={local.get('TELEGRAM_POLLING', 'true')}",
        "OUTBOUND_PROXY_MODE=off",
        "OUTBOUND_PROXY=",
    ]
    if APP_DOMAIN != "localhost":
        lines.append(f"FIGMA_REDIRECT_URI=https://{APP_DOMAIN}/api/figma/callback")
    else:
        lines.append(f"FIGMA_REDIRECT_URI=http://{HOST}:8000/api/figma/callback")
    return "\n".join(lines) + "\n"


def connect() -> tuple[paramiko.SSHClient, str]:
    if not PASSWORD:
        raise SystemExit("Set VPS_PASSWORD env var")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    last_err = None
    for user in USERS:
        try:
            client.connect(
                HOST, username=user, password=PASSWORD,
                timeout=20, allow_agent=False, look_for_keys=False,
            )
            print(f"Connected as {user}@{HOST}")
            return client, user
        except Exception as e:
            last_err = e
            client.close()
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    raise SystemExit(f"SSH failed for {USERS}: {last_err}")


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 900) -> str:
    print(f"\n$ {cmd[:120]}...")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out[-4000:] if len(out) > 4000 else out)
    if code != 0:
        print(err[-2000:] if err else "")
        raise RuntimeError(f"Command failed ({code}): {cmd[:80]}")
    return out


def main():
    import secrets
    import string
    pg_pass = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
    local = read_dotenv(ROOT / ".env")
    prod_env = build_prod_env(local, pg_pass)

    client, user = connect()
    sftp = client.open_sftp()
    sftp.putfo(__import__("io").BytesIO(prod_env.encode()), "/tmp/ai-team.env")
    sftp.put(str(ROOT / "scripts" / "reg-ru-bootstrap.sh"), "/tmp/reg-ru-bootstrap.sh")
    sftp.close()

    # Install our SSH key for future passwordless access
    pub = Path.home() / ".ssh" / "ai_team_regru.pub"
    if pub.exists():
        key_line = pub.read_text(encoding="utf-8").strip()
        run(client, f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && grep -Fq '{key_line[:40]}' ~/.ssh/authorized_keys 2>/dev/null || echo '{key_line}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys")

    if not OWNER_PASSWORD:
        raise SystemExit("Set OWNER_PASSWORD env var")

    cmd = (
        f"chmod +x /tmp/reg-ru-bootstrap.sh && "
        f"USE_PROD={USE_PROD} "
        f"OWNER_EMAIL='{OWNER_EMAIL}' "
        f"OWNER_PASSWORD='{OWNER_PASSWORD}' "
        f"OWNER_NAME='Owner' "
        f"bash /tmp/reg-ru-bootstrap.sh"
    )
    run(client, cmd, timeout=1200)
    client.close()
    print("\n=== SUCCESS ===")
    print(f"Open: http://{HOST}:8000/app")
    print(f"Login: {OWNER_EMAIL}")


if __name__ == "__main__":
    main()
