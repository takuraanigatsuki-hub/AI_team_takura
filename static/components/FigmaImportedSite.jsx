/**
 * FigmaImportedSite — React UI по импортированному Figma Site.
 * Токены figmaTokens, task и fileName инжектируются из react_preview.py.
 */
function App() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const t = figmaTokens;
  const font = t.fontFamily || 'Inter, system-ui, sans-serif';

  const nav = ['Product', 'Features', 'Pricing', 'Resources'];
  const features = [
    { icon: '✦', title: 'Design tokens', desc: 'Цвета и типографика из Figma-макета' },
    { icon: '⚡', title: 'Auto layout', desc: 'Адаптивная сетка с spacing из макета' },
    { icon: '◈', title: 'Components', desc: 'Переиспользуемые UI-блоки как в Figma' },
  ];
  const logos = ['Acme', 'Boltshift', 'FeatherDev', 'GlobalBank', 'Layers'];

  const s = {
    page: { minHeight: '100vh', fontFamily: font, color: t.text, background: t.surface },
    header: {
      position: 'sticky', top: 0, zIndex: 20, background: 'rgba(255,255,255,0.92)',
      backdropFilter: 'blur(8px)', borderBottom: `1px solid ${t.border}`,
      padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    },
    brand: { fontSize: 18, fontWeight: 700, color: t.primary, letterSpacing: '-0.02em' },
    navLink: { color: t.mutedText, textDecoration: 'none', fontSize: 14, fontWeight: 500 },
    btnPrimary: {
      background: t.primary, color: '#fff', border: 'none', borderRadius: 8,
      padding: '10px 18px', fontWeight: 600, cursor: 'pointer', fontSize: 14,
    },
    btnGhost: {
      background: 'transparent', color: t.text, border: `1px solid ${t.border}`,
      borderRadius: 8, padding: '10px 18px', fontWeight: 600, cursor: 'pointer', fontSize: 14,
    },
    hero: {
      background: `linear-gradient(180deg, ${t.surfaceAlt} 0%, ${t.surface} 100%)`,
      padding: '72px 24px 56px', textAlign: 'center',
    },
    badge: {
      display: 'inline-block', background: t.primarySoft, color: t.primary,
      padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 600, marginBottom: 16,
    },
    h1: {
      fontSize: 'clamp(32px, 5vw, 56px)', fontWeight: 700, lineHeight: 1.1,
      margin: '0 0 16px', letterSpacing: '-0.03em', maxWidth: 760, marginLeft: 'auto', marginRight: 'auto',
    },
    lead: {
      fontSize: 18, color: t.mutedText, lineHeight: 1.6, maxWidth: 560,
      margin: '0 auto 32px',
    },
    section: { padding: '56px 24px', maxWidth: 1100, margin: '0 auto' },
    card: {
      background: t.surface, border: `1px solid ${t.border}`, borderRadius: 16,
      padding: 28, textAlign: 'left',
    },
    cta: {
      background: t.primary, color: '#fff', borderRadius: 16, padding: '48px 32px',
      textAlign: 'center', margin: '0 24px 56px', maxWidth: 1100, marginLeft: 'auto', marginRight: 'auto',
    },
    footer: {
      borderTop: `1px solid ${t.border}`, padding: '32px 24px',
      display: 'flex', flexWrap: 'wrap', gap: 16, justifyContent: 'space-between', alignItems: 'center',
      fontSize: 13, color: t.mutedText,
    },
  };

  return (
    <div style={s.page}>
      <header style={s.header}>
        <div style={s.brand}>{fileName}</div>
        <nav style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
          {nav.map((item) => (
            <a key={item} href="#" style={s.navLink}>{item}</a>
          ))}
        </nav>
        <div style={{ display: 'flex', gap: 10 }}>
          <button type="button" style={s.btnGhost}>Log in</button>
          <button type="button" style={s.btnPrimary}>Sign up</button>
        </div>
      </header>

      <section style={s.hero}>
        <span style={s.badge}>Imported from Figma · React</span>
        <h1 style={s.h1}>Build faster with design and code in sync</h1>
        <p style={s.lead}>{task}</p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button type="button" style={s.btnPrimary}>Get started</button>
          <button type="button" style={s.btnGhost}>View demo</button>
        </div>
      </section>

      <section style={{ ...s.section, paddingTop: 24 }}>
        <p style={{ textAlign: 'center', fontSize: 13, color: t.mutedText, marginBottom: 20 }}>
          Trusted by teams shipping with Figma
        </p>
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 24, justifyContent: 'center',
          color: t.mutedText, fontWeight: 600, fontSize: 15,
        }}>
          {logos.map((name) => (
            <span key={name}>{name}</span>
          ))}
        </div>
      </section>

      <section style={s.section}>
        <h2 style={{ textAlign: 'center', fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
          Everything you need
        </h2>
        <p style={{ textAlign: 'center', color: t.mutedText, marginBottom: 36, fontSize: 16 }}>
          Секции макета: {figmaFrames.join(' · ')}
        </p>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 20,
        }}>
          {features.map((f) => (
            <div key={f.title} style={s.card}>
              <div style={{
                width: 40, height: 40, borderRadius: 10, background: t.primarySoft,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 18, marginBottom: 16, color: t.primary,
              }}>
                {f.icon}
              </div>
              <h3 style={{ margin: '0 0 8px', fontSize: 17, fontWeight: 600 }}>{f.title}</h3>
              <p style={{ margin: 0, fontSize: 14, color: t.mutedText, lineHeight: 1.55 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section style={s.cta}>
        <h2 style={{ margin: '0 0 12px', fontSize: 28, fontWeight: 700 }}>Start building today</h2>
        <p style={{ margin: '0 0 24px', opacity: 0.9, fontSize: 16 }}>
          {submitted ? 'Thanks — we will be in touch!' : 'Get updates when the site goes live.'}
        </p>
        {!submitted && (
          <form
            onSubmit={(e) => { e.preventDefault(); if (email.trim()) setSubmitted(true); }}
            style={{ display: 'flex', gap: 8, justifyContent: 'center', maxWidth: 400, margin: '0 auto' }}
          >
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              style={{
                flex: 1, padding: '12px 14px', borderRadius: 8, border: 'none',
                fontSize: 14, minWidth: 0,
              }}
            />
            <button type="submit" style={{ ...s.btnPrimary, background: '#fff', color: t.primary }}>
              Subscribe
            </button>
          </form>
        )}
      </section>

      <footer style={s.footer}>
        <span>© 2026 {fileName} · AI Team Room</span>
        <div style={{ display: 'flex', gap: 20 }}>
          {['Privacy', 'Terms', 'Contact'].map((link) => (
            <a key={link} href="#" style={{ ...s.navLink, fontSize: 13 }}>{link}</a>
          ))}
        </div>
      </footer>
    </div>
  );
}
