import asyncio
import random
import re
from datetime import datetime
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from knowledge_store import KnowledgeStore
from direct_chat_store import DirectChatStore

LEARNING_TOPICS = {
    "architect": [
        "software architecture patterns 2024",
        "microservices best practices",
        "system design principles",
        "cloud architecture AWS Azure",
        "domain driven design DDD",
        "event driven architecture",
        "CQRS pattern",
        "hexagonal architecture",
        "scalable system design",
        "API gateway patterns"
    ],
    "backend": [
        "Python FastAPI best practices",
        "Go lang performance tips",
        "REST API design 2024",
        "database optimization PostgreSQL",
        "Redis caching strategies",
        "gRPC vs REST comparison",
        "Rust backend development",
        "async Python programming",
        "message queues Kafka RabbitMQ",
        "Python asyncio patterns"
    ],
    "frontend": [
        "React 19 new features",
        "Vue.js 3 composition API",
        "Web Components 2024",
        "CSS container queries",
        "JavaScript performance optimization",
        "TypeScript advanced types",
        "Next.js 15 features",
        "WebAssembly frontend",
        "Vite build optimization",
        "Tailwind CSS tips",
        "Figma auto layout best practices",
        "Figma design tokens and variables",
        "Figma component variants",
        "UI design systems 2025",
        "Figma to React workflow",
    ],
    "qa": [
        "test automation best practices",
        "pytest advanced techniques",
        "Playwright vs Selenium 2024",
        "load testing k6",
        "TDD methodology",
        "BDD with Cucumber",
        "API testing strategies",
        "chaos engineering",
        "contract testing Pact",
        "mutation testing"
    ],
    "reviewer": [
        "code review best practices",
        "static analysis tools 2024",
        "clean code principles",
        "SOLID principles examples",
        "refactoring techniques",
        "technical debt management",
        "code smell detection",
        "security code review",
        "design patterns implementation",
        "cyclomatic complexity reduction"
    ],
    "devops": [
        "Kubernetes 2024 best practices",
        "Docker optimization tips",
        "CI/CD GitHub Actions",
        "Terraform infrastructure as code",
        "monitoring Prometheus Grafana",
        "GitOps ArgoCD",
        "service mesh Istio",
        "cloud cost optimization",
        "eBPF observability",
        "platform engineering 2024"
    ],
    "doc_writer": [
        "technical writing best practices",
        "API documentation OpenAPI",
        "documentation as code",
        "Markdown advanced features",
        "architecture decision records ADR",
        "README best practices",
        "diagrams as code Mermaid",
        "developer experience DX",
        "docs site Docusaurus",
        "changelog automation"
    ],
    "pm": [
        "agile project management 2024",
        "sprint planning techniques",
        "OKR goal setting",
        "product roadmap planning",
        "team velocity metrics",
        "risk management software projects",
        "stakeholder communication",
        "Scrum vs Kanban",
        "product discovery techniques",
        "engineering metrics DORA"
    ],
    "cursor": [
        "Cursor IDE AI coding 2025",
        "programmatic coding agents SDK",
        "AI code review automation",
        "MCP model context protocol tools",
        "agentic coding workflows",
        "composer model best practices",
        "cloud agents CI integration",
        "AI pair programming patterns",
        "semantic codebase search",
        "automated refactoring with AI"
    ]
}

SOURCE_LABELS = {
    "web_search": "🌐 Веб",
    "devto": "Dev.to",
    "hackernews": "Hacker News",
    "github": "GitHub",
    "habr": "Хабр",
    "stackoverflow": "Stack Overflow",
    "books": "📖 Книги",
    "wikipedia": "Wikipedia",
    "arxiv": "arXiv",
    "gutenberg": "Project Gutenberg",
    "internal": "Внутренняя база",
    "figma": "🎨 Figma",
    "figma_web": "🎨 Figma",
    "figma_portfolio": "✨ Portfolio",
}

LOCATION_LABELS = {
    "studio": "Студия",
    "rest_room": "Комната отдыха",
    "library": "Библиотека",
}

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


