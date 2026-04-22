import dataclasses
import typing


@dataclasses.dataclass(frozen=True)
class Task:
    description: str


@dataclasses.dataclass(frozen=True)
class Result:
    content: str
    is_successful: bool


class Feedback(typing.Protocol):
    output: str
    error: str
    successful: bool

    def is_successful(self) -> bool:
        raise NotImplementedError

    def execution_details(self) -> str:
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class EmptyFeedback(Feedback):
    output: str = ""
    error: str = ""
    successful: bool = True

    def is_successful(self) -> bool:
        return self.successful

    def execution_details(self) -> str:
        return "No prior execution."


@dataclasses.dataclass(frozen=True)
class ExecutionFeedback(Feedback):
    output: str
    error: str
    successful: bool

    def is_successful(self) -> bool:
        return self.successful

    def execution_details(self) -> str:
        return f"Standard Output: {self.output}\nStandard Error: {self.error}"


@dataclasses.dataclass(frozen=True)
class Dna:
    system_prompt: str
    tools: dict[str, str]
    requires_network: bool


class Workspace(typing.Protocol):
    def execute(
        self,
        code: str,
        timeout_seconds: int = 5,
        requires_network: bool = False,
    ) -> Feedback:
        raise NotImplementedError


class ChatModel(typing.Protocol):
    def ask_json(self, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError


class Evolution(typing.Protocol):
    def mutate(self, domain_signal: str, feedback: Feedback) -> Dna:
        raise NotImplementedError


class Agent(typing.Protocol):
    def act(self, task: Task) -> Result:
        raise NotImplementedError
