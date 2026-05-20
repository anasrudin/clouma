Now build the actual managed-agent orchestration runtime for Clouma.

IMPORTANT:
The frontend already exists.

Focus ONLY on backend orchestration and autonomous agent execution.

==================================================
GOAL
==================================================

Users can type:

"Create an agent that researches trending AI startups every morning and sends a summary to Telegram."

The system should automatically:
- infer tools
- infer workflows
- generate YAML spec
- create execution plan
- bind sandbox runtime
- persist memory
- schedule execution
- stream events in realtime

==================================================
BUILD
==================================================

Implement:

1. Prompt-to-Agent Compiler
- NLP intent extraction
- tool inference
- environment inference
- YAML generation
- validation

2. Agent State Machine
States:
- created
- planning
- provisioning
- running
- waiting
- retrying
- paused
- completed
- failed

3. Execution Runtime
- autonomous loop
- tool execution
- reflection
- retry logic
- checkpointing
- memory persistence

4. CCU Runtime Adapter
Implement adapters for:
- browser sandbox
- terminal sandbox
- filesystem
- websocket streaming
- persistent sessions

5. Event Streaming
Realtime websocket events:
- token streaming
- tool calls
- logs
- browser events
- checkpoints
- execution traces

6. Memory System
- conversation memory
- vector memory
- episodic memory
- retrieval system

7. Scheduler
- cron execution
- delayed tasks
- autonomous agents

8. Multi-Agent Architecture
- supervisor agents
- worker agents
- delegation
- shared memory

==================================================
STACK
==================================================

Use:
- FastAPI
- Temporal
- Redis
- Postgres
- Qdrant
- Kubernetes

==================================================
OUTPUT
==================================================

Generate:
- architecture
- service boundaries
- database schema
- execution flow
- API routes
- websocket protocol
- orchestration logic
- runtime pseudocode
- repo structure
- MVP implementation order

IMPORTANT:
This is NOT a chatbot.

This is a managed autonomous cloud agent runtime platform.