"""Tests for the StateMonitor."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ccp.auditor.monitor import StateMonitor
from ccp.auditor.types import StateSnapshot


class TestStateMonitor:
    """Tests for StateMonitor class."""

    @pytest.fixture
    def mock_db(self, tmp_path: Path) -> Path:
        """Create a mock Claude Mem database."""
        db_path = tmp_path / ".claude-mem" / "claude-mem.db"
        db_path.parent.mkdir(parents=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE observations (
                id INTEGER PRIMARY KEY,
                type TEXT,
                title TEXT,
                body TEXT,
                created_at TEXT,
                created_at_epoch INTEGER
            )
        """)
        cursor.executemany(
            "INSERT INTO observations (type, title, body, created_at, created_at_epoch) VALUES (?, ?, ?, ?, ?)",
            [
                ("discovery", "Found pattern", "Details about the pattern", "2026-01-20T10:00:00", 1737370800000),
                ("decision", "Chose approach", "Reasoning for the decision", "2026-01-20T10:01:00", 1737370860000),
            ],
        )
        conn.commit()
        conn.close()
        return db_path

    @pytest.fixture
    def mock_plan(self, tmp_path: Path) -> Path:
        """Create a mock plan file."""
        plans_dir = tmp_path / "docs" / "plans"
        plans_dir.mkdir(parents=True)

        plan_content = """# Test Plan

Created: 2026-01-20
Status: PENDING
Approved: Yes

## Progress Tracking
- [x] Task 1: First task
- [ ] Task 2: Second task
"""
        plan_file = plans_dir / "2026-01-20-test-plan.md"
        plan_file.write_text(plan_content)
        return tmp_path

    def test_get_recent_observations(self, mock_db: Path) -> None:
        """Should fetch recent observations from database."""
        monitor = StateMonitor(
            project_root=mock_db.parent.parent,
            db_path=mock_db,
        )
        observations = monitor.get_recent_observations(limit=10)

        assert isinstance(observations, list)
        assert len(observations) == 2

    def test_get_active_plan(self, mock_plan: Path) -> None:
        """Should find and parse active plan."""
        monitor = StateMonitor(project_root=mock_plan)
        plan = monitor.get_active_plan()

        assert plan is not None
        assert plan["status"] == "PENDING"
        assert plan["completed"] == 1
        assert plan["total"] == 2

    def test_get_current_state_returns_snapshot(self, mock_plan: Path, mock_db: Path) -> None:
        """Should return a complete state snapshot."""
        monitor = StateMonitor(project_root=mock_plan, db_path=mock_db)
        state = monitor.get_current_state()

        assert isinstance(state, StateSnapshot)
        assert isinstance(state.observations, list)
        assert isinstance(state.git_changes, list)

    def test_handles_missing_database(self, tmp_path: Path) -> None:
        """Should handle missing database gracefully."""
        monitor = StateMonitor(
            project_root=tmp_path,
            db_path=tmp_path / "nonexistent.db",
        )
        observations = monitor.get_recent_observations()

        assert observations == []

    def test_handles_missing_plan_directory(self, tmp_path: Path) -> None:
        """Should handle missing plans directory."""
        monitor = StateMonitor(project_root=tmp_path)
        plan = monitor.get_active_plan()

        assert plan is None

    def test_caches_results(self, mock_db: Path) -> None:
        """Should cache results to avoid repeated operations."""
        monitor = StateMonitor(
            project_root=mock_db.parent.parent,
            db_path=mock_db,
            cache_ttl_seconds=60,
        )

        obs1 = monitor.get_recent_observations()
        obs2 = monitor.get_recent_observations()

        assert obs1 == obs2

    def test_get_git_diff_returns_string(self, tmp_path: Path) -> None:
        """Should return git diff as string."""
        monitor = StateMonitor(project_root=tmp_path)
        diff = monitor.get_git_diff()

        # Should return empty string for non-git directory
        assert isinstance(diff, str)

    def test_get_git_diff_truncates_long_diffs(self, tmp_path: Path) -> None:
        """Should truncate diffs that exceed max_chars."""
        monitor = StateMonitor(project_root=tmp_path)

        # Set a very small limit to test truncation
        diff = monitor.get_git_diff(max_chars=10)

        # Either empty (no git) or truncated
        assert isinstance(diff, str)
        assert len(diff) <= 50  # max_chars + truncation message

    def test_state_snapshot_includes_git_diff(self, mock_plan: Path, mock_db: Path) -> None:
        """Should include git_diff in state snapshot."""
        monitor = StateMonitor(project_root=mock_plan, db_path=mock_db)
        state = monitor.get_current_state()

        assert hasattr(state, "git_diff")
        assert isinstance(state.git_diff, str)


