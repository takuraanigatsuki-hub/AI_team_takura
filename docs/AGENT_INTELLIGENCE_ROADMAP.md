# Agent Intelligence Roadmap — AI Team Room

> План превращения команды из шаблонных ботов в систему с RAG-памятью, умной маршрутизацией и реальными артефактами.
> Статус обновляется по мере реализации. **Фаза A — в работе.**

---

## Цели

1. **Знания не с нуля** — каждый агент имеет базу знаний по роли (цель: до 5 GB/агент через RAG).
2. **Только нужные агенты** — в общий чат не лезет вся команда.
3. **Готовые файлы** — `.pptx`, `.xlsx`, `.docx` в чат + Microsoft 365.
4. **Настоящий ИИ** — LLM + tools + RAG (ключ OpenAI подключится позже).

---

## Архитектура знаний (3 уровня)

```
Уровень 1 — Ядро роли     system prompt + agent_capabilities.py
Уровень 2 — RAG           SQLite FTS5 → позже Qdrant/Chroma + embeddings
Уровень 3 — Live learning  Wikipedia, arXiv, web (уже в base_agent)
```

| Компонент | Путь | Статус |
|-----------|------|--------|
| FTS RAG store | `integrations/rag/store.py` | ✅ Фаза A |
| Ingest packs | `integrations/rag/ingest.py` | ✅ Фаза A |
| Retrieve | `integrations/rag/retrieve.py` | ✅ Фаза A |
| Knowledge packs | `knowledge_packs/packs_data.py` | ✅ Фаза A |
| Embeddings (optional) | `integrations/rag/embeddings.py` | 🔲 Фаза B |
| Qdrant / pgvector | config `rag_backend` | 🔲 Фаза B |

---

## Фаза A — Фундамент ✅

- [x] Дорожная карта (этот документ)
- [x] SQLite FTS5 RAG + ingest скрипт
- [x] Стартовые knowledge packs по 13 ролям (~500+ записей)
- [x] LLM Router (`room/llm_router.py`) с keyword-fallback без API key
- [x] Тихий role triage (без спама «Пропускаю» в чат)
- [x] PPTX генератор (`integrations/pptx_builder.py`)
- [x] XLSX генератор (`integrations/xlsx_builder.py`)
- [x] RAG в `knowledge_applier.get_learned_hints()`
- [x] API `GET /api/rag/status`, `POST /api/rag/reindex`
- [x] Auto-ingest при старте сервера

### Команды

```powershell
# Переиндексация пакетов знаний
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" scripts/ingest_knowledge_packs.py

# Статус RAG
curl http://localhost:8000/api/rag/status
```

### После получения OPENAI_API_KEY

```env
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_ROUTER_MODEL=gpt-4o-mini
```

Router автоматически начнёт использовать LLM вместо keyword-fallback.

---

## Фаза B — Умная команда ✅

- [x] Agent tool registry (`integrations/agent_tools/`)
- [x] MCP gateway (`integrations/mcp_gateway.py`)
- [x] Embeddings + hybrid search (FTS + vectors)
- [ ] Playwright MCP для QA
- [x] Расширение packs: ingest URL docs (FastAPI, React, OWASP)
- [x] Project memory (`room/project_memory.py`)
- [x] Evaluator gate — артеfact не уходит пользователю без оценки ≥ порога

---

## Фаза C — Production (в работе)

- [x] ReAct loop: plan → tool → observe → repeat (`room/react_loop.py`)
- [x] Docker sandbox для выполнения кода (`integrations/sandbox/`)
- [x] Router logs + export fine-tune JSONL (`room/router_logs.py`)
- [x] Bulk corpora ingest — docs + Wikipedia (`integrations/rag/corpora_ingest.py`)
- [x] Multi-tenant RAG isolation per workspace (`integrations/rag/workspace_store.py`)
- [ ] Fine-tuned router (обучение на накопленных логах)
- [ ] Полный Docker sandbox в CI + Playwright MCP

---

## Knowledge packs — целевые объёмы по ролям

| Агент | Стартовый pack (Фаза A) | Цель (Фаза C) |
|-------|-------------------------|---------------|
| pm | ~40 topics | 500 MB |
| architect | ~40 | 1–2 GB |
| backend | ~45 | 2–3 GB |
| frontend | ~45 | 2 GB |
| qa | ~35 | 1 GB |
| reviewer | ~35 | 500 MB |
| doc_writer | ~35 | 500 MB |
| devops | ~40 | 1–2 GB |
| cursor | ~30 | 500 MB |
| presenter | ~30 | 300 MB |
| modeler | ~30 | 500 MB |
| evaluator | ~25 | 200 MB |
| security | ~40 | 1 GB |

Источники для масштабирования: official docs, OWASP, arXiv summaries, Wikipedia, GitHub awesome-lists, внутренние ADR проекта.

---

## Файлы проекта (индекс)

```
docs/AGENT_INTELLIGENCE_ROADMAP.md     ← этот план
integrations/rag/                      ← RAG слой
knowledge_packs/packs_data.py          ← стартовые пакеты
room/llm_router.py                     ← маршрутизация агентов
room/role_triage.py                    ← тихий triage
integrations/pptx_builder.py           ← PowerPoint
integrations/xlsx_builder.py           ← Excel
scripts/ingest_knowledge_packs.py      ← CLI ingest
data/rag/knowledge.db                  ← SQLite FTS (gitignore)
```

---

*Последнее обновление: 2026-06-13 — Smart AIPI + Фаза C started*
