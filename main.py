# import logging
# import os

# from llm_api.openai_client import OpenAiChat
# from stem_core.agents import StemCell
# from stem_core.evolution import PromptDrivenEvolution
# from stem_core.interfaces import Task
# from stem_core.safeguards import SafeguardedEvolution
# from stem_core.workspace import LocalWorkspace

# logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# def execute_evaluation() -> None:
#     api_key = os.environ.get("OPENAI_API_KEY")
#     if not api_key:
#         raise EnvironmentError("The OPENAI_API_KEY environment variable is not set.")

#     chat_model = OpenAiChat(model_name="gpt-4o")
#     isolated_workspace = LocalWorkspace()

#     base_evolution = PromptDrivenEvolution(llm=chat_model)
#     safeguarded_evolution = SafeguardedEvolution(
#         origin=base_evolution, workspace=isolated_workspace, max_attempts=3
#     )

#     stem_cell = StemCell(evolution_process=safeguarded_evolution, llm=chat_model)

#     domain_signal = "Application Programming Interface Quality Assurance Testing"
#     specialized_agent = stem_cell.differentiate(task_domain=domain_signal)

#     evaluation_task = Task(
#         description="Fetch the data from https://jsonplaceholder.typicode.com/posts/1 and verify that the user identifier is equal to 1."
#     )

#     result = specialized_agent.act(task=evaluation_task)
#     logging.info("Evaluation Result: %s", result.content)


# if __name__ == "__main__":
#     execute_evaluation()
import logging
import os

import yaml

from llm_api.openai_client import OpenAiChat
from stem_core.agents import StemCell
from stem_core.docker_workspace import DockerWorkspace
from stem_core.evolution import PromptDrivenEvolution
from stem_core.interfaces import Task, Workspace
from stem_core.safeguards import SafeguardedEvolution
from stem_core.workspace import LocalWorkspace

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class ConfiguredWorkspace:
    """
    Workspace adapter overriding any caller-provided value
    """

    def __init__(self, inner_workspace: Workspace, default_timeout: int):
        self._inner = inner_workspace
        self._default_timeout = int(default_timeout)

    def execute(self, code: str, timeout_seconds: int = 5):
        # timeout
        return self._inner.execute(code, timeout_seconds=self._default_timeout)


def load_configuration(config_path: str) -> dict:
    """Loads the application config from a YAML file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("Configuration file not found at %s", config_path)
        raise
    except yaml.YAMLError as e:
        logging.error("Error parsing YAML configuration: %s", e)
        raise


def execute_evaluation(config: dict) -> None:
    """
    Assembles and runs scagent based on config
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("The OPENAI_API_KEY environment variable is not set.")

    chat_model = OpenAiChat(model_name=config["llm"]["model_name"])
    ws_cfg = config.get("workspace", {})
    workspace_timeout = int(ws_cfg.get("timeout_seconds", 5))
    backend = ws_cfg.get("backend", "local").lower()
    if backend == "docker":
        base_workspace = DockerWorkspace()
    else:
        base_workspace = LocalWorkspace()
    isolated_workspace = ConfiguredWorkspace(
        inner_workspace=base_workspace, default_timeout=workspace_timeout
    )

    base_evolution = PromptDrivenEvolution(llm=chat_model)
    safeguarded_evolution = SafeguardedEvolution(
        origin=base_evolution,
        workspace=isolated_workspace,
        max_attempts=config["agent_settings"]["evolution_attempts"],
        timeout_seconds=workspace_timeout,
    )

    # stem_cell = StemCell(evolution_process=safeguarded_evolution, llm=chat_model)
    stem_cell = StemCell(
        evolution_process=safeguarded_evolution,
        llm=chat_model,
        workspace=isolated_workspace,
    )
    # Diff and Eval
    domain_signal = "Application Programming Interface Quality Assurance Testing"
    specialized_agent = stem_cell.differentiate(task_domain=domain_signal)

    evaluation_task = Task(
        description=(
            "Fetch data from https://jsonplaceholder.typicode.com/posts/1 and verify "
            "that the 'userId' key has a value of 1."
        )
    )

    result = specialized_agent.act(task=evaluation_task)
    logging.info("--- Evaluation Complete ---")
    logging.info("Final Result from Specialized Agent: %s", result.content)
    logging.info("Task Success Status: %s", result.is_successful)


if __name__ == "__main__":
    app_config = load_configuration("config/settings.yaml")
    execute_evaluation(config=app_config)
