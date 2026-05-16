"""Beaver Agent Intent Parser - Skill-based intent routing."""

from typing import List, Optional, Tuple

import structlog

from beaver_agent.core.skill_manager import SkillManager

logger = structlog.get_logger()

__all__ = ["IntentParser"]


class IntentParser:
    """Parse user input to determine intent, with skill-based routing.

    Resolves user input through an ordered pipeline:
    1. **Skill invocation** — lines starting with ``/skill`` → ``skill_invocation``
    2. **Skill routing** — if a SkillManager is attached, matched skills via
       ``skill:<name>`` prefix (0.95 confidence)
    3. **Pattern matching** — keyword matching against ``INTENT_PATTERNS`` dict
       (0.5–1.0 confidence based on keyword count)
    4. **Fallback** — ``general_chat`` when no pattern matches

    Attributes:
        INTENT_PATTERNS: Class-level dict mapping intent names to keyword lists.
            Keys: ``code_generation``, ``code_review``, ``debug``,
            ``github_operation``, ``file_operation``, ``terminal_operation``,
            ``skill_invocation``.
        skill_manager: Optional SkillManager instance for skill-based routing.

    Example:
        >>> parser = IntentParser()
        >>> parser.parse("帮我review代码")
        'code_review'
        >>> parser.parse("帮我写一个函数")
        'code_generation'
        >>> parser.parse("/skill github")
        'skill_invocation'
    """

    INTENT_PATTERNS = {
        "code_generation": [
            "写",
            "生成",
            "创建",
            "编写",
            "implement",
            "write",
            "generate",
            "create",
            "帮我写",
            "帮我生成",
            "写一个",
            "写段代码",
            "写个函数",
            "写个类",
        ],
        "code_review": [
            "review",
            "审查",
            "检查",
            "分析代码",
            "看看代码",
            "review一下",
            "检查代码",
            "代码审查",
            "review 代码",
        ],
        "debug": [
            "debug",
            "调试",
            "报错",
            "错误",
            "exception",
            "traceback",
            "修复",
            "问题",
            "bug",
            "出错",
            "崩溃",
            "segmentation fault",
        ],
        "github_operation": [
            "github",
            "仓库",
            "repo",
            "issue",
            "pr",
            "pull request",
            "创建仓库",
            "创建issue",
            "查看pr",
        ],
        "file_operation": ["读取文件", "读取代码", "打开文件", "查看文件", "cat", "read file"],
        "terminal_operation": ["运行", "执行", "命令", "跑", "terminal", "run command", "执行命令"],
        "skill_invocation": ["/skill"],
    }

    def __init__(self, skill_manager: Optional[SkillManager] = None) -> None:
        """Initialize IntentParser with optional SkillManager.

        Args:
            skill_manager: Optional SkillManager instance for skill-based
                intent routing. When provided, the parser will check skills
                before falling back to keyword pattern matching.
        """
        self.skill_manager = skill_manager

    def parse(self, user_input: str) -> str:
        """Parse user input and return the primary intent name.

        Resolution order: skill invocation (/skill prefix) → skill routing
        (trigger match) → pattern keyword matching → general_chat fallback.

        Args:
            user_input: The raw user input string to analyze.

        Returns:
            Intent name string: one of the INTENT_PATTERNS keys, a
            ``skill:<name>`` prefixed string for skill-matched inputs,
            ``skill_invocation`` for /skill commands, or ``general_chat``
            when no pattern matches.

        Example:
            >>> parser = IntentParser()
            >>> parser.parse("帮我review代码")
            'code_review'
            >>> parser.parse("帮我写一个函数")
            'code_generation'
        """

        # Check for skill invocation first
        if user_input.strip().startswith("/skill "):
            return "skill_invocation"

        # Check if any skill matches
        if self.skill_manager:
            matched_skill = self.skill_manager.find_matching_skill(user_input)
            if matched_skill:
                logger.debug("skill_triggered", skill=matched_skill.name)
                return f"skill:{matched_skill.name}"

        # Fall back to intent patterns
        user_input_lower = user_input.lower()

        for intent, keywords in self.INTENT_PATTERNS.items():
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    logger.debug("intent_matched", intent=intent, keyword=keyword)
                    return intent

        return "general_chat"

    def parse_with_confidence(self, user_input: str) -> Tuple[str, float]:
        """Parse user input and return intent with confidence score.

        Args:
            user_input: The raw user input string to analyze.

        Returns:
            A tuple of (intent_name, confidence_score) where confidence_score
            is a float between 0.0 and 1.0. Skill invocations get 0.95 confidence,
            pattern matches get 0.5-1.0 based on keyword match count.

        Example:
            >>> parser = IntentParser()
            >>> intent, conf = parser.parse_with_confidence("帮我review代码")
            >>> print(f"{intent}: {conf:.2f}")
            code_review: 0.70
        """
        intent = self.parse(user_input)

        # Skill matches get high confidence
        if intent.startswith("skill:") or intent == "skill_invocation":
            return intent, 0.95

        # Calculate confidence based on keyword match count
        user_input_lower = user_input.lower()
        keywords = self.INTENT_PATTERNS.get(intent, [])
        match_count = sum(1 for kw in keywords if kw.lower() in user_input_lower)

        confidence = min(0.5 + (match_count * 0.1), 1.0)
        return intent, confidence

    def get_supported_intents(self) -> List[str]:
        """Return all supported intent names.

        Returns the union of built-in INTENT_PATTERNS keys and any
        loaded skill names prefixed with ``skill:``.

        Returns:
            A list of all supported intent name strings.

        Example:
            >>> parser = IntentParser(skill_manager)
            >>> "code_generation" in parser.get_supported_intents()
            True
            >>> "skill:github" in parser.get_supported_intents()
            True
        """
        intents = list(self.INTENT_PATTERNS.keys())

        # Add skill names if skill_manager is available
        if self.skill_manager:
            for skill in self.skill_manager.list_skills():
                intents.append(f"skill:{skill['name']}")

        return intents

    def set_skill_manager(self, skill_manager: SkillManager) -> None:
        """Attach a SkillManager for skill-based intent routing.

        After calling this, :meth:`parse` and :meth:`parse_with_confidence`
        will attempt to match user input against loaded skills before
        falling back to keyword patterns.

        Args:
            skill_manager: The SkillManager instance to use for skill lookups.
        """
        self.skill_manager = skill_manager
