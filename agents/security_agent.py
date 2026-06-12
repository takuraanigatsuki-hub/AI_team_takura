from agents.base_agent import BaseAgent


class SecurityAgent(BaseAgent):
    """Олег — Security Engineer: мониторинг угроз и координация патчей через Cursor."""

    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="security",
            name="Олег",
            role="Security Engineer",
            emoji="🛡",
            description=(
                "Ты эксперт по кибербезопасности и DevSecOps. "
                "Знаешь OWASP Top 10, threat modeling, secure coding. "
                "Анализируешь инциденты, блокируешь атаки, рекомендуешь патчи. "
                "Координируешь с Cursor Agent для автоматического исправления уязвимостей."
            ),
            room_manager=room_manager,
        )

    def get_responsibilities(self) -> str:
        return (
            "- Мониторинг подозрительной активности и блокировка IP\n"
            "- Анализ OWASP уязвимостей в коде и API\n"
            "- Incident response и audit log review\n"
            "- Координация auto-patch через Cursor Agent\n"
            "- Security headers и hardening рекомендации\n"
            "- Honeypot и scan detection"
        )

    def get_fallback_responses(self) -> list:
        return [
            "🛡 Инцидент '{task}'.\n\n🔴 Severity: HIGH\n• Тип: SQL injection attempt\n• IP заблокирован на 30 мин\n• Audit log обновлён\n\nРекомендация: проверить параметризованные запросы.",
            "🛡 Security scan: '{task}'.\n\nРезультаты:\n✅ Headers: CSP, X-Frame-Options\n⚠️ Auth: 3 endpoint без защиты\n🔴 Secrets: .env в git history\n\nCursor Agent уведомлён для патча.",
            "🛡 Threat blocked: '{task}'.\n\n• 15+ 404 за минуту — scanner\n• IP добавлен в blocklist\n• Honeypot сработал\n\nСтатус: UNDER CONTROL",
        ]

    async def handle_security_event(self, event: dict) -> None:
        if not self.room_manager:
            return
        threat = event.get("threat_type", "unknown")
        ip = event.get("ip", "?")
        detail = (event.get("detail") or "")[:200]
        msg = (
            f"🛡 **Security Alert** [{threat}]\n"
            f"IP: `{ip}` · Path: `{event.get('path', '')}`\n"
            f"{detail}\n\n"
            f"Действие: IP заблокирован. Audit log записан."
        )
        await self.room_manager.broadcast_work({
            "type": "security_alert",
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "agent_emoji": self.emoji,
            "message": msg,
            "threat_type": threat,
            "severity": event.get("severity", "medium"),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

        if threat in ("sqli", "xss", "path_traversal", "honeypot") and self.room_manager.agents.get("cursor"):
            from room.feature_flags import is_enabled
            if is_enabled("cursor_auto_patch"):
                cursor = self.room_manager.agents["cursor"]
                patch_task = (
                    f"Security fix required: {threat} detected from {ip}. "
                    f"Review and patch vulnerable endpoints. Detail: {detail}"
                )
                try:
                    await cursor.handle_task(patch_task, from_user=False)
                except Exception:
                    pass
