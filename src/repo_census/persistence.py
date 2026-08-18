"""Append-oriented SQLite persistence for census observations."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Self

from .models import Commit, PullRequestResult, Repository, TrafficResult

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO schema_metadata(key, value) VALUES ('schema_version', '4');

CREATE TABLE IF NOT EXISTS collection_runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('running', 'successful', 'partial', 'failed')),
    authenticated_login TEXT NOT NULL,
    lookback_days INTEGER NOT NULL,
    repo_pattern TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS owner_collection_results (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES collection_runs(id),
    owner_login TEXT NOT NULL,
    status TEXT NOT NULL,
    repository_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    UNIQUE(run_id, owner_login)
);
CREATE TABLE IF NOT EXISTS repositories (
    github_id INTEGER PRIMARY KEY,
    node_id TEXT,
    owner_id INTEGER NOT NULL,
    owner_login TEXT NOT NULL,
    owner_type TEXT NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL UNIQUE,
    html_url TEXT NOT NULL,
    api_url TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS repository_observations (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES collection_runs(id),
    repository_id INTEGER NOT NULL REFERENCES repositories(github_id),
    observed_at TEXT NOT NULL,
    owner_login TEXT NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    html_url TEXT NOT NULL,
    api_url TEXT NOT NULL,
    visibility TEXT NOT NULL,
    is_private INTEGER NOT NULL,
    is_archived INTEGER NOT NULL,
    is_disabled INTEGER NOT NULL,
    is_fork INTEGER NOT NULL,
    default_branch TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    pushed_at TEXT,
    permission_role TEXT,
    permissions_json TEXT,
    commit_status TEXT NOT NULL,
    commit_error TEXT,
    UNIQUE(run_id, repository_id)
);
CREATE TABLE IF NOT EXISTS maintainer_commits (
    repository_id INTEGER NOT NULL REFERENCES repositories(github_id),
    sha TEXT NOT NULL,
    author_login TEXT,
    authored_at TEXT,
    committed_at TEXT NOT NULL,
    first_observed_run_id INTEGER NOT NULL REFERENCES collection_runs(id),
    PRIMARY KEY(repository_id, sha)
);
CREATE TABLE IF NOT EXISTS traffic_collection_results (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES collection_runs(id),
    repository_id INTEGER NOT NULL REFERENCES repositories(github_id),
    kind TEXT NOT NULL CHECK(kind IN ('views', 'clones')),
    observed_at TEXT NOT NULL,
    status TEXT NOT NULL,
    aggregate_count INTEGER,
    aggregate_uniques INTEGER,
    error TEXT,
    UNIQUE(run_id, repository_id, kind)
);
CREATE TABLE IF NOT EXISTS traffic_observations (
    id INTEGER PRIMARY KEY,
    traffic_result_id INTEGER NOT NULL REFERENCES traffic_collection_results(id),
    traffic_at TEXT NOT NULL,
    count INTEGER NOT NULL,
    uniques INTEGER NOT NULL,
    UNIQUE(traffic_result_id, traffic_at)
);
CREATE TABLE IF NOT EXISTS pull_request_collection_results (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES collection_runs(id),
    repository_id INTEGER NOT NULL REFERENCES repositories(github_id),
    observed_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('available', 'forbidden', 'unavailable', 'error')),
    open_count INTEGER,
    error TEXT,
    UNIQUE(run_id, repository_id)
);
CREATE TABLE IF NOT EXISTS open_pull_request_observations (
    id INTEGER PRIMARY KEY,
    pull_request_result_id INTEGER NOT NULL REFERENCES pull_request_collection_results(id),
    repository_id INTEGER NOT NULL REFERENCES repositories(github_id),
    owner_login TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    author_login TEXT,
    html_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_draft INTEGER NOT NULL,
    is_dependabot INTEGER NOT NULL,
    UNIQUE(pull_request_result_id, number)
);
CREATE INDEX IF NOT EXISTS ix_repository_owner ON repositories(owner_login, name);
CREATE INDEX IF NOT EXISTS ix_commits_time ON maintainer_commits(repository_id, committed_at);
CREATE INDEX IF NOT EXISTS ix_traffic_lookup
    ON traffic_collection_results(repository_id, kind, observed_at);
CREATE INDEX IF NOT EXISTS ix_pull_request_result_lookup
    ON pull_request_collection_results(run_id, repository_id);
CREATE INDEX IF NOT EXISTS ix_open_pull_request_lookup
    ON open_pull_request_observations(pull_request_result_id, number);
"""


class CensusStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self._migrate()

    def close(self) -> None:
        self.connection.close()

    def _migrate(self) -> None:
        """Bring pre-acceptance databases forward without discarding observations."""
        columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(repository_observations)")
        }
        identity_columns = ("owner_login", "name", "full_name", "html_url", "api_url")
        for column in identity_columns:
            if column not in columns:
                self.connection.execute(
                    f"ALTER TABLE repository_observations ADD COLUMN {column} TEXT"
                )
        for column in identity_columns:
            self.connection.execute(
                f"""UPDATE repository_observations
                SET {column}=(SELECT r.{column} FROM repositories r
                    WHERE r.github_id=repository_observations.repository_id)
                WHERE {column} IS NULL"""
            )
        run_columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(collection_runs)")
        }
        if "repo_pattern" not in run_columns:
            self.connection.execute("ALTER TABLE collection_runs ADD COLUMN repo_pattern TEXT")
        self.connection.execute(
            "INSERT INTO schema_metadata(key,value) VALUES('schema_version','4') "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
        )
        self.connection.commit()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def start_run(
        self,
        started_at: str,
        login: str,
        lookback_days: int,
        repo_pattern: str | None = None,
    ) -> int:
        cursor = self.connection.execute(
            "INSERT INTO collection_runs"
            "(started_at, status, authenticated_login, lookback_days, repo_pattern) "
            "VALUES (?, 'running', ?, ?, ?)",
            (started_at, login, lookback_days, repo_pattern),
        )
        self.connection.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return a collection run ID")
        return cursor.lastrowid

    def finish_run(self, run_id: int, completed_at: str, status: str, error: str | None = None) -> None:
        self.connection.execute(
            "UPDATE collection_runs SET completed_at=?, status=?, error=? WHERE id=?",
            (completed_at, status, error, run_id),
        )
        self.connection.commit()

    def record_owner(
        self, run_id: int, owner: str, status: str, count: int = 0, error: str | None = None
    ) -> None:
        self.connection.execute(
            "INSERT INTO owner_collection_results"
            "(run_id, owner_login, status, repository_count, error) VALUES (?, ?, ?, ?, ?)",
            (run_id, owner, status, count, error),
        )

    def record_repository(self, run_id: int, observed_at: str, repository: Repository) -> None:
        self.connection.execute(
            """INSERT INTO repositories(
                github_id,node_id,owner_id,owner_login,owner_type,name,full_name,html_url,api_url
            ) VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(github_id) DO UPDATE SET
                node_id=excluded.node_id, owner_id=excluded.owner_id,
                owner_login=excluded.owner_login, owner_type=excluded.owner_type,
                name=excluded.name, full_name=excluded.full_name,
                html_url=excluded.html_url, api_url=excluded.api_url""",
            (
                repository.github_id, repository.node_id, repository.owner_id,
                repository.owner_login, repository.owner_type, repository.name,
                repository.full_name, repository.html_url, repository.api_url,
            ),
        )
        self.connection.execute(
            """INSERT INTO repository_observations(
                run_id,repository_id,observed_at,owner_login,name,full_name,html_url,api_url,
                visibility,is_private,is_archived,is_disabled,is_fork,default_branch,created_at,
                updated_at,pushed_at,permission_role,permissions_json,commit_status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'pending')""",
            (
                run_id, repository.github_id, observed_at, repository.owner_login,
                repository.name, repository.full_name, repository.html_url, repository.api_url,
                repository.visibility,
                repository.is_private, repository.is_archived, repository.is_disabled,
                repository.is_fork, repository.default_branch, repository.created_at,
                repository.updated_at, repository.pushed_at, repository.permission_role,
                json.dumps(repository.permissions, sort_keys=True) if repository.permissions else None,
            ),
        )

    def record_commits(self, run_id: int, repository_id: int, commits: Iterator[Commit]) -> None:
        self.connection.executemany(
            """INSERT OR IGNORE INTO maintainer_commits(
                repository_id,sha,author_login,authored_at,committed_at,first_observed_run_id
            ) VALUES (?,?,?,?,?,?)""",
            (
                (repository_id, item.sha, item.author_login, item.authored_at, item.committed_at, run_id)
                for item in commits
            ),
        )

    def set_commit_result(
        self, run_id: int, repository_id: int, status: str, error: str | None = None
    ) -> None:
        self.connection.execute(
            "UPDATE repository_observations SET commit_status=?, commit_error=? "
            "WHERE run_id=? AND repository_id=?",
            (status, error, run_id, repository_id),
        )

    def record_traffic(
        self,
        run_id: int,
        repository_id: int,
        kind: str,
        observed_at: str,
        result: TrafficResult,
    ) -> None:
        cursor = self.connection.execute(
            """INSERT INTO traffic_collection_results(
                run_id,repository_id,kind,observed_at,status,aggregate_count,aggregate_uniques,error
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (
                run_id, repository_id, kind, observed_at, result.status,
                result.aggregate_count, result.aggregate_uniques, result.error,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return a traffic result ID")
        result_id = cursor.lastrowid
        self.connection.executemany(
            "INSERT INTO traffic_observations(traffic_result_id,traffic_at,count,uniques) "
            "VALUES (?,?,?,?)",
            ((result_id, day.timestamp, day.count, day.uniques) for day in result.days),
        )

    def record_pull_requests(
        self,
        run_id: int,
        repository: Repository,
        observed_at: str,
        result: PullRequestResult,
    ) -> None:
        observations = result.pull_requests if result.status == "available" else ()
        open_count = len(observations) if result.status == "available" else None
        cursor = self.connection.execute(
            """INSERT INTO pull_request_collection_results(
                run_id,repository_id,observed_at,status,open_count,error
            ) VALUES (?,?,?,?,?,?)""",
            (
                run_id, repository.github_id, observed_at, result.status,
                open_count, result.error,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return a pull request result ID")
        result_id = cursor.lastrowid
        self.connection.executemany(
            """INSERT INTO open_pull_request_observations(
                pull_request_result_id,repository_id,owner_login,repository_name,number,title,
                author_login,html_url,created_at,updated_at,is_draft,is_dependabot
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                (
                    result_id, repository.github_id, repository.owner_login, repository.name,
                    item.number, item.title, item.author_login, item.html_url, item.created_at,
                    item.updated_at, item.is_draft, item.is_dependabot,
                )
                for item in observations
            ),
        )

    def last_successful_started_at(self) -> datetime | None:
        row = self.connection.execute(
            "SELECT started_at FROM collection_runs WHERE status='successful' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(str(row["started_at"]))
