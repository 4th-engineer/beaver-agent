"""Tests for SkillManager"""

import tempfile
from pathlib import Path

import pytest

from beaver_agent.core.skill_manager import Skill, SkillManager, SkillPhase, SkillStep


@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestSkillManager:
    """Test SkillManager functionality"""

    @pytest.fixture
    def skill_manager(self, temp_skills_dir):
        """Create a SkillManager with test skills"""
        return SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )

    def test_load_empty_skills_dir(self, skill_manager):
        """Test loading from empty directory"""
        assert skill_manager.list_skills() == []

    def test_load_single_skill(self, temp_skills_dir):
        """Test loading a single skill"""
        skill_dir = temp_skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: test-skill
category: utility
description: A test skill
trigger: test
---

# Test Skill
Test content
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skills = manager.list_skills()

        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"
        assert skills[0]["trigger"] == "test"

    def test_parse_skill_file_full_frontmatter(self, temp_skills_dir):
        """Test _parse_skill_file extracts all frontmatter fields correctly"""
        skill_dir = temp_skills_dir / "full-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: full-skill
category: engineering
description: A comprehensive test skill
trigger: build
required_commands:
  - git
  - pytest
required_environment_variables:
  - MINIMAX_API_KEY
when_to_use: When you need to build something
checklist:
  - Item A
  - Item B
examples:
  - Example 1
  - Example 2
---

# Full Skill
Skill body content
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager._parse_skill_file(skill_dir / "SKILL.md")

        assert skill is not None
        assert skill.name == "full-skill"
        assert skill.category == "engineering"
        assert skill.description == "A comprehensive test skill"
        assert skill.trigger == "build"
        assert skill.required_commands == ["git", "pytest"]
        assert skill.required_environment_variables == ["MINIMAX_API_KEY"]
        assert skill.when_to_use == "When you need to build something"
        assert skill.checklist == ["Item A", "Item B"]
        assert skill.examples == ["Example 1", "Example 2"]
        assert "# Full Skill" in skill.content

    def test_parse_skill_file_legacy_steps_format(self, temp_skills_dir):
        """Test _parse_skill_file handles legacy steps frontmatter"""
        skill_dir = temp_skills_dir / "legacy-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: legacy-skill
category: testing
description: Legacy format skill
trigger: test
steps:
  - Step one
  - instruction: Step two with dict
    check: Verify step two
  - Step three
---

# Legacy Skill
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager._parse_skill_file(skill_dir / "SKILL.md")

        assert skill is not None
        assert len(skill.phases) == 1
        phase = skill.phases[0]
        assert phase.name == "Steps"
        assert len(phase.steps) == 3
        assert phase.steps[0].instruction == "Step one"
        assert phase.steps[1].instruction == "Step two with dict"
        assert phase.steps[1].check == "Verify step two"
        assert phase.steps[2].instruction == "Step three"

    def test_parse_skill_file_no_frontmatter(self, temp_skills_dir):
        """Test _parse_skill_file uses defaults when no frontmatter"""
        skill_dir = temp_skills_dir / "no-fm-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""# No Frontmatter Skill

Just content, no YAML frontmatter.
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager._parse_skill_file(skill_dir / "SKILL.md")

        assert skill is not None
        assert skill.name == "no-fm-skill"
        assert skill.category == "general"
        assert skill.description == ""
        assert skill.trigger == ""

    def test_find_matching_skill(self, temp_skills_dir):
        """Test finding a matching skill by trigger"""
        skill_dir = temp_skills_dir / "hello-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: hello-skill
category: utility
description: Hello skill
trigger: hello
---

# Hello Skill
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager.find_matching_skill("Hello, how are you?")

        assert skill is not None
        assert skill.name == "hello-skill"

    def test_no_matching_skill(self, temp_skills_dir):
        """Test no match returns None"""
        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager.find_matching_skill("Some unrelated input")
        assert skill is None

    def test_get_skill_by_name(self, temp_skills_dir):
        """Test getting a specific skill by name"""
        skill_dir = temp_skills_dir / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: my-skill
category: test
description: My skill
trigger: trigger-word
---

