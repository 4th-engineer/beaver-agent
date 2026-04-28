"""Beaver Bot Intent Parser"""

from typing import List

import structlog

logger = structlog.get_logger()


class IntentParser:
    """Parse user input to determine intent"""

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
    }

    def parse(self, user_input: str) -> str:
        """Parse user input and return intent"""

        user_input_lower = user_input.lower()

        # Check each intent pattern
        for intent, keywords in self.INTENT_PATTERNS.items():
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    logger.debug("intent_matched", intent=intent, keyword=keyword)
                    return intent

        # Default to general chat
        return "general_chat"

    def parse_with_confidence(self, user_input: str) -> tuple[str, float]:
        """Parse with confidence score"""
        intent = self.parse(user_input)

        # Calculate simple confidence based on keyword match count
        user_input_lower = user_input.lower()
        keywords = self.INTENT_PATTERNS.get(intent, [])
        match_count = sum(1 for kw in keywords if kw.lower() in user_input_lower)

        # More matches = higher confidence
        confidence = min(0.5 + (match_count * 0.1), 1.0)

        return intent, confidence

    def get_supported_intents(self) -> List[str]:
        """Return list of supported intents"""
        return list(self.INTENT_PATTERNS.keys())
