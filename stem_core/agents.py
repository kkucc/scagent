# import json
# import logging

# from stem_core.interfaces import (
#     Agent,
#     ChatModel,
#     Dna,
#     EmptyFeedback,
#     Evolution,
#     Result,
#     Task,
# )

# logger = logging.getLogger(__name__)


# class SpecializedCell(Agent):
#     def __init__(self, dna: Dna, llm: ChatModel):
#         self._dna = dna
#         self._llm = llm

#     def act(self, task: Task) -> Result:
#         logger.info("Specialized cell processing assigned task.")

#         user_prompt = (
#             f"Solve the following task: {task.description} "
#             f"You have a Python tool available named: {self._dna.tool_name}. "
#             "Output a JSON object containing a 'status' key and an 'answer' key."
#         )

#         try:
#             response_dictionary = self._llm.ask_json(
#                 self._dna.system_prompt, user_prompt
#             )
#             return Result(content=json.dumps(response_dictionary), is_successful=True)
#         except Exception as exception:
#             logger.error("Task processing encountered a fatal error.")
#             return Result(content=str(exception), is_successful=False)


# class StemCell:
#     def __init__(self, evolution_process: Evolution, llm: ChatModel):
#         self._evolution = evolution_process
#         self._llm = llm

#     def differentiate(self, task_domain: str) -> SpecializedCell:
#         logger.info(
#             "Stem cell receiving environmental signal. Beginning differentiation."
#         )

#         initial_feedback = EmptyFeedback()
#         stable_dna = self._evolution.mutate(task_domain, initial_feedback)

#         logger.info("Differentiation complete. Assembling specialized cell.")
#         return SpecializedCell(dna=stable_dna, llm=self._llm)

import logging

from stem_core.interfaces import (
    Agent,
    ChatModel,
    Dna,
    EmptyFeedback,
    Evolution,
    Result,
    Task,
    Workspace,
)

logger = logging.getLogger(__name__)


class SpecializedCell(Agent):
    def __init__(self, dna: Dna, llm: ChatModel, workspace: Workspace):
        self._dna = dna
        self._llm = llm
        self._workspace = workspace

    def act(self, task: Task) -> Result:
        logger.info("planning task exec")

        combined_tools_code = "\n\n".join(self._dna.tools.values())
        available_functions = ", ".join(self._dna.tools.keys())

        user_prompt = (
            f"Your task: {task.description}\n"
            f"You have these verified Python tools (functions): {available_functions}\n"
            f"Source code:\n{combined_tools_code}\n\n"
            "Write a short Python script that uses these functions to execute the task and print the final answer to standard output. "
            "Output strictly a JSON object with a 'script_to_run' key containing the code."
        )

        try:
            response_dictionary = self._llm.ask_json(self._dna.system_prompt, user_prompt)
            script_to_run = response_dictionary.get("script_to_run", "")

            logger.info("run script in workspace")
            full_executable_code = f"{combined_tools_code}\n\n{script_to_run}"

            execution = self._workspace.execute(
                full_executable_code, requires_network=self._dna.requires_network
            )

            return Result(
                content=execution.execution_details(),
                is_successful=execution.is_successful(),
            )
        except Exception as exception:
            logger.error("task failed hard")
            return Result(content=str(exception), is_successful=False)


class StemCell:
    def __init__(self, evolution_process: Evolution, llm: ChatModel, workspace: Workspace):
        self._evolution = evolution_process
        self._llm = llm
        self._workspace = workspace

    def differentiate(self, task_domain: str) -> SpecializedCell:
        logger.info("got signal, start diff")

        initial_feedback = EmptyFeedback()
        stable_dna = self._evolution.mutate(task_domain, initial_feedback)

        logger.info("diff done, build cell")
        return SpecializedCell(dna=stable_dna, llm=self._llm, workspace=self._workspace)
