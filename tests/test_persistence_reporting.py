import json
from pathlib import Path

from repo_census.models import Commit, Repository, TrafficDay, TrafficResult
from repo_census.persistence import CensusStore
from repo_census.reporting import build_report, render_json, render_markdown


def populate(store: CensusStore, repository: Repository) -> None:
    run = store.start_run("2026-08-18T12:00:00Z", "denisecase", 365)
    with store.transaction():
        store.record_owner(run, "denisecase", "successful", 1)
        store.record_repository(run, "2026-08-18T12:01:00Z", repository)
        store.record_commits(run, repository.github_id, iter([
            Commit("abc", "denisecase", "2026-08-10T00:00:00Z", "2026-08-10T00:00:00Z")
        ]))
        store.set_commit_result(run, repository.github_id, "available")
        store.record_traffic(run, repository.github_id, "views", "2026-08-18T12:01:00Z", TrafficResult(
            "available", 10, 7, (
                TrafficDay("2026-08-17T00:00:00Z", 6, 5),
                TrafficDay("2026-08-18T00:00:00Z", 4, 4),
            )
        ))
        store.record_traffic(run, repository.github_id, "clones", "2026-08-18T12:01:00Z", TrafficResult(
            "forbidden", error="Must have push access"
        ))
    store.finish_run(run, "2026-08-18T12:02:00Z", "successful")


def test_history_and_commit_deduplication(tmp_path: Path, repository: Repository) -> None:
    with CensusStore(tmp_path / "census.db") as store:
        populate(store, repository)
        second = store.start_run("2026-08-19T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(second, "2026-08-19T12:01:00Z", repository)
            store.record_commits(second, repository.github_id, iter([
                Commit("abc", "denisecase", None, "2026-08-10T00:00:00Z")
            ]))
            store.set_commit_result(second, repository.github_id, "available")
            store.record_traffic(second, repository.github_id, "views", "2026-08-19T12:01:00Z", TrafficResult(
                "available", 12, 8, (TrafficDay("2026-08-18T00:00:00Z", 5, 4),)
            ))
        assert store.connection.execute(
            "SELECT COUNT(*) FROM repository_observations"
        ).fetchone()[0] == 2
        assert store.connection.execute("SELECT COUNT(*) FROM maintainer_commits").fetchone()[0] == 1
        assert store.connection.execute(
            "SELECT COUNT(*) FROM traffic_collection_results WHERE kind='views'"
        ).fetchone()[0] == 2


def test_reports_use_github_aggregate_uniques(tmp_path: Path, repository: Repository) -> None:
    with CensusStore(tmp_path / "census.db") as store:
        populate(store, repository)
        report = build_report(store)
    traffic = report["repositories"][0]["traffic"]["views"]
    assert traffic["aggregate_uniques"] == 7
    assert sum(day["uniques"] for day in traffic["daily"]) == 9
    assert report["repositories"][0]["maintainer_activity"]["commits_30_days"] == 1
    markdown = render_markdown(report)
    assert "7 unique (GitHub aggregate" in markdown
    assert "Clones: forbidden" in markdown
    assert json.loads(render_json(report))["generated_from_run"]["status"] == "successful"
