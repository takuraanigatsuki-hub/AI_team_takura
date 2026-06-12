"""Генерация runnable React-кода для live preview Сони."""
import hashlib
import re


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")[:80]


def _fill(template: str, task: str) -> str:
    """Подставить task в шаблон без str.format (JSX содержит фигурные скобки)."""
    return template.replace("{task}", _esc(task))


def _render_legacy(template: str, task: str) -> str:
    """Рендер legacy-шаблонов с {{ }} экранированием под str.format."""
    open_b, close_b = "\x00LB\x00", "\x00RB\x00"
    s = template.replace("{{", open_b).replace("}}", close_b)
    s = s.replace("{task}", _esc(task))
    return s.replace(open_b, "{").replace(close_b, "}")


def is_site_task(task: str) -> bool:
    t = task.lower()
    return any(w in t for w in [
        "сайт", "website", "веб-сайт", "web-сайт", "лендинг", "landing",
        "портал", "web page", "веб-страниц", "webpage"
    ])


def is_polish_task(task: str) -> bool:
    t = task.lower()
    return any(w in t for w in [
        "production-ready", "production ready", "prod-ready", "prod ready",
        "доработай react preview", "polish ui", "polish preview",
        "production ui", "prod ui", "до production",
    ])


def _normalize_hex(color: str) -> str | None:
    c = (color or "").strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3,8}", c):
        return c if len(c) != 4 else f"#{c[1]}{c[1]}{c[2]}{c[2]}{c[3]}{c[3]}"
    return None


def _inject_figma_colors(code: str, colors: list[str] | None) -> str:
    """Подставить палитру Figma вместо дефолтных токенов."""
    if not colors:
        return code
    palette = [_normalize_hex(c) for c in colors]
    palette = [c for c in palette if c]
    if not palette:
        return code
    primary = palette[0]
    secondary = palette[1] if len(palette) > 1 else primary
    accent = palette[2] if len(palette) > 2 else secondary
    replacements = [
        ("#4f7df3", primary),
        ("#6c63ff", secondary),
        ("#667eea", accent),
        ("#764ba2", secondary),
    ]
    for old, new in replacements:
        code = code.replace(old, new)
    return code


def _pick_fallback_template(task: str):
    """Детерминированный выбор шаблона по задаче (без random)."""
    templates = [_HERO, _CARD, _COUNTER, _BUTTON, _TODO]
    idx = int(hashlib.md5(task.encode()).hexdigest(), 16) % len(templates)
    return templates[idx]


def polish_preview(existing: dict | None, task: str) -> dict:
    """Довести preview до production-ready: a11y, токены, полировка."""
    base = existing or {}
    title = base.get("title") or "Production UI"
    code = base.get("code") or _fill(_PRODUCTION_SHOWCASE, task)
    code = _inject_figma_colors(code, base.get("colors"))
    if "aria-" not in code and "role=" not in code:
        code = _fill(_PRODUCTION_SHOWCASE, task)
    return {
        "title": f"{title} · Production",
        "code": code,
        "is_site": base.get("is_site", False),
        "polished": True,
    }


