"""Крупные корпуса для масштабирования RAG (Фаза C)."""

from __future__ import annotations

# Официальная документация и reference — ingest через url_ingest
CORPORA_URLS: dict[str, list[dict]] = {
    "backend": [
        {"url": "https://fastapi.tiangolo.com/tutorial/security/", "title": "FastAPI Security"},
        {"url": "https://fastapi.tiangolo.com/advanced/async-tests/", "title": "FastAPI Async Tests"},
        {"url": "https://docs.python.org/3/library/asyncio.html", "title": "Python asyncio"},
        {"url": "https://www.postgresql.org/docs/current/tutorial.html", "title": "PostgreSQL Tutorial"},
        {"url": "https://redis.io/docs/latest/develop/get-started/", "title": "Redis Get Started"},
    ],
    "frontend": [
        {"url": "https://react.dev/learn/thinking-in-react", "title": "Thinking in React"},
        {"url": "https://react.dev/reference/react/useState", "title": "useState"},
        {"url": "https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_flexible_box_layout", "title": "CSS Flexbox"},
        {"url": "https://tailwindcss.com/docs", "title": "Tailwind CSS Docs"},
    ],
    "qa": [
        {"url": "https://playwright.dev/docs/intro", "title": "Playwright Intro"},
        {"url": "https://docs.pytest.org/en/stable/getting-started.html", "title": "pytest Getting Started"},
    ],
    "devops": [
        {"url": "https://docs.docker.com/get-started/", "title": "Docker Get Started"},
        {"url": "https://kubernetes.io/docs/concepts/overview/", "title": "Kubernetes Overview"},
        {"url": "https://docs.github.com/en/actions/learn-github-actions", "title": "GitHub Actions"},
    ],
    "security": [
        {"url": "https://owasp.org/www-project-web-security-testing-guide/", "title": "OWASP WSTG"},
        {"url": "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html", "title": "OWASP Auth Cheat Sheet"},
        {"url": "https://cwe.mitre.org/data/definitions/89.html", "title": "CWE-89 SQL Injection"},
    ],
    "architect": [
        {"url": "https://martinfowler.com/articles/microservices.html", "title": "Microservices Fowler"},
        {"url": "https://c4model.com/", "title": "C4 Model"},
    ],
    "doc_writer": [
        {"url": "https://www.writethedocs.org/guide/writing/docs-principles/", "title": "Write the Docs Principles"},
    ],
}

# Wikipedia topics (summary API) — лёгкий bulk без HTML парсинга
WIKIPEDIA_TOPICS: dict[str, list[str]] = {
    "pm": ["Agile software development", "Scrum (software development)", "Kanban"],
    "backend": ["Representational state transfer", "SQL", "NoSQL"],
    "frontend": ["React (JavaScript library)", "CSS", "Responsive web design"],
    "qa": ["Software testing", "Test-driven development"],
    "devops": ["DevOps", "Continuous integration"],
    "security": ["Computer security", "Penetration test"],
}
