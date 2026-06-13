"""Доступ к рабочей области — только нативный/desktop-клиент."""

DESKTOP_UA_MARKERS = (
    "AITeamRoomDesktop",
    "AITeamRoom-Desktop",
)


def is_desktop_client(request) -> bool:
    ua = (request.headers.get("user-agent") or "").lower()
    if any(m.lower() in ua for m in DESKTOP_UA_MARKERS):
        return True
    if "pywebview" in ua:
        return True
    q = getattr(request, "query_params", None)
    if q and q.get("client") == "desktop":
        return True
    return request.headers.get("x-ai-team-client") == "desktop"


def workspace_denied_redirect() -> str:
    return "/download?reason=desktop-only"