def generate_react_preview(
    task: str,
    figma_colors: list[str] | None = None,
    previous: dict | None = None,
) -> dict:
    t = task.lower()

    if is_polish_task(task):
        result = polish_preview(previous, task)
        result["code"] = _inject_figma_colors(result["code"], figma_colors)
        return result

    if is_site_task(task):
        result = {"title": "Готовый сайт", "code": _fill(_WEBSITE, task), "is_site": True}
    elif any(w in t for w in ["saas", "подписк", "subscription", "kpi"]):
        result = {"title": "SaaS Dashboard", "code": _fill(_SAAS, task)}
    elif any(w in t for w in ["e-commerce", "ecommerce", "корзин", "checkout", "каталог", "магазин"]):
        result = {"title": "E-commerce", "code": _fill(_ECOMMERCE, task)}
    elif any(w in t for w in ["admin panel", "админ", "crud", "роли admin"]):
        result = {"title": "Admin Panel", "code": _fill(_ADMIN, task)}
    elif any(w in t for w in ["логин", "login", "авториз", "вход", "sign in"]):
        result = {"title": "Форма входа", "code": _render_legacy(_LOGIN_FORM, task)}
    elif any(w in t for w in ["регистрац", "register", "signup", "sign up"]):
        result = {"title": "Регистрация", "code": _render_legacy(_REGISTER_FORM, task)}
    elif any(w in t for w in ["кнопк", "button", "btn"]):
        result = {"title": "Интерактивная кнопка", "code": _render_legacy(_BUTTON, task)}
    elif any(w in t for w in ["todo", "список дел", "чеклист", "checklist"]):
        result = {"title": "Todo-лист", "code": _render_legacy(_TODO, task)}
    elif any(w in t for w in ["счётчик", "счетчик", "counter", "клик"]):
        result = {"title": "Счётчик", "code": _render_legacy(_COUNTER, task)}
    elif any(w in t for w in ["карточ", "card", "товар", "product"]):
        result = {"title": "Карточка", "code": _render_legacy(_CARD, task)}
    elif any(w in t for w in ["таблиц", "table", "данн", "data grid"]):
        result = {"title": "Таблица данных", "code": _render_legacy(_TABLE, task)}
    elif any(w in t for w in ["модал", "modal", "диалог", "popup", "попап"]):
        result = {"title": "Модальное окно", "code": _render_legacy(_MODAL, task)}
    elif any(w in t for w in ["дашборд", "dashboard", "панел", "аналитик", "статистик"]):
        result = {"title": "Дашборд", "code": _render_legacy(_DASHBOARD, task)}
    elif any(w in t for w in ["навигац", "navbar", "меню", "header", "шапк"]):
        result = {"title": "Навигация", "code": _render_legacy(_NAVBAR, task)}
    elif any(w in t for w in ["форм", "form", "input", "поле"]):
        result = {"title": "Форма", "code": _render_legacy(_GENERIC_FORM, task)}
    else:
        pick = _pick_fallback_template(task)
        result = {"title": "UI компонент", "code": _render_legacy(pick, task)}

    if figma_colors:
        result["colors"] = figma_colors
        result["code"] = _inject_figma_colors(result["code"], figma_colors)
    return result


_COMMON_STYLES = """
const focusRing = {{ outline: '2px solid #4f7df3', outlineOffset: 2 }};
const styles = {
  page: { minHeight: '100vh', background: 'linear-gradient(135deg,#1a1d2e 0%,#252a40 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'clamp(16px,4vw,32px)', fontFamily: 'system-ui,-apple-system,sans-serif' },
  card: { background: '#fff', borderRadius: 16, padding: 'clamp(20px,4vw,28px)', boxShadow: '0 20px 60px rgba(0,0,0,0.25)', maxWidth: 420, width: '100%' },
  title: { margin: '0 0 8px', fontSize: 'clamp(18px,3vw,22px)', fontWeight: 700, color: '#1a1c22' },
  sub: { margin: '0 0 20px', fontSize: 13, color: '#6b7280', lineHeight: 1.5 },
  btn: { padding: '10px 20px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg,#6c63ff,#4f7df3)', color: '#fff', fontWeight: 600, cursor: 'pointer', fontSize: 14, minHeight: 44 },
  input: { width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #e2e4ea', marginBottom: 12, fontSize: 14, boxSizing: 'border-box', minHeight: 44 },
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
          <form onSubmit={submit} aria-label="Форма входа">
            <input id="email" style={styles.input} placeholder="you@example.com" type="email" autoComplete="email" required aria-label="Email" aria-required="true" value={email} onChange={e => setEmail(e.target.value)} />
            <input id="pass" style={styles.input} placeholder="••••••••" type="password" autoComplete="current-password" required aria-label="Пароль" aria-required="true" value={pass} onChange={e => setPass(e.target.value)} />
            <button type="submit" style={{...styles.btn, width: '100%'}} aria-label="Войти в аккаунт">Войти</button>
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
            background: 'transparent', color: '#fff', border: '2px solid rgba(255,255,255,0.5)',
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
    <main style={styles.page} role="main">
      <div style={{textAlign:'center', maxWidth:480}}>
        <div style={{fontSize:48, marginBottom:16}} aria-hidden="true">🎨</div>
        <h1 style={{...styles.title, color:'#fff', fontSize:'clamp(24px,5vw,32px)'}}>Соня · Frontend</h1>
        <p style={{color:'#b0b8c8', fontSize:15, lineHeight:1.6, marginBottom:24}}>{task}</p>
        <button style={{...styles.btn, padding:'12px 28px', fontSize:16}} aria-label="Начать работу">Начать</button>
      </div>
    </main>
  );
}
"""