class BaseAgent:
    def __init__(self, agent_id: str, name: str, role: str, emoji: str, description: str, room_manager=None):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.emoji = emoji
        self.description = description
        self.room_manager = room_manager

        self.status = "idle"
        self.current_task = None
        self.task_queue = asyncio.Queue()
        self.learned_topics = KnowledgeStore.load(agent_id)
        self.direct_chat = DirectChatStore.load(agent_id)
        self.memory = []
        self.messages_log = []

        self.location = "studio"
        self.mood = "focused"
        self._running = False
        self._loop_task = None

    def get_system_prompt(self) -> str:
        return f"""Ты {self.name} — {self.role} в команде разработчиков.
{self.description}

Твои обязанности:
{self.get_responsibilities()}

Отвечай коротко и по делу. Если получаешь задачу — описывай что делаешь.
Если изучаешь что-то — делись интересными находками.
Пиши на русском языке."""

    def get_responsibilities(self) -> str:
        return "- Выполнение задач по своей специализации"

    async def start(self):
        self._running = True
        self._loop_task = asyncio.create_task(self._main_loop())

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()

    def _learning_delay(self) -> float:
        try:
            from config import config
            lo = config.get("learning_interval_min", 5)
            hi = config.get("learning_interval_max", 15)
            return random.uniform(lo, hi)
        except Exception:
            return random.uniform(5, 15)

    async def _interruptible_sleep(self, seconds: float):
        """Сон с проверкой очереди задач — прерывается если пришла задача."""
        elapsed = 0.0
        while elapsed < seconds:
            if not self.task_queue.empty():
                return
            step = min(0.4, seconds - elapsed)
            await asyncio.sleep(step)
            elapsed += step

    async def _main_loop(self):
        while self._running:
            try:
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                    await self._process_task(task)
                    continue
                except asyncio.TimeoutError:
                    pass

                if not self.task_queue.empty():
                    continue

                await self._idle_behavior()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._broadcast(f"⚠️ Ошибка: {str(e)}", "error")
                await asyncio.sleep(3)

    def _work_mode_active(self) -> bool:
        if not self.task_queue.empty():
            return True
        if self.room_manager and self.room_manager.has_pending_work():
            return True
        return False

    async def _idle_behavior(self):
        if self._work_mode_active():
            return
        action = random.choices(
            ["learn", "reflect", "rest"],
            weights=[0.50, 0.15, 0.10]
        )[0]
        if action == "learn":
            await self._learn()
        elif action == "reflect":
            await self._reflect()
        else:
            await self._rest_in_lounge()

    async def _rest_in_lounge(self):
        if not self.task_queue.empty():
            return
        self.status = "resting"
        self.location = "rest_room"
        await self._broadcast("☕ Отдыхаю в комнате отдыха...", "rest")
        await self._interruptible_sleep(random.uniform(4, 8))
        self.location = "studio"
        self.status = "idle"

    async def _learn(self):
        if not self.task_queue.empty():
            return
        self.status = "learning"
        self.location = "library"
        topics = LEARNING_TOPICS.get(self.agent_id, ["programming best practices"])
        topic = random.choice(topics)

        await self._broadcast(f"📚 Изучаю: *{topic}*...", "learning")

        material = await self._fetch_learning_material(topic)

        if material:
            entry = {
                "topic": topic,
                "title": material.get("title", topic),
                "summary": material.get("summary", ""),
                "url": material.get("url", ""),
                "source": material.get("source", "web"),
                "keywords": self._extract_keywords(
                    f"{topic} {material.get('title', '')} {material.get('summary', '')}"
                ),
                "timestamp": datetime.now().isoformat()
            }
            self.learned_topics.append(entry)
            if len(self.learned_topics) > 200:
                self.learned_topics = self.learned_topics[-200:]
            self._persist_knowledge()

            title = material.get("title", topic)
            summary = material.get("summary", "")[:200]
            source_label = SOURCE_LABELS.get(material.get("source", ""), "🌐 Веб")
            url_part = f"\n🔗 {material['url']}" if material.get("url") else ""
            await self._broadcast(
                f"💡 [{source_label}] *{title}*\n{summary}{url_part}",
                "learning_result"
            )
        else:
            entry = {
                "topic": topic,
                "title": topic,
                "summary": f"Основные принципы по теме «{topic}» для роли {self.role}.",
                "url": "",
                "source": "internal",
                "keywords": self._extract_keywords(topic),
                "timestamp": datetime.now().isoformat()
            }
            self.learned_topics.append(entry)
            self._persist_knowledge()
            await self._broadcast(f"✅ Повторил знания: *{topic}*", "learning_result")

        self.location = "studio"
        self.status = "idle"
        await self._interruptible_sleep(self._learning_delay())

    # ══════════════════════════════════════════════════════════════
    #  ИСТОЧНИКИ ОБУЧЕНИЯ
    # ══════════════════════════════════════════════════════════════

    async def _fetch_learning_material(self, topic: str) -> Optional[dict]:
        try:
            from config import config
            sources = config.get(
                "learning_sources",
                ["web_search", "wikipedia", "devto", "github", "habr", "stackoverflow",
                 "hackernews", "books", "arxiv", "gutenberg"]
            )
        except Exception:
            sources = ["web_search", "wikipedia", "devto", "github", "habr", "stackoverflow",
                         "hackernews", "books", "arxiv", "gutenberg"]

        fetcher_map = {
            "web_search": self._fetch_from_web_search,
            "wikipedia": self._fetch_from_wikipedia,
            "devto": self._fetch_from_devto,
            "hackernews": self._fetch_from_hackernews,
            "github": self._fetch_from_github,
            "habr": self._fetch_from_habr,
            "stackoverflow": self._fetch_from_stackoverflow,
            "books": self._fetch_from_books,
            "arxiv": self._fetch_from_arxiv,
            "gutenberg": self._fetch_from_gutenberg,
        }

        fetchers = [fetcher_map[s] for s in sources if s in fetcher_map]
        random.shuffle(fetchers)
        for fetcher in fetchers:
            try:
                material = await fetcher(topic)
                if material:
                    return material
            except Exception:
                continue
        return None

    # ── 1. СВОБОДНЫЙ ВЕБ-ПОИСК (DuckDuckGo) ─────────────────────

    async def _fetch_from_web_search(self, topic: str) -> Optional[dict]:
        """Поиск по всему интернету через DuckDuckGo — без API ключа"""
        try:
            query = topic.replace(" ", "+")
            search_url = f"https://lite.duckduckgo.com/lite/?q={query}"

            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(search_url, headers=BROWSER_HEADERS)
                if resp.status_code != 200:
                    return await self._fetch_from_ddg_html(topic)

                soup = BeautifulSoup(resp.text, "html.parser")
                results = []

                # Парсим DuckDuckGo Lite результаты
                for a in soup.find_all("a", class_="result-link"):
                    href = a.get("href", "")
                    text = a.get_text(strip=True)
                    if href and text and href.startswith("http"):
                        results.append({"url": href, "title": text})

                # Альтернативный парсинг
                if not results:
                    for tr in soup.find_all("tr"):
                        a = tr.find("a")
                        if a and a.get("href", "").startswith("http"):
                            snippet_td = tr.find_next_sibling("tr")
                            snippet = snippet_td.get_text(strip=True)[:150] if snippet_td else ""
                            results.append({"url": a["href"], "title": a.get_text(strip=True), "snippet": snippet})

                if not results:
                    return await self._fetch_from_ddg_html(topic)

                # Берём случайный результат из топ-5
                pick = random.choice(results[:5])
                url = pick.get("url", "")
                title = pick.get("title", topic)
                snippet = pick.get("snippet", "")

                # Пробуем получить содержимое страницы
                if url and not snippet:
                    snippet = await self._extract_page_content(url, client)

                return {
                    "title": title,
                    "summary": snippet[:250] if snippet else f"Материал по теме «{topic}»",
                    "url": url,
                    "source": "web_search"
                }
        except Exception:
            return await self._fetch_from_ddg_html(topic)

    async def _fetch_from_ddg_html(self, topic: str) -> Optional[dict]:
        """Fallback: DuckDuckGo через HTML endpoint"""
        try:
            query = topic.replace(" ", "+")
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    f"https://html.duckduckgo.com/html/?q={query}",
                    headers=BROWSER_HEADERS
                )
                if resp.status_code != 200:
                    return None

                soup = BeautifulSoup(resp.text, "html.parser")
                results = []

                for div in soup.find_all("div", class_="result"):
                    a = div.find("a", class_="result__a")
                    snippet_el = div.find("a", class_="result__snippet")
                    if not snippet_el:
                        snippet_el = div.find("div", class_="result__snippet")
                    if a and a.get("href"):
                        href = a["href"]
                        # DuckDuckGo использует redirect URLs
                        if "uddg=" in href:
                            import urllib.parse
                            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            real_url = qs.get("uddg", [href])[0]
                        else:
                            real_url = href if href.startswith("http") else ""

                        if real_url:
                            results.append({
                                "url": real_url,
                                "title": a.get_text(strip=True),
                                "snippet": snippet_el.get_text(strip=True) if snippet_el else ""
                            })

                if not results:
                    return None

                pick = random.choice(results[:5])
                url = pick["url"]
                title = pick["title"]
                snippet = pick.get("snippet", "")

                # Читаем содержимое страницы если нет сниппета
                if url and len(snippet) < 50:
                    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as c2:
                        snippet = await self._extract_page_content(url, c2) or snippet

                return {
                    "title": title,
                    "summary": snippet[:300] if snippet else f"Статья по теме «{topic}»",
                    "url": url,
                    "source": "web_search"
                }
        except Exception:
            return None

    async def _extract_page_content(self, url: str, client: httpx.AsyncClient) -> str:
        """Извлечь текстовое содержимое любой веб-страницы"""
        try:
            # Пропускаем нетекстовые ресурсы
            skip_exts = (".pdf", ".zip", ".exe", ".png", ".jpg", ".mp4", ".mp3")
            if any(url.lower().endswith(e) for e in skip_exts):
                return ""

            resp = await client.get(url, headers=BROWSER_HEADERS, timeout=6.0)
            if resp.status_code != 200:
                return ""

            content_type = resp.headers.get("content-type", "")
            if "html" not in content_type:
                return ""

            soup = BeautifulSoup(resp.text, "html.parser")

            # Удаляем шум
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
                tag.decompose()

            # Ищем основной контент
            main = (
                soup.find("article") or
                soup.find("main") or
                soup.find(class_=re.compile(r"content|post|article|body", re.I)) or
                soup.find("body")
            )

            if not main:
                return ""

            text = " ".join(main.get_text(separator=" ").split())
            return text[:400]
        except Exception:
            return ""

    # ── 2. DEV.TO ─────────────────────────────────────────────────

    async def _fetch_from_devto(self, topic: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                tag = re.sub(r"[^a-z0-9]", "", topic.split()[0].lower())
                resp = await client.get(
                    f"https://dev.to/api/articles?tag={tag}&per_page=5&top=30",
                    headers={"User-Agent": "AI-Team-Room/1.0"}
                )
                articles = resp.json() if resp.status_code == 200 else []
                if not articles:
                    resp2 = await client.get(
                        "https://dev.to/api/articles?per_page=10&top=7",
                        headers={"User-Agent": "AI-Team-Room/1.0"}
                    )
                    if resp2.status_code == 200:
                        articles = [a for a in resp2.json()
                                    if any(w in a.get("title", "").lower() for w in topic.lower().split()[:3])]
                if not articles:
                    return None
                art = random.choice(articles[:5])
                title = art.get("title", "")
                if not title:
                    return None
                return {
                    "title": title,
                    "summary": (art.get("description", "") or "")[:300] or f"Статья о {topic}",
                    "url": art.get("url", ""),
                    "source": "devto"
                }
        except Exception:
            return None

    # ── 3. HACKER NEWS ────────────────────────────────────────────

    async def _fetch_from_hackernews(self, topic: str) -> Optional[dict]:
        try:
            topic_words = [w.lower() for w in re.findall(r"\w+", topic) if len(w) > 3]
            if not topic_words:
                return None
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    "https://hacker-news.firebaseio.com/v0/topstories.json",
                    headers={"User-Agent": "AI-Team-Room/1.0"}
                )
                if resp.status_code != 200:
                    return None
                ids = resp.json()[:40]
                random.shuffle(ids)
                for story_id in ids[:15]:
                    item_resp = await client.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                        headers={"User-Agent": "AI-Team-Room/1.0"}
                    )
                    if item_resp.status_code != 200:
                        continue
                    item = item_resp.json()
                    title = item.get("title", "")
                    if not any(w in title.lower() for w in topic_words):
                        continue
                    url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                    return {
                        "title": title,
                        "summary": f"HN: {item.get('score', 0)} points, {item.get('descendants', 0)} комментариев",
                        "url": url,
                        "source": "hackernews"
                    }
        except Exception:
            return None
        return None

    # ── 4. GITHUB ─────────────────────────────────────────────────

    async def _fetch_from_github(self, topic: str) -> Optional[dict]:
        try:
            query = "+".join(topic.split()[:3])
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=10",
                    headers={"User-Agent": "AI-Team-Room/1.0", "Accept": "application/vnd.github.v3+json"}
                )
                if resp.status_code != 200:
                    return None
                items = resp.json().get("items", [])
                if not items:
                    return None
                repo = random.choice(items[:5])
                name = repo.get("full_name", "")
                desc = repo.get("description", "") or ""
                stars = repo.get("stargazers_count", 0)
                lang = repo.get("language", "") or ""
                url = repo.get("html_url", "")
                if not name:
                    return None
                return {
                    "title": f"{name} ⭐{stars:,}",
                    "summary": f"{desc[:200]}{' | ' + lang if lang else ''}",
                    "url": url,
                    "source": "github"
                }
        except Exception:
            return None

    # ── 5. ХАБР ──────────────────────────────────────────────────

    async def _fetch_from_habr(self, topic: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://habr.com/ru/rss/best/daily/?fl=ru",
                    headers=BROWSER_HEADERS
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "xml")
                    items = soup.find_all("item")
                    if items:
                        topic_words = [w.lower() for w in topic.split() if len(w) > 3]
                        matched = [
                            it for it in items
                            if any(w in (it.find("title").get_text().lower() if it.find("title") else "") for w in topic_words)
                        ]
                        chosen = random.choice(matched) if matched else random.choice(items[:10])
                        t_el = chosen.find("title")
                        l_el = chosen.find("link")
                        d_el = chosen.find("description")
                        title = t_el.get_text(strip=True) if t_el else ""
                        link = str(l_el.next_sibling).strip() if l_el and l_el.next_sibling else "https://habr.com"
                        desc = BeautifulSoup(d_el.get_text(), "html.parser").get_text()[:200] if d_el else ""
                        if title:
                            return {"title": title, "summary": desc or f"Хабр: «{topic}»", "url": link, "source": "habr"}
                return {
                    "title": f"Хабр: {topic}",
                    "summary": "IT-статьи на русском языке",
                    "url": f"https://habr.com/ru/search/?q={'+'.join(topic.split()[:2])}",
                    "source": "habr"
                }
        except Exception:
            return None

    # ── 6. STACK OVERFLOW ─────────────────────────────────────────

    async def _fetch_from_stackoverflow(self, topic: str) -> Optional[dict]:
        try:
            tag = re.sub(r"[^a-z0-9\-]", "", topic.split()[0].lower())
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"https://api.stackexchange.com/2.3/questions"
                    f"?order=desc&sort=votes&tagged={tag}&site=stackoverflow&pagesize=10",
                    headers={"User-Agent": "AI-Team-Room/1.0"}
                )
                items = resp.json().get("items", []) if resp.status_code == 200 else []
                if not items:
                    query = "+".join(topic.split()[:3])
                    resp2 = await client.get(
                        f"https://api.stackexchange.com/2.3/search/advanced"
                        f"?order=desc&sort=votes&q={query}&site=stackoverflow&pagesize=10",
                        headers={"User-Agent": "AI-Team-Room/1.0"}
                    )
                    items = resp2.json().get("items", []) if resp2.status_code == 200 else []
                if not items:
                    return None
                q = random.choice(items[:5])
                answered = "✅" if q.get("is_answered") else "❓"
                return {
                    "title": f"{answered} {q.get('title', '')}",
                    "summary": f"Score: {q.get('score', 0)} | Ответов: {q.get('answer_count', 0)} | {', '.join(q.get('tags', [])[:4])}",
                    "url": q.get("link", ""),
                    "source": "stackoverflow"
                }
        except Exception:
            return None

    # ── 6b. WIKIPEDIA ─────────────────────────────────────────────

    async def _fetch_from_wikipedia(self, topic: str) -> Optional[dict]:
        try:
            from urllib.parse import quote
            async with httpx.AsyncClient(timeout=8.0) as client:
                search = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query", "list": "search", "srsearch": topic,
                        "format": "json", "srlimit": 5
                    },
                    headers={"User-Agent": "AI-Team-Room/1.0"}
                )
                if search.status_code != 200:
                    return None
                hits = search.json().get("query", {}).get("search", [])
                if not hits:
                    return None
                title = random.choice(hits[:3]).get("title", topic)
                resp = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
                    headers={"User-Agent": "AI-Team-Room/1.0"}
                )
                if resp.status_code != 200:
                    return None

                data = resp.json()
                extract = data.get("extract", "")[:350]
                url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                if not extract:
                    return None
                return {
                    "title": data.get("title", title),
                    "summary": extract,
                    "url": url or f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
                    "source": "wikipedia"
                }
        except Exception:
            return None

    # ── 6c. arXiv ─────────────────────────────────────────────────

    async def _fetch_from_arxiv(self, topic: str) -> Optional[dict]:
        try:
            query = "+".join(topic.split()[:4])
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://export.arxiv.org/api/query",
                    params={"search_query": f"all:{query}", "max_results": 8, "sortBy": "relevance"},
                    headers={"User-Agent": "AI-Team-Room/1.0"}
                )
                if resp.status_code != 200:
                    return None
                soup = BeautifulSoup(resp.text, "xml")
                entries = soup.find_all("entry")
                if not entries:
                    return None
                entry = random.choice(entries[:5])
                title_el = entry.find("title")
                summary_el = entry.find("summary")
                id_el = entry.find("id")
                title = title_el.get_text(strip=True).replace("\n", " ") if title_el else topic
                summary = summary_el.get_text(strip=True)[:300] if summary_el else ""
                url = id_el.get_text(strip=True) if id_el else "https://arxiv.org"
                return {
                    "title": title[:120],
                    "summary": summary or "Научная статья с arXiv",
                    "url": url,
                    "source": "arxiv"
                }
        except Exception:
            return None

    # ── 6d. PROJECT GUTENBERG ──────────────────────────────────────

    async def _fetch_from_gutenberg(self, topic: str) -> Optional[dict]:
        try:
            query = "+".join(topic.split()[:3])
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://gutendex.com/books/?search={query}",
                    headers={"User-Agent": "AI-Team-Room/1.0"}
                )
                if resp.status_code != 200:
                    return None
                results = resp.json().get("results", [])
                if not results:
                    return None
                book = random.choice(results[:5])
                title = book.get("title", "")
                authors = ", ".join(a.get("name", "") for a in book.get("authors", [])[:2])
                subjects = ", ".join(book.get("subjects", [])[:2])
                gid = book.get("id", "")
                if not title:
                    return None
                return {
                    "title": title,
                    "summary": f"Автор: {authors} | {subjects}" if authors else subjects[:200],
                    "url": f"https://www.gutenberg.org/ebooks/{gid}" if gid else "https://www.gutenberg.org",
                    "source": "gutenberg"
                }
        except Exception:
            return None

    # ── 7. КНИГИ (Open Library + кураторский список) ─────────────

    async def _fetch_from_books(self, topic: str) -> Optional[dict]:
        try:
            query = "+".join(topic.split()[:3])
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"https://openlibrary.org/search.json?q={query}&limit=10",
                    headers={"User-Agent": "AI-Team-Room/1.0"}
                )
                if resp.status_code == 200:
                    rated = [d for d in resp.json().get("docs", [])[:15]
                             if d.get("ratings_average", 0) >= 3.5 and d.get("title")]
                    if rated:
                        book = random.choice(rated[:5])
                        title = book.get("title", "")
                        author = ", ".join(book.get("author_name", [])[:2])
                        year = book.get("first_publish_year", "")
                        rating = book.get("ratings_average", 0)
                        key = book.get("key", "")
                        url = f"https://openlibrary.org{key}" if key else "https://openlibrary.org"
                        rating_str = f" ⭐{rating:.1f}" if rating else ""
                        return {
                            "title": f"{title}{rating_str}",
                            "summary": f"Автор: {author} | Год: {year}",
                            "url": url,
                            "source": "books"
                        }
        except Exception:
            pass
        return self._get_curated_book()

    def _get_curated_book(self) -> dict:
        CURATED = {
            "architect": [
                ("Clean Architecture", "Robert C. Martin", "https://openlibrary.org/works/OL18667915W"),
                ("Designing Data-Intensive Applications", "Martin Kleppmann", "https://dataintensive.net"),
                ("Building Microservices", "Sam Newman", "https://openlibrary.org"),
                ("Domain-Driven Design", "Eric Evans", "https://openlibrary.org/works/OL8449922W"),
                ("A Philosophy of Software Design", "John Ousterhout", "https://openlibrary.org"),
            ],
            "backend": [
                ("Fluent Python", "Luciano Ramalho", "https://openlibrary.org"),
                ("High Performance Python", "Micha Gorelick", "https://openlibrary.org"),
                ("Database Internals", "Alex Petrov", "https://openlibrary.org"),
                ("Python Cookbook", "David Beazley", "https://openlibrary.org"),
                ("Designing Web APIs", "Brenda Jin", "https://openlibrary.org"),
            ],
            "frontend": [
                ("JavaScript: The Good Parts", "Douglas Crockford", "https://openlibrary.org/works/OL8449924W"),
                ("You Don't Know JS", "Kyle Simpson", "https://github.com/getify/You-Dont-Know-JS"),
                ("CSS: The Definitive Guide", "Eric Meyer", "https://openlibrary.org"),
                ("Learning React", "Alex Banks & Eve Porcello", "https://openlibrary.org"),
                ("TypeScript Deep Dive", "Basarat Ali Syed", "https://basarat.gitbook.io/typescript"),
            ],
            "qa": [
                ("The Art of Software Testing", "Glenford Myers", "https://openlibrary.org"),
                ("Test-Driven Development", "Kent Beck", "https://openlibrary.org/works/OL8449923W"),
                ("Agile Testing", "Lisa Crispin", "https://openlibrary.org"),
                ("How Google Tests Software", "James Whittaker", "https://openlibrary.org"),
                ("Growing Object-Oriented Software, Guided by Tests", "Freeman & Pryce", "https://openlibrary.org"),
            ],
            "reviewer": [
                ("Clean Code", "Robert C. Martin", "https://openlibrary.org/works/OL8449921W"),
                ("Refactoring", "Martin Fowler", "https://openlibrary.org/works/OL8449926W"),
                ("Code Complete", "Steve McConnell", "https://openlibrary.org/works/OL8449927W"),
                ("The Pragmatic Programmer", "Andrew Hunt & Dave Thomas", "https://openlibrary.org"),
                ("Working Effectively with Legacy Code", "Michael Feathers", "https://openlibrary.org"),
            ],
            "devops": [
                ("The Phoenix Project", "Gene Kim", "https://openlibrary.org/works/OL16807358W"),
                ("Site Reliability Engineering", "Google SRE Team", "https://sre.google/sre-book/table-of-contents"),
                ("Kubernetes in Action", "Marko Luksa", "https://openlibrary.org"),
                ("Infrastructure as Code", "Kief Morris", "https://openlibrary.org"),
                ("The DevOps Handbook", "Gene Kim & Jez Humble", "https://openlibrary.org"),
            ],
            "doc_writer": [
                ("Docs for Developers", "Jared Bhatti", "https://openlibrary.org"),
                ("The Elements of Style", "Strunk & White", "https://openlibrary.org/works/OL464018W"),
                ("Every Page is Page One", "Mark Baker", "https://openlibrary.org"),
                ("Technical Writing 101", "Alan Pringle", "https://openlibrary.org"),
                ("Developing Quality Technical Information", "IBM Press", "https://openlibrary.org"),
            ],
            "pm": [
                ("The Mythical Man-Month", "Frederick Brooks", "https://openlibrary.org/works/OL5726436W"),
                ("Scrum: The Art of Doing Twice the Work", "Jeff Sutherland", "https://openlibrary.org"),
                ("Inspired", "Marty Cagan", "https://openlibrary.org"),
                ("Shape Up", "Ryan Singer", "https://basecamp.com/shapeup"),
                ("Accelerate", "Nicole Forsgren", "https://openlibrary.org"),
            ],
        }
        books = CURATED.get(self.agent_id, CURATED["reviewer"])
        title, author, url = random.choice(books)
        return {
            "title": title,
            "summary": f"Автор: {author} | Рекомендованная книга для {self.role}",
            "url": url,
            "source": "books"
        }

    # ══════════════════════════════════════════════════════════════
    #  ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ══════════════════════════════════════════════════════════════

    def _extract_keywords(self, text: str) -> list:
        words = re.findall(r"[a-zA-Zа-яА-Я0-9]{3,}", text.lower())
        stop = {"the", "and", "for", "with", "from", "this", "that", "как", "для", "при", "или"}
        return list(dict.fromkeys(w for w in words if w not in stop))[:20]

    def _persist_knowledge(self):
        try:
            from config import config
            if config.get("persist_knowledge", True):
                KnowledgeStore.save(self.agent_id, self.learned_topics)
        except Exception:
            KnowledgeStore.save(self.agent_id, self.learned_topics)

    async def _reflect(self):
        if not self.learned_topics:
            await self._broadcast("🤔 Пока мало знаний — скоро пойду учиться.", "reflection")
            return
        recent = random.choice(self.learned_topics[-5:])
        source = SOURCE_LABELS.get(recent.get("source", ""), "")
        src = f" [{source}]" if source else ""
        await self._broadcast(
            f"🤔 Размышляю над «{recent.get('title', recent['topic'])}»{src}. Применю в следующей задаче.",
            "reflection"
        )

    async def handle_direct_chat(self, text: str):
        """Личный диалог с пользователем — не попадает в общий чат."""
        self.direct_chat.append({
            "role": "user",
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        self.status = "working"
        self.location = "studio"

        if self.room_manager:
            await self.room_manager.broadcast({
                "type": "direct_user_echo",
                "agent_id": self.agent_id,
                "message": text,
                "timestamp": datetime.now().isoformat()
            })

        response = self.build_task_response(text, self._find_relevant_knowledge(text))
        self.direct_chat.append({
            "role": "agent",
            "text": response,
            "timestamp": datetime.now().isoformat()
        })
        DirectChatStore.save(self.agent_id, self.direct_chat)

        if self.room_manager:
            await self.room_manager.broadcast({
                "type": "direct_agent_message",
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "message": response,
                "status": self.status,
                "location": self.location,
                "timestamp": datetime.now().isoformat()
            })

        self.status = "idle"

    async def _process_task(self, task: dict):
        self.status = "working"
        self.location = "studio"
        self.current_task = task
        task_text = task.get("text", "")
        sender = task.get("sender", "Пользователь")
        task_id = task.get("task_id")

        if self.room_manager and task_id:
            self.room_manager.record_task_started(task_id)

        await self._broadcast_work(
            f"📋 Задача от {sender}: *{task_text}*\nПриступаю...",
            "task_received"
        )

        response = ""
        try:
            response = self.build_task_response(task_text, self._find_relevant_knowledge(task_text))
            await self._broadcast_work(f"✅ Выполнено:\n{response}", "task_done")
            if self.room_manager and task_id:
                self.room_manager.record_task_completed(
                    task_id, response, self.name, self.emoji
                )
        except Exception as e:
            err = str(e)
            await self._broadcast_work(f"❌ Ошибка: {err}", "error")
            if self.room_manager and task_id:
                self.room_manager.record_task_failed(task_id, err)
        finally:
            if self.room_manager:
                await self.room_manager._broadcast_task_history()
            self.memory.append({
                "task": task_text, "response": response,
                "timestamp": datetime.now().isoformat()
            })
            self.status = "idle"
            self.current_task = None

    def _find_relevant_knowledge(self, task_text: str, limit: int = 3) -> list:
        task_words = set(self._extract_keywords(task_text))
        if not task_words or not self.learned_topics:
            return []
        scored = []
        for item in self.learned_topics:
            item_words = set(item.get("keywords", []))
            item_words.update(self._extract_keywords(
                f"{item.get('topic', '')} {item.get('title', '')} {item.get('summary', '')}"
            ))
            overlap = len(task_words & item_words)
            if overlap > 0:
                scored.append((overlap, item))
        scored.sort(key=lambda x: (-x[0], x[1].get("timestamp", "")))
        return [item for _, item in scored[:limit]]

    def build_task_response(self, task_text: str, relevant_knowledge: list) -> str:
        base = random.choice(self.get_fallback_responses()).format(task=task_text)
        if relevant_knowledge:
            lines = []
            for item in relevant_knowledge[:2]:
                title = item.get("title", item.get("topic", ""))
                summary = item.get("summary", "")[:150]
                source = SOURCE_LABELS.get(item.get("source", ""), item.get("source", ""))
                lines.append(f"• *{title}* [{source}]: {summary}")
            base += "\n\n📚 Применяю изученное:\n" + "\n".join(lines)
        if len(self.learned_topics) >= 5:
            sources_used = list(dict.fromkeys(
                SOURCE_LABELS.get(t.get("source", ""), t.get("source", ""))
                for t in self.learned_topics[-20:]
                if t.get("source") and t.get("source") != "internal"
            ))
            base += f"\n\n🧠 База знаний: {len(self.learned_topics)} тем"
            if sources_used:
                base += f" | Источники: {', '.join(sources_used[:4])}"
        return base

    def get_fallback_responses(self) -> list:
        return [
            "Задача '{task}' принята. Анализирую требования и готовлю решение.",
            "Работаю над: '{task}'. Ожидайте результат.",
            "Задача '{task}' — понял, начинаю реализацию."
        ]

    async def assign_task(self, task_text: str, sender: str = "Пользователь",
                          parent_id: str = None, task_id: str = None):
        await self.task_queue.put({
            "text": task_text,
            "sender": sender,
            "parent_id": parent_id,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        })
        if self.room_manager:
            await self.room_manager._broadcast_task_history()

    async def _broadcast(self, message: str, msg_type: str = "message"):
        if msg_type in ("learning", "learning_result", "reflection", "rest"):
            await self._broadcast_learning(message, msg_type)
        else:
            await self._broadcast_work(message, msg_type)

    async def _broadcast_work(self, message: str, msg_type: str = "message"):
        if self.room_manager:
            await self.room_manager.broadcast_work({
                "type": msg_type,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "message": message,
                "status": self.status,
                "location": self.location,
                "timestamp": datetime.now().isoformat()
            })
        self._log_message(msg_type, message)

    async def _broadcast_learning(self, message: str, msg_type: str = "learning"):
        if self.room_manager:
            await self.room_manager.broadcast_learning({
                "type": msg_type,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "message": message,
                "status": self.status,
                "location": self.location,
                "timestamp": datetime.now().isoformat()
            })
        self._log_message(msg_type, message)

    def _log_message(self, msg_type: str, message: str):
        self.messages_log.append({
            "type": msg_type, "message": message,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.messages_log) > 100:
            self.messages_log = self.messages_log[-100:]

    def get_state(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "emoji": self.emoji,
            "description": self.description,
            "status": self.status,
            "location": self.location,
            "location_label": LOCATION_LABELS.get(self.location, self.location),
            "mood": self.mood,
            "current_task": self.current_task,
            "direct_chat_count": len(self.direct_chat),
            "learned_count": len(self.learned_topics),
            "memory_count": len(self.memory),
            "last_topics": [t.get("topic", t.get("title", "")) for t in self.learned_topics[-3:]] if self.learned_topics else [],
            "knowledge_sources": list(dict.fromkeys(
                t.get("source", "") for t in self.learned_topics[-10:] if t.get("source")
            ))
        }
