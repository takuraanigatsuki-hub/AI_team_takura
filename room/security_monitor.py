"""Мониторинг угроз: блокировка IP, события, триггер Security Agent."""

from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from room.audit_log import log_event

EVENTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "security_events.json")
BLOCKS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "blocked_ips.json")

THREAT_PATTERNS = [
    (re.compile(r"(?i)(union\s+select|drop\s+table|;\s*--|';\s*drop)"), "sqli"),
    (re.compile(r"(?i)(<script|javascript:|onerror=|onload=)"), "xss"),
    (re.compile(r"(?i)(\.\./|\.\.\\|/etc/passwd|/proc/self)"), "path_traversal"),
    # Не матчить легитимный GET /api/config — иначе блокируется IP пользователя
    (re.compile(r"(?i)(/wp-admin|/admin\.php|/\.env\b|/api/\.env|/phpmyadmin)"), "probe"),
]

HONEYPOT_PATHS = frozenset({
    "/admin.php", "/wp-login.php", "/.env", "/api/.env",
    "/api/admin/config", "/phpmyadmin", "/.git/config",
})


class SecurityMonitor:
    def __init__(self):
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._404_hits: dict[str, list[float]] = defaultdict(list)
        self._pending: list[dict] = []
        self._blocks = self._load_blocks()

    def _load_blocks(self) -> dict:
        if not os.path.exists(BLOCKS_FILE):
            return {}
        try:
            with open(BLOCKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_blocks(self) -> None:
        os.makedirs(os.path.dirname(BLOCKS_FILE), exist_ok=True)
        with open(BLOCKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._blocks, f, ensure_ascii=False, indent=2)

    def _save_event(self, event: dict) -> None:
        events = []
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                    events = json.load(f)
            except Exception:
                pass
        events.append(event)
        os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events[-500:], f, ensure_ascii=False, indent=2)

    def is_blocked(self, ip: str) -> bool:
        if not ip:
            return False
        entry = self._blocks.get(ip)
        if not entry:
            return False
        try:
            until = datetime.fromisoformat(entry["until"])
            if datetime.now() < until:
                return True
            del self._blocks[ip]
            self._save_blocks()
        except Exception:
            pass
        return False

    def block_ip(self, ip: str, minutes: int = 60, reason: str = "") -> None:
        if not ip or ip in ("127.0.0.1", "::1"):
            return
        self._blocks[ip] = {
            "until": (datetime.now() + timedelta(minutes=minutes)).isoformat(),
            "reason": reason[:200],
            "blocked_at": datetime.now().isoformat(),
        }
        self._save_blocks()
        log_event("ip_blocked", ip=ip, detail=reason, severity="critical")

    def check_rate(self, ip: str, max_req: int = 120, window: int = 60) -> bool:
        now = time.time()
        hits = [t for t in self._hits[ip] if t > now - window]
        self._hits[ip] = hits
        if len(hits) >= max_req:
            return False
        hits.append(now)
        return True

    def record_404(self, ip: str, path: str) -> Optional[dict]:
        now = time.time()
        hits = [t for t in self._404_hits[ip] if t > now - 60]
        hits.append(now)
        self._404_hits[ip] = hits
        if len(hits) >= 15:
            return self.record_threat(
                ip=ip, path=path, threat_type="scan",
                detail=f"15+ 404 за минуту с {ip}",
                severity="high",
            )
        return None

    def scan_payload(self, text: str, ip: str = "", path: str = "") -> Optional[dict]:
        if not text:
            return None
        for pattern, kind in THREAT_PATTERNS:
            if pattern.search(text):
                return self.record_threat(
                    ip=ip, path=path, threat_type=kind,
                    detail=text[:200], severity="high",
                )
        return None

    def is_honeypot(self, path: str) -> bool:
        p = (path or "").lower().split("?")[0]
        return p in HONEYPOT_PATHS or p.endswith("/.env")

    def record_threat(
        self,
        *,
        ip: str = "",
        path: str = "",
        threat_type: str = "unknown",
        detail: str = "",
        severity: str = "medium",
        user_id: str = "",
    ) -> dict:
        event = {
            "id": f"sec-{int(time.time())}",
            "ip": ip,
            "path": path,
            "threat_type": threat_type,
            "detail": detail[:400],
            "severity": severity,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "handled": False,
        }
        self._pending.append(event)
        self._save_event(event)
        log_event(
            f"threat_{threat_type}",
            ip=ip, path=path, detail=detail, severity=severity, user_id=user_id,
        )
        if severity in ("high", "critical"):
            self.block_ip(ip, minutes=30, reason=threat_type)
        try:
            from room import notifications
            notifications.push(
                f"🛡 Threat: {threat_type}",
                detail[:200],
                ntype="security",
                link="/app?view=admin",
            )
        except Exception:
            pass
        return event

    def pop_pending(self, limit: int = 5) -> list:
        batch = self._pending[:limit]
        self._pending = self._pending[limit:]
        return batch

    def dashboard(self) -> dict:
        events = []
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                    events = json.load(f)
            except Exception:
                pass
        blocked = [
            {"ip": ip, **data}
            for ip, data in self._blocks.items()
            if self.is_blocked(ip)
        ]
        last = events[-50:]
        by_type: dict[str, int] = {}
        for e in last:
            t = e.get("threat_type", "other")
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "blocked_ips": blocked,
            "recent_events": list(reversed(last[-30:])),
            "pending_count": len(self._pending),
            "stats": {
                "total_events": len(events),
                "blocked_now": len(blocked),
                "by_type": by_type,
            },
        }


_monitor: Optional[SecurityMonitor] = None


def get_monitor() -> SecurityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SecurityMonitor()
    return _monitor
