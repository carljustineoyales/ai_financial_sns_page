"""Common interface every LLM provider must implement."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name = "unnamed"

    @abstractmethod
    def is_available(self):
        """Returns True if this provider has what it needs (e.g. an API key set)."""

    @abstractmethod
    def generate(self, prompt):
        """Sends prompt to the model and returns the text response. Raises on failure."""
