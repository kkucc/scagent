import logging
import os
import subprocess
import tempfile

from stem_core.interfaces import ExecutionFeedback, Feedback, Workspace

# log stuff quick
logger = logging.getLogger(__name__)


# local runner no isolation
class LocalWorkspace(Workspace):
    # run code with timeout (net flag ignored here)
    def execute(
        self, code: str, timeout_seconds: int = 5, requires_network: bool = False
    ) -> Feedback:
        # local doesn't block net, warn
        if not requires_network:
            logger.warning(
                "LocalWorkspace does not isolate network. requires_network flag ignored."
            )
        # tmp dir for code
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "generated_tool.py")

            # write code to file
            with open(file_path, "w", encoding="utf-8") as source_file:
                source_file.write(code)

            try:
                # run python here
                result = subprocess.run(
                    ["python", file_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )

                # success if exit code ok
                success = result.returncode == 0
                return ExecutionFeedback(
                    output=result.stdout.strip(),
                    error=result.stderr.strip(),
                    successful=success,
                )

            # timeout -> probably hang
            except subprocess.TimeoutExpired:
                return ExecutionFeedback(
                    output="",
                    error=f"Execution exceeded {timeout_seconds} seconds. Probable infinite loop.",
                    successful=False,
                )
            # other error catch
            except Exception as exception:
                return ExecutionFeedback(output="", error=str(exception), successful=False)
