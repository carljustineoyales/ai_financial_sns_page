"""Provider-agnostic LLM entrypoint. Tries providers in priority order and
automatically falls through to the next one if the current provider is
unavailable or fails, so callers don't need to care which vendor is used.
"""

import os

from llm.claude_provider import ClaudeProvider
from llm.gemini_provider import GeminiProvider

PROVIDER_REGISTRY = {
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
}

DEFAULT_PROVIDER_ORDER = "gemini,claude"


def get_provider_order():
    names = os.environ.get("LLM_PROVIDER_ORDER", DEFAULT_PROVIDER_ORDER).split(",")
    names = [n.strip() for n in names if n.strip()]
    return [PROVIDER_REGISTRY[n]() for n in names if n in PROVIDER_REGISTRY]


def generate(prompt):
    errors = []

    for provider in get_provider_order():
        if not provider.is_available():
            print(f"[llm] {provider.name} not available (no API key), skipping")
            continue

        try:
            return provider.generate(prompt)
        except Exception as e:
            print(f"[llm] {provider.name} failed: {e}, trying next provider")
            errors.append(f"{provider.name}: {e}")

    raise RuntimeError(f"All LLM providers failed or unavailable: {errors}")
