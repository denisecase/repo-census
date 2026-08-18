import io
from pathlib import Path

import pytest

from repo_census.cli import main, parser
from repo_census.models import Repository
from repo_census.persistence import CensusStore

from .test_persistence_reporting import populate


def test_collect_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert main(["collect"]) == 2


def test_report_cli_writes_markdown(
    tmp_path: Path, repository: Repository
) -> None:
    database = tmp_path / "census.db"
    with CensusStore(database) as store:
        populate(store, repository)
    output = io.StringIO()
    assert main(["report", "--database", str(database)], stdout=output) == 0
    assert output.getvalue().startswith("# Repository Census")
    assert "GitHub aggregate" in output.getvalue()


def test_collect_cli_accepts_repository_pattern() -> None:
    args = parser().parse_args([
        "collect", "--owner", "denisecase", "--repo-pattern", "datafun-*"
    ])
    assert args.repo_pattern == "datafun-*"
