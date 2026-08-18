from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from repo_census.collector import Collector
from repo_census.constants import DEFAULT_OWNERS
from repo_census.github import GitHubError
from repo_census.models import Commit, Repository, TrafficResult
from repo_census.persistence import CensusStore


class FakeGitHub:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self.since: list[datetime] = []

    def verify_identity(self) -> None:
        return None

    def repositories_for_owner(self, owner: str) -> list[Repository]:
        if owner == "broken-org":
            raise GitHubError("owner unavailable")
        return [self.repository]

    def commits(self, repository: Repository, *, since: datetime):
        self.since.append(since)
        return iter([Commit("abc", "denisecase", None, "2026-08-10T00:00:00Z")])

    def traffic(self, repository: Repository, kind: str) -> TrafficResult:
        return TrafficResult("forbidden", error="no traffic permission")


class OwnerTrackingGitHub(FakeGitHub):
    def __init__(self, repository: Repository) -> None:
        super().__init__(repository)
        self.owners: list[str] = []

    def repositories_for_owner(self, owner: str) -> list[Repository]:
        self.owners.append(owner)
        return []


class RepositoryFailureGitHub(FakeGitHub):
    def __init__(self, repositories: list[Repository]) -> None:
        super().__init__(repositories[0])
        self.repositories = repositories
        self.commit_attempts: list[str] = []

    def repositories_for_owner(self, owner: str) -> list[Repository]:
        return self.repositories

    def commits(self, repository: Repository, *, since: datetime):
        self.commit_attempts.append(repository.full_name)
        if repository.name == "broken":
            raise GitHubError("commit unavailable")
        return super().commits(repository, since=since)


def test_collector_keeps_repository_when_traffic_is_forbidden(
    tmp_path: Path, repository: Repository
) -> None:
    github = FakeGitHub(repository)
    now = datetime(2026, 8, 18, 12, tzinfo=UTC)
    with CensusStore(tmp_path / "census.db") as store:
        run = Collector(github, store, clock=lambda: now).collect(owners=("denisecase",))
        assert store.connection.execute("SELECT status FROM collection_runs WHERE id=?", (run,)).fetchone()[0] == "successful"
        assert store.connection.execute("SELECT COUNT(*) FROM repositories").fetchone()[0] == 1
        statuses = [row[0] for row in store.connection.execute(
            "SELECT status FROM traffic_collection_results ORDER BY kind"
        )]
        assert statuses == ["forbidden", "forbidden"]


def test_owner_failure_produces_partial_run(tmp_path: Path, repository: Repository) -> None:
    now = datetime(2026, 8, 18, 12, tzinfo=UTC)
    with CensusStore(tmp_path / "census.db") as store:
        run = Collector(FakeGitHub(repository), store, clock=lambda: now).collect(
            owners=("denisecase", "broken-org")
        )
        assert store.connection.execute("SELECT status FROM collection_runs WHERE id=?", (run,)).fetchone()[0] == "partial"
        assert store.connection.execute(
            "SELECT error FROM owner_collection_results WHERE owner_login='broken-org'"
        ).fetchone()[0] == "owner unavailable"


def test_default_collection_traverses_exact_configured_owners(
    tmp_path: Path, repository: Repository
) -> None:
    github = OwnerTrackingGitHub(repository)
    now = datetime(2026, 8, 18, 12, tzinfo=UTC)
    with CensusStore(tmp_path / "census.db") as store:
        Collector(github, store, clock=lambda: now).collect()
    assert tuple(github.owners) == DEFAULT_OWNERS
    assert len(github.owners) == 22
    assert len(set(github.owners)) == 22


def test_incremental_collection_uses_successful_baseline_with_overlap(
    tmp_path: Path, repository: Repository
) -> None:
    github = FakeGitHub(repository)
    with CensusStore(tmp_path / "census.db") as store:
        first = datetime(2026, 8, 1, 12, tzinfo=UTC)
        Collector(github, store, clock=lambda: first).collect(owners=("denisecase",))
        second = datetime(2026, 8, 10, 12, tzinfo=UTC)
        Collector(github, store, clock=lambda: second).collect(owners=("denisecase",))
    assert github.since == [
        datetime(2025, 8, 1, 12, tzinfo=UTC),
        datetime(2026, 7, 31, 12, tzinfo=UTC),
    ]


