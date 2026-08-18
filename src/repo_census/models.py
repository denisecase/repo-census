"""Typed values passed between collection, persistence, and reporting."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Repository:
    """Repository metadata returned by GitHub."""

    github_id: int
    node_id: str | None
    owner_id: int
    owner_login: str
    owner_type: str
    name: str
    full_name: str
    html_url: str
    api_url: str
    visibility: str
    is_private: bool
    is_archived: bool
    is_disabled: bool
    is_fork: bool
    default_branch: str | None
    created_at: str
    updated_at: str
    pushed_at: str | None
    permission_role: str | None
    permissions: dict[str, bool] | None

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> Repository:
        owner = value["owner"]
        raw_permissions = value.get("permissions")
        permissions = None
        if isinstance(raw_permissions, dict):
            permissions = {
                key: bool(raw_permissions[key])
                for key in ("admin", "maintain", "push", "triage", "pull")
                if key in raw_permissions
            }
        return cls(
            github_id=int(value["id"]),
            node_id=value.get("node_id"),
            owner_id=int(owner["id"]),
            owner_login=str(owner["login"]),
            owner_type=str(owner.get("type", "Unknown")),
            name=str(value["name"]),
            full_name=str(value["full_name"]),
            html_url=str(value["html_url"]),
            api_url=str(value["url"]),
            visibility=str(value.get("visibility", "private" if value.get("private") else "public")),
            is_private=bool(value.get("private", False)),
            is_archived=bool(value.get("archived", False)),
            is_disabled=bool(value.get("disabled", False)),
            is_fork=bool(value.get("fork", False)),
            default_branch=value.get("default_branch"),
            created_at=str(value["created_at"]),
            updated_at=str(value["updated_at"]),
            pushed_at=value.get("pushed_at"),
            permission_role=value.get("role_name"),
            permissions=permissions,
        )


@dataclass(frozen=True)
class Commit:
    sha: str
    author_login: str | None
    authored_at: str | None
    committed_at: str

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> Commit:
        commit = value["commit"]
        author = value.get("author")
        return cls(
            sha=str(value["sha"]),
            author_login=author.get("login") if isinstance(author, dict) else None,
            authored_at=commit.get("author", {}).get("date"),
            committed_at=str(commit["committer"]["date"]),
        )


@dataclass(frozen=True)
class TrafficDay:
    timestamp: str
    count: int
    uniques: int


@dataclass(frozen=True)
class TrafficResult:
    status: str
    aggregate_count: int | None = None
    aggregate_uniques: int | None = None
    days: tuple[TrafficDay, ...] = ()
    error: str | None = None


DEPENDABOT_LOGINS = frozenset({"dependabot[bot]", "dependabot-preview[bot]"})


@dataclass(frozen=True)
class PullRequest:
    """An open pull request returned by GitHub."""

    number: int
    title: str
    author_login: str | None
    html_url: str
    created_at: str
    updated_at: str
    is_draft: bool
    is_dependabot: bool

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> PullRequest:
        author = value.get("user")
        author_login = author.get("login") if isinstance(author, dict) else None
        return cls(
            number=int(value["number"]),
            title=str(value["title"]),
            author_login=str(author_login) if author_login is not None else None,
            html_url=str(value["html_url"]),
            created_at=str(value["created_at"]),
            updated_at=str(value["updated_at"]),
            is_draft=bool(value.get("draft", False)),
            is_dependabot=(
                author_login.casefold() in DEPENDABOT_LOGINS
                if isinstance(author_login, str)
                else False
            ),
        )


@dataclass(frozen=True)
class PullRequestResult:
    """Availability and observations from an open-pull-request request."""

    status: str
    pull_requests: tuple[PullRequest, ...] = ()
    error: str | None = None


def utc_text(value: datetime) -> str:
    """Return a stable UTC ISO timestamp."""
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")