class TestStateMonitorBaseline:
    """Tests for baseline tracking to ignore pre-session changes."""

    def test_first_call_establishes_baseline_returns_empty(self, tmp_path: Path) -> None:
        """First call to get_git_changes should establish baseline and return empty."""
        monitor = StateMonitor(project_root=tmp_path)

        # Simulate pre-existing changes by setting internal state
        monitor._baseline_files = None
        monitor._baseline_initialized = False

        # First call should return empty (baseline established)
        changes = monitor.get_git_changes()

        assert changes == []
        assert monitor._baseline_initialized is True

    def test_subsequent_calls_return_only_new_files(self, tmp_path: Path) -> None:
        """Subsequent calls should only return files not in baseline."""
        monitor = StateMonitor(project_root=tmp_path)

        # Simulate baseline with some pre-existing files
        monitor._baseline_files = {"old_file.py", "another_old.py"}
        monitor._baseline_initialized = True
        monitor._git_cache = None  # Clear cache to force recalculation

        # Mock _get_all_git_changes to return both old and new files
        original_get_all = monitor._get_all_git_changes

        def mock_get_all() -> set[str]:
            return {"old_file.py", "another_old.py", "new_file.py"}

        monitor._get_all_git_changes = mock_get_all  # type: ignore[method-assign]

        changes = monitor.get_git_changes()

        # Should only return the new file, not baseline files
        assert changes == ["new_file.py"]

        # Restore original method
        monitor._get_all_git_changes = original_get_all  # type: ignore[method-assign]

    def test_git_diff_empty_when_no_new_changes(self, tmp_path: Path) -> None:
        """get_git_diff should return empty when no new files since baseline."""
        monitor = StateMonitor(project_root=tmp_path)

        # Establish baseline
        monitor._baseline_files = {"existing.py"}
        monitor._baseline_initialized = True
        monitor._git_cache = None
        monitor._diff_cache = None

        # Mock to return only baseline files (no new changes)
        def mock_get_all() -> set[str]:
            return {"existing.py"}

        monitor._get_all_git_changes = mock_get_all  # type: ignore[method-assign]

        diff = monitor.get_git_diff()

        # Should be empty since no new files
        assert diff == ""

    def test_baseline_not_reestablished_on_subsequent_calls(self, tmp_path: Path) -> None:
        """Baseline should only be set once, not on every call."""
        monitor = StateMonitor(project_root=tmp_path)

        # First call establishes baseline
        monitor._baseline_files = None
        monitor._baseline_initialized = False

        def mock_get_all() -> set[str]:
            return {"initial.py"}

        monitor._get_all_git_changes = mock_get_all  # type: ignore[method-assign]

        # First call
        monitor._git_cache = None
        changes1 = monitor.get_git_changes()
        assert changes1 == []
        assert monitor._baseline_files == {"initial.py"}

        # Simulate new file appearing
        def mock_get_all_with_new() -> set[str]:
            return {"initial.py", "new.py"}

        monitor._get_all_git_changes = mock_get_all_with_new  # type: ignore[method-assign]

        # Second call should NOT reset baseline
        monitor._git_cache = None
        changes2 = monitor.get_git_changes()

        # Should return only the new file
        assert changes2 == ["new.py"]
        # Baseline should still be the original
        assert monitor._baseline_files == {"initial.py"}

    def test_get_current_state_respects_baseline(self, tmp_path: Path) -> None:
        """get_current_state should return state respecting baseline."""
        monitor = StateMonitor(project_root=tmp_path)

        # Set up baseline
        monitor._baseline_files = {"preexisting.py"}
        monitor._baseline_initialized = True

        def mock_get_all() -> set[str]:
            return {"preexisting.py"}  # Only baseline files

        monitor._get_all_git_changes = mock_get_all  # type: ignore[method-assign]

        state = monitor.get_current_state()

        # git_changes should be empty (no new changes)
        assert state.git_changes == []
        # git_diff should be empty (no new changes to diff)
        assert state.git_diff == ""
