"""Orchestrate a complete repository census."""

from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatchcase
from typing import Protocol

import httpx

from .constants import DEFAULT_OWNERS
from .github import GitHubError
from .models import Commit, PullRequestResult, Repository, TrafficResult, utc_text
from .persistence import CensusStore


class GitHubReader(Protocol):
    def verify_identity(self) -> None: ...
    def repositories_for_owner(self, owner: str) -> list[Repository]: ...
    def commits(self, repository: Repository, *, since: datetime) -> Iterator[Commit]: ...
    def traffic(self, repository: Repository, kind: str) -> TrafficResult: ...
    def open_pull_requests(self, repository: Repository) -> PullRequestResult: ...


class Collector:
    def __init__(
        self,
        github: GitHubReader,
        store: CensusStore,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.github = github
        self.store = store
        self.clock = clock

    def collect(
        self,
        *,
        lookback_days: int = 365,
        owners: Sequence[str] = DEFAULT_OWNERS,
        repo_pattern: str | None = None,
    ) -> int:
        self.github.verify_identity()
        started = self.clock()
        run_id = self.store.start_run(
            utc_text(started), "denisecase", lookback_days, repo_pattern
        )
        baseline = self.store.last_successful_started_at()
        since = started - timedelta(days=lookback_days)
        if baseline is not None:
            since = max(since, baseline - timedelta(days=1))
        partial = False
        try:
            for owner in owners:
                try:
                    repositories = self.github.repositories_for_owner(owner)
                except (GitHubError, httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                    partial = True
                    with self.store.transaction():
                        self.store.record_owner(run_id, owner, "error", error=str(exc))
                    continue
                if repo_pattern is not None:
                    repositories = [
                        repository
                        for repository in repositories
                        if fnmatchcase(repository.name, repo_pattern)
                    ]
                with self.store.transaction():
                    self.store.record_owner(run_id, owner, "successful", len(repositories))
                for repository in repositories:
                    observed_at = utc_text(self.clock())
                    with self.store.transaction():
                        self.store.record_repository(run_id, observed_at, repository)
                    try:
                        commits = self.github.commits(repository, since=since)
                        with self.store.transaction():
                            self.store.record_commits(run_id, repository.github_id, commits)
                            self.store.set_commit_result(run_id, repository.github_id, "available")
                    except (GitHubError, httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                        partial = True
                        with self.store.transaction():
                            self.store.set_commit_result(
                                run_id, repository.github_id, "error", str(exc)
                            )
                    try:
                        pull_requests = self.github.open_pull_requests(repository)
                    except (GitHubError, httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                        pull_requests = PullRequestResult("error", error=str(exc))
                    if pull_requests.status != "available":
                        partial = True
                    with self.store.transaction():
                        self.store.record_pull_requests(
                            run_id, repository, observed_at, pull_requests
                        )
                    for kind in ("views", "clones"):
                        result = self.github.traffic(repository, kind)
                        if result.status == "error":
                            partial = True
                        with self.store.transaction():
                            self.store.record_traffic(
                                run_id, repository.github_id, kind, observed_at, result
                            )
            self.store.finish_run(
                run_id, utc_text(self.clock()), "partial" if partial else "successful"
            )
        except Exception as exc:
            self.store.finish_run(run_id, utc_text(self.clock()), "failed", str(exc))
            raise
        return run_id
