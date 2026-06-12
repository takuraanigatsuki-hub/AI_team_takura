"""Бухгалтерия — SQLite-таблицы: план счетов, контрагенты, документы, проводки."""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator, Optional

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "..", "db", "accounting_schema.sql")

DEFAULT_ACCOUNTS = [
    ("50", "Касса", "asset"),
    ("51", "Расчётные счета", "asset"),
    ("60", "Расчёты с поставщиками", "liability"),
    ("62", "Расчёты с покупателями", "asset"),
    ("68", "Расчёты по налогам и сборам", "liability"),
    ("70", "Расчёты с персоналом по оплате труда", "liability"),
    ("80", "Уставный капитал", "equity"),
    ("84", "Нераспределённая прибыль (непокрытый убыток)", "equity"),
    ("90", "Продажи", "income"),
    ("91", "Прочие доходы и расходы", "expense"),
    ("99", "Прибыли и убытки", "equity"),
]


def _now() -> str:
    return datetime.now().isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def get_db_path() -> str:
  path = os.environ.get("SQLITE_DB_PATH", "data/ai_team.sqlite").strip()
  if not os.path.isabs(path):
    path = os.path.join(os.path.dirname(__file__), "..", path)
  return os.path.normpath(path)


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(*, seed_accounts: bool = True) -> dict:
    """Создаёт таблицы бухгалтерии и при необходимости заполняет план счетов."""
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with connect() as conn:
        conn.executescript(schema_sql)
        seeded = 0
        if seed_accounts:
            seeded = _seed_default_accounts(conn)

    return {
        "db_path": get_db_path(),
        "tables": [
            "accounting_accounts",
            "accounting_counterparties",
            "accounting_documents",
            "accounting_journal_entries",
            "accounting_journal_lines",
        ],
        "seeded_accounts": seeded,
    }


def _seed_default_accounts(conn: sqlite3.Connection) -> int:
    existing = conn.execute("SELECT COUNT(*) AS c FROM accounting_accounts").fetchone()["c"]
    if existing:
        return 0

    ts = _now()
    for code, name_ru, account_type in DEFAULT_ACCOUNTS:
        conn.execute(
            """
            INSERT INTO accounting_accounts
                (id, code, name_ru, account_type, parent_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, NULL, 1, ?, ?)
            """,
            (_uid("acc-"), code, name_ru, account_type, ts, ts),
        )
    return len(DEFAULT_ACCOUNTS)


def list_accounts(*, active_only: bool = True) -> list[dict]:
    query = "SELECT * FROM accounting_accounts"
    params: tuple = ()
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY code"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_account(account_id: str) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM accounting_accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def create_account(
    code: str,
    name_ru: str,
    account_type: str,
    *,
    parent_id: Optional[str] = None,
) -> dict:
    code = code.strip()
    name_ru = name_ru.strip()[:200]
    if account_type not in {"asset", "liability", "equity", "income", "expense"}:
        raise ValueError("Недопустимый тип счёта")
    if not code or not name_ru:
        raise ValueError("Код и название счёта обязательны")

    ts = _now()
    account_id = _uid("acc-")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO accounting_accounts
                (id, code, name_ru, account_type, parent_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (account_id, code, name_ru, account_type, parent_id, ts, ts),
        )
    account = get_account(account_id)
    assert account is not None
    return account


def list_counterparties(*, active_only: bool = True) -> list[dict]:
    query = "SELECT * FROM accounting_counterparties"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY name"
    with connect() as conn:
        rows = conn.execute(query).fetchall()
    return [_row_to_dict(r) for r in rows]


def create_counterparty(
    name: str,
    *,
    inn: str = "",
    counterparty_type: str = "both",
    email: str = "",
    phone: str = "",
) -> dict:
    name = name.strip()[:200]
    if not name:
        raise ValueError("Название контрагента обязательно")
    if counterparty_type not in {"client", "supplier", "both"}:
        raise ValueError("Недопустимый тип контрагента")

    ts = _now()
    cp_id = _uid("cp-")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO accounting_counterparties
                (id, name, inn, counterparty_type, email, phone, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (cp_id, name, inn.strip()[:20], counterparty_type, email[:120], phone[:40], ts, ts),
        )
    return get_counterparty(cp_id)  # type: ignore[return-value]


