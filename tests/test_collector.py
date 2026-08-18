from datetime import UTC, datetime
from pathlib import Path

from repo_census.collector import Collector
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
