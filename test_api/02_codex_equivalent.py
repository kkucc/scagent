import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("CodexEquivalent")


def run_code_generation():
    """
    config GPT simulating Codex.
    """
    load_dotenv(dotenv_path="config/.env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY is missing.")
        return

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a pure code generation engine. "
        "Output ONLY valid, executable Python code. "
        "Do not output markdown formatting (e.g., ```python). "
        "Do not output explanations, greetings, or comments outside of the code block. "
        "If you violate these rules, the compilation will fail."
    )

    user_prompt = "Write a Python function that calculates the Fibonacci sequence up to n terms using a generator."

    logger.info("Requesting pure Python code generation...")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        raw_code = response.choices[0].message.content

        clean_code = raw_code.replace("```python", "").replace("```", "").strip()

        print("\n--- Generated Source Code (Sanitized) ---")
        print(clean_code)
        print("-------------------------------------------\n")

        try:
            compile(clean_code, "<string>", "exec")
            logger.info("Validation: Code compiled successfully into an AST.")
        except SyntaxError as e:
            logger.error("Validation: LLM generated invalid syntax even after cleaning: %s", str(e))

    except Exception as exception:
        logger.error("API call failed: %s", str(exception))


if __name__ == "__main__":
    run_code_generation()


# (venv) (base) karina@MacBook-Air-Ymnumi stem_agent_project % python test_api/02_codex_equivalent.py
# [03:15:10] INFO Requesting pure Python code generation...
# [03:15:12] INFO HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"

# --- Generated Source Code (Sanitized) ---
# def fibonacci_generator(n):
#     a, b = 0, 1
#     for _ in range(n):
#         yield a
#         a, b = b, a + b

# # Example usage:
# # for num in fibonacci_generator(10):
# #     print(num)
# -------------------------------------------

# [03:15:12] INFO Validation: Code compiled successfully into an AST.
# (venv) (base) karina@MacBook-Air-Ymnumi stem_agent_project %
