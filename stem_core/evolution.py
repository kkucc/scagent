# import logging

# from stem_core.interfaces import ChatModel, Dna, Evolution, Feedback

# logger = logging.getLogger(__name__)


# class PromptDrivenEvolution(Evolution):
#     def __init__(self, llm: ChatModel):
#         self._llm = llm

#     def mutate(self, domain_signal: str, feedback: Feedback) -> Dna:
#         system_prompt = (
#             "You are the biological core of a Stem Cell AI. "
#             f"Your environment signal is: '{domain_signal}'. "
#             "You must differentiate into a Specialized Agent. "
#             "Provide the following strictly in JSON format: "
#             "1. 'system_prompt': The prompt for the specialized agent. "
#             "2. 'tool_name': The name of the Python function it needs. "
#             "3. 'tool_code': Valid Python code for this function. Use stdlib and 'requests' only."
#         )

#         user_prompt = "Generate the DNA for differentiation."

#         if not feedback.is_successful():
#             user_prompt += (
#                 " Warning. Previous mutation failed during execution. "
#                 f"Execution details: {feedback.execution_details()} "
#                 "Rewrite the tool code to resolve this error."
#             )

#         response_dictionary = self._llm.ask_json(system_prompt, user_prompt)

#         return Dna(
#             system_prompt=response_dictionary.get("system_prompt", ""),
#             tool_name=response_dictionary.get("tool_name", "custom_tool"),
#             tool_code=response_dictionary.get("tool_code", ""),
#         )
import logging

from stem_core.interfaces import ChatModel, Dna, Evolution, Feedback

logger = logging.getLogger(__name__)


class PromptDrivenEvolution(Evolution):
    def __init__(self, llm: ChatModel):
        self._llm = llm

    def mutate(self, domain_signal: str, feedback: Feedback) -> Dna:
        system_prompt = (
            "You are the biological core of a Stem Cell AI. "
            f"Your environment signal is: '{domain_signal}'. "
            "You must differentiate into a Specialized Agent. "
            "Provide the following strictly in JSON format: "
            "1. 'system_prompt': The prompt for the specialized agent. "
            "2. 'tool_name': The name of the Python function it needs. "
            "3. 'tool_code': Valid Python code for this function. Use stdlib and 'requests' only. DO NOT wrap the code in markdown blocks."
        )

        user_prompt = "Generate the DNA for differentiation."

        if not feedback.is_successful():
            user_prompt += (
                " Warning. Previous mutation failed during execution. "
                f"Execution details: {feedback.execution_details()} "
                "Rewrite the tool code to resolve this error. Ensure the function name exactly matches 'tool_name'."
            )

        response_dictionary = self._llm.ask_json(system_prompt, user_prompt)

        raw_code = response_dictionary.get("tool_code", "")
        clean_code = raw_code.replace("```python", "").replace("```", "").strip()
        # Basic static validation
        _banned = {
            "numpy",
            "pandas",
            "torch",
            "tensorflow",
            "sklearn",
            "openai",
            "httpx",
            "aiohttp",
            "bs4",
            "lxml",
            "matplotlib",
            "seaborn",
            "scipy",
            "PIL",
            "cv2",
        }
        _filtered_lines = []
        for _line in clean_code.splitlines():
            _s = _line.strip()
            _deny = False
            if _s.startswith("import "):
                _base = _s[len("import ") :].split(",")[0].strip().split(".")[0]
                if _base in _banned and _base != "requests":
                    _deny = True
            elif _s.startswith("from "):
                _base = _s[len("from ") :].split("import", 1)[0].strip().split(".")[0]
                if _base in _banned and _base != "requests":
                    _deny = True
            if not _deny:
                _filtered_lines.append(_line)
        clean_code = "\n".join(_filtered_lines)

        return Dna(
            system_prompt=response_dictionary.get("system_prompt", ""),
            tool_name=response_dictionary.get("tool_name", "custom_tool"),
            tool_code=clean_code,
        )