# My Skill
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager.get_skill("my-skill")

        assert skill is not None
        assert skill.name == "my-skill"

    def test_list_skills_by_category(self, temp_skills_dir):
        """Test filtering skills by category"""
        for name, category in [("skill-a", "utils"), ("skill-b", "utils"), ("skill-c", "analysis")]:
            skill_dir = temp_skills_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"""---
name: {name}
category: {category}
description: {name}
trigger: {name}
---

# {name}
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )

        utils = manager.list_skills_by_category("utils")
        assert len(utils) == 2

        analysis = manager.list_skills_by_category("analysis")
        assert len(analysis) == 1

    def test_skill_matches_case_insensitive(self, temp_skills_dir):
        """Test that skill matching is case insensitive"""
        skill_dir = temp_skills_dir / "case-test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: case-test
category: test
description: Case test
trigger: TeSt
---

# Case Test
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager.find_matching_skill("This is a TeSt input")
        assert skill is not None

    def test_reload(self, temp_skills_dir):
        """Test that reload() clears cache and re-discovers skills"""
        skill_dir = temp_skills_dir / "reload-test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: reload-test
category: test
description: Reload test
trigger: reload-trigger
---

# Reload Test
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        assert manager.get_skill("reload-test") is not None

        (skill_dir / "SKILL.md").write_text("""---
name: reload-test
category: test
description: Reload test modified
trigger: reload-trigger
---

# Reload Test Modified
""")
        manager.reload()
        skill = manager.get_skill("reload-test")
        assert skill is not None
        assert skill.description == "Reload test modified"

    def test_get_skill_not_found(self, temp_skills_dir):
        """Test that get_skill returns None for nonexistent skill"""
        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        assert manager.get_skill("nonexistent-skill") is None

    def test_list_skills_returns_all_fields(self, temp_skills_dir):
        """Test that list_skills returns complete skill info including category"""
        skill_dir = temp_skills_dir / "fields-test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: fields-test
category: my-category
description: Fields test
trigger: fields-trigger
---

# Fields Test
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skills = manager.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "fields-test"
        assert skills[0]["category"] == "my-category"


class TestSkill:
    """Test Skill class"""

    def test_skill_matches(self):
        """Test Skill.matches() method"""
        skill = Skill(
            name="test",
            category="test",
            description="test",
            trigger="hello",
            content="",
            file_path=Path("test.md"),
        )

        assert skill.matches("hello world")
        assert skill.matches("say hello")
        assert not skill.matches("goodbye")

    def test_skill_to_dict(self):
        """Test Skill.to_dict() method"""
        skill = Skill(
            name="my-skill",
            category="utils",
            description="A useful skill",
            trigger="do thing",
            content="# My Skill",
            file_path=Path("/path/to/skills/my-skill/SKILL.md"),
        )

        d = skill.to_dict()
        assert d["name"] == "my-skill"
        assert d["category"] == "utils"
        assert d["description"] == "A useful skill"
        assert d["trigger"] == "do thing"


class TestStructuredSkill:
    """Test structured skill parsing (Matt Pocock style)"""

    def test_parse_phases(self, temp_skills_dir):
        """Test parsing a skill with phases"""
        skill_dir = temp_skills_dir / "structured-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: structured-skill
category: engineering
description: A skill with phases and steps
trigger: build
when_to_use: When you need to build something
phases:
  - name: Plan
    instruction: Plan the work
    steps:
      - instruction: Step 1
        check: Verify step 1
      - instruction: Step 2
  - name: Execute
    steps:
      - instruction: Execute step
checklist:
  - Item 1
  - Item 2
examples:
  - Example 1
  - Example 2
---

# Skill Content
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager.get_skill("structured-skill")

        assert skill is not None
        assert skill.is_structured
        assert len(skill.phases) == 2
        assert skill.phases[0].name == "Plan"
        assert len(skill.phases[0].steps) == 2
        assert skill.phases[0].steps[0].check == "Verify step 1"
        assert len(skill.checklist) == 2
        assert len(skill.examples) == 2
        assert skill.when_to_use == "When you need to build something"

    def test_structured_skill_prompt(self, temp_skills_dir):
        """Test generating a prompt from structured skill"""
        skill_dir = temp_skills_dir / "prompt-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: prompt-skill
category: test
description: Test skill
trigger: test
when_to_use: For testing
phases:
  - name: Phase1
    instruction: Do phase 1
    steps:
      - instruction: Step 1
        check: Check 1
---

Content
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager.get_skill("prompt-skill")
        prompt = skill.get_prompt()

        assert "# prompt-skill" in prompt
        assert "**When to use**: For testing" in prompt
        assert "## Phase1" in prompt
        assert "Step 1" in prompt
        assert "Verify: Check 1" in prompt

    def test_legacy_steps_backward_compat(self, temp_skills_dir):
        """Test that legacy steps format still works"""
        skill_dir = temp_skills_dir / "legacy-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: legacy-skill
category: test
description: Legacy format
trigger: legacy
steps:
  - Do this
  - Then do that
  - instruction: Finally this
    check: Check it works
---

Content
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        skill = manager.get_skill("legacy-skill")

        assert skill is not None
        assert skill.is_structured
        assert len(skill.phases) == 1
        assert len(skill.phases[0].steps) == 3

    def test_to_dict_includes_new_fields(self, temp_skills_dir):
        """Test that to_dict includes new structured fields"""
        skill_dir = temp_skills_dir / "dict-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: dict-skill
category: test
description: Test
trigger: dict
when_to_use: Testing
phases:
  - name: Phase
    steps:
      - instruction: Step
checklist:
  - Item
examples:
  - Example
---

Content
""")

        manager = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        d = manager.get_skill("dict-skill").to_dict()

        assert d["when_to_use"] == "Testing"
        assert len(d["phases"]) == 1
        assert d["checklist"] == ["Item"]
        assert d["examples"] == ["Example"]


