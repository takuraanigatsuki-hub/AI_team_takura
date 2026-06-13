"""Тесты прав admin / tech_admin."""

import pytest


@pytest.fixture
def auth():
    import room.user_auth as ua
    return ua


def test_tech_admin_has_manage_users(auth):
    user = {"role": "tech_admin", "privileges": auth.ROLE_PRIVILEGES["tech_admin"]}
    assert auth.can_manage_users(user) is True


def test_tech_admin_cannot_assign_admin(auth):
    admin = {"role": "tech_admin", "privileges": auth.ROLE_PRIVILEGES["tech_admin"]}
    assert auth.can_assign_role(admin, "member") is True
    assert auth.can_assign_role(admin, "support") is True
    assert auth.can_assign_role(admin, "admin") is False
    assert auth.can_assign_role(admin, "owner") is False


def test_tech_admin_cannot_modify_admin_user(auth):
    admin = {"role": "tech_admin", "privileges": auth.ROLE_PRIVILEGES["tech_admin"]}
    target = {"role": "admin", "id": "x"}
    assert auth.can_modify_user(admin, target) is False


def test_owner_can_assign_any_role(auth):
    owner = {"role": "owner", "is_owner": True, "privileges": auth.ALL_PRIVILEGES}
    for role in auth.ROLE_PRIVILEGES:
        assert auth.can_assign_role(owner, role) is True


def test_admin_can_set_tier(auth):
    owner = {"role": "owner", "is_owner": True}
    admin = {"role": "admin"}
    member = {"role": "member"}
    assert auth.can_set_tier(owner) is True
    assert auth.can_set_tier(admin) is True
    assert auth.can_set_tier(member) is False
