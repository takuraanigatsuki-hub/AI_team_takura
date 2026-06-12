import sys
import uvicorn
from config import config

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 60)
    print("  🤖 AI TEAM ROOM — Команда ИИ-агентов")
    print("=" * 60)
    print(f"  🌐 Адрес: http://localhost:{config['port']}")
    print("  🏢 3D Студия + комната отдыха + личные диалоги")
    print(f"  📚 Обучение: веб, Wikipedia, книги, arXiv, Gutenberg и др.")
    print(f"  💾 Сохранение знаний: {'✅ Включено' if config.get('persist_knowledge', True) else '❌ Выключено'}")
    print("=" * 60)
    print("  Агенты:")
    print("  🎯 Виктор  — PM & Orchestrator")
    print("  🏛️ Алекс   — Software Architect")
    print("  ⚙️ Макс    — Backend Developer")
    print("  🎨 Соня    — Frontend Developer")
    print("  🧪 Рита    — QA Engineer")
    print("  🔍 Дэн     — Code Reviewer")
    print("  📝 Лена    — Technical Writer")
    print("  🔧 Кирилл  — DevOps Engineer")
    print("  ⚡ Лео     — Cursor SDK")
    print("  📽️ Ника    — Presentations")
    print("  🧊 Зоя     — 3D Artist")
    print("  🎓 Маша    — Skill Evaluator")
    print("  🛡 Олег    — Security Engineer")
    print("=" * 60)

    uvicorn.run(
        "app:app",
        host=config["host"],
        port=config["port"],
        reload=config.get("debug", False),
        log_level="info"
    )
