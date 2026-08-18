"""Read-only GitHub REST API client."""

from collections.abc import Iterator
from datetime import datetime
from typing import Any, Self

import httpx

from .constants import AUTHENTICATED_OWNER, ORGANIZATION_ALLOWLIST
from .models import (
    Commit,
    PullRequest,
    PullRequestResult,
    Repository,
    TrafficDay,
    TrafficResult,
)


class GitHubError(RuntimeError):
    """A GitHub request or response was unusable."""


class GitHubClient:
    """Minimal client exposing only GET operations needed by the census."""

    def __init__(
        self,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
        base_url: str = "https://api.github.com",
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "repo-census/0.1",
            },
            timeout=30.0,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def authenticated_login(self) -> str:
        data = self._get_json("/user")
        return str(data["login"])

    def verify_identity(self) -> None:
        login = self.authenticated_login()
        if login.casefold() != AUTHENTICATED_OWNER.casefold():
            raise GitHubError(
                f"GITHUB_TOKEN authenticates as {login!r}; expected {AUTHENTICATED_OWNER!r}"
            )

    def repositories_for_owner(self, owner: str) -> list[Repository]:
        if owner == AUTHENTICATED_OWNER:
            values = self._paginate("/user/repos", {"affiliation": "owner", "sort": "full_name"})
        elif owner in ORGANIZATION_ALLOWLIST:
            values = self._paginate(f"/orgs/{owner}/repos", {"type": "all", "sort": "full_name"})
        else:
            raise ValueError(f"owner is not configured: {owner}")
        return [Repository.from_api(value) for value in values]

    def commits(
        self, repository: Repository, *, since: datetime
    ) -> Iterator[Commit]:
        if repository.default_branch is None:
            return iter(())
        try:
            values = self._paginate(
                f"/repos/{repository.full_name}/commits",
                {
                    "author": AUTHENTICATED_OWNER,
                    "sha": repository.default_branch,
                    "since": since.isoformat().replace("+00:00", "Z"),
                },
            )
        except GitHubError as exc:
            if "returned 409" in str(exc):
                return iter(())
            raise
        return (Commit.from_api(value) for value in values)

    def traffic(self, repository: Repository, kind: str) -> TrafficResult:
        if kind not in {"views", "clones"}:
            raise ValueError(f"unsupported traffic kind: {kind}")
        try:
            response = self._client.get(
                f"/repos/{repository.full_name}/traffic/{kind}", params={"per": "day"}
            )
        except httpx.HTTPError as exc:
            return TrafficResult(status="error", error=str(exc))
        if response.status_code == 403:
            return TrafficResult(status="forbidden", error=self._error_message(response))
        if response.status_code in {404, 422}:
            return TrafficResult(status="unavailable", error=self._error_message(response))
        try:
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return TrafficResult(status="error", error=str(exc))
        try:
            return TrafficResult(
                status="available",
                aggregate_count=int(data["count"]),
                aggregate_uniques=int(data["uniques"]),
                days=tuple(
                    TrafficDay(
                        timestamp=str(day["timestamp"]),
                        count=int(day["count"]),
                        uniques=int(day["uniques"]),
                    )
                    for day in data.get(kind, [])
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            return TrafficResult(status="error", error=f"invalid traffic response: {exc}")

    def open_pull_requests(self, repository: Repository) -> PullRequestResult:
        """Return every open pull request without modifying the repository."""
        try:
            values = self._paginate(
                f"/repos/{repository.full_name}/pulls",
                {"state": "open", "sort": "created", "direction": "asc"},
            )
            return PullRequestResult(
                status="available",
                pull_requests=tuple(PullRequest.from_api(value) for value in values),
            )
        except GitHubError as exc:
            message = str(exc)
            if "returned 403" in message:
                return PullRequestResult(status="forbidden", error=message)
            if "returned 404" in message or "returned 422" in message:
                return PullRequestResult(status="unavailable", error=message)
            return PullRequestResult(status="error", error=message)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            return PullRequestResult(status="error", error=str(exc))

    def _paginate(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self._client.get(path, params={**params, "per_page": "100", "page": str(page)})
            self._raise_for_status(response)
            values = response.json()
            if not isinstance(values, list):
                raise GitHubError(f"expected a list from {path}")
            output.extend(values)
            if len(values) < 100:
                return output
            page += 1

    def _get_json(self, path: str) -> dict[str, Any]:
        response = self._client.get(path)
        self._raise_for_status(response)
        value = response.json()
        if not isinstance(value, dict):
            raise GitHubError(f"expected an object from {path}")
        return value

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            remaining = response.headers.get("x-ratelimit-remaining")
            suffix = " (rate limit exhausted)" if remaining == "0" else ""
            raise GitHubError(
                f"GitHub API returned {response.status_code}: "
                f"{GitHubClient._error_message(response)}{suffix}"
            ) from exc

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            value = response.json()
            if isinstance(value, dict) and "message" in value:
                return str(value["message"])
        except ValueError:
            pass
        return response.reason_phrase
