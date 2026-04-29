"""Tests for SkillManager"""

import tempfile
from pathlib import Path

import pytest

from beaver_bot.core.skill_manager import SkillManager, Skill


class TestSkillManager:
    """Test SkillManager functionality"""

    @pytest.fixture
    def temp_skills_dir(self):
        """Create a temporary skills directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def skill_manager(self, temp_skills_dir):
        """Create a SkillManager with test skills"""
        return SkillManager(project_root=temp_skills_dir.parent, skills_dir=str(temp_skills_dir))

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

        manager = SkillManager(project_root=temp_skills_dir.parent, skills_dir=str(temp_skills_dir))
        skills = manager.list_skills()

        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"
        assert skills[0]["trigger"] == "test"

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

        manager = SkillManager(project_root=temp_skills_dir.parent, skills_dir=str(temp_skills_dir))
        skill = manager.find_matching_skill("Hello, how are you?")

        assert skill is not None
        assert skill.name == "hello-skill"

    def test_no_matching_skill(self, temp_skills_dir):
        """Test no match returns None"""
        manager = SkillManager(project_root=temp_skills_dir.parent, skills_dir=str(temp_skills_dir))
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

        manager = SkillManager(project_root=temp_skills_dir.parent, skills_dir=str(temp_skills_dir))
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

        manager = SkillManager(project_root=temp_skills_dir.parent, skills_dir=str(temp_skills_dir))

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

        manager = SkillManager(project_root=temp_skills_dir.parent, skills_dir=str(temp_skills_dir))
        skill = manager.find_matching_skill("This is a TeSt input")
        assert skill is not None


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
