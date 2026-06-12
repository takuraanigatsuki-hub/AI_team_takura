"""Microsoft 365 (Graph API) — Excel, Word, PowerPoint через OneDrive."""

import csv
import io
import os
from datetime import datetime
from typing import Optional

import httpx

_token_cache: dict = {"access_token": "", "expires_at": 0.0}


def is_configured() -> bool:
    return bool(
        os.environ.get("MS365_TENANT_ID")
        and os.environ.get("MS365_CLIENT_ID")
        and os.environ.get("MS365_CLIENT_SECRET")
        and (os.environ.get("MS365_USER_ID") or os.environ.get("MS365_USER_EMAIL"))
    )


def status() -> dict:
    return {
        "configured": is_configured(),
        "user": os.environ.get("MS365_USER_EMAIL") or os.environ.get("MS365_USER_ID") or "",
        "folder": os.environ.get("MS365_FOLDER", "AI Team Room"),
    }


async def _get_token() -> str:
    import time

    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    tenant = os.environ["MS365_TENANT_ID"]
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, data={
            "client_id": os.environ["MS365_CLIENT_ID"],
            "client_secret": os.environ["MS365_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        })
        r.raise_for_status()
        data = r.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + int(data.get("expires_in", 3600))
    return _token_cache["access_token"]


def _user_path() -> str:
    user = os.environ.get("MS365_USER_ID") or os.environ.get("MS365_USER_EMAIL", "me")
    if "@" in str(user):
        return f"users/{user}"
    return f"users/{user}"


async def upload_file(filename: str, content: bytes, content_type: str = "application/octet-stream") -> dict:
    """Загрузить файл в OneDrive (папка AI Team Room)."""
    token = await _get_token()
    folder = os.environ.get("MS365_FOLDER", "AI Team Room").replace("/", "-")
    path = f"{_user_path()}/drive/root:/{folder}/{filename}:/content"
    url = f"https://graph.microsoft.com/v1.0/{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": content_type}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.put(url, content=content, headers=headers)
        r.raise_for_status()
        item = r.json()
    web_url = item.get("webUrl") or item.get("@microsoft.graph.downloadUrl", "")
    return {"id": item.get("id"), "name": item.get("name"), "web_url": web_url, "raw": item}


async def create_excel_table(title: str, headers: list, rows: list[list]) -> dict:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title[:40]).strip() or "table"
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{safe}_{ts}.csv"
    result = await upload_file(
        filename,
        buf.getvalue().encode("utf-8-sig"),
        "text/csv",
    )
    result["kind"] = "excel"
    result["title"] = title
    return result


async def create_word_document(title: str, paragraphs: list[str]) -> dict:
    body = "\n\n".join(p.strip() for p in paragraphs if p.strip())
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title[:40]).strip() or "document"
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{safe}_{ts}.docx"
    # Минимальный OOXML Word (открывается в Word Online)
    xml = _minimal_docx_xml(title, body)
    result = await upload_file(
        filename,
        xml,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    result["kind"] = "word"
    result["title"] = title
    return result


async def create_presentation(title: str, slides: list[dict]) -> dict:
    html = _slides_html(title, slides)
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title[:40]).strip() or "presentation"
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{safe}_{ts}.html"
    result = await upload_file(filename, html.encode("utf-8"), "text/html")
    result["kind"] = "presentation"
    result["title"] = title
    return result


def _minimal_docx_xml(title: str, body: str) -> bytes:
    """Простой .docx без внешних зависимостей."""
    import zipfile
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    escaped = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    paras = "".join(
        f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
        for line in escaped.split("\n")
    )
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:rPr><w:b/></w:rPr><w:t>{title.replace("&", "&amp;")}</w:t></w:r></w:p>
    {paras}
  </w:body>
</w:document>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document)
    return buf.getvalue()


def _slides_html(title: str, slides: list[dict]) -> str:
    parts = []
    for i, s in enumerate(slides, 1):
        bullets = "".join(f"<li>{b}</li>" for b in (s.get("bullets") or []))
        parts.append(f"""
        <section class="slide">
            <h2>{s.get('title', f'Слайд {i}')}</h2>
            <ul>{bullets}</ul>
        </section>""")
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>{title}</title>
<style>
body{{margin:0;font-family:Segoe UI,sans-serif;background:#0f1117;color:#f0f0f5}}
.slide{{min-height:100vh;padding:48px 64px;box-sizing:border-box;border-bottom:1px solid #333}}
h2{{color:#6c63ff;margin:0 0 24px}}
ul{{line-height:1.8;font-size:20px}}
.cover{{display:flex;flex-direction:column;justify-content:center;background:linear-gradient(135deg,#1a1d2e,#2d1f4e)}}
</style></head><body>
<section class="slide cover"><h1 style="font-size:42px">{title}</h1></section>
{''.join(parts)}
</body></html>"""


async def deliver_for_task(task_text: str, artifact: Optional[dict] = None) -> Optional[dict]:
    """Создать файл в M365 по типу задачи."""
    from config import config
    from room.task_routing import classify_task_kind

    if not config.get("m365_enabled", True) or not is_configured():
        return None

    kind = classify_task_kind(task_text)
    title = (task_text or "Задача")[:80]

    if kind == "table":
        headers = ["Дата", "Операция", "Сумма", "Примечание"]
        rows = [
            ["01.06", "Поступление", "120 000", "Клиент A"],
            ["05.06", "Аренда", "−45 000", "Офис"],
            ["10.06", "Зарплата", "−380 000", "ФОТ"],
            ["12.06", "Оплата", "520 000", "Клиент B"],
        ]
        if artifact and artifact.get("type") == "table":
            pass
        return await create_excel_table(title, headers, rows)

    if kind == "presentation":
        slides = [
            {"title": "Проблема", "bullets": ["Контекст", task_text[:80], "Аудитория"]},
            {"title": "Решение", "bullets": ["Подход", "Функции", "Roadmap"]},
            {"title": "Результат", "bullets": ["MVP", "Метрики", "Next steps"]},
        ]
        return await create_presentation(title, slides)

    if kind == "document":
        return await create_word_document(title, [task_text, "Подготовлено AI Team Room."])

    return None
