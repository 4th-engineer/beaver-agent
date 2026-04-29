"""Beaver Bot Skill Manager - Load, parse, and execute user-defined skills"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

import structlog

logger = structlog.get_logger()


class Skill:
    """Represents a loaded skill"""

    def __init__(self, name: str, category: str, description: str,
                 trigger: str, content: str, file_path: Path,
                 required_commands: List[str] = None,
                 required_environment_variables: List[str] = None):
        self.name = name
        self.category = category
        self.description = description
        self.trigger = trigger  # keyword or pattern to match
        self.content = content  # full SKILL.md content
        self.file_path = file_path
        self.required_commands = required_commands or []
        self.required_environment_variables = required_environment_variables or []

    def matches(self, user_input: str) -> bool:
        """Check if user input matches this skill's trigger"""
        if not self.trigger:
            return False
        trigger_lower = self.trigger.lower()
        input_lower = user_input.lower()
        return trigger_lower in input_lower

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "trigger": self.trigger,
            "file_path": str(self.file_path),
        }


class SkillManager:
    """Manages skill loading, discovery, and execution"""

    SKILL_FILE = "SKILL.md"
    DEFAULT_SKILLS_DIR = "skills"

    def __init__(self, project_root: Path, skills_dir: str = None):
        self.project_root = project_root
        self.skills_dir = Path(skills_dir) if skills_dir else project_root / self.DEFAULT_SKILLS_DIR
        self._skills: Dict[str, Skill] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        """Discover and load all skills from the skills directory"""
        if not self.skills_dir.exists():
            logger.warning("skills_dir_not_found", path=str(self.skills_dir))
            return

        for skill_path in self.skills_dir.rglob(self.SKILL_FILE):
            skill = self._parse_skill_file(skill_path)
            if skill:
                self._skills[skill.name] = skill
                logger.info("skill_loaded", name=skill.name, category=skill.category)

        logger.info("skills_loaded_total", count=len(self._skills))

    def _parse_skill_file(self, file_path: Path) -> Optional[Skill]:
        """Parse a SKILL.md file and extract metadata"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract YAML frontmatter
            frontmatter = self._extract_frontmatter(content)

            name = frontmatter.get("name", file_path.parent.name)
            category = frontmatter.get("category", "general")
            description = frontmatter.get("description", "")
            trigger = frontmatter.get("trigger", "")
            required_commands = frontmatter.get("required_commands", [])
            required_env_vars = frontmatter.get("required_environment_variables", [])

            return Skill(
                name=name,
                category=category,
                description=description,
                trigger=trigger,
                content=content,
                file_path=file_path,
                required_commands=required_commands,
                required_environment_variables=required_env_vars,
            )
        except Exception as e:
            logger.error("skill_parse_failed", file=str(file_path), error=str(e))
            return None

    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from skill content"""
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if match:
            try:
                return yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError as e:
                logger.warning("yaml_parse_failed", error=str(e))
        return {}

    def find_matching_skill(self, user_input: str) -> Optional[Skill]:
        """Find the first skill that matches the user input"""
        for skill in self._skills.values():
            if skill.matches(user_input):
                logger.debug("skill_matched", skill=skill.name, trigger=skill.trigger)
                return skill
        return None

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name"""
        return self._skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        """List all available skills"""
        return [skill.to_dict() for skill in self._skills.values()]

    def list_skills_by_category(self, category: str) -> List[Dict[str, Any]]:
        """List skills in a specific category"""
        return [
            skill.to_dict() for skill in self._skills.values()
            if skill.category == category
        ]

    def reload(self) -> None:
        """Reload all skills from disk"""
        self._skills.clear()
        self._load_skills()
