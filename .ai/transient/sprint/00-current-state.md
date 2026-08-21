# Current Sprint: BitNet AI Runtime & Verticals Foundation

## Sprint Goal
Build the unified local AI agent runtime powered by 1-bit / edge inference with modular memory, tools, agent scheduler, REST/SSE server, CLI, and top 5 vertical business solutions.

## Completed Milestones
- [x] Knowledge base initialization (.ai/ docs)
- [x] Core runtime engine (inference, memory, tools, agent, server, CLI)
- [x] Verticals package (AI Employee, Personal Memory OS, AI Computer, WhatsApp Employee, QA Box)
- [x] Integration with live bitnet-server container at localhost:8080
- [x] Rigorous Architecture Audit (`docs/qa/review1.md`)
- [x] **Review 1 Remediations**:
  - [x] Decoupled runtime from verticals via dynamic plugin discovery (`VerticalRegistry`, `VerticalManifest`)
  - [x] Implemented deterministic capability and security policy engine (`SecurityPolicyEngine` with `PolicyDecision.ALLOW/DENY/ASK`)
  - [x] Fixed SQLite `:memory:` connection persistence in `DatabaseManager`
  - [x] Hardened ReAct loop with markdown fenced block JSON extraction, isolated prompt context delimiters (`<retrieved_local_context>`), and argument-aware loop detection
  - [x] Converted all hardcoded variables to environment variable and `.env` file loading (`.env`, `.env.example`, `pydantic-settings`, and `load_dotenv`)
  - [x] Expanded test suite to **34/34 tests passing** across all core modules, policies, plugins, and verticals
