"""Генерация runnable React-кода для live preview Сони."""
import re
from integrations.figma_client import parse_figma_url
from room.task_routing import classify_task_kind


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")[:80]


def _fmt(template: str, task: str) -> str:
    """Подставить task без конфликта с JSX-фигурными скобками."""
    return template.replace("{task}", _esc(task))


def _extract_figma_url(task: str) -> str:
    for word in task.split():
        if "figma.com" in word:
            return word.strip("()[]<>\"'")
    return ""


def is_figma_import_task(task: str) -> bool:
    t = task.lower()
    if "figma.com" not in task:
        return False
    return any(w in t for w in [
        "figma", "импорт", "import", "макет", "design", "создай react", "react ui",
    ])

def is_site_task(task: str) -> bool:
    t = task.lower()
    return any(w in t for w in [
        "сайт", "website", "веб-сайт", "web-сайт", "лендинг", "landing",
        "портал", "web page", "веб-страниц", "webpage"
    ])


def is_production_polish_task(task: str) -> bool:
    t = task.lower()
    return any(w in t for w in [
        "production-ready", "production ready", "production ui",
        "продакшн", "production-ready ui", "до production",
    ])


def apply_figma_tokens(preview: dict, figma_data: dict) -> dict:
    """Подставить цвета из Figma в сгенерированный React-код."""
    if not figma_data:
        return preview
    summary = figma_data.get("summary") or {}
    colors = summary.get("colors") or figma_data.get("colors") or []
    if not colors:
        return preview

    primary = colors[0]
    secondary = colors[1] if len(colors) > 1 else primary
    accent = colors[2] if len(colors) > 2 else secondary

    code = preview.get("code", "")
    for old in ("#4f7df3", "#6c63ff", "#667eea", "#764ba2"):
        code = code.replace(old, primary)
    code = code.replace("#10b981", accent)
    code = code.replace("#f59e0b", secondary)

    tokens_block = f"""
/* Figma design tokens */
const figmaTokens = {{
  primary: '{primary}',
  secondary: '{secondary}',
  accent: '{accent}',
}};
"""
    if "figmaTokens" not in code:
        code = tokens_block + code

    out = dict(preview)
    out["code"] = code
    out["figma_applied"] = True
    out["title"] = preview.get("title", "UI") + " · Figma"
    return out


def polish_preview(preview: dict, task: str = "") -> dict:
    """Production-ready polish: design tokens and shared styling helpers."""
    code = preview.get("code", "")
    if not code.strip():
        return preview

    polish_header = """
/* Production-ready design system */
const ds = {
  colors: {
    primary: '#6c63ff',
    primaryHover: '#5a52e0',
    surface: '#ffffff',
    surfaceMuted: '#f6f7f9',
    text: '#1a1c22',
    textMuted: '#6b7280',
    border: '#e2e4ea',
    success: '#059669',
    danger: '#ef4444',
  },
  radius: { sm: 8, md: 12, lg: 16 },
  shadow: '0 4px 24px rgba(0,0,0,0.08)',
  font: 'system-ui, -apple-system, "Segoe UI", sans-serif',
};
const focusRing = { outline: '2px solid ' + ds.colors.primary, outlineOffset: 2 };
"""
    if "const ds = {" not in code:
        code = polish_header + code

    out = dict(preview)
    out["code"] = code
    out["polished"] = True
    out["title"] = "Production UI · " + preview.get("title", "Компонент")
    return out


def _apply_learned_palette(preview: dict) -> dict:
    """Подставить цвета из Design Lab (figma_learning), если есть."""
    try:
        from integrations.figma_learning import load_patterns
        patterns = load_patterns() or {}
        colors = (patterns.get("colors") or [])[:6]
        if not colors:
            return preview
        primary = colors[0]
        secondary = colors[1] if len(colors) > 1 else primary
        accent = colors[2] if len(colors) > 2 else secondary
        code = preview.get("code", "")
        for old in ("#4f7df3", "#6c63ff", "#667eea", "#764ba2"):
            code = code.replace(old, primary)
        code = code.replace("#10b981", accent)
        code = code.replace("#f59e0b", secondary)
        out = dict(preview)
        out["code"] = code
        out["learned_palette"] = colors[:4]
        return out
    except Exception:
        return preview


def generate_react_preview(task: str) -> dict:
    preview = _match_preview_template(task)
    preview = _apply_learned_palette(preview)
    if is_production_polish_task(task):
        preview = polish_preview(preview, task)
    return preview


