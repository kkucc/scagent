from stem_core.workspace import LocalWorkspace


def test_workspace_execution_success():
    workspace = LocalWorkspace()
    code = "print('system_stable')"

    feedback = workspace.execute(code)

    assert feedback.is_successful() is True
    assert "system_stable" in feedback.output
    assert feedback.error == ""


def test_workspace_execution_syntax_error():
    workspace = LocalWorkspace()
    code = "print('missing_quote)"

    feedback = workspace.execute(code)

    assert feedback.is_successful() is False
    assert "SyntaxError" in feedback.error
    assert feedback.output == ""


def test_workspace_execution_timeout():
    workspace = LocalWorkspace()
    code = "import time\nwhile True:\n    time.sleep(0.1)\n"

    feedback = workspace.execute(code, timeout_seconds=1)

    assert feedback.is_successful() is False
    # assert feedback.output == ""
    # assert feedback.error == ""
    assert "Execution exceeded" in feedback.error
