"""Фильтрация GitHub/commit сообщений для обычных пользователей."""

from room.message_filter import should_show_message


def test_pr_ready_hidden_for_member():
    msg = {"type": "pr_ready", "message": "📦 Commit на GitHub: https://github.com/x/y"}
    viewer = {"role": "member", "user_id": "u1"}
    assert should_show_message(msg, viewer) is False


def test_pr_ready_visible_for_admin():
    msg = {"type": "pr_ready", "message": "📦 Commit на GitHub: https://github.com/x/y"}
    viewer = {"role": "admin", "user_id": "u1"}
    assert should_show_message(msg, viewer) is True


def test_support_cannot_see_commit_text():
    msg = {"type": "message", "message": "📦 Commit на GitHub: link"}
    viewer = {"role": "support", "user_id": "u1"}
    assert should_show_message(msg, viewer) is False
