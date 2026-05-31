"""
Central LLM provider factory.

Provides a single, composable entry point (`create_llm_service`) for building a
LangChain chat model so the rest of the codebase never instantiates a provider
client directly. This avoids duplicating provider/credentials logic and makes the
LLM backend configurable via environment variables.

Supported providers (env `LLM_PROVIDER`):
- ``local``  (default): an OpenAI-compatible local server such as Ollama
  (``http://localhost:11434/v1``) or LM Studio (``http://localhost:1234/v1``).
  No API key/quota required. Reuses ``langchain_openai.ChatOpenAI`` so structured
  output, chains and ``.invoke`` all behave identically to the OpenAI path.
- ``openai``: the hosted OpenAI API (requires ``OPENAI_API_KEY``).

Configuration (all optional, sensible defaults):
- ``LLM_PROVIDER``         : ``local`` | ``openai``        (default ``local``)
- ``LOCAL_LLM_BASE_URL``   : OpenAI-compatible base URL    (default Ollama)
- ``LOCAL_LLM_MODEL``      : local model tag               (default ``llama3.2``)
- ``LOCAL_LLM_API_KEY``    : placeholder key for local srv (default ``ollama``)
- ``DEFAULT_LLM_MODEL``    : model used for the openai path (default ``gpt-4o-mini``)
"""

import os
import logging
from typing import Any, Optional

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Defaults kept here so every call site shares the same behaviour.
DEFAULT_LOCAL_BASE_URL = "http://localhost:11434/v1"  # Ollama OpenAI-compatible API
DEFAULT_LOCAL_MODEL = "llama3.2:3b"
DEFAULT_LOCAL_API_KEY = "ollama"  # local servers ignore the value but require a non-empty key
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def get_provider(provider: Optional[str] = None) -> str:
    """Resolve the active provider, honouring an explicit override then env."""
    return (provider or os.getenv("LLM_PROVIDER", "local")).strip().lower()


def create_llm_service(
    model: Optional[str] = None,
    temperature: float = 0.0,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> ChatOpenAI:
    """Build a LangChain chat model for the configured provider.

    Args:
        model: Preferred model name. Used only by the ``openai`` provider; the
            ``local`` provider always uses ``LOCAL_LLM_MODEL`` (or its default)
            because OpenAI-style names such as ``gpt-3.5-turbo`` do not exist locally.
        temperature: Sampling temperature.
        provider: Explicit provider override (``local`` | ``openai``); defaults to env.
        **kwargs: Passed through to ``ChatOpenAI`` (e.g. ``request_timeout``,
            ``model_kwargs={"response_format": {"type": "json_object"}}``).

    Returns:
        A configured ``ChatOpenAI`` instance.

    Raises:
        ValueError: if the openai provider is selected without ``OPENAI_API_KEY``.
    """
    resolved = get_provider(provider)

    if resolved == "local":
        base_url = os.getenv("LOCAL_LLM_BASE_URL", DEFAULT_LOCAL_BASE_URL)
        api_key = os.getenv("LOCAL_LLM_API_KEY", DEFAULT_LOCAL_API_KEY)
        # Callers pass OpenAI-style names (e.g. "gpt-3.5-turbo") that do not exist
        # locally, so the local model is taken from env/default, not the arg.
        local_model = os.getenv("LOCAL_LLM_MODEL", DEFAULT_LOCAL_MODEL)
        logger.info(f"Creating LOCAL LLM '{local_model}' via {base_url}")
        return ChatOpenAI(
            model=local_model,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
            **kwargs,
        )

    if resolved == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "Set the key or use LLM_PROVIDER=local."
            )
        openai_model = model or os.getenv("DEFAULT_LLM_MODEL", DEFAULT_OPENAI_MODEL)
        logger.info(f"Creating OpenAI LLM '{openai_model}'")
        return ChatOpenAI(
            model=openai_model,
            temperature=temperature,
            api_key=api_key,
            **kwargs,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{resolved}'. Expected 'local' or 'openai'."
    )


def create_structured_llm(llm: ChatOpenAI, schema: Any, provider: Optional[str] = None):
    """Wrap a chat model for structured (schema-typed) output, provider-aware.

    Small local models are unreliable with the default tool/function-calling method
    but respond well to JSON mode, so the local provider uses ``method="json_mode"``.
    The OpenAI provider keeps LangChain's default (function calling).

    Note: ``json_mode`` requires the prompt to instruct the model to return JSON.

    Args:
        llm: A chat model produced by ``create_llm_service``.
        schema: A Pydantic model describing the desired output.
        provider: Explicit provider override; defaults to env.
    """
    if get_provider(provider) == "local":
        return llm.with_structured_output(schema, method="json_mode")
    return llm.with_structured_output(schema)


def llm_is_available(provider: Optional[str] = None) -> bool:
    """Lightweight check that the configured provider can be constructed.

    Does not make a network call; verifies credentials/config preconditions only.
    """
    resolved = get_provider(provider)
    if resolved == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    # Local provider has no credential precondition.
    return resolved == "local"
