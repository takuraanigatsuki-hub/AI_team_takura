import os
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "sites")


def export_site_html(code: str, task: str, title: str = "Сайт") -> str:
    """Сохранить React-компонент как standalone HTML-файл."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:40].strip() or "site"
    filename = f"{safe_title.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(OUTPUT_DIR, filename)

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
<body>
<div id="root"></div>
<script type="text/babel" data-presets="react">
const {{ useState, useEffect }} = React;
{code}
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
</script>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    latest = os.path.join(OUTPUT_DIR, "latest.html")
    with open(latest, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath
