# Changelog

All notable changes to NeuroCore will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] — 2026-04-03

### Added

#### GeminiProvider (NC-FIX-001)
- `GeminiProvider` class implementing `LLMProvider` protocol using `google-genai` SDK
- Automatic message format conversion (system → `system_instruction`, assistant → model role)
- Async `complete()` and `stream()` via `client.aio.models.generate_content()`
- `"gemini"` handled by `build_provider()` factory
- `google-genai>=1.0` optional dependency group (`pip install neurocore-ai[gemini]`)
- `neurocore-skill-gemini-auditor` — adversarial reproducibility auditor using Gemini
- Updated `ac1-research.flow.yaml` blueprint: reviewer-auditor now uses Gemini provider

#### Retry & Exponential Backoff (NC-FIX-002)
- `max_retries`, `retry_delay_base`, `retry_delay_max`, `retry_on` fields on `SkillMeta`
- Truncated exponential backoff with full jitter in `_run_skill_async()`
- Warning-level structured logging on each retry attempt
- `neurocore-skill-base` shared package with `RateLimitError`, `ServiceUnavailableError`, `check_response()`
- All 13 research skill packages updated with retry configuration (v0.1.1)

### Changed
- Version bumped to 0.2.1
- `build_provider()` error message now includes `gemini` in expected providers
- `GeminiProvider` exported from `neurocore.llm` package

## [0.2.0] — 2026-04-03

### Added

#### Async Skill Execution (NC-001)
- `AsyncSkill` base class for skills whose `process()` is an async coroutine
- `is_async_skill()` helper to detect async skills at runtime
- Automatic async/sync detection — blueprints with any async skill execute in an asyncio event loop
- Sync skills wrapped automatically via `run_in_executor` when mixed with async skills

#### Concurrent DAG Execution (NC-002)
- Topological-layer DAG execution using `asyncio.gather()` for concurrent node processing
- Kahn's algorithm for computing execution layers from blueprint edges
- Cycle detection with clear error messages
- Context merging across concurrent nodes (last-write-wins per key)

#### Streaming Execution (NC-003)
- `execute_blueprint_stream()` async generator yielding `FlowEvent` objects in real-time
- `FlowEvent` and `FlowEventType` dataclasses for structured event data
- Event types: `FLOW_STARTED`, `STEP_STARTED`, `STEP_COMPLETED`, `STEP_FAILED`, `FLOW_COMPLETED`, `FLOW_FAILED`
- `--stream` flag on `neurocore run` for JSONL event output
- Duration tracking per step and per flow

#### LLM Provider Protocol (NC-004)
- `LLMProvider` runtime-checkable protocol for pluggable LLM backends
- `AnthropicProvider` — Claude integration via anthropic SDK
- `OpenAIProvider` — GPT integration via openai SDK
- `MockProvider` — deterministic testing provider with response queuing
- `build_provider()` factory from config dict
- `LLMMessage` and `LLMResponse` dataclasses
- `requires_llm` flag on `SkillMeta` — automatic provider injection during skill init
- `llm` attribute on `Skill` base class

#### AC1 Research Skills (NC-005) — separate pip-installable packages
- `neurocore-skill-arxiv` — arXiv preprint search and PDF download
- `neurocore-skill-openalex` — OpenAlex academic paper search with citation data
- `neurocore-skill-semantic-scholar` — Semantic Scholar search, recommendations, citations
- `neurocore-skill-tavily` — Tavily AI-optimized web search (search/extract/research modes)
- `neurocore-skill-exa` — Exa.ai neural semantic search for papers
- `neurocore-skill-core-api` — CORE full-text open access paper retrieval
- `neurocore-skill-unpaywall` — Unpaywall DOI-to-PDF resolver with concurrent lookups
- `neurocore-skill-qdrant` — Qdrant vector store (search/upsert modes)
- `neurocore-skill-grobid` — GROBID PDF-to-TEI XML parser
- `neurocore-skill-lean4` — Lean4 formal proof verification with certificate generation
- `neurocore-skill-sagemath` — SageMath computation (eval/script modes)
- `neurocore-skill-sympy` — SymPy symbolic math with sandboxed evaluation
- `neurocore-skill-oeis` — OEIS integer sequence lookup

