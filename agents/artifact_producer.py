"""Генерация артефактов по роли агента."""

from room.agent_capabilities import detect_artifact_type, get_capabilities


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _presentation_html(title: str, task: str, slides: list) -> str:
    slides_html = ""
    for i, s in enumerate(slides, 1):
        slides_html += f"""
        <section class="slide" data-slide="{i}">
            <h2>{_esc(s.get('title', f'Слайд {i}'))}</h2>
            <ul>{''.join(f'<li>{_esc(b)}</li>' for b in s.get('bullets', []))}</ul>
        </section>"""
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>{_esc(title)}</title>
<style>
body{{margin:0;font-family:Inter,Segoe UI,sans-serif;background:#0f1117;color:#f0f0f5}}
.slide{{min-height:100vh;padding:48px 64px;box-sizing:border-box;border-bottom:1px solid #333}}
.slide h1,.slide h2{{color:#6c63ff;margin:0 0 24px}}
.slide ul{{line-height:1.7;font-size:18px}}
.cover{{display:flex;flex-direction:column;justify-content:center;background:linear-gradient(135deg,#1a1d2e,#2d1f4e)}}
nav{{position:fixed;bottom:16px;right:16px;opacity:.6;font-size:12px}}
</style></head><body>
<section class="slide cover"><h1>{_esc(title)}</h1><p>{_esc(task[:120])}</p></section>
{slides_html}
<nav>AI Team · Презентация</nav></body></html>"""


def _threejs_scene_html(title: str, task: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{_esc(title)}</title>
<style>body{{margin:0;overflow:hidden;background:#1a1d24}}#info{{position:fixed;top:12px;left:12px;color:#fff;font:14px Inter,sans-serif;opacity:.8}}</style>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script></head>
<body><div id="info">{_esc(title)}</div>
<script>
const scene=new THREE.Scene();scene.background=new THREE.Color(0x1a1d24);
const camera=new THREE.PerspectiveCamera(55,innerWidth/innerHeight,0.1,100);
camera.position.set(0,2,5);
const renderer=new THREE.WebGLRenderer({{antialias:true}});renderer.setSize(innerWidth,innerHeight);
document.body.appendChild(renderer.domElement);
scene.add(new THREE.AmbientLight(0xffffff,0.6));
const sun=new THREE.DirectionalLight(0xffffff,0.9);sun.position.set(5,8,5);scene.add(sun);
const geo=new THREE.BoxGeometry(1,1,1);
const mat=new THREE.MeshStandardMaterial({{color:0x6c63ff,roughness:0.4,metalness:0.3}});
const mesh=new THREE.Mesh(geo,mat);scene.add(mesh);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(10,10),new THREE.MeshStandardMaterial({{color:0x333}}));
floor.rotation.x=-Math.PI/2;floor.position.y=-0.6;scene.add(floor);
function animate(){{requestAnimationFrame(animate);mesh.rotation.y+=0.01;renderer.render(scene,camera)}}
animate();
addEventListener('resize',()=>{{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)}});
</script></body></html>"""


async def _presentation_response(task_text: str, hints: dict = None) -> str:
    """Текст слайдов для .pptx — через LLM или структурированный fallback."""
    hints = hints or {}
    try:
        from integrations.llm_client import is_configured, agent_reply
        if is_configured():
            prompt = (
                f"Задача: {task_text}\n{hints.get('prompt_extra', '')}\n\n"
                "Создай структуру презентации 6–8 слайдов для PowerPoint.\n"
                "Формат — markdown: ## Заголовок слайда, затем буллеты - пункт.\n"
                "Без кода, без HTML, без React. Только содержание слайдов на русском."
            )
            text = await agent_reply(
                "Ника", "Presentation Designer",
                "Эксперт по pitch decks и PowerPoint", prompt, [],
            )
            if text and len(text.strip()) > 80:
                return text.strip()
    except Exception:
        pass
    return (
        f"## {task_text[:60]}\n"
        f"- Контекст и цель\n- Аудитория\n- Ключевое сообщение\n\n"
        "## Проблема\n- Боль клиента\n- Текущие ограничения\n- Почему сейчас\n\n"
        "## Решение\n- Наш подход\n- Основные функции\n- Отличия от альтернатив\n\n"
        "## Демо / продукт\n- Главный сценарий\n- UI/UX highlights\n- Метрики\n\n"
        "## Бизнес\n- Модель монетизации\n- TAM/SAM\n- Тraction\n\n"
        "## Следующие шаги\n- Roadmap\n- Call to action\n- Контакты"
    )


async def produce_artifact(agent, task_text: str, response: str, revision_of: str = None, original_task: str = ""):
    if not task_text.strip():
        return None

    from room.knowledge_applier import get_learned_hints
    from room.task_routing import effective_task_text
    hints = get_learned_hints(agent.agent_id, task_text, getattr(agent, "learned_topics", None))

    art_type = detect_artifact_type(agent.agent_id, task_text, original_task)
    caps = get_capabilities(agent.agent_id)
    user_task = effective_task_text(task_text, original_task)
    title = user_task[:80].strip()
    if len(user_task) > 80:
        title += "…"

    if len(response or "") < 80:
        from integrations.llm_codegen import generate_artifact_content
        response = await generate_artifact_content(
            task_text, art_type, agent.name, hints,
        )

    if art_type == "presentation" and len(response or "") < 200:
        response = await _presentation_response(user_task, hints)

    content = response
    preview_html = ""
    files = {}
    tags = caps.get("skills", [])[:4]

    if art_type == "presentation":
        from integrations.pptx_builder import _parse_slides, build_pptx_bytes
        slides = _parse_slides(user_task, response or "")
        preview_html = _presentation_html(title, user_task, slides)
        content = preview_html
        files = {"slides.html": preview_html}
        try:
            files["presentation.pptx"] = build_pptx_bytes(user_task, response or "", title=title)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("pptx build failed: %s", e)

    elif art_type == "model_3d":
        preview_html = _threejs_scene_html(title, user_task)
        content = preview_html
        files = {"scene.html": preview_html, "scene.js": "// Three.js scene for: " + user_task[:100]}

    elif art_type == "table":
        preview_html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>{_esc(title)}</title>
<style>
body{{margin:0;font-family:Inter,Segoe UI,sans-serif;background:#f6f7f9;padding:24px}}
h1{{font-size:20px;margin:0 0 8px}}
p{{color:#6b7280;font-size:13px;margin:0 0 16px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.06)}}
th,td{{padding:12px 16px;text-align:left;border-bottom:1px solid #e5e7eb;font-size:14px}}
th{{background:#f3f4f6;font-weight:600}}
</style></head><body>
<h1>{_esc(title)}</h1><p>{_esc(user_task[:120])}</p>
<table><thead><tr><th>#</th><th>Название</th><th>Значение</th><th>Статус</th></tr></thead>
<tbody>
<tr><td>1</td><td>Строка A</td><td>100</td><td>OK</td></tr>
<tr><td>2</td><td>Строка B</td><td>250</td><td>OK</td></tr>
<tr><td>3</td><td>Строка C</td><td>75</td><td>Pending</td></tr>
</tbody></table></body></html>"""
        content = preview_html
        files = {"table.html": preview_html}
        try:
            from integrations.xlsx_builder import build_xlsx_bytes
            files["table.xlsx"] = build_xlsx_bytes(task_text)
        except Exception:
            pass

    elif art_type in ("code", "api", "tests", "infra"):
        lang = "python" if agent.agent_id in ("backend", "qa", "devops") else "typescript"
        if "```" not in content:
            content = f"```{lang}\n# {task_text[:100]}\n# Generated by {agent.name}\n\n{response[:2000]}\n```"
        files = {f"main.{ 'py' if lang == 'python' else 'ts' }": content}

    elif art_type == "ui":
        tags.append("react")
        files = {"component.jsx": response[:3000] if response else f"// UI: {task_text}"}

    elif art_type == "architecture":
        content = f"## Architecture: {title}\n\n{response}\n\n```mermaid\ngraph TD\n  Client --> API\n  API --> DB\n```"
        files = {"architecture.md": content}

    elif art_type == "plan":
        content = f"# План: {title}\n\n{response}"

    artifact = {
        "type": art_type,
        "title": title,
        "description": response[:300] if response else task_text[:300],
        "task": user_task,
        "content": content,
        "preview_html": preview_html,
        "files": files,
        "tags": tags,
        "agent_name": agent.name,
        "agent_emoji": agent.emoji,
        "revision_of": revision_of,
        "status": "completed",
    }
    return artifact
