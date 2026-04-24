#!/usr/bin/env python3

# small benchmark for before vs after
# baseline = no safeguards
# stem = with safeguards
# prints simple ascii report

import argparse
import logging
import os
import time
from dataclasses import dataclass

import yaml

from llm_api.openai_client import OpenAiChat
from stem_core.agents import StemCell
from stem_core.docker_workspace import DockerWorkspace
from stem_core.evolution import PromptDrivenEvolution
from stem_core.interfaces import Task, Workspace
from stem_core.safeguards import SafeguardedEvolution
from stem_core.workspace import LocalWorkspace


# force timeout from config
class ConfiguredWorkspace:
    def __init__(self, inner_workspace: Workspace, default_timeout: int):
        self._inner = inner_workspace
        self._default_timeout = int(default_timeout)

    def execute(self, code: str, timeout_seconds: int = 5, requires_network: bool = False):
        return self._inner.execute(
            code, timeout_seconds=self._default_timeout, requires_network=requires_network
        )


@dataclass
class RunStats:
    name: str
    runs: int
    passes: int
    total_sec: float


def load_cfg(path: str) -> dict:
    # load yaml quick
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_workspace(backend: str, timeout_sec: int) -> Workspace:
    # choose local or docker
    if backend.lower() == "docker":
        base = DockerWorkspace()
    else:
        base = LocalWorkspace()
    return ConfiguredWorkspace(base, timeout_sec)


def make_agents(
    use_safeguards: bool, model_name: str, backend: str, timeout_sec: int, attempts: int
) -> tuple[StemCell, str]:
    # build llm + workspace + evolution
    llm = OpenAiChat(model_name=model_name)
    ws = pick_workspace(backend, timeout_sec)

    evo = PromptDrivenEvolution(llm=llm)
    if use_safeguards:
        evo = SafeguardedEvolution(
            origin=evo, workspace=ws, max_attempts=attempts, timeout_seconds=timeout_sec
        )
        tag = f"stem+safeguards:{backend}"
    else:
        tag = f"baseline:{backend}"

    agent = StemCell(evolution_process=evo, llm=llm, workspace=ws)
    return agent, tag


def one_task() -> tuple[str, Task]:
    # domain + task text (same as main)
    domain = "Application Programming Interface Quality Assurance Testing"
    task = Task(
        description=(
            "Fetch data from https://jsonplaceholder.typicode.com/posts/1 and verify "
            "that the 'userId' key has a value of 1."
        )
    )
    return domain, task


def run_bench_variant(
    use_safeguards: bool,
    runs: int,
    model_name: str,
    backend: str,
    timeout_sec: int,
    attempts: int,
) -> RunStats:
    # simple loop run
    agent, tag = make_agents(use_safeguards, model_name, backend, timeout_sec, attempts)
    domain, task = one_task()

    passes = 0
    t0 = time.perf_counter()

    for i in range(runs):
        # evolve fresh each run (realistic baseline vs stem)
        try:
            specialized = agent.differentiate(domain)
            res = specialized.act(task)
            if res.is_successful:
                passes += 1
        except Exception as e:
            logging.info("run %d failed: %s", i + 1, str(e))

    total_sec = time.perf_counter() - t0
    return RunStats(name=tag, runs=runs, passes=passes, total_sec=total_sec)


def print_report(stats_a: RunStats, stats_b: RunStats) -> None:
    # tiny ascii report
    def line(s: RunStats) -> str:
        rate = int(round(100 * (s.passes / max(1, s.runs))))
        mean = s.total_sec / max(1, s.runs)
        return (
            f"{s.name:<22} | runs {s.runs:<3} | pass {s.passes}/{s.runs} {rate:>3}% | "
            f"mean {mean:0.2f}s | total {s.total_sec:0.2f}s"
        )

    print("")
    print("=== benchmark result ===")
    print(line(stats_a))
    print(line(stats_b))
    print("========================")
    print("note: docker needs daemon running; local has no net isolation")
    print("")


def main():
    # basic logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # cli flags
    p = argparse.ArgumentParser(description="run before/after benchmark")
    p.add_argument("--cfg", default="config/settings.yaml", help="path to yaml config")
    p.add_argument("--runs", type=int, default=5, help="runs per variant")
    p.add_argument(
        "--backend",
        default=None,
        help="override backend local|docker (default takes from cfg)",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="override timeout seconds (default from cfg)",
    )
    p.add_argument(
        "--attempts",
        type=int,
        default=None,
        help="override safeguard attempts (default from cfg)",
    )
    args = p.parse_args()

    # api key check
    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY not set")

    # cfg load
    cfg = load_cfg(args.cfg)
    model_name = cfg["llm"]["model_name"]

    ws_cfg = cfg.get("workspace", {}) or {}
    backend = args.backend or ws_cfg.get("backend", "local")
    timeout_sec = int(args.timeout or ws_cfg.get("timeout_seconds", 10))

    agent_cfg = cfg.get("agent_settings", {}) or {}
    attempts = int(args.attempts or agent_cfg.get("evolution_attempts", 3))

    # run both variants
    base_stats = run_bench_variant(
        use_safeguards=False,
        runs=args.runs,
        model_name=model_name,
        backend=backend,
        timeout_sec=timeout_sec,
        attempts=attempts,
    )
    stem_stats = run_bench_variant(
        use_safeguards=True,
        runs=args.runs,
        model_name=model_name,
        backend=backend,
        timeout_sec=timeout_sec,
        attempts=attempts,
    )

    print_report(base_stats, stem_stats)


if __name__ == "__main__":
    main()