_PRODUCTION_SHOWCASE = """
function App() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const task = "{task}";
  const tokens = {
    primary: '#4f7df3',
    secondary: '#6c63ff',
    bg: '#0f1117',
    surface: '#1a1d28',
    text: '#f3f4f6',
    muted: '#9ca3af',
    success: '#10b981',
    radius: 12,
  };
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setTimeout(() => { setLoading(false); setSubmitted(true); }, 800);
  };
  const stats = [
    { label: 'Lighthouse', value: '98', unit: '/100' },
    { label: 'A11y score', value: '100', unit: '%' },
    { label: 'Bundle', value: '< 50', unit: 'KB' },
  ];
  return (
    <div style={{ minHeight: '100vh', background: tokens.bg, color: tokens.text, fontFamily: 'system-ui,-apple-system,sans-serif' }}>
      <header style={{ padding: '16px 24px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }} role="banner">
        <strong style={{ fontSize: 16, background: `linear-gradient(135deg,${tokens.secondary},${tokens.primary})`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Production UI</strong>
        <nav aria-label="Основная навигация" style={{ display: 'flex', gap: 16, fontSize: 13 }}>
          {['Features', 'Metrics', 'Contact'].map((item) => (
            <a key={item} href="#" style={{ color: tokens.muted, textDecoration: 'none' }}>{item}</a>
          ))}
        </nav>
      </header>
      <main style={{ maxWidth: 720, margin: '0 auto', padding: '48px 24px' }} role="main">
        <p style={{ fontSize: 12, color: tokens.muted, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Production-ready · React</p>
        <h1 style={{ fontSize: 'clamp(28px,5vw,40px)', fontWeight: 800, margin: '0 0 12px', lineHeight: 1.15 }}>{task.length > 50 ? task.slice(0, 50) + '…' : task}</h1>
        <p style={{ color: tokens.muted, lineHeight: 1.6, marginBottom: 32, fontSize: 15 }}>
          Адаптивная вёрстка, доступность WCAG 2.1, семантическая разметка и оптимизированные интерактивные элементы.
        </p>
        <section aria-label="Метрики качества" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 12, marginBottom: 32 }}>
          {stats.map((s) => (
            <article key={s.label} style={{ background: tokens.surface, borderRadius: tokens.radius, padding: 20, border: '1px solid rgba(255,255,255,0.06)' }}>
              <div style={{ fontSize: 11, color: tokens.muted, marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: 28, fontWeight: 700 }}>{s.value}<span style={{ fontSize: 14, color: tokens.muted }}>{s.unit}</span></div>
            </article>
          ))}
        </section>
        <section aria-label="Подписка" style={{ background: tokens.surface, borderRadius: tokens.radius, padding: 24, border: '1px solid rgba(255,255,255,0.06)' }}>
          {submitted ? (
            <div role="status" style={{ color: tokens.success, fontSize: 14 }}>✓ Спасибо! Мы свяжемся с {email}</div>
          ) : (
            <form onSubmit={handleSubmit} aria-label="Форма подписки">
              <label htmlFor="prod-email" style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Email для демо</label>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <input id="prod-email" type="email" required aria-required="true" autoComplete="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} style={{ flex: '1 1 200px', padding: '12px 14px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: tokens.bg, color: tokens.text, fontSize: 14, minHeight: 44 }} />
                <button type="submit" disabled={loading} aria-busy={loading} style={{ padding: '12px 24px', borderRadius: 8, border: 'none', background: `linear-gradient(135deg,${tokens.secondary},${tokens.primary})`, color: '#fff', fontWeight: 600, cursor: loading ? 'wait' : 'pointer', fontSize: 14, minHeight: 44, opacity: loading ? 0.7 : 1 }}>
                  {loading ? 'Отправка…' : 'Получить демо'}
                </button>
              </div>
            </form>
          )}
        </section>
      </main>
      <footer style={{ textAlign: 'center', padding: 24, fontSize: 12, color: tokens.muted, borderTop: '1px solid rgba(255,255,255,0.06)' }} role="contentinfo">
        © 2026 AI Team Room · Production-ready React Preview
      </footer>
    </div>
  );
}
"""

