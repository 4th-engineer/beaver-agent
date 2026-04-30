"""Beaver Bot Intent Parser v2 - With Skill routing"""

from typing import List, Optional, Tuple

import structlog

from beaver_agent.core.skill_manager import SkillManager

logger = structlog.get_logger()


class IntentParser:
    """Parse user input to determine intent, with skill support"""

    INTENT_PATTERNS = {
        "code_generation": [
            "写", "生成", "创建", "编写", "implement", "write", "generate", "create",
            "帮我写", "帮我生成", "写一个", "写段代码", "写个函数", "写个类"
        ],
        "code_review": [
            "review", "审查", "检查", "分析代码", "看看代码", "review一下",
            "检查代码", "代码审查", "review 代码"
        ],
        "debug": [
            "debug", "调试", "报错", "错误", "exception", "traceback", "修复",
            "问题", "bug", "出错", "崩溃", "segmentation fault"
        ],
        "github_operation": [
            "github", "仓库", "repo", "issue", "pr", "pull request", "创建仓库",
            "创建issue", "查看pr"
        ],
        "file_operation": [
            "读取文件", "读取代码", "打开文件", "查看文件", "cat", "read file"
        ],
        "terminal_operation": [
            "运行", "执行", "命令", "跑", "terminal", "run command", "执行命令"
        ],
        "skill_invocation": [
            "/skill"
        ],
    }

    def __init__(self, skill_manager: Optional[SkillManager] = None):
        self.skill_manager = skill_manager

    def parse(self, user_input: str) -> str:
        """Parse user input and return intent"""

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
        """Parse with confidence score"""
        intent = self.parse(user_input)

        # Skill matches get high confidence
        if intent.startswith("skill:"):
            return intent, 0.95

        # Calculate confidence based on keyword match count
        user_input_lower = user_input.lower()
        keywords = self.INTENT_PATTERNS.get(intent, [])
        match_count = sum(1 for kw in keywords if kw.lower() in user_input_lower)

        confidence = min(0.5 + (match_count * 0.1), 1.0)
        return intent, confidence

    def get_supported_intents(self) -> List[str]:
        """Return list of supported intents"""
        intents = list(self.INTENT_PATTERNS.keys())

        # Add skill names if skill_manager is available
        if self.skill_manager:
            for skill in self.skill_manager.list_skills():
                intents.append(f"skill:{skill['name']}")

        return intents

    def set_skill_manager(self, skill_manager: SkillManager) -> None:
        """Set the skill manager"""
        self.skill_manager = skill_manager
