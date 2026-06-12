"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient

    with TestClient(app, follow_redirects=True) as c:
        yield c