_SAAS = """
function App() {
  const [section, setSection] = useState('dashboard');
  const task = "{task}";
  const nav = [{ id: 'dashboard', label: 'Dashboard', icon: '📊' }, { id: 'users', label: 'Users', icon: '👥' }, { id: 'billing', label: 'Billing', icon: '💳' }];
  const kpis = [{ l: 'MRR', v: '$12.4k', d: '+8%' }, { l: 'Users', v: '1,842', d: '+12%' }, { l: 'Churn', v: '2.1%', d: '-0.3%' }];
  const users = [{ n: 'Анна К.', r: 'Admin', s: 'active' }, { n: 'Игорь М.', r: 'Editor', s: 'active' }, { n: 'Елена С.', r: 'Viewer', s: 'pending' }];
  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui,sans-serif', background: '#f6f7f9' }}>
      <aside aria-label="Sidebar" style={{ width: 200, background: '#1a1c22', color: '#fff', padding: '20px 0', flexShrink: 0 }}>
        <div style={{ padding: '0 16px 20px', fontWeight: 700, fontSize: 15, color: '#4f7df3' }}>SaaS App</div>
        {nav.map((item) => (
          <button key={item.id} onClick={() => setSection(item.id)} aria-current={section === item.id ? 'page' : undefined}
            style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '10px 16px', border: 'none', background: section === item.id ? 'rgba(79,125,243,0.15)' : 'transparent', color: section === item.id ? '#4f7df3' : '#9ca3af', cursor: 'pointer', fontSize: 13, textAlign: 'left' }}>
            <span aria-hidden="true">{item.icon}</span>{item.label}
          </button>
        ))}
      </aside>
      <main style={{ flex: 1, padding: '24px clamp(16px,3vw,32px)' }} role="main">
        <h1 style={{ margin: '0 0 4px', fontSize: 22 }}>{section.charAt(0).toUpperCase() + section.slice(1)}</h1>
        <p style={{ margin: '0 0 24px', fontSize: 13, color: '#6b7280' }}>{task}</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 12, marginBottom: 24 }}>
          {kpis.map((k) => (
            <div key={k.l} style={{ background: '#fff', borderRadius: 12, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>{k.l}</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{k.v}</div>
              <div style={{ fontSize: 12, color: k.d.startsWith('+') ? '#059669' : '#dc2626' }}>{k.d}</div>
            </div>
          ))}
        </div>
        <table style={{ width: '100%', background: '#fff', borderRadius: 12, borderCollapse: 'collapse', fontSize: 13, boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }} aria-label="Пользователи">
          <thead><tr style={{ borderBottom: '2px solid #f3f4f6' }}>
            <th scope="col" style={{ textAlign: 'left', padding: 12 }}>Имя</th>
            <th scope="col" style={{ textAlign: 'left', padding: 12 }}>Роль</th>
            <th scope="col" style={{ textAlign: 'left', padding: 12 }}>Статус</th>
          </tr></thead>
          <tbody>{users.map((u) => (
            <tr key={u.n} style={{ borderBottom: '1px solid #f9fafb' }}>
              <td style={{ padding: 12 }}>{u.n}</td>
              <td style={{ padding: 12 }}>{u.r}</td>
              <td style={{ padding: 12 }}><span style={{ padding: '2px 8px', borderRadius: 12, fontSize: 11, background: u.s === 'active' ? '#d1fae5' : '#fef3c7', color: u.s === 'active' ? '#059669' : '#d97706' }}>{u.s}</span></td>
            </tr>
          ))}</tbody>
        </table>
      </main>
    </div>
  );
}
"""

