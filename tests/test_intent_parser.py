"""Tests for Beaver Bot Intent Parser"""

import tempfile
from pathlib import Path

import pytest

from beaver_agent.core.intent_parser import IntentParser


@pytest.fixture
def parser():
    return IntentParser()


@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory for skill manager tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_code_generation_intent(parser):
    """Test code generation intent detection"""
    assert parser.parse("帮我写一个快排") == "code_generation"
    assert parser.parse("写一个函数") == "code_generation"
    assert parser.parse("generate code") == "code_generation"
    assert parser.parse("帮我生成代码") == "code_generation"


def test_code_review_intent(parser):
    """Test code review intent detection"""
    assert parser.parse("帮我review代码") == "code_review"
    assert parser.parse("检查代码问题") == "code_review"
    assert parser.parse("review一下") == "code_review"


def test_debug_intent(parser):
    """Test debug intent detection"""
    assert parser.parse("代码报错了") == "debug"
    assert parser.parse("调试一下") == "debug"
    assert parser.parse("程序崩溃了") == "debug"


def test_github_operation_intent(parser):
    """Test GitHub operation intent detection"""
    assert parser.parse("查看这个issue") == "github_operation"
    assert parser.parse("github仓库信息") == "github_operation"
    # "创建一个PR" matches "创建" first (code_generation)
    assert parser.parse("PR信息") == "github_operation"


def test_general_chat_intent(parser):
    """Test general chat fallback"""
    assert parser.parse("今天天气怎么样") == "general_chat"
    assert parser.parse("你好啊") == "general_chat"


def test_intent_with_confidence(parser):
    """Test intent parsing with confidence"""
    intent, confidence = parser.parse_with_confidence("帮我写一个快排算法")
    assert intent == "code_generation"
    assert 0.5 <= confidence <= 1.0


def test_get_supported_intents(parser):
    """Test getting supported intents"""
    intents = parser.get_supported_intents()
    assert "code_generation" in intents
    assert "code_review" in intents
    assert "debug" in intents


def test_parse_empty_whitespace_input(parser):
    """Test that empty or whitespace-only input returns general_chat"""
    assert parser.parse("") == "general_chat"
    assert parser.parse("   ") == "general_chat"
    assert parser.parse("\t") == "general_chat"
    assert parser.parse("\n") == "general_chat"


def test_parse_with_confidence_general_chat(parser):
    """Test parse_with_confidence returns 0.5 confidence for general_chat fallback"""
    intent, conf = parser.parse_with_confidence("random text that matches nothing")
    assert intent == "general_chat"
    assert conf == 0.5


def test_parse_with_confidence_skill_invocation_direct(parser):
    """Test parse_with_confidence returns 0.95 confidence for /skill direct command.

    /skill some-skill is a direct skill invocation command (not a skill trigger),
    matching the 'skill_invocation' pattern (keyword: '/skill'). Direct /skill
    commands get 0.95 confidence just like skill triggers (skill:<name>).
    """
    intent, conf = parser.parse_with_confidence("/skill some-skill")
    assert intent == "skill_invocation"
    assert conf == 0.95


def test_parse_file_operation_intent(parser):
    """Test file operation intent detection"""
    assert parser.parse("帮我读取文件") == "file_operation"
    # Must use exact pattern "打开文件" not just "打开"
    assert parser.parse("打开文件 /tmp/test.py") == "file_operation"


def test_parse_terminal_operation_intent(parser):
    """Test terminal operation intent detection"""
    assert parser.parse("运行这个命令") == "terminal_operation"
    assert parser.parse("执行 python test.py") == "terminal_operation"


def test_parse_skill_invocation_direct(parser):
    """Test skill invocation via /skill prefix returns skill_invocation"""
    assert parser.parse("/skill my-skill") == "skill_invocation"
    assert parser.parse("/skill   another-skill") == "skill_invocation"


class TestIntentParserWithSkillManager:
    """Test IntentParser when a SkillManager is attached."""

    def test_set_skill_manager(self, parser, temp_skills_dir):
        """Test that set_skill_manager correctly attaches a SkillManager"""
        from beaver_agent.core.skill_manager import SkillManager

        sm = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        parser.set_skill_manager(sm)
        assert parser.skill_manager is sm

    def test_get_supported_intents_includes_skills(self, parser, temp_skills_dir):
        """Test that get_supported_intents includes skill names when manager is set"""
        from beaver_agent.core.skill_manager import SkillManager

        # Create a test skill
        skill_dir = temp_skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: test-skill
category: test
description: A test skill
trigger: test-trigger
---

# Test Skill
""")
        sm = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        parser.set_skill_manager(sm)

        intents = parser.get_supported_intents()
        assert "skill:test-skill" in intents

    def test_parse_with_skill_manager_routes_to_skill(self, parser, temp_skills_dir):
        """Test that parse routes to skill when trigger matches"""
        from beaver_agent.core.skill_manager import SkillManager

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
        sm = SkillManager(
            project_root=temp_skills_dir.parent,
            skills_dirs={"user": temp_skills_dir, "builtin": Path("/nonexistent")},
        )
        parser.set_skill_manager(sm)

        result = parser.parse("Hello there!")
        assert result == "skill:hello-skill"
