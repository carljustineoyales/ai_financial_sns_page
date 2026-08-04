import os

from google import genai

from llm.base import LLMProvider

MODEL = "gemini-flash-latest"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def is_available(self):
        return bool(os.environ.get("GEMINI_API_KEY"))

    def generate(self, prompt):
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        response = client.models.generate_content(model=MODEL, contents=prompt)

        return response.text