def test_owner_failure_does_not_prevent_later_owner(
    tmp_path: Path, repository: Repository
) -> None:
    now = datetime(2026, 8, 18, 12, tzinfo=UTC)
    with CensusStore(tmp_path / "census.db") as store:
        run = Collector(FakeGitHub(repository), store, clock=lambda: now).collect(
            owners=("broken-org", "denisecase")
        )
        result = store.connection.execute(
            "SELECT status FROM owner_collection_results "
            "WHERE run_id=? AND owner_login='denisecase'", (run,)
        ).fetchone()
        assert result["status"] == "successful"
        assert store.connection.execute(
            "SELECT COUNT(*) FROM repository_observations WHERE run_id=?", (run,)
        ).fetchone()[0] == 1


def test_repository_failure_does_not_prevent_later_repository(
    tmp_path: Path, repository_payload: dict[str, object]
) -> None:
    broken_payload = {**repository_payload, "id": 201, "name": "broken", "full_name": "denisecase/broken"}
    good_payload = {**repository_payload, "id": 202, "name": "good", "full_name": "denisecase/good"}
    github = RepositoryFailureGitHub([
        Repository.from_api(broken_payload), Repository.from_api(good_payload)
    ])
    now = datetime(2026, 8, 18, 12, tzinfo=UTC)
    with CensusStore(tmp_path / "census.db") as store:
        run = Collector(github, store, clock=lambda: now).collect(owners=("denisecase",))
        statuses = [row["commit_status"] for row in store.connection.execute(
            "SELECT commit_status FROM repository_observations WHERE run_id=? ORDER BY repository_id",
            (run,),
        )]
        assert store.connection.execute(
            "SELECT status FROM collection_runs WHERE id=?", (run,)
        ).fetchone()[0] == "partial"
    assert statuses == ["error", "available"]
    assert github.commit_attempts == ["denisecase/broken", "denisecase/good"]


def test_traffic_error_causes_partial_run(tmp_path: Path, repository: Repository) -> None:
    class TrafficErrorGitHub(FakeGitHub):
        def traffic(self, repository: Repository, kind: str) -> TrafficResult:
            if kind == "views":
                return TrafficResult("error", error="offline")
            return TrafficResult("available", 0, 0)

    now = datetime(2026, 8, 18, 12, tzinfo=UTC)
    with CensusStore(tmp_path / "census.db") as store:
        run = Collector(
            TrafficErrorGitHub(repository), store, clock=lambda: now
        ).collect(owners=("denisecase",))
        assert store.connection.execute(
            "SELECT status FROM collection_runs WHERE id=?", (run,)
        ).fetchone()[0] == "partial"


@pytest.mark.parametrize(
    ("repo_pattern", "expected"),
    [
        ("datafun-*", ["datafun-one"]),
        ("missing-*", []),
        (None, ["datafun-one", "other"]),
    ],
    ids=("matching", "nonmatching", "omitted"),
)
def test_repository_name_pattern_filter(
    tmp_path: Path,
    repository: Repository,
    repo_pattern: str | None,
    expected: list[str],
) -> None:
    repositories = [
        replace(
            repository,
            github_id=401,
            name="datafun-one",
            full_name="denisecase/datafun-one",
        ),
        replace(
            repository,
            github_id=402,
            name="other",
            full_name="denisecase/other",
        ),
    ]
    github = RepositoryFailureGitHub(repositories)
    now = datetime(2026, 8, 18, 12, tzinfo=UTC)
    with CensusStore(tmp_path / "census.db") as store:
        run = Collector(github, store, clock=lambda: now).collect(
            owners=("denisecase",), repo_pattern=repo_pattern
        )
        names = [row["name"] for row in store.connection.execute(
            "SELECT name FROM repository_observations WHERE run_id=? ORDER BY name", (run,)
        )]
        stored_pattern = store.connection.execute(
            "SELECT repo_pattern FROM collection_runs WHERE id=?", (run,)
        ).fetchone()[0]
    assert names == expected
    assert stored_pattern == repo_pattern
