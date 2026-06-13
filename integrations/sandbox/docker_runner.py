"""Docker sandbox для безопасного выполнения кода (Фаза C)."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import uuid
from typing import Optional

_WIN_DOCKER_PATHS = [
    r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
    os.path.expandvars(r"%ProgramFiles%\Docker\Docker\resources\bin\docker.exe"),
]


def docker_bin() -> Optional[str]:
    found = shutil.which("docker")
    if found:
        return found
    for p in _WIN_DOCKER_PATHS:
        if p and os.path.isfile(p):
            return p
    return None


def docker_available() -> bool:
    return docker_bin() is not None


async def docker_engine_ready() -> bool:
    exe = docker_bin()
    if not exe:
        return False
    try:
        proc = await asyncio.create_subprocess_exec(
            exe, "info", "-f", "{{.ServerVersion}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
        return proc.returncode == 0 and bool(stdout.strip())
    except Exception:
        return False


async def ensure_sandbox_image(image: str = "python:3.12-slim") -> dict:
    exe = docker_bin()
    if not exe or not await docker_engine_ready():
        return {"ok": False, "reason": "docker engine not ready"}
    try:
        proc = await asyncio.create_subprocess_exec(
            exe, "pull", image,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        return {"ok": proc.returncode == 0, "image": image, "stderr": stderr.decode("utf-8", errors="replace")[-500:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def run_python(
    code: str,
    timeout: int = 30,
    memory_mb: int = 256,
) -> dict:
    """Запуск Python в Docker; fallback — локальный subprocess."""
    import config as cfg

    if not cfg.config.get("sandbox_enabled", True):
        return {"ok": False, "error": "sandbox disabled"}

    code = (code or "").strip()
    if not code:
        return {"ok": False, "error": "empty code"}
    if len(code) > 50000:
        return {"ok": False, "error": "code too large"}

    image = cfg.config.get("sandbox_docker_image") or "python:3.12-slim"

    if docker_bin() and await docker_engine_ready():
        result = await _run_docker(code, image, timeout, memory_mb)
        if result.get("ok") or "Cannot connect" not in str(result.get("error", "")):
            return result

    return await _run_local_restricted(code, timeout)


async def _run_docker(code: str, image: str, timeout: int, memory_mb: int) -> dict:
    exe = docker_bin() or "docker"
    run_id = uuid.uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix=f"takura_sandbox_{run_id}_") as tmp:
        script = os.path.join(tmp, "main.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)

        cmd = [
            exe, "run", "--rm",
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


def _local_python() -> str:
    py312 = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python312", "python.exe")
    if os.path.isfile(py312):
        return py312
    return sys.executable or "python"


async def _run_local_restricted(code: str, timeout: int) -> dict:
    """Fallback без Docker — subprocess с тем же Python."""
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "main.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)
        py = _local_python()
        try:
            proc = await asyncio.create_subprocess_exec(
                py, script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmp,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            warn = None
            if docker_bin():
                warn = "Docker установлен, но engine ещё не готов — local fallback"
            else:
                warn = "Docker not found — local subprocess (less isolated)"
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:8000],
                "stderr": stderr.decode("utf-8", errors="replace")[:4000],
                "sandbox": "local",
                "warning": warn,
            }
        except asyncio.TimeoutError:
            return {"ok": False, "error": "timeout", "sandbox": "local"}
        except Exception as e:
            return {"ok": False, "error": str(e), "sandbox": "local"}
