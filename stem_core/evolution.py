import ast
import logging
from typing import Dict

from stem_core.interfaces import ChatModel, Dna, Evolution, Feedback

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    pass


class SecurityASTVisitor(ast.NodeVisitor):
    # check imports only
    def __init__(self, allowed_bases: set[str]):
        self._allowed = allowed_bases

    def visit_Import(self, node: ast.Import):
        # deny anything not in whitelist
        for alias in node.names:
            full = alias.name
            base = full.split(".")[0]
            if full not in self._allowed and base not in self._allowed:
                raise SecurityError(f"import '{full}' not allowed")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # forbid relative imports
        if getattr(node, "level", 0) and node.level > 0:
            raise SecurityError("relative imports are strictly forbidden in generated dna")
        module_full = node.module or ""
        base = module_full.split(".")[0] if module_full else ""
        if module_full and (module_full not in self._allowed and base not in self._allowed):
            raise SecurityError(f"from '{module_full}' not allowed")
        self.generic_visit(node)


class PromptDrivenEvolution(Evolution):
    def __init__(self, llm: ChatModel):
        self._llm = llm

    def mutate(self, domain_signal: str, feedback: Feedback) -> Dna:
        system_prompt = (
            "You are the biological core of a Stem Cell AI. "
            f"Your environment signal is: '{domain_signal}'. "
            "You must differentiate into a Specialized Agent. "
            "Return strictly a JSON object with: "
            "1. 'system_prompt': The prompt for the specialized agent. "
            "2. 'tools': An object whose keys are Python function names and "
            "values are the full, valid Python code for those functions. "
            "3. 'requires_network': boolean true only if external internet is needed "
            "(not for localhost) "
            "CRITICAL RULES: DO NOT import or use external libraries such as 'jsonschema', 'pydantic', 'logging', 'threading', or 'concurrent.futures'. "
            "Only use Python standard library and 'requests'. Use built-in 'json', 'urllib', 're', 'time', 'datetime', and simple if-statements for validation. "
            "STRUCTURE RULES: All code must be inside top-level function definitions only. No top-level execution, no test blocks, no 'if __name__ == \"__main__\"', no network or I/O at import time. No module-level variables that perform computations or requests. "
            "Do NOT wrap code in markdown fences."
        )

        user_prompt = (
            "Generate the DNA (system_prompt + tools + requires_network) for differentiation."
        )

        if not feedback.is_successful():
            user_prompt += (
                " Warning. Previous mutation failed during execution. "
                f"Execution details: {feedback.execution_details()} "
                "Rewrite the tools to resolve this error. "
                "Ensure each function name exactly matches its definition."
            )

        response_dictionary = self._llm.ask_json(system_prompt, user_prompt)

        tools_raw = response_dictionary.get("tools", {})
        if not isinstance(tools_raw, dict):
            raise ValueError("Invalid LLM response: 'tools' must be a dictionary.")

        # sanitize tool src quick
        tools_clean: Dict[str, str] = {}
        for name, src in tools_raw.items():
            if not isinstance(name, str) or not isinstance(src, str):
                raise ValueError("Invalid tools entry: keys and values must be strings.")
            cleaned = src.replace("```python", "").replace("```", "").strip()
            tools_clean[name] = cleaned

        # ast whitelist check
        combined_source = "\n\n".join(tools_clean.values())
        try:
            tree = ast.parse(combined_source)
        except SyntaxError as e:
            # bubble syntax err early
            raise e

        # allowed base modules only
        allowed_bases = {"requests", "json", "urllib", "re", "time", "datetime"}
        SecurityASTVisitor(allowed_bases).visit(tree)

        # no top-level execution
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.Import, ast.ImportFrom)):
                continue
            if (
                isinstance(node, ast.Expr)
                and isinstance(getattr(node, "value", None), ast.Constant)
                and isinstance(node.value.value, str)
            ):
                # allow module docstring
                continue
            raise SecurityError("top-level code is forbidden, put all logic inside functions")

        # net flag from llm
        req_net = response_dictionary.get("requires_network", False)
        if not isinstance(req_net, bool):
            raise ValueError("Invalid LLM response: 'requires_network' must be a boolean.")
        return Dna(
            system_prompt=response_dictionary.get("system_prompt", ""),
            tools=tools_clean,
            requires_network=req_net,
        )
