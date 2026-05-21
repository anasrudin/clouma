# apps/api/agent_runtime/claw_runner.py
"""Claw Code subprocess orchestrator — replaces Google ADK for agent execution.

Spawns the `claw` binary in one-shot mode, injecting the agent's instruction
via CLAUDE.md in a temporary workspace. Stdout is streamed in real-time as
`adk_event` text events compatible with the sessions WebSocket protocol.

Multi-turn conversation history is maintained in-memory and prepended to each
new user message so claw has context across turns within a single session.

Configuration
-------------
CLAW_BINARY       Path to the compiled claw binary.
                  Default: bin/claw (macOS) or bin/claw-linux-x64 (Linux).
CLAW_MODEL        Model name passed to claw. Defaults to LLM_MODEL from env.

Provider (pick one):
  Anthropic:      set ANTHROPIC_API_KEY
  OpenAI-compat:  set OPENAI_API_KEY + OPENAI_BASE_URL  ← for NVIDIA/Qwen
  xAI:            set XAI_API_KEY
  DashScope:      set DASHSCOPE_API_KEY
"""
from __future__ import annotations

import asyncio
import os
import platform as _platform
import re
import tempfile
from pathlib import Path
from typing import AsyncIterator

_REPO_ROOT = Path(__file__).parents[3]
_IS_LINUX = _platform.system() == "Linux"
_DEFAULT_CLAW = _REPO_ROOT / "bin" / ("claw-linux-x64" if _IS_LINUX else "claw")
CLAW_BINARY: Path = Path(os.environ.get("CLAW_BINARY", str(_DEFAULT_CLAW)))

# Default to whatever LLM_MODEL Clouma is already configured with
CLAW_MODEL: str = os.environ.get("CLAW_MODEL", os.environ.get("LLM_MODEL", "claude-sonnet-4-6"))

# Strip ANSI escape sequences from claw's terminal output
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHFABCDEFSTJ]|\x1b\].*?\x07|\r")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _build_prompt(instruction: str, history: list[tuple[str, str]], user_input: str) -> str:
    """Build the full prompt including conversation history."""
    parts: list[str] = []
    if history:
        parts.append("Previous conversation:")
        for u, a in history:
            parts.append(f"User: {u}")
            parts.append(f"Assistant: {a}")
        parts.append("")
    parts.append(user_input)
    return "\n".join(parts)


async def run_claw_turn(
    instruction: str,
    user_input: str,
    history: list[tuple[str, str]] | None = None,
) -> AsyncIterator[dict]:
    """Execute one agent turn through the claw orchestrator.

    Yields dicts in the WebSocket event format:
      {"type": "adk_event", "raw": {...}}    — streaming text / turn_complete
      {"type": "stream_error", "error": "..."} — on failure

    Args:
        instruction: Agent system instruction (injected via CLAUDE.md).
        user_input:  The user's message for this turn.
        history:     List of (user_msg, assistant_response) from prior turns.
    """
    if not CLAW_BINARY.exists():
        yield {
            "type": "stream_error",
            "error": f"claw binary not found at {CLAW_BINARY}.",
        }
        return

    # Build provider env for claw.
    # We read from Clouma's settings object (not os.environ) to guarantee the
    # values are always available regardless of how the server was started.
    # claw auto-selects the provider based on which env vars are present:
    #   OPENAI_API_KEY + OPENAI_BASE_URL  → any OpenAI-compatible endpoint
    #   ANTHROPIC_API_KEY                 → Anthropic
    from api.config import settings as _settings  # local import avoids circular
    provider_env: dict[str, str] = {}

    if _settings.llm_api_key and _settings.llm_base_url:
        # claw hardcodes qwen/* models to DASHSCOPE_* env vars.
        # For any other model it uses OPENAI_* env vars.
        # We set both so whichever routing claw picks, it hits our endpoint.
        provider_env["DASHSCOPE_API_KEY"] = _settings.llm_api_key
        provider_env["DASHSCOPE_BASE_URL"] = _settings.llm_base_url
        provider_env["OPENAI_API_KEY"] = _settings.llm_api_key
        provider_env["OPENAI_BASE_URL"] = _settings.llm_base_url
    elif os.environ.get("ANTHROPIC_API_KEY"):
        provider_env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    else:
        yield {
            "type": "stream_error",
            "error": "No LLM credentials found. Set LLM_API_KEY + LLM_BASE_URL in .env.",
        }
        return

    full_prompt = _build_prompt(instruction, history or [], user_input)

    with tempfile.TemporaryDirectory(prefix="clouma_claw_") as tmpdir:
        # Inject agent instruction as CLAUDE.md so claw loads it as system context
        (Path(tmpdir) / "CLAUDE.md").write_text(
            f"# System Instruction\n\n{instruction}\n"
        )

        cmd = [
            str(CLAW_BINARY),
            "--model", CLAW_MODEL,
            "prompt",
            full_prompt,
        ]

        env = {
            **os.environ,
            **provider_env,
            # Disable color output so we get clean plain text
            "NO_COLOR": "1",
            "TERM": "dumb",
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=tmpdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError:
            yield {"type": "stream_error", "error": f"claw binary not executable: {CLAW_BINARY}"}
            return

        # Stream stdout in 256-byte chunks → text events
        accumulated = ""
        while True:
            chunk = await proc.stdout.read(256)
            if not chunk:
                break
            text = _strip_ansi(chunk.decode("utf-8", errors="replace"))
            if text:
                accumulated += text
                yield {
                    "type": "adk_event",
                    "raw": {
                        "author": "agent",
                        "content": {"role": "model", "parts": [{"text": text}]},
                        "turn_complete": False,
                    },
                }

        await proc.wait()

        if proc.returncode != 0:
            try:
                stderr_bytes = await asyncio.wait_for(proc.stderr.read(), timeout=2.0)
            except asyncio.TimeoutError:
                stderr_bytes = b""
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")[:500]
            yield {
                "type": "stream_error",
                "error": f"claw exited {proc.returncode}: {stderr_text}",
            }
            return

        # turn_complete carries accumulated text so the caller can update history
        yield {
            "type": "adk_event",
            "raw": {
                "author": "agent",
                "turn_complete": True,
                "_claw_response": accumulated,
            },
        }
