# apps/api/services/compiler.py  — STUB, will be replaced in Task 4
from typing import AsyncIterator

async def compile_prompt_to_yaml(prompt: str) -> AsyncIterator[str]:
    # Stub: returns a minimal YAML so the endpoint works before Task 4
    yaml_stub = f"name: stub-agent\ndescription: {prompt[:50]}\nmodel: llama3.2\nschedule: null\ntools:\n  - memory_store\n"
    for char in yaml_stub:
        yield char
