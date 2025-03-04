import os
import time
from typing import Any, cast

from loguru import logger
from openai import OpenAI


class VLMClient:
    """Client for interacting with Vision Language Models via OpenRouter."""

    # Available providers and their models
    PROVIDERS = {
        "OpenAI": ["openai/gpt-4o"],
        "Google": [
            "google/gemini-2.0-flash-001",
        ],
        "Meta": [
            "meta-llama/llama-3.2-11b-vision-instruct"
            "meta-llama/llama-3.2-90b-vision-instruct",
        ],
        "Qwen": [
            "qwen/qwen2.5-vl-72b-instruct",
        ],
        "MistralAI": ["mistralai/pixtral-large-2411"],
    }

    # Flat list of all models
    ALL_MODELS = [model for models in PROVIDERS.values() for model in models]

    def __init__(self) -> None:
        """Initialize the VLM client with OpenRouter API credentials."""
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
            )

    def is_configured(self) -> bool:
        """Check if the client is properly configured with an API key."""
        return self.api_key is not None and self.client is not None

    def get_models_by_provider(self, provider: str) -> list[str]:
        """Get the list of models available for a specific provider."""
        return self.PROVIDERS.get(provider, [])

    def get_providers(self) -> list[str]:
        """Get the list of all providers."""
        return list(self.PROVIDERS.keys())

    def send_message(self, messages: list[dict[str, Any]], model: str) -> str:
        """
        Send messages to the selected model and return the response.
        Uses Weave to track the prompt and response.

        Args:
            messages: List of message dictionaries in OpenAI format
            model: Model identifier string

        Returns:
            Response text from the model

        Raises:
            Exception: If there's an error in the API call
        """
        if not self.is_configured():
            raise ValueError("OpenRouter API key is not configured")

        try:
            max_retries = 5
            wait_seconds = 5
            for attempt in range(1, max_retries + 1):
                try:
                    completion = cast(OpenAI, self.client).chat.completions.create(model=model, messages=messages)  # type: ignore

                    if (
                        (not completion)
                        or (not hasattr(completion, "choices"))
                        or (not completion.choices)
                        or (len(completion.choices) == 0)
                    ):
                        raise ValueError("Invalid completion received from API")

                    response_text = str(completion.choices[0].message.content)
                    return response_text
                except Exception as e:
                    logger.error(
                        f"Attempt {attempt}: Error calling OpenRouter API: {str(e)}"
                    )
                    if attempt < max_retries:
                        time.sleep(wait_seconds)
                    else:
                        raise
            raise RuntimeError("No valid response obtained from API")
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {str(e)}")
            raise
