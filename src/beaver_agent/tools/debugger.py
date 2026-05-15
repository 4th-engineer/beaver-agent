"""Beaver Agent Debugger Tool"""

from typing import Optional

import structlog

logger = structlog.get_logger()

__all__ = ["DebuggerTool"]

# Common Python error patterns — module-level constant, no per-call rebuild
_COMMON_ERRORS = {
    "indexerror": {
        "cause": "索引超出序列范围",
        "fix": "检查索引是否在有效范围内，使用 len() 验证",
    },
    "keyerror": {
        "cause": "字典中不存在该键",
        "fix": "使用 dict.get() 方法或先检查键是否存在",
    },
    "attributeerror": {
        "cause": "对象没有该属性或方法",
        "fix": "检查对象类型，确保属性/方法存在",
    },
    "typeerror": {"cause": "类型不匹配", "fix": "检查变量类型，使用 isinstance() 验证"},
    "valueerror": {"cause": "值不合法", "fix": "检查输入值的有效范围和格式"},
    "filenotfounderror": {
        "cause": "文件路径不存在",
        "fix": "检查文件路径是否正确，使用 os.path.exists() 验证",
    },
    "permissionerror": {"cause": "权限不足", "fix": "检查文件/目录权限"},
    "timeout": {"cause": "操作超时", "fix": "增加超时时间或优化操作"},
    "connectionerror": {"cause": "网络连接失败", "fix": "检查网络连接和目标地址"},
    "none": {"cause": "对象为 None", "fix": "添加 None 检查，使用 if obj is not None"},
}


class DebuggerTool:
    """Tool for debugging code and analyzing errors"""

    def __init__(self, config, llm_client) -> None:
        """Initialize the DebuggerTool.

        Args:
            config: Application configuration object.
            llm_client: LLM client for advanced code analysis.
        """
        self.config = config
        self.llm = llm_client

    def analyze(
        self,
        code: str,
        error: Optional[str] = None,
        language: str = "python",
        stack_trace: Optional[str] = None,
    ) -> str:
        """Analyze code and/or error to provide debugging assistance.

        Args:
            code: Source code to analyze.
            error: Optional error message to diagnose.
            language: Programming language of the code (default: "python").
            stack_trace: Optional stack trace for context.

        Returns:
            A string containing the debugging analysis and recommendations.
        """
        logger.info("debugging_code", language=language, has_error=bool(error))

        try:
            if error:
                return self._analyze_error(code, error, language, stack_trace)
            return self._analyze_code_health(code, language)
        except Exception as e:
            logger.error("debug_analysis_failed", exc_info=e)
            return f"❌ Debug analysis failed: {e}"

    def _analyze_error(
        self,
        code: str,
        error: str,
        language: str,
        stack_trace: Optional[str] = None,
    ) -> str:
        """Analyze a specific error using LLM or fallback to basic analysis."""
        try:
            response = self.llm.debug_code(
                code=code, error=error, language=language
            )
            if not response.content or "not configured" in response.content:
                return self._basic_error_analysis(error, stack_trace)
            return self._format_debug_response(response.content, error)
        except Exception as e:
            logger.error("error_analysis_failed", exc_info=e)
            return f"❌ Error analysis failed: {e}"

    def _analyze_code_health(self, code: str, language: str) -> str:
        """Analyze code health without specific error."""
        prompt = (
            f"Analyze this {language} code for potential issues:\n"
            "- Logic errors\n"
            "- Edge cases not handled\n"
            "- Resource leaks\n"
            "- Race conditions\n"
            "- Common pitfalls\n\n"
            f"Code:\n```{language}\n{code}\n```"
        )
        try:
            response = self.llm.chat(prompt)
            return self._format_debug_response(response.content, None)
        except Exception as e:
            logger.error("code_health_analysis_failed", language=language, exc_info=e)
            return f"❌ Code health analysis failed: {e}"

    def _basic_error_analysis(
        self, error: str, stack_trace: Optional[str] = None
    ) -> str:
        """Perform basic error analysis without LLM by pattern-matching common errors.

        Uses a built-in dictionary of common Python error types to provide
        instant Chinese-language diagnosis and fix suggestions when the LLM
        is unavailable.
        """
        error_lower = error.lower()

        # Detect error type via substring match
        detected = None
        for err_type, info in _COMMON_ERRORS.items():
            if err_type in error_lower:
                detected = (err_type, info)
                break

        # Build error section
        error_section = f"""**错误信息**:
```
{error}
```"""

        stack_section = (
            f"\n**堆栈跟踪**:\n```\n{stack_trace}\n```\n" if stack_trace else "\n"
        )

        if detected:
            err_type, info = detected
            error_name = error.split(":")[0] if ":" in error else err_type
            analysis = (
                f"**问题类型**: {error_name}\n"
                f"**可能原因**: {info['cause']}\n"
                f"**修复建议**: {info['fix']}"
            )
        else:
            analysis = (
                "**分析**: 检测到未知错误类型\n\n"
                "请配置 `MINIMAX_API_KEY` 获取详细调试建议。"
            )

        return (
            f"## 🐛 调试分析\n\n"
            f"{error_section}\n"
            f"{stack_section}"
            f"{analysis}"
        )

    def _format_debug_response(
        self, llm_response: str, error: Optional[str]
    ) -> str:
        """Format LLM debug response with consistent header."""
        if error:
            header = (
                f"## 🐛 调试分析\n\n"
                f"**错误**:\n```\n{error}\n```\n\n"
                f"---\n\n"
            )
        else:
            header = (
                "## 🐛 调试分析\n\n"
                "**分析**: 代码健康检查\n\n"
                "---\n\n"
            )
        return header + llm_response

    def suggest_fixes(
        self, code: str, issue: str, language: str = "python"
    ) -> str:
        """Suggest fixes for a specific issue.

        Args:
            code: Source code containing the issue.
            issue: Description of the problem to fix.
            language: Programming language of the code (default: "python").

        Returns:
            A string containing root cause explanation, fixed code, and prevention tips.
        """
        prompt = (
            f"The following {language} code has this issue:\n"
            f"{issue}\n\n"
            "Provide:\n"
            "1. Root cause explanation\n"
            "2. The fixed code\n"
            "3. Prevention tips\n\n"
            f"Code:\n```{language}\n{code}\n```"
        )
        try:
            response = self.llm.chat(prompt)
            return response.content
        except Exception as e:
            logger.error("suggest_fixes_failed", language=language, exc_info=e)
            return f"❌ Failed to suggest fixes: {e}"
