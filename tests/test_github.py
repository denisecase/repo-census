from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from repo_census.constants import ORGANIZATION_ALLOWLIST
from repo_census.github import GitHubClient, GitHubError
from repo_census.models import Repository


def client(handler: Any) -> GitHubClient:
    return GitHubClient("secret", transport=httpx.MockTransport(handler))


def test_organization_allowlist_is_exact() -> None:
    assert ORGANIZATION_ALLOWLIST == (
        "aauw-ely", "adaptive-interfaces", "analytics-toolworks", "applied-models",
        "civic-interconnect", "composable-data", "denisecase-org", "ely-has-pride",
        "ely-monday", "elytc", "genealogy-clusiau", "genealogy-hall",
        "genealogy-johnson", "genealogy-kokkinen", "humanity-lab",
        "kapsch-genealogy", "mn-area35-d08", "pup-pack", "structural-explainability",
        "toy-gpt", "wmnlp-materials",
    )


def test_verify_identity_requires_denisecase() -> None:
    github = client(lambda request: httpx.Response(200, json={"login": "someone-else"}))
    with pytest.raises(GitHubError, match="expected 'denisecase'"):
        github.verify_identity()


def test_repository_discovery_uses_only_configured_endpoints(
    repository_payload: dict[str, Any],
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[repository_payload])

    github = client(handler)
    assert github.repositories_for_owner("denisecase")[0].permission_role == "admin"
    github.repositories_for_owner(ORGANIZATION_ALLOWLIST[0])
    assert requests[0].url.path == "/user/repos"
    assert requests[0].url.params["affiliation"] == "owner"
    assert requests[1].url.path == f"/orgs/{ORGANIZATION_ALLOWLIST[0]}/repos"
    with pytest.raises(ValueError, match="not configured"):
        github.repositories_for_owner("unlisted-org")


def test_repository_discovery_paginates(repository_payload: dict[str, Any]) -> None:
    requested_pages: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params["page"]
        requested_pages.append(page)
        values = [repository_payload] * 100 if page == "1" else [repository_payload]
        return httpx.Response(200, json=values)

    repositories = client(handler).repositories_for_owner("denisecase")
    assert len(repositories) == 101
    assert requested_pages == ["1", "2"]


def test_commits_are_filtered_by_author_and_default_branch(
    repository: Repository,
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{
            "sha": "abc",
            "author": {"login": "denisecase"},
            "commit": {
                "author": {"date": "2026-08-01T00:00:00Z"},
                "committer": {"date": "2026-08-01T01:00:00Z"},
            },
        }])

    commits = list(client(handler).commits(repository, since=datetime(2026, 1, 1, tzinfo=UTC)))
    assert commits[0].sha == "abc"
    assert seen[0].url.params["author"] == "denisecase"
    assert seen[0].url.params["sha"] == "main"


def test_empty_repository_has_no_commits(repository: Repository) -> None:
    github = client(
        lambda request: httpx.Response(409, json={"message": "Git Repository is empty."})
    )
    assert list(github.commits(repository, since=datetime(2026, 1, 1, tzinfo=UTC))) == []


def test_traffic_preserves_aggregate_and_daily_values(repository: Repository) -> None:
    github = client(lambda request: httpx.Response(200, json={
        "count": 10,
        "uniques": 7,
        "views": [
            {"timestamp": "2026-08-17T00:00:00Z", "count": 6, "uniques": 5},
            {"timestamp": "2026-08-18T00:00:00Z", "count": 4, "uniques": 4},
        ],
    }))
    result = github.traffic(repository, "views")
    assert result.aggregate_count == 10
    assert result.aggregate_uniques == 7
    assert sum(day.uniques for day in result.days) == 9  # Deliberately differs from aggregate.


@pytest.mark.parametrize(
    ("status_code", "status"), [(403, "forbidden"), (404, "unavailable"), (422, "unavailable")]
)
def test_traffic_permission_states(
    repository: Repository, status_code: int, status: str
) -> None:
    github = client(
        lambda request: httpx.Response(status_code, json={"message": "not accessible"})
    )
    result = github.traffic(repository, "clones")
    assert result.status == status
    assert result.error == "not accessible"


def test_traffic_transport_failure_is_recorded(repository: Repository) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    result = client(fail).traffic(repository, "views")
    assert result.status == "error"
    assert result.error == "offline"


def test_malformed_traffic_response_is_recorded(repository: Repository) -> None:
    result = client(
        lambda request: httpx.Response(200, json={"count": 3, "views": []})
    ).traffic(repository, "views")
    assert result.status == "error"
    assert result.error is not None
    assert result.error.startswith("invalid traffic response:")


def pull_request_payload(
    number: int = 1,
    *,
    login: str | None = "octocat",
    draft: bool = False,
) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Pull request {number}",
        "user": {"login": login} if login is not None else None,
        "html_url": f"https://github.com/denisecase/example/pull/{number}",
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-08-01T00:00:00Z",
        "draft": draft,
    }


def test_open_pull_requests_use_open_state_and_paginate(repository: Repository) -> None:
    requested_pages: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/denisecase/example/pulls"
        assert request.url.params["state"] == "open"
        page = request.url.params["page"]
        requested_pages.append(page)
        values = [pull_request_payload(index) for index in range(1, 101)]
        if page == "2":
            values = [pull_request_payload(101, draft=True)]
        return httpx.Response(200, json=values)

    result = client(handler).open_pull_requests(repository)
    assert result.status == "available"
    assert len(result.pull_requests) == 101
    assert result.pull_requests[-1].is_draft is True
    assert requested_pages == ["1", "2"]


@pytest.mark.parametrize(
    ("login", "expected"),
    [
        ("dependabot[bot]", True),
        ("Dependabot-Preview[bot]", True),
        ("renovate[bot]", False),
        ("octocat", False),
        (None, False),
    ],
)
def test_dependabot_is_derived_only_from_author_identity(
    repository: Repository, login: str | None, expected: bool
) -> None:
    result = client(
        lambda request: httpx.Response(200, json=[pull_request_payload(login=login)])
    ).open_pull_requests(repository)
    pull_request = result.pull_requests[0]
    assert pull_request.author_login == login
    assert pull_request.is_dependabot is expected


@pytest.mark.parametrize(
    ("status_code", "status"),
    [(403, "forbidden"), (404, "unavailable"), (422, "unavailable"), (500, "error")],
)
def test_pull_request_collection_statuses(
    repository: Repository, status_code: int, status: str
) -> None:
    result = client(
        lambda request: httpx.Response(status_code, json={"message": "not accessible"})
    ).open_pull_requests(repository)
    assert result.status == status
    assert result.error is not None


def test_pull_request_transport_failure_is_recorded(repository: Repository) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    result = client(fail).open_pull_requests(repository)
    assert result.status == "error"
    assert result.error == "offline"
