"""Тесты хранилища тикетов поддержки."""

import json
import os
import tempfile
import uuid

import pytest


@pytest.fixture
def ticket_env(monkeypatch):
    import room.ticket_store as ts
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(path)
    monkeypatch.setattr(ts, "TICKETS_FILE", path)
    yield ts


def test_create_and_list(ticket_env):
    ts = ticket_env
    t = ts.create_ticket(
        user_id="u1",
        user_email="a@test.com",
        user_name="Alice",
        subject="Help",
        message="Need help",
        category="other",
    )
    assert t["id"]
    assert t["status"] == "open"
    assert len(t["messages"]) == 1

    mine = ts.list_for_user("u1")
    assert len(mine) == 1
    assert mine[0]["subject"] == "Help"

    other = ts.list_for_user("u2")
    assert other == []


def test_support_reply(ticket_env):
    ts = ticket_env
    t = ts.create_ticket(
        user_id="u1",
        user_email="a@test.com",
        user_name="Alice",
        subject="Billing",
        message="Question",
    )
    updated = ts.add_message(
        t["id"],
        author_id="sup1",
        author_role="support",
        author_name="Support",
        text="We will check",
        is_solution=True,
    )
    assert updated["status"] == "in_progress"
    assert len(updated["messages"]) == 2
    assert updated["messages"][-1]["is_solution"] is True


def test_templates_exist(ticket_env):
    ts = ticket_env
    tpls = ts.list_templates()
    assert len(tpls) >= 5
    login = ts.get_template("login")
    assert login and login.get("solution")
