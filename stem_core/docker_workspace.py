"""
DockerWorkspace —  executes code inside a Docker container for stronger isolation than a local subprocess

- Uses a read-only volume mount
- Defaults to "--network none" (no egress) unless overridden
- Installs 'requests' inside the container when requested

- It is not default workspace

- Requirements:
  - Docker must be installed and available on PATH
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import tempfile
from typing import Iterable, List, Optional

from stem_core.interfaces import ExecutionFeedback, Feedback, Workspace

logger = logging.getLogger(__name__)


class DockerWorkspace(Workspace):
    def __init__(
        self,
        image: str = "python:3.11-slim",
        *,
        install_requests: bool = True,
        extra_pip_packages: Optional[Iterable[str]] = None,
        network_mode: str = "none",  # "none" (default), "bridge", etc.
        readonly_mount: bool = True,
        workdir_in_container: str = "/work",
        python_executable: str = "python",
        pip_quiet: bool = True,
    ) -> None:
        """
        :param image: Docker image to use for execution.
        :param install_requests: If True, install 'requests' in the container before running.
        :param extra_pip_packages: Additional pip packages to install (iterable of names).
        :param network_mode: Docker network mode; "none" disables egress by default.
        :param readonly_mount: If True, mounts the working directory as read-only.
        :param workdir_in_container: Working directory path inside the container.
        :param python_executable: Python executable name inside the container.
        :param pip_quiet: If True, use quieter pip flags for faster logs.
        """
        self._image = image
        self._install_requests = install_requests
        self._extra_pip_packages = list(extra_pip_packages or [])
        self._network_mode = network_mode
        self._readonly_mount = readonly_mount
        self._workdir_in_container = workdir_in_container
        self._python = python_executable
        self._pip_quiet = pip_quiet

    def execute(
        self, code: str, timeout_seconds: int = 5, requires_network: bool = False
    ) -> Feedback:
        """
        Execute provided Python code in an ephemeral Docker container.

        Steps:
          - Create a temp directory on host and write code to runner.py
          - Run docker with a bind mount of that directory to /work (read-only by default)
          - Optionally install pip packages inside the container
          - Run the code and capture stdout/stderr

        Returns:
          ExecutionFeedback with stdout, stderr, and success flag.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            runner_host_path = os.path.join(temp_dir, "runner.py")
            try:
                with open(runner_host_path, "w", encoding="utf-8") as f:
                    f.write(code)
            except Exception as write_exc:
                return ExecutionFeedback(
                    output="",
                    error=f"Failed to write code to temp file: {write_exc}",
                    successful=False,
                )

            net_mode = "bridge" if requires_network else "none"
            docker_cmd = self._build_docker_command(temp_dir=temp_dir, network_mode=net_mode)

            try:
                result = subprocess.run(
                    docker_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                success = result.returncode == 0
                return ExecutionFeedback(
                    output=(result.stdout or "").strip(),
                    error=(result.stderr or "").strip(),
                    successful=success,
                )
            except FileNotFoundError:
                return ExecutionFeedback(
                    output="",
                    error="Docker is not installed or not available on PATH.",
                    successful=False,
                )
            except subprocess.TimeoutExpired:
                return ExecutionFeedback(
                    output="",
                    error=f"Execution exceeded {timeout_seconds} seconds inside Docker. Probable hang or long install.",
                    successful=False,
                )
            except Exception as exc:
                return ExecutionFeedback(output="", error=str(exc), successful=False)

    def _build_docker_command(self, temp_dir: str, network_mode: str) -> List[str]:
        """
        Construct a docker run command that:
          - Mounts temp_dir to the container's workdir
          - Optionally performs pip installs
          - Runs the Python script
        """
        cmd: List[str] = ["docker", "run", "--rm"]

        if network_mode:
            cmd += ["--network", network_mode]

        # Bind mount temp_dir to container
        mount_flag = f"{temp_dir}:{self._workdir_in_container}"
        if self._readonly_mount:
            mount_flag += ":ro"
        cmd += ["-v", mount_flag, "-w", self._workdir_in_container]

        cmd.append(self._image)

        if self._install_requests or self._extra_pip_packages:
            pip_flags = "--no-cache-dir"
            if self._pip_quiet:
                pip_flags += " -q"
            packages = []
            if self._install_requests:
                packages.append("requests")
            if self._extra_pip_packages:
                packages.extend(self._extra_pip_packages)

            # Escape packages for shell safety
            pkgs = " ".join(shlex.quote(p) for p in packages)
            inner = (
                f"{shlex.quote(self._python)} -m pip install {pip_flags} {pkgs} && "
                f"{shlex.quote(self._python)} runner.py"
            )
            cmd += ["sh", "-lc", inner]
        else:
            # Directly run the script without shell or installs
            cmd += [self._python, "runner.py"]

        logger.debug("Docker command: %s", " ".join(shlex.quote(p) for p in cmd))
        return cmd
        """
        DockerWorkspace —  executes code inside a Docker container for stronger isolation than a local subprocess

        - Uses a read-only volume mount.
        - Defaults to "--network none" (no egress) unless overridden.
        - Installs 'requests' inside the container when requested.

        - It is not default workspace.

        - Requirements:
          - Docker must be installed and available on PATH.
          - The chosen base image (default: python:3.11-slim) should have Python and pip.

        Caveats:
        - Volume mounting syntax is POSIX-oriented. Windows environments may need adaptation.
        - Timeout covers the entire container run (including potential pip installs).
        - If your generated code needs to write files, disable read-only mount for that use case.
        """