def _match_preview_template(task: str) -> dict:
    t = task.lower()
    kind = classify_task_kind(task)

    if is_figma_import_task(task):
        figma_url = _extract_figma_url(task)
        parsed = parse_figma_url(figma_url) if figma_url else None
        if parsed:
            from integrations.figma_react import generate_react_from_figma, resolve_component_for_file

            if resolve_component_for_file(parsed["file_key"]):
                figma_stub = {
                    "file_key": parsed["file_key"],
                    "url": figma_url,
                    "summary": {"file_name": "Untitled", "colors": [], "fonts": [], "frames": []},
                }
                return generate_react_from_figma(figma_stub, task=task)

    if kind == "site" or is_site_task(task):
        return {"title": "Готовый сайт", "code": _fmt(_WEBSITE, task), "is_site": True}

    if kind == "table" or any(w in t for w in ["таблиц", "table", "excel", "spreadsheet", "csv", "data grid"]):
        return {"title": "Таблица данных", "code": _fmt(_TABLE, task)}

    if any(w in t for w in ["логин", "login", "авториз", "вход", "sign in"]):
        return {"title": "Форма входа", "code": _fmt(_LOGIN_FORM, task)}

    if any(w in t for w in ["регистрац", "register", "signup", "sign up"]):
        return {"title": "Регистрация", "code": _fmt(_REGISTER_FORM, task)}

    if any(w in t for w in ["кнопк", "button", "btn"]):
        return {"title": "Интерактивная кнопка", "code": _fmt(_BUTTON, task)}

    if any(w in t for w in ["todo", "список дел", "чеклист", "checklist", "todo-лист", "todo list"]):
        return {"title": "Todo-лист", "code": _fmt(_TODO, task)}

    if any(w in t for w in ["счётчик", "счетчик", "counter", "клик"]):
        return {"title": "Счётчик", "code": _fmt(_COUNTER, task)}

    if any(w in t for w in ["карточ", "card", "товар", "product"]):
        return {"title": "Карточка", "code": _fmt(_CARD, task)}

    if any(w in t for w in ["модал", "modal", "диалог", "popup", "попап"]):
        return {"title": "Модальное окно", "code": _fmt(_MODAL, task)}

    if any(w in t for w in ["дашборд", "dashboard", "панел", "аналитик", "статистик"]):
        return {"title": "Дашборд", "code": _fmt(_DASHBOARD, task)}

    if any(w in t for w in ["навигац", "navbar", "меню", "header", "шапк"]):
        return {"title": "Навигация", "code": _fmt(_NAVBAR, task)}

    if any(w in t for w in ["форм", "form", "input", "поле"]):
        return {"title": "Форма", "code": _fmt(_GENERIC_FORM, task)}

    return {"title": "UI компонент", "code": _fmt(_CARD, task)}


_COMMON_STYLES = """
const styles = {
  page: { minHeight: '100vh', background: 'linear-gradient(135deg,#1a1d2e 0%,#252a40 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, fontFamily: 'system-ui,sans-serif' },
  card: { background: '#fff', borderRadius: 16, padding: 28, boxShadow: '0 20px 60px rgba(0,0,0,0.25)', maxWidth: 420, width: '100%' },
  title: { margin: '0 0 8px', fontSize: 22, fontWeight: 700, color: '#1a1c22' },
  sub: { margin: '0 0 20px', fontSize: 13, color: '#6b7280' },
  btn: { padding: '10px 20px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg,#6c63ff,#4f7df3)', color: '#fff', fontWeight: 600, cursor: 'pointer', fontSize: 14 },
  input: { width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #e2e4ea', marginBottom: 12, fontSize: 14, boxSizing: 'border-box' },
};
"""

_BUTTON = _COMMON_STYLES + """
function App() {
  const [clicks, setClicks] = useState(0);
  const [hover, setHover] = useState(false);
  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Кнопка</h1>
        <p style={styles.sub}>Задача: "{task}"</p>
        <button
          style={{...styles.btn, transform: hover ? 'scale(1.05)' : 'scale(1)', transition: 'all 0.2s'}}
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
          onClick={() => setClicks(c => c + 1)}
        >
          Нажато: {clicks}
        </button>
      </div>
    </div>
  );
}
"""

