"""Права support на тикеты."""

import room.user_auth as ua


def test_support_can_manage_tickets():
    user = {"role": "support", "is_support": True, "privileges": ua.ROLE_PRIVILEGES["support"]}
    assert ua.can_manage_tickets(user) is True
    assert ua.can_access_support_panel(user) is True


def test_member_cannot_manage_tickets():
    user = {"role": "member", "privileges": []}
    assert ua.can_manage_tickets(user) is False
