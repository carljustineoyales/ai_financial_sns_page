"""Provider-agnostic LLM entrypoint. Tries providers in priority order and
automatically falls through to the next one if the current provider is
unavailable or fails, so callers don't need to care which vendor is used.
"""

import logging
import os

from llm.claude_provider import ClaudeProvider
from llm.gemini_provider import GeminiProvider

PROVIDER_REGISTRY = {
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
}

DEFAULT_PROVIDER_ORDER = "gemini,claude"

logger = logging.getLogger(__name__)


def get_provider_order():
    names = os.environ.get("LLM_PROVIDER_ORDER", DEFAULT_PROVIDER_ORDER).split(",")
    names = [n.strip() for n in names if n.strip()]
    return [PROVIDER_REGISTRY[n]() for n in names if n in PROVIDER_REGISTRY]


def generate(prompt):
    errors = []

    for provider in get_provider_order():
        if not provider.is_available():
            logger.warning("%s not available (no API key), skipping", provider.name)
            continue

        try:
            return provider.generate(prompt)
        except Exception as e:
            logger.warning("%s failed: %s, trying next provider", provider.name, e)
            errors.append(f"{provider.name}: {e}")

    raise RuntimeError(f"All LLM providers failed or unavailable: {errors}")
