import os
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "sites")

_NAV_FIX_SCRIPT = """
<script>
document.addEventListener('click', function(e) {
  var a = e.target.closest('a');
  if (!a) return;
  var href = (a.getAttribute('href') || '').trim();
  if (!href || href === '#' || href === '/' || href === './' || href === '../') {
    e.preventDefault();
    return;
  }
  if (href.charAt(0) === '#' && href.length > 1) {
    e.preventDefault();
    try {
      var el = document.querySelector(href);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (_) {}
  }
}, true);
</script>
"""


def _sanitize_site_code(code: str) -> str:
    """Ссылки href=\"/\" и href=\"#\" не должны уводить на главную студию."""
    code = code.replace('href="/"', 'href="#top"')
    code = code.replace("href='/'", "href='#top'")
    code = code.replace('href="#"', 'href="#top"')
    code = code.replace("href='#'", "href='#top'")
    return code


def export_site_html(code: str, task: str, title: str = "Сайт") -> str:
    """Сохранить React-компонент как standalone HTML-файл."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:40].strip() or "site"
    filename = f"{safe_title.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(OUTPUT_DIR, filename)

    code = _sanitize_site_code(code)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<style>body{{margin:0}}#root{{min-height:100vh}}</style>
</head>
<body id="top">
<div id="root"></div>
<script type="text/babel" data-presets="react">
const {{ useState, useEffect }} = React;
{code}
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
</script>
{_NAV_FIX_SCRIPT}
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    latest = os.path.join(OUTPUT_DIR, "latest.html")
    with open(latest, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath
