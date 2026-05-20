---
source: https://ai.google.dev/gemini-api/docs/antigravity-agent
fetched: 2026-05-20
---

# Antigravity Agent

The Antigravity agent is a general-purpose managed agent on the Gemini API. A single API call gives you an agent that reasons, executes code, manages files, and browses the web inside your own secure Linux sandbox, hosted by Google.

It is powered by Gemini 3.5 Flash and uses the same harness as the Antigravity IDE. Available through the [Interactions API](/gemini-api/docs/interactions) and [Google AI Studio](https://aistudio.google.com).

## Capabilities

Each call can provision a Linux sandbox and starts a tool-use loop. The agent plans, acts, observes results, and repeats until the task is done.

* **Code execution:** Run Bash, Python, and Node.js commands. Install packages, run tests, build apps.
* **File management:** Read, write, edit, search, and list files in the sandbox. Files persist across interactions.
* **Web access:** Google Search and URL fetching for data.
* **Context compaction:** Automatic context compaction (triggered at ~135k tokens) to support long-running, multi-turn sessions without losing context or hitting token limits.

## Supported tools

By default, the agent has access to `code_execution`, `google_search`, and `url_context`. Filesystem tools are enabled automatically when you specify the `environment` parameter. You only need to specify the `tools` parameter when customizing or restricting the default set.

| Tool | Type value | Description |
|------|-----------|-------------|
| Code Execution | `code_execution` | Run shell commands (bash, Python, Node) with stdout/stderr capture. |
| Google Search | `google_search` | Search the public web. |
| URL Context | `url_context` | Fetch and read web pages. |
| Filesystem | _(enabled via `environment`)_ | Read, write, edit, search, and list files in the sandbox. No separate tool type; enabled automatically when `environment` is set. |

## Multimodal Input

The Antigravity agent supports multimodal inputs. Currently, only `text` and `image` inputs are supported. Images must be supplied as inline base64-encoded strings (`data`).

## Customizing the agent

You can extend the Antigravity agent by customizing its instructions, tools, and environment. The agent supports a filesystem-native approach to customization: you can mount files like `AGENTS.md` for instructions and skills under `.agents/skills/` directly into the sandbox, or pass configuration inline at interaction time. You can iterate on your configuration inline and then save it as a managed agent when you are ready.

For full details on how to build custom agents, see [Building Managed Agents](/gemini-api/docs/custom-agents).

## Environments

Each call creates or reuses a Linux sandbox. The `environment` parameter takes three forms:

| Form | Description |
|------|-------------|
| `"remote"` | Provision a fresh sandbox with default settings. |
| `"env_abc123"` | Reuse an existing environment by ID, preserving all files and state. |
| `{...}` | Full `EnvironmentConfig` with custom sources and network rules. |

See [Environments](/gemini-api/docs/agent-environment) for details on sources (Git, GCS, inline), networking, lifecycle, and resource limits.

## Availability and pricing

Antigravity agent is available in preview through the [Interactions API](/gemini-api/docs/interactions) in Google AI Studio and the Gemini API.

Pricing follows a [pay-as-you-go model](/gemini-api/docs/pricing#pricing-for-agents) based on the underlying Gemini model tokens and the tools the agent uses. Unlike a standard chat request that produces a single output, an Antigravity interaction is an agentic workflow. A single request triggers an autonomous loop of reasoning, tool execution, code running, and file management.

**Note:** Unlike standard Gemini models, the Antigravity agent runs through multiple autonomous loops per interaction and can accumulate a high number of tokens. You can monitor your agent runs (through [SSE streaming](/gemini-api/docs/interactions/streaming)) and cancel the request if the agent appears to be stuck or is running longer than expected.

### Estimated costs

Costs vary based on task complexity. The agent autonomously determines how many tool calls, code executions, and file operations are needed. The following estimates are based on runs.

| Task category | Input tokens | Output tokens | Typical cost |
|---------------|-------------|--------------|-------------|
| **Research & information synthesis** | 100k–500k | 10k–40k | $0.30–$1.00 |
| **Document & content generation** | 100k–500k | 15k–50k | $0.30–$1.30 |
| **Process & system design** | 100k–400k | 10k–30k | $0.25–$0.80 |
| **Data processing & analysis** | 300k–3M | 30k–150k | $0.70–$3.25 |

50–70% of input tokens are typically cached. Complex agentic workflows with many tool calls can accumulate 3–5 million tokens in a single interaction, with costs up to ~$5.

**Environment compute** (CPU, memory, sandbox execution) is **not billed** during the preview period.

## Limitations

* **Preview status:** The Antigravity agent and the Interactions API are in preview. Features and schemas may change.
* **Unsupported generation config:** The following parameters are not supported and return a 400 error: `temperature`, `top_p`, `top_k`, `stop_sequences`, `max_output_tokens`.
* **Structured output:** The Antigravity agent does not support structured outputs.
* **Unavailable tools:** `file_search`, `computer_use`, `google_maps`, `function_calling` and `mcp` are not yet supported.
* **Filesystem tool:** There is no filesystem tool at the moment. It is part of the `environment`.
* **Background:** Agent does not support using `background=True` and requires `store=True`.
* **Unsupported multimodal types.** Audio, video, and document inputs are not supported at the moment. Only text and image are allowed.

## What's next

* [Quickstart](/gemini-api/docs/managed-agents-quickstart): multi-turn conversations and streaming.
* [Building Custom Agents](/gemini-api/docs/custom-agents): custom instructions, skills, and saving agents.
* [Environments](/gemini-api/docs/agent-environment): sandbox configuration, sources, networking.
* [Deep Research Agent](/gemini-api/docs/interactions/deep-research): long-form research tasks.
* [Interactions API](/gemini-api/docs/interactions): the underlying API.
