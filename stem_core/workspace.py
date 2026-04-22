import logging
import os
import subprocess
import tempfile

from stem_core.interfaces import ExecutionFeedback, Feedback, Workspace

logger = logging.getLogger(__name__)


class LocalWorkspace(Workspace):
    def execute(self, code: str, timeout_seconds: int = 5) -> Feedback:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "generated_tool.py")

            with open(file_path, "w", encoding="utf-8") as source_file:
                source_file.write(code)

            try:
                result = subprocess.run(
                    ["python", file_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )

                success = result.returncode == 0
                return ExecutionFeedback(
                    output=result.stdout.strip(),
                    error=result.stderr.strip(),
                    successful=success,
                )

            except subprocess.TimeoutExpired:
                return ExecutionFeedback(
                    output="",
                    error=f"Execution exceeded {timeout_seconds} seconds. Probable infinite loop.",
                    successful=False,
                )
            except Exception as exception:
                return ExecutionFeedback(output="", error=str(exception), successful=False)
