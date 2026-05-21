"""Resolve a model name to a native Gemini string or a LiteLlm wrapper.

ADK supports Gemini models natively. For any OpenAI-compatible endpoint
(NVIDIA NIM, Ollama, vLLM, OpenAI, Anthropic via proxy), we wrap the model
in LiteLlm using the 'openai/' provider prefix so LiteLlm routes the call
to the configured LLM_BASE_URL.

Usage:
    from agent_runtime.model_resolver import resolve_model
    model = resolve_model("meta/llama-3.1-70b-instruct")  # -> LiteLlm(...)
    model = resolve_model("gemini-flash-latest")           # -> "gemini-flash-latest"
"""

from __future__ import annotations


def resolve_model(model_name: str):
    """Return native string for Gemini, LiteLlm wrapper for all other models.

    Args:
        model_name: Raw model name from agent config.

    Returns:
        str for Gemini models; LiteLlm instance for non-Gemini models.
    """
    if model_name.lower().startswith("gemini"):
        return model_name

    from api.config import settings
    from google.adk.models.lite_llm import LiteLlm

    return LiteLlm(
        model=f"openai/{model_name}",
        api_base=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
