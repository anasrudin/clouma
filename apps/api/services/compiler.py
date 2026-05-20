# apps/api/services/compiler.py
from typing import AsyncIterator
from openai import AsyncOpenAI
from ..config import settings

def get_client() -> AsyncOpenAI:
    """Create and return an AsyncOpenAI client with configured settings."""
    return AsyncOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )

SYSTEM_PROMPT = """You are an agent compiler for the Clouma platform.
Given a natural language instruction from the user, output a valid YAML agent spec.

The YAML must include these fields:
- name: (slug, lowercase, hyphens)
- description: (one line)
- model: (use the model name from the instruction, or default to "llama3.2")
- schedule: (cron string like "0 8 * * *", or null if not scheduled)
- tools: (list of tool names inferred from the task)
- memory:
    type: episodic
    backend: qdrant
- runtime:
    sandbox: browser
    timeout: 300

Available tools: web_search, telegram_send, slack_send, email_send, memory_store, file_read, file_write, code_exec, browser_navigate, api_call

Output ONLY valid YAML. No explanation. No markdown code fences. No extra text."""

async def compile_prompt_to_yaml(prompt: str) -> AsyncIterator[str]:
    client = get_client()
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=True,
        temperature=0.2,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
