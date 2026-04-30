"""Beaver Bot Debugger Tool"""

from typing import Optional, Dict, Any

import structlog

logger = structlog.get_logger()


class DebuggerTool:
    """Tool for debugging code and analyzing errors"""

    def __init__(self, config, llm_client):
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
        stack_trace: Optional[str] = None
    ) -> str:
        """Analyze code and/or error to provide debugging assistance"""

        logger.info("debugging_code", language=language, has_error=bool(error))

        try:
            if error:
                return self._analyze_error(code, error, language, stack_trace)
            else:
                return self._analyze_code_health(code, language)

        except Exception as e:
            logger.error("debug_analysis_failed", error=str(e))
            return f"❌ Debug analysis failed: {e}"

    def _analyze_error(
        self,
        code: str,
        error: str,
        language: str,
        stack_trace: Optional[str] = None
    ) -> str:
        """Analyze a specific error"""

        try:
            response = self.llm.debug_code(
                code=code,
                error=error,
                language=language
            )

            if not response.content or "not configured" in response.content:
                return self._basic_error_analysis(error, stack_trace)

            return self._format_debug_response(response.content, error)

        except Exception as e:
            return f"❌ Error analysis failed: {e}"

    def _analyze_code_health(self, code: str, language: str) -> str:
        """Analyze code health without specific error"""

        prompt = f"""Analyze this {language} code for potential issues:
- Logic errors
- Edge cases not handled
- Resource leaks
- Race conditions
- Common pitfalls

Code:
```{language}
{code}
```"""

        try:
            response = self.llm.chat(prompt)
            return self._format_debug_response(response.content, None)
        except Exception as e:
            return f"❌ Code health analysis failed: {e}"

    def _basic_error_analysis(
        self,
        error: str,
        stack_trace: Optional[str] = None
    ) -> str:
        """Basic error analysis without LLM"""

        error_lower = error.lower()

        # Common Python errors
        common_errors = {
            "indexerror": {
                "cause": "索引超出序列范围",
                "fix": "检查索引是否在有效范围内，使用 len() 验证"
            },
            "keyerror": {
                "cause": "字典中不存在该键",
                "fix": "使用 dict.get() 方法或先检查键是否存在"
            },
            "attributeerror": {
                "cause": "对象没有该属性或方法",
                "fix": "检查对象类型，确保属性/方法存在"
            },
            "typeerror": {
                "cause": "类型不匹配",
                "fix": "检查变量类型，使用 isinstance() 验证"
            },
            "valueerror": {
                "cause": "值不合法",
                "fix": "检查输入值的有效范围和格式"
            },
            "filenotfounderror": {
                "cause": "文件路径不存在",
                "fix": "检查文件路径是否正确，使用 os.path.exists() 验证"
            },
            "permissionerror": {
                "cause": "权限不足",
                "fix": "检查文件/目录权限"
            },
            "timeout": {
                "cause": "操作超时",
                "fix": "增加超时时间或优化操作"
            },
            "connectionerror": {
                "cause": "网络连接失败",
                "fix": "检查网络连接和目标地址"
            },
            "none": {
                "cause": "对象为 None",
                "fix": "添加 None 检查，使用 if obj is not None"
            }
        }

        # Detect error type
        detected_type = None
        for err_type, info in common_errors.items():
            if err_type in error_lower:
                detected_type = err_type
                break

        result = ["""## 🐛 调试分析

**错误信息**:
```
"""
        ]

        result.append(error)
        result.append("```\n")

        if stack_trace:
            result.append(f"\n**堆栈跟踪**:\n```\n{stack_trace}\n```\n")

        if detected_type:
            info = common_errors[detected_type]
            result.append(f"""**问题类型**: {error.split(':')[0] if ':' in error else detected_type}
**可能原因**: {info['cause']}
**修复建议**: {info['fix']}
""")
        else:
            result.append("""**分析**: 检测到错误

请配置 `OPENROUTER_API_KEY` 或 `ANTHROPIC_API_KEY` 获取详细调试建议。
""")

        return "".join(result)

    def _format_debug_response(self, llm_response: str, error: Optional[str]) -> str:
        """Format LLM debug response"""

        header = """## 🐛 调试分析

"""

        if error:
            header += f"""**错误**:
```
{error}
```

---

"""
        else:
            header += """**分析**: 代码健康检查

---

"""

        return header + llm_response

    def suggest_fixes(
        self,
        code: str,
        issue: str,
        language: str = "python"
    ) -> str:
        """Suggest fixes for a specific issue"""

        prompt = f"""The following {language} code has this issue:
{issue}

Provide:
1. Root cause explanation
2. The fixed code
3. Prevention tips

Code:
```{language}
{code}
```"""

        try:
            response = self.llm.chat(prompt)
            return response.content
        except Exception as e:
            return f"❌ Failed to suggest fixes: {e}"
