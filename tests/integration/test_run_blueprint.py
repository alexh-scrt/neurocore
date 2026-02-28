"""Integration test: blueprint execution end-to-end.

Tests the full flow: config loading → skill discovery → blueprint
parsing → execution via FlowEngine → context output.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flowengine import FlowContext

from neurocore.config.loader import load_config
from neurocore.runtime.blueprint import load_blueprint, validate_blueprint
from neurocore.runtime.executor import execute_blueprint, load_and_run
from neurocore.skills.loader import discover_skills


def _make_echo_project(tmp_path: Path) -> Path:
    """Create a project with an echo skill."""
    (tmp_path / "neurocore.yaml").write_text(
        "project:\n  name: integration-test\n"
        "skills:\n"
        "  echo:\n"
        "    prefix: 'ECHOED: '\n"
    )
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "echo.py").write_text(
        "from flowengine import FlowContext\n"
        "from neurocore.skills.base import Skill, SkillMeta\n"
        "\n"
        "class EchoSkill(Skill):\n"
        "    skill_meta = SkillMeta(\n"
        "        name='echo', version='1.0.0',\n"
        "        description='Echoes with optional prefix',\n"
        "        provides=['output'],\n"
        "        consumes=['input'],\n"
        "    )\n"
        "    def process(self, context: FlowContext) -> FlowContext:\n"
        "        prefix = self.config.get('prefix', '')\n"
        "        msg = context.get('input', '')\n"
        "        context.set('output', f'{prefix}{msg}')\n"
        "        return context\n"
    )
    return tmp_path


class TestLoadAndRun:
    """Test load_and_run() end-to-end."""

    def test_simple_echo(self, tmp_path: Path):
        project = _make_echo_project(tmp_path)
        bp_file = project / "flow.yaml"
        bp_file.write_text(
            "name: simple-echo\n"
            "components:\n"
            "  - name: e1\n"
            "    type: echo\n"
            "flow:\n"
            "  type: sequential\n"
            "  steps:\n"
            "    - component: e1\n"
        )

        result = load_and_run(
            bp_file, project_root=project,
            initial_data={"input": "hello"},
        )
        assert isinstance(result, FlowContext)
        # prefix from neurocore.yaml + input
        assert result.get("output") == "ECHOED: hello"

    def test_blueprint_config_overrides_yaml(self, tmp_path: Path):
        project = _make_echo_project(tmp_path)
        bp_file = project / "flow.yaml"
        bp_file.write_text(
            "name: override-test\n"
            "components:\n"
            "  - name: e1\n"
            "    type: echo\n"
            "    config:\n"
            "      prefix: 'CUSTOM: '\n"
            "flow:\n"
            "  type: sequential\n"
            "  steps:\n"
            "    - component: e1\n"
        )

        result = load_and_run(
            bp_file, project_root=project,
            initial_data={"input": "world"},
        )
        assert result.get("output") == "CUSTOM: world"

    def test_multi_step_pipeline(self, tmp_path: Path):
        """Two skills in sequence."""
        (tmp_path / "neurocore.yaml").write_text(
            "project:\n  name: multi-test\n"
        )
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "pipeline.py").write_text(
            "from flowengine import FlowContext\n"
            "from neurocore.skills.base import Skill, SkillMeta\n"
            "\n"
            "class PrepSkill(Skill):\n"
            "    skill_meta = SkillMeta(name='prep', version='0.1.0')\n"
            "    def process(self, context: FlowContext) -> FlowContext:\n"
            "        context.set('prepared', context.get('raw', '').strip())\n"
            "        return context\n"
            "\n"
            "class FormatSkill(Skill):\n"
            "    skill_meta = SkillMeta(name='format', version='0.1.0')\n"
            "    def process(self, context: FlowContext) -> FlowContext:\n"
            "        context.set('formatted', context.get('prepared', '').upper())\n"
            "        return context\n"
        )

        bp_file = tmp_path / "pipeline.yaml"
        bp_file.write_text(
            "name: pipeline\n"
            "components:\n"
            "  - name: step1\n"
            "    type: prep\n"
            "  - name: step2\n"
            "    type: format\n"
            "flow:\n"
            "  type: sequential\n"
            "  steps:\n"
            "    - component: step1\n"
            "    - component: step2\n"
        )

        result = load_and_run(
            bp_file, project_root=tmp_path,
            initial_data={"raw": "  hello world  "},
        )
        assert result.get("prepared") == "hello world"
        assert result.get("formatted") == "HELLO WORLD"


class TestValidateThenRun:
    """Validate a blueprint, then run it."""

    def test_validate_and_run(self, tmp_path: Path):
        project = _make_echo_project(tmp_path)
        bp_file = project / "flow.yaml"
        bp_file.write_text(
            "name: validated\n"
            "components:\n"
            "  - name: e1\n"
            "    type: echo\n"
            "flow:\n"
            "  type: sequential\n"
            "  steps:\n"
            "    - component: e1\n"
        )

        # Validate
        config = load_config(project_root=project)
        registry = discover_skills(config)
        bp = load_blueprint(bp_file)
        errors = validate_blueprint(bp, registry)
        assert errors == []

        # Run
        result = execute_blueprint(bp, registry, config, initial_data={"input": "test"})
        assert result.get("output") == "ECHOED: test"
