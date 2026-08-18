import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
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


def test_report_uses_only_selected_run_inventory_and_traffic(
    tmp_path: Path, repository: Repository
) -> None:
    removed = replace(repository, github_id=201, name="removed", full_name="denisecase/removed")
    current = replace(repository, github_id=202, name="current", full_name="denisecase/current")
    with CensusStore(tmp_path / "census.db") as store:
        first = store.start_run("2026-08-17T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(first, "2026-08-17T12:01:00Z", removed)
            store.set_commit_result(first, removed.github_id, "available")
            store.record_repository(first, "2026-08-17T12:01:00Z", current)
            store.set_commit_result(first, current.github_id, "available")
            store.record_traffic(first, current.github_id, "views", "2026-08-17T12:01:00Z", TrafficResult(
                "available", 99, 88
            ))
        store.finish_run(first, "2026-08-17T12:02:00Z", "successful")

        second = store.start_run("2026-08-18T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(second, "2026-08-18T12:01:00Z", current)
            store.set_commit_result(second, current.github_id, "available")
        store.finish_run(second, "2026-08-18T12:02:00Z", "failed", "interrupted")
        report = build_report(store)

    assert [item["name"] for item in report["repositories"]] == ["current"]
    assert report["repositories"][0]["traffic"]["views"] == {"status": "not_collected"}


def test_repository_identity_is_preserved_per_observation(
    tmp_path: Path, repository: Repository
) -> None:
    renamed = replace(
        repository,
        owner_login="new-owner",
        name="new-name",
        full_name="new-owner/new-name",
        html_url="https://github.com/new-owner/new-name",
        api_url="https://api.github.com/repos/new-owner/new-name",
    )
    with CensusStore(tmp_path / "census.db") as store:
        first = store.start_run("2026-08-17T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(first, "2026-08-17T12:01:00Z", repository)
        store.finish_run(first, "2026-08-17T12:02:00Z", "successful")
        second = store.start_run("2026-08-18T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(second, "2026-08-18T12:01:00Z", renamed)
        store.finish_run(second, "2026-08-18T12:02:00Z", "successful")
        rows = list(store.connection.execute(
            "SELECT owner_login,name,full_name,html_url,api_url "
            "FROM repository_observations ORDER BY run_id"
        ))
    assert tuple(rows[0]) == (
        "denisecase", "example", "denisecase/example",
        "https://github.com/denisecase/example",
        "https://api.github.com/repos/denisecase/example",
    )
    assert tuple(rows[1]) == (
        "new-owner", "new-name", "new-owner/new-name",
        "https://github.com/new-owner/new-name",
        "https://api.github.com/repos/new-owner/new-name",
    )


def test_commit_count_boundaries(tmp_path: Path, repository: Repository) -> None:
    completed = datetime(2026, 8, 18, 12, tzinfo=UTC)
    offsets = (30, 30.0001, 90, 90.0001, 365, 365.0001)
    commits = [
        Commit(
            f"sha-{index}", "denisecase", None,
            (completed - timedelta(days=offset)).isoformat().replace("+00:00", "Z"),
        )
        for index, offset in enumerate(offsets)
    ]
    with CensusStore(tmp_path / "census.db") as store:
        run = store.start_run("2025-08-18T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(run, "2026-08-18T12:01:00Z", repository)
            store.record_commits(run, repository.github_id, iter(commits))
            store.set_commit_result(run, repository.github_id, "available")
        store.finish_run(run, completed.isoformat().replace("+00:00", "Z"), "successful")
        activity = build_report(store)["repositories"][0]["maintainer_activity"]
    assert activity["commits_30_days"] == 1
    assert activity["commits_90_days"] == 3
    assert activity["commits_365_days"] == 5


def test_markdown_order_is_deterministic_by_owner_and_repository(
    tmp_path: Path, repository: Repository
) -> None:
    repositories = [
        replace(repository, github_id=301, owner_login="z-owner", name="b", full_name="z-owner/b"),
        replace(repository, github_id=302, owner_login="a-owner", name="z", full_name="a-owner/z"),
        replace(repository, github_id=303, owner_login="z-owner", name="a", full_name="z-owner/a"),
    ]
    with CensusStore(tmp_path / "census.db") as store:
        run = store.start_run("2026-08-18T12:00:00Z", "denisecase", 365)
        with store.transaction():
            for item in reversed(repositories):
                store.record_repository(run, "2026-08-18T12:01:00Z", item)
                store.set_commit_result(run, item.github_id, "available")
        store.finish_run(run, "2026-08-18T12:02:00Z", "successful")
        markdown = render_markdown(build_report(store))
    assert markdown.index("## a-owner") < markdown.index("## z-owner")
    assert markdown.index("[a](https://github.com/denisecase/example)") < markdown.index(
        "[b](https://github.com/denisecase/example)"
    )
