from unittest.mock import MagicMock

import pytest

from stem_core.agents import StemCell
from stem_core.interfaces import (
    ChatModel,
    Dna,
    EmptyFeedback,
    Evolution,
    ExecutionFeedback,
    Workspace,
)
from stem_core.safeguards import SafeguardedEvolution

# Mock Objects for Testing \\


class MockFailingWorkspace(Workspace):
    """always reports failure."""

    def execute(
        self, code: str, timeout_seconds: int = 5, requires_network: bool = False
    ) -> ExecutionFeedback:
        return ExecutionFeedback(output="", error="SyntaxError: Invalid syntax", successful=False)


class MockSuccessfulWorkspace(Workspace):
    """always reports success."""

    def execute(
        self, code: str, timeout_seconds: int = 5, requires_network: bool = False
    ) -> ExecutionFeedback:
        return ExecutionFeedback(output="Safeguard check passed.", error="", successful=True)


# Test Suite


def test_safeguard_succeeds_on_first_try():
    """
    initial DNA is valid and passes the safeguard.
    """
    mock_origin_evolution = MagicMock(spec=Evolution)
    valid_dna = Dna("prompt", {"tool": "def tool():\n    return 'ok'"}, False)
    mock_origin_evolution.mutate.return_value = valid_dna

    successful_workspace = MockSuccessfulWorkspace()

    safeguard = SafeguardedEvolution(
        origin=mock_origin_evolution, workspace=successful_workspace, max_attempts=3
    )

    result_dna = safeguard.mutate("test_domain", EmptyFeedback())

    assert result_dna == valid_dna
    assert isinstance(result_dna.tools, dict)
    assert "tool" in result_dna.tools
    mock_origin_evolution.mutate.assert_called_once()


def test_safeguard_recovers_from_failure():
    """
    first DNA is invalid, but the second one is valid.
    """
    mock_origin_evolution = MagicMock(spec=Evolution)
    invalid_dna = Dna("prompt", {"tool": "print(invalid)"}, False)
    valid_dna = Dna("prompt_fixed", {"tool_fixed": "def tool_fixed():\n    return 'ok'"}, False)

    # mock will return bad DNA first, then good DNA on the second call
    mock_origin_evolution.mutate.side_effect = [invalid_dna, valid_dna]

    # fail once, then succeed
    mock_workspace = MagicMock(spec=Workspace)
    failing_feedback = ExecutionFeedback("", "SyntaxError", False)
    successful_feedback = ExecutionFeedback("OK", "", True)
    mock_workspace.execute.side_effect = [failing_feedback, successful_feedback]

    safeguard = SafeguardedEvolution(
        origin=mock_origin_evolution, workspace=mock_workspace, max_attempts=3
    )

    result_dna = safeguard.mutate("test_domain", EmptyFeedback())

    assert result_dna == valid_dna
    assert mock_origin_evolution.mutate.call_count == 2
    assert len(mock_origin_evolution.mutate.call_args_list) == 2
    second_call_args = mock_origin_evolution.mutate.call_args_list[1]
    assert second_call_args[0][1] == failing_feedback


def test_safeguard_fails_after_max_attempts():
    """
    safeguard raises a RuntimeError if it cannot produce valid DNA
    """
    mock_origin_evolution = MagicMock(spec=Evolution)
    invalid_dna = Dna("prompt", {"tool": "print(invalid)"}, False)
    mock_origin_evolution.mutate.return_value = invalid_dna

    failing_workspace = MockFailingWorkspace()

    safeguard = SafeguardedEvolution(
        origin=mock_origin_evolution, workspace=failing_workspace, max_attempts=2
    )

    with pytest.raises(RuntimeError):
        safeguard.mutate("test_domain", EmptyFeedback())

    assert mock_origin_evolution.mutate.call_count == 2
    assert isinstance(invalid_dna.tools, dict)


def test_stem_cell_differentiation_process():
    """
    sc ensure it correctly uses the evolution process
    """
    mock_evolution = MagicMock(spec=Evolution)
    mock_llm = MagicMock(spec=ChatModel)
    final_dna = Dna("final_prompt", {"final_tool": "def final_tool():\n    return 'final'"}, False)
    mock_evolution.mutate.return_value = final_dna

    workspace = MockSuccessfulWorkspace()
    stem_cell = StemCell(evolution_process=mock_evolution, llm=mock_llm, workspace=workspace)

    specialized_cell = stem_cell.differentiate("test_domain")

    mock_evolution.mutate.assert_called_once()
    assert specialized_cell is not None
    assert hasattr(specialized_cell, "_dna")
    assert specialized_cell._dna == final_dna
