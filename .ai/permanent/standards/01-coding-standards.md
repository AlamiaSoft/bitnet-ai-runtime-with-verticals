# Coding Standards & Invariants

## 1. Python Architecture Standards
- Python 3.11+ async-first implementation (syncio, httpx, FastAPI).
- Strict typing with mypy-compatible type annotations across all interfaces.
- Pydantic v2 schemas for all configuration, tool parameters, message payloads, and database DTOs.
- Clear error handling with domain exceptions: InferenceError, ToolExecutionError, MemoryIndexError.

## 2. Local-First & Zero-Leak Invariant
- Under no circumstances should agent thoughts, user documents, or vector embeddings be sent to external cloud APIs unless explicitly instructed by a user via a dedicated cloud tool.
- All persistent data resides locally in the user-configured storage directory (~/.bitnet_runtime/data/ or project root).

## 3. Tool Sandboxing
- Filesystem tools must enforce directory boundary containment (no escaping configured working directories without explicit permission).
- Shell commands must enforce timeout limits and prohibit recursive destructive commands.

## 4. Testing Standards
- 100% mocked offline tests for all inference engines and tool execution layers.
- Pytest suite with async support (pytest-asyncio).
