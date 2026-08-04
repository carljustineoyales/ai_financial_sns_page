import os

import anthropic

from llm.base import LLMProvider

MODEL = "claude-sonnet-5"


class ClaudeProvider(LLMProvider):
    name = "claude"

    def is_available(self):
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def generate(self, prompt):
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text
