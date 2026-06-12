"""Стартовые знания для каждого агента."""

from datetime import datetime

NOW = datetime.now().isoformat()

SEED_KNOWLEDGE = {
    "pm": [
        {"topic": "Agile", "title": "Scrum Guide 2020", "summary": "Спринты 2 нед, daily standup, retro, increment.", "source": "internal", "keywords": ["scrum", "agile", "sprint"]},
        {"topic": "OKR", "title": "Objectives & Key Results", "summary": "Цели + измеримые KR, квартальный цикл.", "source": "internal", "keywords": ["okr", "metrics"]},
        {"topic": "DORA", "title": "DORA Metrics", "summary": "Deployment frequency, lead time, MTTR, change fail rate.", "source": "internal", "keywords": ["dora", "devops"]},
        {"topic": "Planning", "title": "User Story Mapping", "summary": "Backbone, walking skeleton, релизные слайсы.", "source": "internal", "keywords": ["story", "backlog"]},
    ],
    "architect": [
        {"topic": "Patterns", "title": "Clean Architecture", "summary": "Entities, use cases, adapters, frameworks.", "source": "internal", "keywords": ["clean", "layers"]},
        {"topic": "Microservices", "title": "12-Factor App", "summary": "Config in env, stateless, logs as streams.", "source": "internal", "keywords": ["12factor", "cloud"]},
        {"topic": "API", "title": "REST API Design", "summary": "Resources, HTTP verbs, pagination, versioning.", "source": "internal", "keywords": ["rest", "api"]},
        {"topic": "DDD", "title": "Domain-Driven Design", "summary": "Bounded contexts, aggregates, ubiquitous language.", "source": "internal", "keywords": ["ddd", "domain"]},
    ],
    "backend": [
        {"topic": "FastAPI", "title": "FastAPI Best Practices", "summary": "Depends, Pydantic v2, async routes, lifespan.", "source": "internal", "keywords": ["fastapi", "python"]},
        {"topic": "PostgreSQL", "title": "PostgreSQL Indexing", "summary": "B-tree, partial indexes, EXPLAIN ANALYZE.", "source": "internal", "keywords": ["postgres", "sql"]},
        {"topic": "Redis", "title": "Redis Caching Patterns", "summary": "Cache-aside, TTL, invalidation strategies.", "source": "internal", "keywords": ["redis", "cache"]},
        {"topic": "Async", "title": "Python asyncio", "summary": "Event loop, gather, semaphores, backpressure.", "source": "internal", "keywords": ["async", "asyncio"]},
    ],
    "frontend": [
        {"topic": "React", "title": "React 19 Patterns", "summary": "Server components, hooks, suspense boundaries.", "source": "internal", "keywords": ["react", "hooks"]},
        {"topic": "CSS", "title": "Modern CSS Layout", "summary": "Grid, flex, container queries, clamp().", "source": "internal", "keywords": ["css", "layout"]},
        {"topic": "Figma", "title": "Figma to React", "summary": "Auto layout, tokens, component variants.", "source": "figma", "keywords": ["figma", "design"]},
        {"topic": "a11y", "title": "Web Accessibility", "summary": "ARIA, focus, contrast WCAG 2.2.", "source": "internal", "keywords": ["a11y", "wcag"]},
    ],
    "qa": [
        {"topic": "pytest", "title": "pytest Fixtures", "summary": "conftest, parametrize, markers, async tests.", "source": "internal", "keywords": ["pytest", "test"]},
        {"topic": "E2E", "title": "Playwright E2E", "summary": "Page objects, trace, CI parallelization.", "source": "internal", "keywords": ["playwright", "e2e"]},
        {"topic": "Load", "title": "k6 Load Testing", "summary": "VUs, thresholds, smoke/load/stress.", "source": "internal", "keywords": ["k6", "load"]},
    ],
    "reviewer": [
        {"topic": "SOLID", "title": "SOLID Principles", "summary": "SRP, OCP, LSP, ISP, DIP with examples.", "source": "internal", "keywords": ["solid", "oop"]},
        {"topic": "Clean Code", "title": "Clean Code Checklist", "summary": "Naming, functions <20 lines, no magic numbers.", "source": "internal", "keywords": ["clean", "review"]},
        {"topic": "Security", "title": "OWASP Top 10", "summary": "Injection, XSS, auth, SSRF awareness.", "source": "internal", "keywords": ["owasp", "security"]},
    ],
    "doc_writer": [
        {"topic": "Docs", "title": "Docs as Code", "summary": "Markdown, MDX, versioned docs in repo.", "source": "internal", "keywords": ["docs", "markdown"]},
        {"topic": "OpenAPI", "title": "OpenAPI 3.1", "summary": "Schemas, examples, SDK generation.", "source": "internal", "keywords": ["openapi", "api"]},
        {"topic": "ADR", "title": "Architecture Decision Records", "summary": "Context, decision, consequences format.", "source": "internal", "keywords": ["adr", "architecture"]},
    ],
    "devops": [
        {"topic": "Docker", "title": "Multi-stage Docker builds", "summary": "Alpine base, non-root, layer caching.", "source": "internal", "keywords": ["docker", "container"]},
        {"topic": "K8s", "title": "Kubernetes Deployments", "summary": "Replicas, probes, HPA, ConfigMaps.", "source": "internal", "keywords": ["kubernetes", "k8s"]},
        {"topic": "CI", "title": "GitHub Actions CI", "summary": "Matrix builds, cache, deploy gates.", "source": "internal", "keywords": ["ci", "github"]},
    ],
    "cursor": [
        {"topic": "Cursor", "title": "Cursor Cloud Agents", "summary": "SDK, repo context, auto PR workflow.", "source": "internal", "keywords": ["cursor", "ai"]},
        {"topic": "MCP", "title": "Model Context Protocol", "summary": "Tools, resources, agent orchestration.", "source": "internal", "keywords": ["mcp", "tools"]},
    ],
    "presenter": [
        {"topic": "Slides", "title": "Pitch Deck Structure", "summary": "Problem, solution, market, traction, team, ask.", "source": "internal", "keywords": ["pitch", "slides"]},
        {"topic": "Story", "title": "Storytelling for Tech", "summary": "Hook, conflict, resolution, CTA.", "source": "internal", "keywords": ["story", "narrative"]},
        {"topic": "Design", "title": "Slide Design Principles", "summary": "One idea per slide, contrast, whitespace.", "source": "internal", "keywords": ["design", "visual"]},
    ],
    "modeler": [
        {"topic": "Three.js", "title": "Three.js Fundamentals", "summary": "Scene, camera, renderer, mesh, materials.", "source": "internal", "keywords": ["threejs", "webgl"]},
        {"topic": "glTF", "title": "glTF 2.0 Pipeline", "summary": "Blender export, Draco compression, loaders.", "source": "internal", "keywords": ["gltf", "3d"]},
        {"topic": "WebGL", "title": "Real-time 3D on Web", "summary": "PBR materials, lighting, performance tips.", "source": "internal", "keywords": ["webgl", "pbr"]},
    ],
}


def seed_agent(agent) -> int:
    seeds = SEED_KNOWLEDGE.get(agent.agent_id, [])
    if not seeds:
        return 0
    existing = {t.get("title", "") for t in agent.learned_topics}
    added = 0
    for s in seeds:
        if s["title"] in existing:
            continue
        entry = {**s, "url": "", "timestamp": NOW}
        agent.learned_topics.insert(0, entry)
        added += 1
    if added:
        agent._persist_knowledge()
    return added


def seed_all_agents(agents: dict) -> dict:
    report = {}
    for aid, agent in agents.items():
        report[aid] = seed_agent(agent)
    return report