_COUNTER = _COMMON_STYLES + """
function App() {
  const [n, setN] = useState(0);
  return (
    <div style={styles.page}>
      <div style={{...styles.card, textAlign: 'center'}}>
        <h1 style={styles.title}>Счётчик</h1>
        <p style={styles.sub}>{task}</p>
        <div style={{fontSize: 48, fontWeight: 700, color: '#4f7df3', margin: '16px 0'}}>{n}</div>
        <div style={{display: 'flex', gap: 8, justifyContent: 'center'}}>
          <button style={{...styles.btn, background: '#ef4444'}} onClick={() => setN(n-1)}>−</button>
          <button style={styles.btn} onClick={() => setN(0)}>Сброс</button>
          <button style={styles.btn} onClick={() => setN(n+1)}>+</button>
        </div>
      </div>
    </div>
  );
}
"""

_LOGIN_FORM = _COMMON_STYLES + """
function App() {
  const [email, setEmail] = useState('');
  const [pass, setPass] = useState('');
  const [ok, setOk] = useState(false);
  const submit = (e) => { e.preventDefault(); if(email && pass) setOk(true); };
  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Вход</h1>
        <p style={styles.sub}>{task}</p>
        {ok ? (
          <div style={{padding: 16, background: '#ecfdf5', borderRadius: 10, color: '#059669'}}>✓ Добро пожаловать, {email}!</div>
        ) : (
          <form onSubmit={submit}>
            <input style={styles.input} placeholder="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} />
            <input style={styles.input} placeholder="Пароль" type="password" value={pass} onChange={e => setPass(e.target.value)} />
            <button type="submit" style={{...styles.btn, width: '100%'}}>Войти</button>
          </form>
        )}
      </div>
    </div>
  );
}
"""

_REGISTER_FORM = _COMMON_STYLES + """
function App() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [done, setDone] = useState(false);
  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Регистрация</h1>
        <p style={styles.sub}>{task}</p>
        {done ? <p style={{color:'#059669'}}>Аккаунт {name} создан!</p> : (
          <form onSubmit={e => { e.preventDefault(); setDone(true); }}>
            <input style={styles.input} placeholder="Имя" value={name} onChange={e => setName(e.target.value)} />
            <input style={styles.input} placeholder="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} />
            <button type="submit" style={{...styles.btn, width:'100%'}}>Создать аккаунт</button>
          </form>
        )}
      </div>
    </div>
  );
}
"""

_GENERIC_FORM = _LOGIN_FORM

_TODO = _COMMON_STYLES + """
function App() {
  const [items, setItems] = useState(['Изучить React', 'Сверстать UI']);
  const [text, setText] = useState('');
  const add = () => { if(text.trim()) { setItems([...items, text.trim()]); setText(''); } };
  const toggle = (i) => setItems(items.map((it, j) => j===i ? '✓ '+it.replace(/^✓ /,'') : it));
  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Todo</h1>
        <p style={styles.sub}>{task}</p>
        <div style={{display:'flex', gap:8, marginBottom:16}}>
          <input style={{...styles.input, margin:0, flex:1}} value={text} onChange={e=>setText(e.target.value)} placeholder="Новая задача" onKeyDown={e=>e.key==='Enter'&&add()} />
          <button style={styles.btn} onClick={add}>+</button>
        </div>
        {items.map((it,i) => (
          <div key={i} onClick={()=>toggle(i)} style={{padding:'8px 12px', marginBottom:6, background:'#f3f4f6', borderRadius:8, cursor:'pointer', fontSize:14}}>{it}</div>
        ))}
      </div>
    </div>
  );
}
"""

_CARD = _COMMON_STYLES + """
function App() {
  const [liked, setLiked] = useState(false);
  return (
    <div style={styles.page}>
      <div style={{...styles.card, maxWidth: 320}}>
        <div style={{height:140, background:'linear-gradient(135deg,#667eea,#764ba2)', borderRadius:12, marginBottom:16}} />
        <h2 style={{margin:'0 0 4px', fontSize:18}}>Продукт</h2>
        <p style={{margin:'0 0 12px', fontSize:13, color:'#6b7280'}}>{task}</p>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <span style={{fontSize:20, fontWeight:700, color:'#4f7df3'}}>2 490 ₽</span>
          <button style={{...styles.btn, background: liked ? '#ef4444' : styles.btn.background}} onClick={()=>setLiked(!liked)}>
            {liked ? '♥' : '♡'} В избранное
          </button>
        </div>
      </div>
    </div>
  );
}
"""