class TestSkillStepAndSkillPhase:
    """Test SkillStep and SkillPhase dataclasses"""

    def test_skill_step_basic(self):
        """Test SkillStep creation with required fields"""
        step = SkillStep(order=1, instruction="Run tests")
        assert step.order == 1
        assert step.instruction == "Run tests"
        assert step.check is None

    def test_skill_step_with_check(self):
        """Test SkillStep with optional check field"""
        step = SkillStep(order=2, instruction="Verify output", check="assert output == 'ok'")
        assert step.order == 2
        assert step.instruction == "Verify output"
        assert step.check == "assert output == 'ok'"

    def test_skill_step_equality(self):
        """Test SkillStep equality comparison"""
        step1 = SkillStep(order=1, instruction="Run tests")
        step2 = SkillStep(order=1, instruction="Run tests")
        step3 = SkillStep(order=2, instruction="Run tests")
        assert step1 == step2
        assert step1 != step3

    def test_skill_phase_basic(self):
        """Test SkillPhase creation with required fields"""
        phase = SkillPhase(name="Implementation", instruction="Implement the feature")
        assert phase.name == "Implementation"
        assert phase.instruction == "Implement the feature"
        assert phase.steps == []

    def test_skill_phase_with_steps(self):
        """Test SkillPhase with nested SkillSteps"""
        step1 = SkillStep(order=1, instruction="Write code")
        step2 = SkillStep(order=2, instruction="Run tests", check="pytest passes")
        phase = SkillPhase(name="Build", instruction="Build steps", steps=[step1, step2])
        assert len(phase.steps) == 2
        assert phase.steps[0].instruction == "Write code"
        assert phase.steps[1].check == "pytest passes"

    def test_skill_phase_equality(self):
        """Test SkillPhase equality comparison"""
        phase1 = SkillPhase(name="Test", instruction="test", steps=[])
        phase2 = SkillPhase(name="Test", instruction="test", steps=[])
        phase3 = SkillPhase(name="Build", instruction="test", steps=[])
        assert phase1 == phase2
        assert phase1 != phase3

    def test_skill_phase_references_steps(self):
        """Test SkillPhase step ordering is preserved"""
        steps = [SkillStep(order=i, instruction=f"Step {i}") for i in range(5)]
        phase = SkillPhase(name="All Steps", instruction="All", steps=steps)
        for i, step in enumerate(phase.steps):
            assert step.order == i
            assert step.instruction == f"Step {i}"
