from typing import Any

import pytest

from repo_census.models import Repository


@pytest.fixture
def repository_payload() -> dict[str, Any]:
    return {
        "id": 101,
        "node_id": "R_101",
        "owner": {"id": 1, "login": "denisecase", "type": "User"},
        "name": "example",
        "full_name": "denisecase/example",
        "html_url": "https://github.com/denisecase/example",
        "url": "https://api.github.com/repos/denisecase/example",
        "visibility": "public",
        "private": False,
        "archived": False,
        "disabled": False,
        "fork": False,
        "default_branch": "main",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2026-08-01T00:00:00Z",
        "pushed_at": "2026-08-10T00:00:00Z",
        "role_name": "admin",
        "permissions": {"admin": True, "push": True, "pull": True},
    }


@pytest.fixture
def repository(repository_payload: dict[str, Any]) -> Repository:
    return Repository.from_api(repository_payload)
