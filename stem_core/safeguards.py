# import logging

# from stem_core.interfaces import Dna, EmptyFeedback, Evolution, Feedback, Workspace

# logger = logging.getLogger(__name__)


# class SafeguardedEvolution(Evolution):
#     def __init__(self, origin: Evolution, workspace: Workspace, max_attempts: int = 3):
#         self._origin = origin
#         self._workspace = workspace
#         self._max_attempts = max_attempts

#     def mutate(self, domain_signal: str, feedback: Feedback) -> Dna:
#         current_feedback = feedback

#         for attempt in range(1, self._max_attempts + 1):
#             logger.info(
#                 "Initiating evolution attempt %d for domain signal: %s",
#                 attempt,
#                 domain_signal,
#             )

#             dna = self._origin.mutate(domain_signal, current_feedback)

#             validation_code = (
#                 f"{dna.tool_code}\n\n"
#                 f"if '{dna.tool_name}' not in locals() and '{dna.tool_name}' not in globals():\n"
#                 f"    raise NameError(\"Function '{dna.tool_name}' was not found in the generated code.\")\n"
#             )

#             test_feedback = self._workspace.execute(validation_code)

#             if test_feedback.is_successful():
#                 logger.info("Safeguard validation passed. DNA sequence is stable.")
#                 return dna

#             logger.warning("Safeguard validation failed. Triggering genetic mutation.")
#             current_feedback = test_feedback

#         raise RuntimeError(
#             "Evolutionary process terminated. Maximum mutation attempts reached."
#         )
import logging  # logging basic

from stem_core.interfaces import Dna, Evolution, Feedback, Workspace

logger = logging.getLogger(__name__)  # log stuff


# retry + validate dna
class SafeguardedEvolution(Evolution):
    def __init__(
        self,
        origin: Evolution,
        workspace: Workspace,
        max_attempts: int = 3,
        timeout_seconds: int = 5,
    ):
        self._origin = origin
        self._workspace = workspace
        self._max_attempts = max_attempts
        self._timeout_seconds = timeout_seconds
        self._dna_cache = {}  # cache dna per domain

    def mutate(self, domain_signal: str, feedback: Feedback) -> Dna:  # main loop
        current_feedback = feedback
        if (
            getattr(feedback, "is_successful", lambda: False)() and domain_signal in self._dna_cache
        ):  # reuse cached
            logger.info("Using cached DNA for domain: %s", domain_signal)
            return self._dna_cache[domain_signal]

        for attempt in range(1, self._max_attempts + 1):  # retries
            logger.info(
                "Initiating evolution attempt %d for domain signal: %s",
                attempt,
                domain_signal,
            )

            dna = self._origin.mutate(domain_signal, current_feedback)

            combined_tools_code = "\n\n".join(dna.tools.values())  # glue tools src
            tool_names = ", ".join([f"'{name}'" for name in dna.tools.keys()])  # tool names
            validation_code = (  # check all funcs exist
                f"{combined_tools_code}\n\n"
                f"_expected = [{tool_names}]\n"
                "_missing = [name for name in _expected if name not in locals() and name not in globals()]\n"
                "if _missing:\n"
                "    raise NameError('Functions not found: ' + ', '.join(_missing))\n"
            )

            test_feedback = self._workspace.execute(  # no net for checks
                validation_code, timeout_seconds=self._timeout_seconds, requires_network=False
            )

            if test_feedback.is_successful():
                logger.info("Safeguard validation passed. DNA sequence is stable.")
                self._dna_cache[domain_signal] = dna
                return dna

            logger.warning(
                "Safeguard validation failed.\nCompiler Output:\n%s\nCompiler Error:\n%s\nTriggering genetic mutation.",
                test_feedback.output,
                test_feedback.error,
            )
            current_feedback = test_feedback

        raise RuntimeError("Evolutionary process terminated. Maximum mutation attempts reached.")
