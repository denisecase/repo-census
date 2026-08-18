"""Deterministic census report generation."""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from .persistence import CensusStore


def build_report(store: CensusStore) -> dict[str, Any]:
    run = store.connection.execute(
        "SELECT * FROM collection_runs WHERE status != 'running' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if run is None:
        raise ValueError("the census database has no completed collection runs")
    reference = datetime.fromisoformat(str(run["completed_at"]))
    owner_results = [dict(row) for row in store.connection.execute(
        "SELECT owner_login, status, repository_count, error "
        "FROM owner_collection_results WHERE run_id=? ORDER BY owner_login",
        (run["id"],),
    )]
    repositories: list[dict[str, Any]] = []
    rows = store.connection.execute(
        """SELECT r.github_id, o.* FROM repositories r
        JOIN repository_observations o ON o.repository_id=r.github_id
        WHERE o.run_id=?
        ORDER BY r.owner_login COLLATE NOCASE, r.name COLLATE NOCASE""",
        (run["id"],),
    )
    for row in rows:
        repository_id = int(row["github_id"])
        commit_summary = _commit_summary(store.connection, repository_id, reference)
        traffic = {
            kind: _traffic_for_run(store.connection, repository_id, kind, int(run["id"]))
            for kind in ("views", "clones")
        }
        repositories.append(
            {
                "owner": row["owner_login"],
                "name": row["name"],
                "full_name": row["full_name"],
                "url": row["html_url"],
                "visibility": row["visibility"],
                "private": bool(row["is_private"]),
                "archived": bool(row["is_archived"]),
                "disabled": bool(row["is_disabled"]),
                "fork": bool(row["is_fork"]),
                "default_branch": row["default_branch"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "pushed_at": row["pushed_at"],
                "observed_at": row["observed_at"],
                "permission_role": row["permission_role"],
                "permissions": json.loads(row["permissions_json"])
                if row["permissions_json"] else None,
                "commit_collection": {
                    "status": row["commit_status"], "error": row["commit_error"]
                },
                "maintainer_activity": commit_summary,
                "traffic": traffic,
            }
        )
    return {
        "generated_from_run": {
            "id": run["id"],
            "started_at": run["started_at"],
            "completed_at": run["completed_at"],
            "status": run["status"],
            "authenticated_login": run["authenticated_login"],
            "lookback_days": run["lookback_days"],
            "error": run["error"],
        },
        "owner_collection_results": owner_results,
        "repositories": repositories,
    }


def _commit_summary(
    connection: sqlite3.Connection, repository_id: int, reference: datetime
) -> dict[str, Any]:
    last = connection.execute(
        "SELECT MAX(committed_at) AS value FROM maintainer_commits WHERE repository_id=?",
        (repository_id,),
    ).fetchone()["value"]
    counts: dict[str, int] = {}
    for days in (30, 90, 365):
        threshold = (reference - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        counts[f"commits_{days}_days"] = int(connection.execute(
            "SELECT COUNT(*) AS value FROM maintainer_commits "
            "WHERE repository_id=? AND committed_at>=?",
            (repository_id, threshold),
        ).fetchone()["value"])
    days_since = None
    if last:
        commit_time = datetime.fromisoformat(str(last))
        days_since = max(0, (reference - commit_time).days)
    return {"last_commit_at": last, "days_since_last_commit": days_since, **counts}


def _traffic_for_run(
    connection: sqlite3.Connection, repository_id: int, kind: str, run_id: int
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM traffic_collection_results "
        "WHERE repository_id=? AND kind=? AND run_id=?",
        (repository_id, kind, run_id),
    ).fetchone()
    if row is None:
        return {"status": "not_collected"}
    days = [dict(day) for day in connection.execute(
        "SELECT traffic_at AS date, count, uniques FROM traffic_observations "
        "WHERE traffic_result_id=? ORDER BY traffic_at",
        (row["id"],),
    )]
    return {
        "status": row["status"],
        "observed_at": row["observed_at"],
        "aggregate_count": row["aggregate_count"],
        "aggregate_uniques": row["aggregate_uniques"],
        "error": row["error"],
        "daily": days,
    }


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    run = report["generated_from_run"]
    lines = [
        "# Repository Census",
        "",
        f"Collection run: {run['id']} ({run['status']})  ",
        f"Completed: {run['completed_at']}  ",
        f"Authenticated user: `{run['authenticated_login']}`",
        "",
        "Traffic unique values below are GitHub's aggregate values; daily unique values are not summed.",
        "",
    ]
    owner_results = report["owner_collection_results"]
    failures = [item for item in owner_results if item["status"] != "successful"]
    if failures:
        lines.extend(["## Owner collection warnings", ""])
        for item in failures:
            lines.append(f"- `{item['owner_login']}`: {item['status']} — {item['error']}")
        lines.append("")
    current_owner: str | None = None
    for repository in report["repositories"]:
        if repository["owner"] != current_owner:
            current_owner = repository["owner"]
            lines.extend([f"## {current_owner}", ""])
        flags = [
            flag for flag in ("private", "archived", "disabled", "fork") if repository[flag]
        ]
        suffix = f"; {', '.join(flags)}" if flags else ""
        lines.extend(
            [
                f"### [{repository['name']}]({repository['url']})",
                "",
                f"- Status: {repository['visibility']}{suffix}",
                f"- Permission: {repository['permission_role'] or 'not reported'}",
                f"- Pushed: {repository['pushed_at'] or 'never'}",
                _activity_line(repository["maintainer_activity"]),
                _traffic_line("Views", repository["traffic"]["views"]),
                _traffic_line("Clones", repository["traffic"]["clones"]),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _activity_line(activity: dict[str, Any]) -> str:
    return (
        f"- Maintainer commits: {activity['commits_30_days']} / "
        f"{activity['commits_90_days']} / {activity['commits_365_days']} "
        f"(30 / 90 / 365 days); latest: {activity['last_commit_at'] or 'none observed'}"
    )


def _traffic_line(label: str, traffic: dict[str, Any]) -> str:
    if traffic["status"] != "available":
        detail = f" — {traffic.get('error')}" if traffic.get("error") else ""
        return f"- {label}: {traffic['status']}{detail}"
    return (
        f"- {label}: {traffic['aggregate_count']} total, "
        f"{traffic['aggregate_uniques']} unique (GitHub aggregate; observed {traffic['observed_at']})"
    )