_TABLE = _COMMON_STYLES + """
function App() {
  const rows = [
    { id: 1, name: 'Алекс', role: 'Architect', status: 'online' },
    { id: 2, name: 'Макс', role: 'Backend', status: 'busy' },
    { id: 3, name: 'Соня', role: 'Frontend', status: 'online' },
  ];
  return (
    <div style={styles.page}>
      <div style={{...styles.card, maxWidth: 520}}>
        <h1 style={styles.title}>Команда</h1>
        <p style={styles.sub}>{task}</p>
        <table style={{width:'100%', borderCollapse:'collapse', fontSize:13}}>
          <thead><tr style={{borderBottom:'2px solid #e5e7eb'}}>
            <th style={{textAlign:'left', padding:8}}>ID</th>
            <th style={{textAlign:'left', padding:8}}>Имя</th>
            <th style={{textAlign:'left', padding:8}}>Роль</th>
            <th style={{textAlign:'left', padding:8}}>Статус</th>
          </tr></thead>
          <tbody>{rows.map(r => (
            <tr key={r.id} style={{borderBottom:'1px solid #f3f4f6'}}>
              <td style={{padding:8}}>{r.id}</td>
              <td style={{padding:8}}>{r.name}</td>
              <td style={{padding:8}}>{r.role}</td>
              <td style={{padding:8}}><span style={{padding:'2px 8px', borderRadius:12, background: r.status==='online'?'#d1fae5':'#fef3c7', fontSize:11}}>{r.status}</span></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
"""

_MODAL = _COMMON_STYLES + """
function App() {
  const [open, setOpen] = useState(true);
  return (
    <div style={styles.page}>
      {!open && <button style={styles.btn} onClick={()=>setOpen(true)}>Открыть модал</button>}
      {open && (
        <div style={{position:'fixed', inset:0, background:'rgba(0,0,0,0.5)', display:'flex', alignItems:'center', justifyContent:'center'}} onClick={()=>setOpen(false)}>
          <div style={styles.card} onClick={e=>e.stopPropagation()}>
            <h1 style={styles.title}>Подтверждение</h1>
            <p style={styles.sub}>{task}</p>
            <div style={{display:'flex', gap:8, justifyContent:'flex-end'}}>
              <button style={{...styles.btn, background:'#9ca3af'}} onClick={()=>setOpen(false)}>Отмена</button>
              <button style={styles.btn} onClick={()=>setOpen(false)}>OK</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
"""

_DASHBOARD = _COMMON_STYLES + """
function App() {
  const stats = [{l:'Пользователи',v:'1.2k',c:'#4f7df3'},{l:'Заказы',v:'348',c:'#10b981'},{l:'Выручка',v:'89k',c:'#f59e0b'}];
  return (
    <div style={{...styles.page, alignItems:'flex-start', paddingTop:40}}>
      <div style={{maxWidth:600, width:'100%'}}>
        <h1 style={{...styles.title, color:'#fff', marginBottom:4}}>Дашборд</h1>
        <p style={{color:'#9ca3af', marginBottom:24, fontSize:13}}>{task}</p>
        <div style={{display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:12}}>
          {stats.map((s,i) => (
            <div key={i} style={{background:'#fff', borderRadius:12, padding:20, borderTop:`4px solid ${s.c}`}}>
              <div style={{fontSize:12, color:'#6b7280'}}>{s.l}</div>
              <div style={{fontSize:28, fontWeight:700, color:'#1a1c22'}}>{s.v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
"""

_NAVBAR = _COMMON_STYLES + """
function App() {
  const [active, setActive] = useState('home');
  const links = ['home','projects','about','contact'];
  return (
    <div style={{minHeight:'100vh', background:'#f6f7f9', fontFamily:'system-ui'}}>
      <nav style={{background:'#fff', padding:'12px 24px', display:'flex', gap:24, alignItems:'center', boxShadow:'0 1px 3px rgba(0,0,0,0.08)'}}>
        <strong style={{color:'#4f7df3'}}>App</strong>
        {links.map(l => (
          <button key={l} onClick={()=>setActive(l)} style={{border:'none', background:'none', cursor:'pointer', fontWeight: active===l?700:400, color: active===l?'#4f7df3':'#6b7280', textTransform:'capitalize'}}>{l}</button>
        ))}
      </nav>
      <div style={{padding:40, textAlign:'center'}}>
        <h1 style={{fontSize:28}}>Раздел: {active}</h1>
        <p style={{color:'#6b7280'}}>{task}</p>
      </div>
    </div>
  );
}
"""

