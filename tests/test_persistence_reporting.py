import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from repo_census.models import (
    Commit,
    PullRequest,
    PullRequestResult,
    Repository,
    TrafficDay,
    TrafficResult,
)
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


def pull_request(
    number: int,
    *,
    author: str = "octocat",
    created_at: str = "2026-08-01T00:00:00Z",
    draft: bool = False,
    dependabot: bool = False,
) -> PullRequest:
    return PullRequest(
        number=number,
        title=f"Pull request {number}",
        author_login=author,
        html_url=f"https://github.com/denisecase/example/pull/{number}",
        created_at=created_at,
        updated_at="2026-08-17T00:00:00Z",
        is_draft=draft,
        is_dependabot=dependabot,
    )


def test_zero_pull_requests_is_distinct_from_unavailable(
    tmp_path: Path, repository: Repository
) -> None:
    unavailable = replace(
        repository, github_id=602, name="unavailable", full_name="denisecase/unavailable"
    )
    with CensusStore(tmp_path / "census.db") as store:
        run = store.start_run("2026-08-18T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(run, "2026-08-18T12:01:00Z", repository)
            store.record_pull_requests(
                run, repository, "2026-08-18T12:01:00Z", PullRequestResult("available")
            )
            store.record_repository(run, "2026-08-18T12:01:00Z", unavailable)
            store.record_pull_requests(
                run, unavailable, "2026-08-18T12:01:00Z",
                PullRequestResult("unavailable", error="not accessible"),
            )
        store.finish_run(run, "2026-08-18T12:02:00Z", "partial")
        repositories = build_report(store)["repositories"]
    assert repositories[0]["open_pull_requests"]["total_open"] == 0
    assert repositories[0]["open_pull_requests"]["status"] == "available"
    assert repositories[1]["open_pull_requests"]["total_open"] is None
    assert repositories[1]["open_pull_requests"]["status"] == "unavailable"


def test_pull_request_details_counts_oldest_age_and_rendering(
    tmp_path: Path, repository: Repository
) -> None:
    observations = (
        pull_request(9, draft=True),
        pull_request(
            2, author="dependabot[bot]", created_at="2026-06-18T12:00:00Z",
            dependabot=True,
        ),
        pull_request(5, author="renovate[bot]"),
    )
    with CensusStore(tmp_path / "census.db") as store:
        run = store.start_run("2026-08-18T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(run, "2026-08-18T12:01:00Z", repository)
            store.record_pull_requests(
                run, repository, "2026-08-18T12:01:00Z",
                PullRequestResult("available", observations),
            )
        store.finish_run(run, "2026-08-18T12:00:00Z", "successful")
        report = build_report(store)
    result = report["repositories"][0]["open_pull_requests"]
    assert result["total_open"] == 3
    assert result["dependabot_open"] == 1
    assert result["oldest_open_age_days"] == 61
    assert [item["number"] for item in result["pull_requests"]] == [2, 5, 9]
    assert result["pull_requests"][-1]["draft"] is True
    assert report["open_pull_request_summary"][0]["full_name"] == "denisecase/example"
    json_summary = json.loads(render_json(report))["open_pull_request_summary"]
    assert json_summary[0]["dependabot_open"] == 1
    markdown = render_markdown(report)
    assert "## Open Pull Request Summary" in markdown
    assert "3 total; 1 Dependabot; oldest: 61 days" in markdown
    assert "[#2: Pull request 2]" in markdown


def test_pull_request_summary_order_is_deterministic(
    tmp_path: Path, repository: Repository
) -> None:
    repositories = [
        replace(repository, github_id=701, owner_login="z", name="human", full_name="z/human"),
        replace(repository, github_id=702, owner_login="z", name="bot-new", full_name="z/bot-new"),
        replace(repository, github_id=703, owner_login="a", name="bot-old", full_name="a/bot-old"),
        replace(repository, github_id=704, owner_login="b", name="bot-old", full_name="b/bot-old"),
    ]
    created = (
        "2026-05-01T00:00:00Z",
        "2026-08-01T00:00:00Z",
        "2026-06-01T00:00:00Z",
        "2026-06-01T00:00:00Z",
    )
    with CensusStore(tmp_path / "census.db") as store:
        run = store.start_run("2026-08-18T12:00:00Z", "denisecase", 365)
        with store.transaction():
            for index, item in enumerate(repositories):
                store.record_repository(run, "2026-08-18T12:01:00Z", item)
                is_bot = index > 0
                store.record_pull_requests(
                    run, item, "2026-08-18T12:01:00Z",
                    PullRequestResult("available", (
                        pull_request(
                            index + 1, created_at=created[index], dependabot=is_bot,
                            author="dependabot[bot]" if is_bot else "octocat",
                        ),
                    )),
                )
        store.finish_run(run, "2026-08-18T12:02:00Z", "successful")
        summary = build_report(store)["open_pull_request_summary"]
    assert [item["full_name"] for item in summary] == [
        "a/bot-old", "b/bot-old", "z/bot-new", "z/human"
    ]


def test_open_pull_request_observations_are_run_specific(
    tmp_path: Path, repository: Repository
) -> None:
    with CensusStore(tmp_path / "census.db") as store:
        first = store.start_run("2026-08-17T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(first, "2026-08-17T12:01:00Z", repository)
            store.record_pull_requests(
                first, repository, "2026-08-17T12:01:00Z",
                PullRequestResult("available", (pull_request(1),)),
            )
        store.finish_run(first, "2026-08-17T12:02:00Z", "successful")

        second = store.start_run("2026-08-18T12:00:00Z", "denisecase", 365)
        with store.transaction():
            store.record_repository(second, "2026-08-18T12:01:00Z", repository)
            store.record_pull_requests(
                second, repository, "2026-08-18T12:01:00Z", PullRequestResult("available")
            )
        store.finish_run(second, "2026-08-18T12:02:00Z", "successful")
        report = build_report(store)
        historical_count = store.connection.execute(
            "SELECT COUNT(*) FROM open_pull_request_observations"
        ).fetchone()[0]
    assert historical_count == 1
    assert report["repositories"][0]["open_pull_requests"]["total_open"] == 0
    assert report["open_pull_request_summary"] == []


def test_version_1_database_migrates_without_losing_history(
    tmp_path: Path, repository: Repository
) -> None:
    database = tmp_path / "census.db"
    with CensusStore(database) as store:
        populate(store, repository)
        store.connection.execute("DROP TABLE open_pull_request_observations")
        store.connection.execute("DROP TABLE pull_request_collection_results")
        store.connection.execute(
            "UPDATE schema_metadata SET value='1' WHERE key='schema_version'"
        )
        store.connection.commit()
    with CensusStore(database) as migrated:
        report = build_report(migrated)
        version = migrated.connection.execute(
            "SELECT value FROM schema_metadata WHERE key='schema_version'"
        ).fetchone()[0]
    assert version == "4"
    assert report["repositories"][0]["name"] == "example"
    assert report["repositories"][0]["open_pull_requests"]["status"] == "not_collected"
