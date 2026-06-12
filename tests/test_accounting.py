"""Тесты бухгалтерии — SQLite-таблицы и проводки."""

import os
import tempfile
import uuid

import pytest


@pytest.fixture
def accounting_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_accounting.sqlite"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    from room import accounting_db

    accounting_db.init_schema(seed_accounts=True)
    return accounting_db


def test_init_schema_creates_tables(accounting_db):
    status = accounting_db.schema_status()
    assert status["tables"]["accounting_accounts"] == 11
    assert status["tables"]["accounting_counterparties"] == 0
    assert status["tables"]["accounting_journal_entries"] == 0


def test_seed_runs_once(accounting_db):
    first = accounting_db.init_schema(seed_accounts=True)
    second = accounting_db.init_schema(seed_accounts=True)
    assert first["seeded_accounts"] == 11
    assert second["seeded_accounts"] == 0
    assert accounting_db.schema_status()["tables"]["accounting_accounts"] == 11


def test_create_account(accounting_db):
    account = accounting_db.create_account("10", "Материалы", "asset")
    assert account["code"] == "10"
    assert account["name_ru"] == "Материалы"
    assert account["account_type"] == "asset"


def test_create_counterparty(accounting_db):
    cp = accounting_db.create_counterparty(
        "ООО Ромашка",
        inn="7701234567",
        counterparty_type="supplier",
    )
    assert cp["name"] == "ООО Ромашка"
    assert cp["inn"] == "7701234567"


def test_journal_entry_balanced(accounting_db):
    accounts = accounting_db.list_accounts()
    cash = next(a for a in accounts if a["code"] == "50")
    sales = next(a for a in accounts if a["code"] == "90")

    entry = accounting_db.create_journal_entry(
        "2026-06-12",
        "Продажа за наличные",
        [
            {"account_id": cash["id"], "debit": 1000, "credit": 0},
            {"account_id": sales["id"], "debit": 0, "credit": 1000},
        ],
        post=True,
    )
    assert entry["status"] == "posted"
    assert entry["total_debit"] == 1000
    assert entry["total_credit"] == 1000
    assert len(entry["lines"]) == 2


def test_journal_entry_rejects_unbalanced(accounting_db):
    accounts = accounting_db.list_accounts()
    cash = next(a for a in accounts if a["code"] == "50")
    sales = next(a for a in accounts if a["code"] == "90")

    with pytest.raises(ValueError, match="не сбалансирована"):
        accounting_db.create_journal_entry(
            "2026-06-12",
            "Ошибка",
            [
                {"account_id": cash["id"], "debit": 1000, "credit": 0},
                {"account_id": sales["id"], "debit": 0, "credit": 500},
            ],
        )


def test_post_draft_entry(accounting_db):
    accounts = accounting_db.list_accounts()
    cash = next(a for a in accounts if a["code"] == "50")
    bank = next(a for a in accounts if a["code"] == "51")

    draft = accounting_db.create_journal_entry(
        "2026-06-12",
        "Перевод в банк",
        [
            {"account_id": bank["id"], "debit": 500, "credit": 0},
            {"account_id": cash["id"], "debit": 0, "credit": 500},
        ],
    )
    assert draft["status"] == "draft"

    posted = accounting_db.post_journal_entry(draft["id"])
    assert posted["status"] == "posted"


def test_account_balances(accounting_db):
    accounts = accounting_db.list_accounts()
    cash = next(a for a in accounts if a["code"] == "50")
    sales = next(a for a in accounts if a["code"] == "90")

    accounting_db.create_journal_entry(
        "2026-06-12",
        "Выручка",
        [
            {"account_id": cash["id"], "debit": 2500, "credit": 0},
            {"account_id": sales["id"], "debit": 0, "credit": 2500},
        ],
        post=True,
    )

    balances = {b["code"]: b for b in accounting_db.account_balances()}
    assert balances["50"]["balance"] == 2500
    assert balances["90"]["balance"] == -2500


@pytest.fixture
def client(accounting_db):
    from app import app
    from starlette.testclient import TestClient

    with TestClient(app, follow_redirects=True) as c:
        yield c


def _register_owner(client):
    from room.user_auth import ensure_owner

    email = f"acc-admin-{uuid.uuid4().hex[:8]}@test.com"
    user = ensure_owner(email, "ownerpass1", "Acc Admin")
    r = client.post("/api/auth/login", json={"email": email, "password": "ownerpass1"})
    assert r.status_code == 200
    return user, r.cookies


def test_api_accounting_accounts(client):
    _, cookies = _register_owner(client)
    r = client.get("/api/accounting/accounts", cookies=cookies)
    assert r.status_code == 200
    accounts = r.json()["accounts"]
    assert len(accounts) >= 11
    codes = {a["code"] for a in accounts}
    assert "50" in codes
    assert "90" in codes


def test_api_accounting_requires_admin(client):
    email = f"user-{uuid.uuid4().hex[:8]}@test.com"
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass1", "name": "User"},
    )
    assert reg.status_code == 200
    r = client.get("/api/accounting/accounts", cookies=reg.cookies)
    assert r.status_code == 403
