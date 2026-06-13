#!/usr/bin/env python3
"""Deploy by uploading project tarball to VPS (no git clone needed)."""
import io
import os
import secrets
import string
import tarfile
import tempfile
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get("VPS_HOST", "80.78.245.66")
PASSWORD = os.environ.get("VPS_PASSWORD", "")
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "takura.anigatsuki@yandex.ru")
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "")
INSTALL_DIR = "/root/AI_team_takura"

SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".cursor", "backups", "data", "output", "knowledge",
}
SKIP_FILES = {".env"}


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
    host = HOST
    lines = [
        "APP_DOMAIN=localhost",
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
        f"FIGMA_REDIRECT_URI=http://{host}:8000/api/figma/callback",
        f"TELEGRAM_BOT_TOKEN={local.get('TELEGRAM_BOT_TOKEN', '')}",
        f"TELEGRAM_CHAT_ID={local.get('TELEGRAM_CHAT_ID', '')}",
        f"TELEGRAM_POLLING={local.get('TELEGRAM_POLLING', 'true')}",
        "OUTBOUND_PROXY_MODE=off",
        "OUTBOUND_PROXY=",
    ]
    return "\n".join(lines) + "\n"


def make_tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in ROOT.rglob("*"):
            rel = path.relative_to(ROOT)
            parts = rel.parts
            if parts and parts[0] in SKIP_DIRS:
                continue
            if any(p in SKIP_DIRS for p in parts):
                continue
            if path.name in SKIP_FILES:
                continue
            if path.is_file():
                tar.add(path, arcname=str(rel))
    buf.seek(0)
    return buf.read()


def run(client, cmd, timeout=900):
    print(f"\n$ {cmd[:100]}...")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out[-5000:] if len(out) > 5000 else out)
    if code != 0:
        if err:
            print(err[-2000:])
        raise RuntimeError(f"Failed ({code}): {cmd[:60]}")
    return out


def main():
    if not PASSWORD or not OWNER_PASSWORD:
        raise SystemExit("Set VPS_PASSWORD and OWNER_PASSWORD")

    pg_pass = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
    prod_env = build_prod_env(read_dotenv(ROOT / ".env"), pg_pass)

    print("==> Build tarball")
    data = make_tarball()
    print(f"    {len(data) // 1024} KB")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="root", password=PASSWORD, timeout=30, allow_agent=False, look_for_keys=False)
    print(f"Connected root@{HOST}")

    sftp = client.open_sftp()
    with sftp.file("/tmp/ai-team-project.tar.gz", "wb") as f:
        f.write(data)
    sftp.putfo(io.BytesIO(prod_env.encode()), "/tmp/ai-team.env")
    sftp.close()

    run(client, f"mkdir -p {INSTALL_DIR} && rm -rf {INSTALL_DIR}/* {INSTALL_DIR}/.[!.]* 2>/dev/null; tar -xzf /tmp/ai-team-project.tar.gz -C {INSTALL_DIR}")
    run(client, f"cp /tmp/ai-team.env {INSTALL_DIR}/.env && chmod 600 {INSTALL_DIR}/.env")
    run(client, f"mkdir -p {INSTALL_DIR}/data {INSTALL_DIR}/output {INSTALL_DIR}/knowledge {INSTALL_DIR}/backups")

    run(client, f"cd {INSTALL_DIR} && docker compose build --pull", timeout=1200)
    run(client, f"cd {INSTALL_DIR} && docker compose up -d", timeout=600)

    for _ in range(40):
        try:
            out = run(client, "curl -sf http://127.0.0.1:8000/api/health")
            if "ok" in out:
                break
        except Exception:
            import time
            time.sleep(5)

    run(client, (
        f"cd {INSTALL_DIR} && docker compose exec -T ai-team-room python scripts/create_owner.py "
        f"--email '{OWNER_EMAIL}' --password '{OWNER_PASSWORD}' --name 'Owner'"
    ))

    # Open firewall port 8000 if ufw exists
    run(client, "command -v ufw >/dev/null && ufw allow 8000/tcp || true", timeout=60)

    client.close()
    print("\n=== SUCCESS ===")
    print(f"Site: http://{HOST}:8000/app")
    print(f"Login: {OWNER_EMAIL}")


if __name__ == "__main__":
    main()
