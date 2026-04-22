import json
import logging

from openai import OpenAI

from stem_core.interfaces import ChatModel

logger = logging.getLogger(__name__)


class OpenAiChat(ChatModel):
    def __init__(self, model_name: str = "gpt-4o"):
        self._client = OpenAI()
        self._model = model_name

    def ask_json(self, system_prompt: str, user_prompt: str) -> dict:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Received empty response from llm")
        return json.loads(content)