def get_counterparty(counterparty_id: str) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM accounting_counterparties WHERE id = ?",
            (counterparty_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def create_journal_entry(
    entry_date: str,
    description: str,
    lines: list[dict],
    *,
    document_id: Optional[str] = None,
    post: bool = False,
) -> dict:
    """Создаёт проводку. lines: [{account_id, debit, credit, description?}, ...]."""
    if len(lines) < 2:
        raise ValueError("Проводка должна содержать минимум две строки")

    total_debit = 0.0
    total_credit = 0.0
    normalized: list[dict] = []
    for i, line in enumerate(lines):
        account_id = line.get("account_id", "").strip()
        debit = float(line.get("debit") or 0)
        credit = float(line.get("credit") or 0)
        if not account_id:
            raise ValueError(f"Строка {i + 1}: не указан счёт")
        if debit < 0 or credit < 0:
            raise ValueError(f"Строка {i + 1}: суммы не могут быть отрицательными")
        if debit > 0 and credit > 0:
            raise ValueError(f"Строка {i + 1}: дебет и кредит одновременно заполнены")
        if debit == 0 and credit == 0:
            raise ValueError(f"Строка {i + 1}: укажите дебет или кредит")
        total_debit += debit
        total_credit += credit
        normalized.append({
            "account_id": account_id,
            "debit": round(debit, 2),
            "credit": round(credit, 2),
            "description": (line.get("description") or "")[:300],
            "line_order": i,
        })

    if round(total_debit, 2) != round(total_credit, 2):
        raise ValueError(
            f"Проводка не сбалансирована: дебет {total_debit:.2f}, кредит {total_credit:.2f}"
        )

    ts = _now()
    entry_id = _uid("je-")
    status = "posted" if post else "draft"

    with connect() as conn:
        account_ids = {line["account_id"] for line in normalized}
        placeholders = ",".join("?" * len(account_ids))
        found = conn.execute(
            f"SELECT id FROM accounting_accounts WHERE id IN ({placeholders}) AND is_active = 1",
            tuple(account_ids),
        ).fetchall()
        if len(found) != len(account_ids):
            raise ValueError("Один или несколько счетов не найдены")

        if document_id:
            doc = conn.execute(
                "SELECT id FROM accounting_documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            if not doc:
                raise ValueError("Документ не найден")

        conn.execute(
            """
            INSERT INTO accounting_journal_entries
                (id, document_id, entry_date, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (entry_id, document_id, entry_date, description[:500], status, ts, ts),
        )

        for line in normalized:
            conn.execute(
                """
                INSERT INTO accounting_journal_lines
                    (id, entry_id, account_id, debit, credit, description, line_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _uid("jl-"),
                    entry_id,
                    line["account_id"],
                    line["debit"],
                    line["credit"],
                    line["description"],
                    line["line_order"],
                    ts,
                ),
            )

    return get_journal_entry(entry_id)  # type: ignore[return-value]


def get_journal_entry(entry_id: str) -> Optional[dict]:
    with connect() as conn:
        entry = conn.execute(
            "SELECT * FROM accounting_journal_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if not entry:
            return None
        lines = conn.execute(
            """
            SELECT jl.*, a.code AS account_code, a.name_ru AS account_name
            FROM accounting_journal_lines jl
            JOIN accounting_accounts a ON a.id = jl.account_id
            WHERE jl.entry_id = ?
            ORDER BY jl.line_order
            """,
            (entry_id,),
        ).fetchall()

    result = _row_to_dict(entry)
    result["lines"] = [_row_to_dict(r) for r in lines]
    result["total_debit"] = round(sum(l["debit"] for l in result["lines"]), 2)
    result["total_credit"] = round(sum(l["credit"] for l in result["lines"]), 2)
    return result


def list_journal_entries(*, limit: int = 50, status: Optional[str] = None) -> list[dict]:
    limit = max(1, min(limit, 200))
    query = "SELECT * FROM accounting_journal_entries"
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY entry_date DESC, created_at DESC LIMIT ?"
    params.append(limit)

    with connect() as conn:
        rows = conn.execute(query, params).fetchall()

    entries = []
    for row in rows:
        entry = _row_to_dict(row)
        entry_id = entry["id"]
        with connect() as conn:
            lines = conn.execute(
                """
                SELECT jl.debit, jl.credit
                FROM accounting_journal_lines jl
                WHERE jl.entry_id = ?
                """,
                (entry_id,),
            ).fetchall()
        entry["total_debit"] = round(sum(r["debit"] for r in lines), 2)
        entry["total_credit"] = round(sum(r["credit"] for r in lines), 2)
        entry["line_count"] = len(lines)
        entries.append(entry)
    return entries


def post_journal_entry(entry_id: str) -> dict:
    entry = get_journal_entry(entry_id)
    if not entry:
        raise ValueError("Проводка не найдена")
    if entry["status"] == "posted":
        return entry
    if entry["status"] == "cancelled":
        raise ValueError("Отменённую проводку нельзя провести")
    if entry["total_debit"] != entry["total_credit"]:
        raise ValueError("Проводка не сбалансирована")

    ts = _now()
    with connect() as conn:
        conn.execute(
            "UPDATE accounting_journal_entries SET status = 'posted', updated_at = ? WHERE id = ?",
            (ts, entry_id),
        )
    return get_journal_entry(entry_id)  # type: ignore[return-value]


def account_balances() -> list[dict]:
    """Сальдо по счетам (только проведённые проводки)."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                a.id,
                a.code,
                a.name_ru,
                a.account_type,
                COALESCE(SUM(jl.debit), 0) AS total_debit,
                COALESCE(SUM(jl.credit), 0) AS total_credit
            FROM accounting_accounts a
            LEFT JOIN accounting_journal_lines jl ON jl.account_id = a.id
            LEFT JOIN accounting_journal_entries je ON je.id = jl.entry_id AND je.status = 'posted'
            WHERE a.is_active = 1
            GROUP BY a.id, a.code, a.name_ru, a.account_type
            ORDER BY a.code
            """
        ).fetchall()

    out = []
    for row in rows:
        item = _row_to_dict(row)
        debit = round(item["total_debit"], 2)
        credit = round(item["total_credit"], 2)
        item["balance"] = round(debit - credit, 2)
        out.append(item)
    return out


def schema_status() -> dict:
    """Статус таблиц бухгалтерии для health-check."""
    tables = [
        "accounting_accounts",
        "accounting_counterparties",
        "accounting_documents",
        "accounting_journal_entries",
        "accounting_journal_lines",
    ]
    counts: dict[str, int] = {}
    with connect() as conn:
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
                counts[table] = int(row["c"]) if row else 0
            except sqlite3.OperationalError:
                counts[table] = -1
    return {"db_path": get_db_path(), "tables": counts}
