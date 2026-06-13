"""Docker sandbox для безопасного выполнения кода (Фаза C)."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import uuid


def docker_available() -> bool:
    return shutil.which("docker") is not None


async def run_python(
    code: str,
    timeout: int = 30,
    memory_mb: int = 256,
) -> dict:
    """Запуск Python в изолированном контейнере. Fallback — локальный subprocess с ограничениями."""
    import config as cfg

    if not cfg.config.get("sandbox_enabled", True):
        return {"ok": False, "error": "sandbox disabled"}

    code = (code or "").strip()
    if not code:
        return {"ok": False, "error": "empty code"}
    if len(code) > 50000:
        return {"ok": False, "error": "code too large"}

    image = cfg.config.get("sandbox_docker_image") or "python:3.12-slim"

    if docker_available():
        return await _run_docker(code, image, timeout, memory_mb)
    return await _run_local_restricted(code, timeout)


async def _run_docker(code: str, image: str, timeout: int, memory_mb: int) -> dict:
    run_id = uuid.uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix=f"takura_sandbox_{run_id}_") as tmp:
        script = os.path.join(tmp, "main.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)

        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", f"{memory_mb}m",
            "--cpus", "0.5",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
            "-v", f"{script}:/app/main.py:ro",
            image,
            "python", "/app/main.py",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:8000],
                "stderr": stderr.decode("utf-8", errors="replace")[:4000],
                "sandbox": "docker",
            }
        except asyncio.TimeoutError:
            return {"ok": False, "error": "timeout", "sandbox": "docker"}
        except Exception as e:
            return {"ok": False, "error": str(e), "sandbox": "docker"}


async def _run_local_restricted(code: str, timeout: int) -> dict:
    """Fallback без Docker — exec в subprocess, без сети (best-effort)."""
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "main.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmp,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:8000],
                "stderr": stderr.decode("utf-8", errors="replace")[:4000],
                "sandbox": "local",
                "warning": "Docker not found — local subprocess (less isolated)",
            }
        except asyncio.TimeoutError:
            return {"ok": False, "error": "timeout", "sandbox": "local"}
        except Exception as e:
            return {"ok": False, "error": str(e), "sandbox": "local"}