_WEBSITE = """
function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const task = "{task}";
  const features = [
    { icon: '⚡', title: 'Быстро', desc: 'Оптимизированная загрузка и Core Web Vitals' },
    { icon: '🎨', title: 'Красиво', desc: 'Современный UI с адаптивной вёрсткой' },
    { icon: '🔒', title: 'Надёжно', desc: 'Best practices безопасности и доступности' },
  ];
  const nav = ['Главная', 'О нас', 'Услуги', 'Контакты'];
  const s = {
    font: 'system-ui, -apple-system, sans-serif',
    primary: '#4f7df3',
    dark: '#1a1c22',
    muted: '#6b7280',
  };
  return (
    <div style={{ fontFamily: s.font, color: s.dark, minHeight: '100vh' }}>
      <header style={{
        background: '#fff', boxShadow: '0 1px 8px rgba(0,0,0,0.06)',
        padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 10
      }}>
        <strong style={{ fontSize: 18, color: s.primary }}>MySite</strong>
        <nav style={{ display: 'flex', gap: 20, fontSize: 14 }}>
          {nav.map(n => (
            <a key={n} href="#" style={{ color: s.muted, textDecoration: 'none' }}>{n}</a>
          ))}
        </nav>
        <button style={{
          background: s.primary, color: '#fff', border: 'none', borderRadius: 8,
          padding: '8px 16px', fontWeight: 600, cursor: 'pointer', fontSize: 13
        }}>Начать</button>
      </header>

      <section style={{
        background: 'linear-gradient(135deg, #1a1d2e 0%, #2d3561 50%, #4f7df3 100%)',
        color: '#fff', padding: '64px 24px', textAlign: 'center'
      }}>
        <p style={{ opacity: 0.8, fontSize: 13, marginBottom: 8 }}>✨ Собрано Соней · React</p>
        <h1 style={{ fontSize: 'clamp(28px, 5vw, 42px)', margin: '0 0 16px', fontWeight: 800 }}>
          {task.length > 60 ? task.slice(0, 60) + '…' : task}
        </h1>
        <p style={{ fontSize: 16, opacity: 0.85, maxWidth: 520, margin: '0 auto 28px', lineHeight: 1.6 }}>
          Современный адаптивный сайт с интерактивными элементами. Готов к доработке и деплою.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button style={{
            background: '#fff', color: s.primary, border: 'none', borderRadius: 10,
            padding: '12px 28px', fontWeight: 700, cursor: 'pointer', fontSize: 15
          }}>Подробнее</button>
          <button style={{
            background: 'rgba(255,255,255,0.18)', color: '#fff',
            border: '2px solid rgba(255,255,255,0.45)',
            borderRadius: 10, padding: '12px 28px', fontWeight: 600, cursor: 'pointer', fontSize: 15
          }}>Связаться</button>
        </div>
      </section>

      <section style={{ padding: '48px 24px', maxWidth: 900, margin: '0 auto' }}>
        <h2 style={{ textAlign: 'center', fontSize: 24, marginBottom: 32 }}>Почему мы</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20 }}>
          {features.map((f, i) => (
            <div key={i} style={{
              background: '#f8f9fc', borderRadius: 14, padding: 24, textAlign: 'center',
              border: '1px solid #e8eaef'
            }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>{f.icon}</div>
              <h3 style={{ margin: '0 0 8px', fontSize: 16 }}>{f.title}</h3>
              <p style={{ margin: 0, fontSize: 13, color: s.muted, lineHeight: 1.5 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section style={{ background: '#f0f4ff', padding: '40px 24px', textAlign: 'center' }}>
        <h2 style={{ fontSize: 22, marginBottom: 12 }}>Готовы начать?</h2>
        <p style={{ color: s.muted, marginBottom: 20 }}>Оставьте email — свяжемся в течение дня</p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', maxWidth: 400, margin: '0 auto' }}>
          <input placeholder="your@email.com" style={{
            flex: 1, padding: '10px 14px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 14
          }} />
          <button style={{
            background: s.primary, color: '#fff', border: 'none', borderRadius: 8,
            padding: '10px 20px', fontWeight: 600, cursor: 'pointer'
          }}>OK</button>
        </div>
      </section>

      <footer style={{ background: s.dark, color: '#9ca3af', padding: '24px', textAlign: 'center', fontSize: 12 }}>
        © 2026 MySite · Сделано командой AI Team Room
      </footer>
    </div>
  );
}
"""

_HERO = _COMMON_STYLES + """
function App() {
  return (
    <div style={styles.page}>
      <div style={{textAlign:'center', maxWidth:480}}>
        <div style={{fontSize:48, marginBottom:16}}>🎨</div>
        <h1 style={{...styles.title, color:'#fff', fontSize:32}}>Соня · Frontend</h1>
        <p style={{color:'#b0b8c8', fontSize:15, lineHeight:1.6, marginBottom:24}}>{task}</p>
        <button style={{...styles.btn, padding:'12px 28px', fontSize:16}}>Начать</button>
      </div>
    </div>
  );
}
"""
