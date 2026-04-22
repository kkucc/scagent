import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("OpenAIBasics")


def run_basic_completion():
    """
    test OpenAI API,
    """
    load_dotenv(dotenv_path="config/.env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY is missing. Check your config/.env file.")
        return

    client = OpenAI(api_key=api_key)
    model_name = "gpt-4o"

    logger.info("Sending request to %s...", model_name)

    try:
        response_stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a pragmatic, concise senior software engineer.",
                },
                {
                    "role": "user",
                    "content": "Explain the concept of Dependency Injection in one short sentence.",
                },
            ],
            stream=True,
        )

        print("\n--- LLM Response Stream ---")
        for chunk in response_stream:
            # Каждый chunk содержит дельту (новую часть текста)
            if chunk.choices[0].delta.content is not None:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n---------------------------\n")

    except Exception as exception:
        logger.error("API call failed: %s", str(exception))


if __name__ == "__main__":
    run_basic_completion()