#### AC1 Blueprint (NC-006)
- Reference `ac1-research.flow.yaml` blueprint wiring all AC1 skills into a DAG pipeline
- Concurrent literature discovery (arXiv + OpenAlex + Semantic Scholar + Tavily)
- Concurrent adversarial review (skeptic + alt-theory + auditor)
- Full pipeline: frontier scan → literature → full text → PDF parsing → knowledge integration → reasoning → review → verification → storage

#### Config Schema Extensions (NC-007)
- `LLMConfig` model for project-level LLM configuration
- Project-level LLM config auto-injected into skill configs when `llm_provider` not set at skill level
- Skill-level config overrides project-level LLM config
- Updated `neurocore init` scaffold template with LLM config section

### Changed
- Version bumped to 0.2.0
- `anthropic>=0.42` added as core dependency
- `pytest-asyncio>=0.24` added to dev dependencies
- `openai>=1.0` available as optional dependency (`pip install neurocore-ai[openai]`)
- Graph flow validation now requires both `nodes` and `edges` to be defined
- Project URLs updated to point to correct GitHub repository

## [0.1.0] — 2026-02-28

Initial release of NeuroCore — a pluggable, YAML-driven framework for building
agentic AI applications.

### Added

#### Core Framework
- `Skill` base class extending FlowEngine's `BaseComponent` with declarative metadata
- `SkillMeta` frozen dataclass for skill identity, versioning, dependencies, and data contracts
- Config validation against JSON Schema with type checking
- Health check interface for runtime monitoring

#### Configuration System
- YAML-based project configuration via `neurocore.yaml`
- `.env` file support with environment variable overlay
- Nested env var overrides using double-underscore syntax (`NEUROCORE_LOGGING__LEVEL`)
- Path resolution relative to project root
- `pydantic-settings` backed schema with type validation

#### Structured Logging
- `structlog` integration with console (colored, dev) and JSON (structured, production) renderers
- Per-module named loggers via `get_logger("module")`
- File output support alongside stderr

#### Skill Discovery
- Directory scanning — auto-discovers `Skill` subclasses from `.py` files in `skills/`
- Entry point scanning — loads skills from `neurocore.skills` entry point group in installed packages
- Unified `SkillRegistry` with entry points taking precedence over directory-discovered skills
- Registry supports `register()`, `get()`, `list_skills()`, `has()`

#### Runtime & Execution
- Blueprint parser — loads YAML flow files with skill-aware component resolution
- Blueprint validation — three-stage check (YAML parse, structure, skill references)
- Config merging — `neurocore.yaml` base + blueprint overlay (blueprint wins)
- FlowEngine executor — resolves skill names, creates instances, builds FlowConfig, executes
- `load_and_run()` convenience function for single-call execution
- Custom error hierarchy: `NeuroCoreError`, `ConfigError`, `SkillError`, `BlueprintError`, `ExecutionError`

#### CLI
- `neurocore init <name>` — scaffold new projects with templates
- `neurocore run <blueprint>` — execute blueprints with `--data`, `--json`, `--verbose` options
- `neurocore skill list` — Rich table of all discovered skills
- `neurocore skill info <name>` — detailed skill metadata, config schema, and health check
- `neurocore validate <blueprint>` — validate blueprints without executing
- `neurocore --version` — version display

#### NeuroWeave Integration (separate package: `neurocore-skill-neuroweave`)
- `NeuroWeaveSkill` wrapper bridging NeuroWeave's async API to sync FlowEngine
- Three operation modes: `process` (extract), `query` (retrieve), `context` (both)
- Async-to-sync bridge via `asyncio.run()`
- Lazy NeuroWeave initialization on first `process()` call
- Entry point registration for automatic discovery

#### Documentation & Examples
- README with quickstart, skill development guide, CLI reference, and configuration reference
- `echo_agent` example — minimal working project with echo and upper skills
- `research_agent` example — NeuroWeave-powered knowledge graph agent

#### Testing
- 265 unit and integration tests in neurocore
- 17 unit tests in neurocore-skill-neuroweave
- pytest + pytest-cov + pytest-mock test infrastructure
