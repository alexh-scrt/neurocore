# Changelog

All notable changes to NeuroCore will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