_ECOMMERCE = """
function App() {
  const [cart, setCart] = useState([]);
  const task = "{task}";
  const products = [
    { id: 1, name: 'Наушники Pro', price: 4990, tag: 'Хит' },
    { id: 2, name: 'Клавиатура Mech', price: 7490, tag: 'New' },
    { id: 3, name: 'Монитор 27"', price: 24990, tag: '' },
  ];
  const add = (p) => setCart([...cart, p]);
  const total = cart.reduce((s, p) => s + p.price, 0);
  return (
    <div style={{ minHeight: '100vh', background: '#fafbfc', fontFamily: 'system-ui,sans-serif' }}>
      <header style={{ background: '#fff', padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }} role="banner">
        <strong style={{ color: '#4f7df3', fontSize: 18 }}>Shop</strong>
        <div aria-label={`Корзина: ${cart.length} товаров`} style={{ fontSize: 14 }}>🛒 {cart.length} · {total.toLocaleString('ru-RU')} ₽</div>
      </header>
      <main style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }} role="main">
        <h1 style={{ fontSize: 24, marginBottom: 4 }}>Каталог</h1>
        <p style={{ color: '#6b7280', fontSize: 13, marginBottom: 24 }}>{task}</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 16 }}>
          {products.map((p) => (
            <article key={p.id} style={{ background: '#fff', borderRadius: 14, overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
              <div style={{ height: 120, background: 'linear-gradient(135deg,#667eea,#764ba2)' }} aria-hidden="true" />
              <div style={{ padding: 16 }}>
                {p.tag && <span style={{ fontSize: 10, fontWeight: 700, color: '#4f7df3', textTransform: 'uppercase' }}>{p.tag}</span>}
                <h2 style={{ margin: '4px 0', fontSize: 15 }}>{p.name}</h2>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
                  <span style={{ fontWeight: 700, fontSize: 16 }}>{p.price.toLocaleString('ru-RU')} ₽</span>
                  <button onClick={() => add(p)} aria-label={`Добавить ${p.name} в корзину`} style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: '#4f7df3', color: '#fff', fontWeight: 600, cursor: 'pointer', fontSize: 12 }}>В корзину</button>
                </div>
              </div>
            </article>
          ))}
        </div>
        {cart.length > 0 && (
          <section aria-label="Оформление заказа" style={{ marginTop: 32, background: '#fff', borderRadius: 14, padding: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
            <h2 style={{ fontSize: 18, marginBottom: 12 }}>Checkout</h2>
            <p style={{ fontSize: 14, color: '#6b7280' }}>Итого: <strong>{total.toLocaleString('ru-RU')} ₽</strong> ({cart.length} шт.)</p>
            <button style={{ marginTop: 12, padding: '12px 28px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg,#6c63ff,#4f7df3)', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>Оплатить</button>
          </section>
        )}
      </main>
    </div>
  );
}
"""

_ADMIN = """
function App() {
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState([
    { id: 1, name: 'Запись A', status: 'active', updated: '12.06' },
    { id: 2, name: 'Запись B', status: 'draft', updated: '11.06' },
    { id: 3, name: 'Запись C', status: 'archived', updated: '10.06' },
  ]);
  const task = "{task}";
  const filtered = rows.filter((r) => r.name.toLowerCase().includes(query.toLowerCase()));
  const statusColor = { active: '#10b981', draft: '#f59e0b', archived: '#6b7280' };
  return (
    <div style={{ minHeight: '100vh', background: '#0f1117', color: '#e5e7eb', fontFamily: 'system-ui,sans-serif' }}>
      <header style={{ padding: '16px 24px', borderBottom: '1px solid #1f2937', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }} role="banner">
        <strong style={{ fontSize: 16 }}>Admin Panel</strong>
        <span style={{ fontSize: 12, color: '#6b7280' }}>role: admin</span>
      </header>
      <main style={{ padding: '24px' }} role="main">
        <h1 style={{ fontSize: 20, marginBottom: 4 }}>Записи</h1>
        <p style={{ fontSize: 13, color: '#9ca3af', marginBottom: 20 }}>{task}</p>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <input type="search" placeholder="Поиск…" aria-label="Поиск записей" value={query} onChange={(e) => setQuery(e.target.value)} style={{ flex: '1 1 200px', padding: '10px 14px', borderRadius: 8, border: '1px solid #374151', background: '#1a1d28', color: '#e5e7eb', fontSize: 14 }} />
          <button style={{ padding: '10px 20px', borderRadius: 8, border: 'none', background: '#4f7df3', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>+ Создать</button>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#1a1d28', borderRadius: 12, overflow: 'hidden' }} aria-label="Таблица записей">
          <thead><tr style={{ borderBottom: '1px solid #374151', color: '#9ca3af' }}>
            <th scope="col" style={{ textAlign: 'left', padding: 12 }}>ID</th>
            <th scope="col" style={{ textAlign: 'left', padding: 12 }}>Название</th>
            <th scope="col" style={{ textAlign: 'left', padding: 12 }}>Статус</th>
            <th scope="col" style={{ textAlign: 'left', padding: 12 }}>Обновлено</th>
          </tr></thead>
          <tbody>{filtered.map((r) => (
            <tr key={r.id} style={{ borderBottom: '1px solid #1f2937' }}>
              <td style={{ padding: 12 }}>{r.id}</td>
              <td style={{ padding: 12 }}>{r.name}</td>
              <td style={{ padding: 12 }}><span style={{ color: statusColor[r.status] }}>{r.status}</span></td>
              <td style={{ padding: 12, color: '#6b7280' }}>{r.updated}</td>
            </tr>
          ))}</tbody>
        </table>
      </main>
    </div>
  );
}
"""
