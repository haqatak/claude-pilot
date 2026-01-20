"""Tests for the AuditorAgent module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from ccp.auditor.config import AuditorConfig
from ccp.auditor.types import RuleDefinition, StateSnapshot, Violation


class TestAuditorAgent:
    """Tests for the AuditorAgent class."""

    @pytest.fixture
    def mock_rules_loader(self) -> MagicMock:
        """Create a mock RulesLoader."""
        loader = MagicMock()
        loader.build_system_prompt.return_value = "You are the Auditor.\n# Rules\n## TDD\nAlways write tests first."
        loader.load_all.return_value = [
            RuleDefinition(
                name="tdd-enforcement",
                path=Path(".claude/rules/standard/tdd-enforcement.md"),
                content="Write tests first",
                source="standard",
            )
        ]
        return loader

    @pytest.fixture
    def sample_state(self) -> StateSnapshot:
        """Create a sample state snapshot."""
        return StateSnapshot(
            observations=[
                {"id": 1, "type": "change", "title": "Wrote production code without tests"},
            ],
            git_changes=["src/feature.py"],
            git_diff="diff --git a/src/feature.py\n+def new_function():\n+    pass",
            active_plan={"name": "add-feature", "status": "PENDING", "completed": 2, "total": 5},
        )

    @pytest.fixture
    def config(self) -> AuditorConfig:
        """Create test configuration."""
        return AuditorConfig(
            enabled=True,
            interval_seconds=30,
            model="claude-sonnet-4-5",
        )

    def _create_mock_client(self, json_response: dict[str, Any]) -> MagicMock:
        """Create a mock ClaudeSDKClient that returns JSON in text response."""
        # Create text block with JSON response
        mock_text_block = MagicMock(spec=TextBlock)
        mock_text_block.text = json.dumps(json_response)

        mock_assistant = MagicMock(spec=AssistantMessage)
        mock_assistant.content = [mock_text_block]

        mock_result = MagicMock(spec=ResultMessage)

        async def mock_receive_messages() -> AsyncIterator[Any]:
            yield mock_assistant
            yield mock_result

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_messages = mock_receive_messages
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    @pytest.mark.asyncio
    async def test_analyze_returns_violations_list(
        self, mock_rules_loader: MagicMock, sample_state: StateSnapshot, config: AuditorConfig
    ) -> None:
        """Test that analyze returns a list of Violation objects."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        mock_client = self._create_mock_client({
            "violations": [
                {
                    "rule": "tdd-enforcement",
                    "severity": "error",
                    "message": "Code was written without a failing test first",
                    "evidence": "src/feature.py was modified without corresponding test file",
                }
            ]
        })

        with patch("ccp.auditor.agent.ClaudeSDKClient", return_value=mock_client):
            violations = await agent.analyze(sample_state)

        assert isinstance(violations, list)
        assert len(violations) == 1
        assert isinstance(violations[0], Violation)
        assert violations[0].rule == "tdd-enforcement"
        assert violations[0].severity == "error"

        # Clean up
        await agent.stop_session()

    @pytest.mark.asyncio
    async def test_analyze_with_no_violations(
        self, mock_rules_loader: MagicMock, config: AuditorConfig
    ) -> None:
        """Test analyze returns empty list when no violations detected."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)
        state = StateSnapshot(observations=[], git_changes=[], git_diff="", active_plan=None)

        mock_client = self._create_mock_client({"violations": []})

        with patch("ccp.auditor.agent.ClaudeSDKClient", return_value=mock_client):
            violations = await agent.analyze(state)

        assert violations == []
        await agent.stop_session()

    @pytest.mark.asyncio
    async def test_analyze_handles_sdk_errors_gracefully(
        self, mock_rules_loader: MagicMock, sample_state: StateSnapshot, config: AuditorConfig
    ) -> None:
        """Test that SDK errors are handled gracefully."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(side_effect=RuntimeError("SDK connection failed"))
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("ccp.auditor.agent.ClaudeSDKClient", return_value=mock_client):
            violations = await agent.analyze(sample_state)

        # Should return empty list on error, not crash
        assert violations == []
        assert agent.state.last_error is not None

    @pytest.mark.asyncio
    async def test_analyze_uses_correct_model(
        self, mock_rules_loader: MagicMock, sample_state: StateSnapshot
    ) -> None:
        """Test that the configured model is used."""
        from ccp.auditor.agent import AuditorAgent

        config = AuditorConfig(model="claude-opus-4-5")
        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        # Test that _get_client_options returns correct model
        options = agent._get_client_options()
        assert options.model == "claude-opus-4-5"

    @pytest.mark.asyncio
    async def test_analyze_builds_prompt_with_state(
        self, mock_rules_loader: MagicMock, sample_state: StateSnapshot, config: AuditorConfig
    ) -> None:
        """Test that the analysis prompt includes state information."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        captured_prompt = None

        async def capture_query(prompt: str) -> None:
            nonlocal captured_prompt
            captured_prompt = prompt

        mock_client = self._create_mock_client({"violations": []})
        mock_client.query = capture_query

        with patch("ccp.auditor.agent.ClaudeSDKClient", return_value=mock_client):
            await agent.analyze(sample_state)

        assert captured_prompt is not None
        assert "src/feature.py" in captured_prompt  # Git changes
        assert "PENDING" in captured_prompt  # Plan status

        await agent.stop_session()

    def test_build_analysis_prompt_includes_observations(
        self, mock_rules_loader: MagicMock, sample_state: StateSnapshot, config: AuditorConfig
    ) -> None:
        """Test that _build_analysis_prompt includes observations."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)
        prompt = agent._build_analysis_prompt(sample_state)

        assert "Wrote production code without tests" in prompt
        assert "src/feature.py" in prompt

    def test_parse_violations_from_valid_response(
        self, mock_rules_loader: MagicMock, config: AuditorConfig
    ) -> None:
        """Test parsing violations from structured output."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        data = {
            "violations": [
                {
                    "rule": "tdd-enforcement",
                    "severity": "error",
                    "message": "No test written",
                    "evidence": "file.py changed without test",
                },
                {
                    "rule": "git-commits",
                    "severity": "warning",
                    "message": "Commit without message",
                    "evidence": "Empty commit detected",
                },
            ]
        }

        violations = agent._parse_violations(data)

        assert len(violations) == 2
        assert violations[0].rule == "tdd-enforcement"
        assert violations[1].rule == "git-commits"
        assert violations[1].severity == "warning"

    def test_parse_violations_handles_empty_response(
        self, mock_rules_loader: MagicMock, config: AuditorConfig
    ) -> None:
        """Test parsing empty violations list."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        violations = agent._parse_violations({"violations": []})
        assert violations == []

    def test_parse_violations_handles_malformed_response(
        self, mock_rules_loader: MagicMock, config: AuditorConfig
    ) -> None:
        """Test parsing handles malformed response gracefully."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        # Missing violations key
        violations = agent._parse_violations({})
        assert violations == []

        # Not a dict
        violations = agent._parse_violations(None)
        assert violations == []

    def test_state_tracking(
        self, mock_rules_loader: MagicMock, config: AuditorConfig
    ) -> None:
        """Test that AuditorState is updated correctly."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        assert agent.state.running is False
        assert agent.state.total_checks == 0
        assert agent.state.violations_found == 0

    @pytest.mark.asyncio
    async def test_analyze_updates_state(
        self, mock_rules_loader: MagicMock, sample_state: StateSnapshot, config: AuditorConfig
    ) -> None:
        """Test that analyze updates the agent state."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        mock_client = self._create_mock_client({
            "violations": [
                {"rule": "test", "severity": "error", "message": "msg", "evidence": "ev"}
            ]
        })

        with patch("ccp.auditor.agent.ClaudeSDKClient", return_value=mock_client):
            await agent.analyze(sample_state)

        assert agent.state.total_checks == 1
        assert agent.state.violations_found == 1
        assert agent.state.last_check is not None
        assert agent.state.last_error is None

        await agent.stop_session()

    @pytest.mark.asyncio
    async def test_session_persistence(
        self, mock_rules_loader: MagicMock, sample_state: StateSnapshot, config: AuditorConfig
    ) -> None:
        """Test that session is reused across multiple analyze calls."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        mock_client = self._create_mock_client({"violations": []})

        with patch("ccp.auditor.agent.ClaudeSDKClient", return_value=mock_client) as mock_class:
            # First call should create client
            await agent.analyze(sample_state)
            assert mock_class.call_count == 1

            # Second call should reuse client (no new instantiation)
            await agent.analyze(sample_state)
            assert mock_class.call_count == 1  # Still 1, not 2

        await agent.stop_session()

    def test_extract_json_from_text(
        self, mock_rules_loader: MagicMock, config: AuditorConfig
    ) -> None:
        """Test JSON extraction from various text formats."""
        from ccp.auditor.agent import AuditorAgent

        agent = AuditorAgent(config=config, rules_loader=mock_rules_loader)

        # Plain JSON
        result = agent._extract_json_from_text('{"violations": []}')
        assert result == {"violations": []}

        # JSON in markdown code block
        result = agent._extract_json_from_text('```json\n{"violations": []}\n```')
        assert result == {"violations": []}

        # JSON with surrounding text
        result = agent._extract_json_from_text('Here is the result: {"violations": []} Done.')
        assert result == {"violations": []}

        # Invalid JSON
        result = agent._extract_json_from_text('Not JSON at all')
        assert result is None
