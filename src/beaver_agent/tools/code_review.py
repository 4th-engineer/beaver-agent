"""Beaver Agent Code Review Tool"""

from typing import Optional, List

import structlog

logger = structlog.get_logger()

__all__ = ["CodeReviewIssue", "CodeReviewTool"]

# Severity emoji — module-level constant, avoids dict re-creation per call
_SEVERITY_EMOJI = {
    "critical": "🔴",
    "major": "🟠",
    "minor": "🟡",
    "suggestion": "💡",
}


class CodeReviewIssue:
    """Represents a code review issue"""

    def __init__(
        self,
        severity: str,  # critical, major, minor, suggestion
        line: Optional[int],
        message: str,
        suggestion: Optional[str] = None,
    ):
        """Initialize a code review issue.

        Args:
            severity: Issue severity level - one of critical, major, minor,
                or suggestion.
            line: Line number where the issue occurs, or None if it applies
                to the whole file.
            message: Human-readable description of the issue.
            suggestion: Optional fix suggestion for resolving the issue.
        """
        self.severity = severity
        self.line = line
        self.message = message
        self.suggestion = suggestion

    def format(self) -> str:
        """Format issue as a human-readable string with emoji severity indicator."""
        emoji = _SEVERITY_EMOJI.get(self.severity, "⚪")
        line_info = f" Line {self.line}:" if self.line else ""
        result = f"{emoji} [{self.severity.upper()}]{line_info} {self.message}"
        if self.suggestion:
            result += f"\n   💡 Suggestion: {self.suggestion}"
        return result


class CodeReviewTool:
    """Tool for code review using LLM"""

    def __init__(self, config, llm_client):
        """Initialize CodeReviewTool.

        Args:
            config: Application configuration object containing LLM settings.
            llm_client: LLM client instance for performing deep code reviews.
        """
        self.config = config
        self.llm = llm_client

    def review(
        self,
        code: str,
        language: str = "python",
        file_path: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """Review code and return findings.

        Attempts LLM-based review first; falls back to static analysis
        if the LLM client is unavailable or returns an error.

        Args:
            code: Source code to review.
            language: Programming language hint (e.g., "python", "javascript").
            file_path: Optional file path for context in the review.
            context: Optional additional context for the review.

        Returns:
            A formatted review report string containing identified issues,
            or an error message if review fails completely.
        """
        logger.info("reviewing_code", file_path=file_path, language=language)

        try:
            response = self.llm.review_code(
                code=code, language=language, file_path=file_path
            )
            if not response.content or "not configured" in response.content:
                return self._basic_review(code, language, file_path)
            return self._format_review_response(response.content, file_path)

        except Exception as e:
            logger.error("code_review_failed", exc_info=e)
            return f"❌ Code review failed: {e}"

    # ── Single-pass static analysis ───────────────────────────────────────────

    def _basic_review(
        self, code: str, language: str, file_path: Optional[str]
    ) -> str:
        """Perform basic static analysis when LLM is unavailable.

        Single-pass analysis detecting language-specific and generic issues
        in one traversal.

        Args:
            code: Source code to analyze.
            language: Programming language hint.
            file_path: Optional file path for the report header.

        Returns:
            A formatted string containing review findings or a clean bill of health.
        """
        lang = language.lower()
        is_python = lang in ("python", "py")
        is_js = lang in ("javascript", "js", "typescript", "ts")

        issues: List[CodeReviewIssue] = []
        code_lines = code.split("\n")

        for i, line in enumerate(code_lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            is_comment = stripped.startswith("#") or stripped.startswith("//")

            # ── Generic checks (all languages) ───────────────────────────────
            if len(line) > 120:
                issues.append(CodeReviewIssue(
                    severity="minor", line=i,
                    message=f"行长度 {len(line)} 超过 120 字符",
                    suggestion="考虑拆分为多行",
                ))

            if line != line.rstrip():
                issues.append(CodeReviewIssue(
                    severity="suggestion", line=i,
                    message="行尾存在多余空格",
                    suggestion="移除尾随空格",
                ))

            # ── Python-specific checks ──────────────────────────────────────
            if is_python and not is_comment:
                self._check_python_line(i, stripped, issues)

            # ── JS/TS-specific checks ─────────────────────────────────────────
            if is_js and not is_comment:
                self._check_js_line(i, stripped, issues)

        if not issues:
            return (
                f"## 🔍 代码审查\n\n"
                f"**文件**: {file_path or '未指定'}\n"
                f"**语言**: {language}\n\n"
                f"✅ 静态检查未发现问题\n\n"
                f"如需深度分析，请配置 `MINIMAX_API_KEY`"
            )

        header = (
            f"## 🔍 代码审查\n\n"
            f"**文件**: {file_path or '未指定'}\n"
            f"**语言**: {language}\n\n"
            f"**发现问题**: {len(issues)} 个\n\n"
        )
        return header + "\n".join(issue.format() for issue in issues)

    def _check_python_line(
        self, lineno: int, line: str, issues: List[CodeReviewIssue]
    ) -> None:
        """Detect Python-specific issues on a single stripped line."""
        if "TODO" in line or "FIXME" in line:
            issues.append(CodeReviewIssue(
                severity="minor", line=lineno,
                message=f"发现未完成代码: {line[:50]}",
                suggestion="完成后移除 TODO 注释",
            ))
        if line.startswith("except:") or line == "except:":
            issues.append(CodeReviewIssue(
                severity="major", line=lineno,
                message="使用裸 except 子句",
                suggestion="使用 `except Exception:` 并指定具体异常类型",
            ))
        if line.startswith("print("):
            issues.append(CodeReviewIssue(
                severity="minor", line=lineno,
                message="发现 print 语句",
                suggestion="考虑使用日志模块 (logging)",
            ))
        if "def " in line and "=[]" in line:
            issues.append(CodeReviewIssue(
                severity="major", line=lineno,
                message="使用可变默认参数",
                suggestion="使用 None 作为默认值，在函数内检查",
            ))

    def _check_js_line(
        self, lineno: int, line: str, issues: List[CodeReviewIssue]
    ) -> None:
        """Detect JavaScript/TypeScript-specific issues on a single stripped line."""
        if "console.log" in line:
            issues.append(CodeReviewIssue(
                severity="minor", line=lineno,
                message="console.log found in code",
                suggestion="Remove debug statements from production code",
            ))
        if line.startswith("var "):
            issues.append(CodeReviewIssue(
                severity="major", line=lineno,
                message="var declaration used",
                suggestion="Use let or const instead — var hoists and has function scope",
            ))
        if " == " in line or line.endswith("==") or ("==" in line and "===" not in line and "!=" not in line and "!(" not in line):
            # Avoid flagging !==  or ==  in comments/strings
            issues.append(CodeReviewIssue(
                severity="major", line=lineno,
                message="Loose equality (==) used",
                suggestion="Use === or !== for type-safe comparison",
            ))

    def _format_review_response(
        self, llm_response: str, file_path: Optional[str]
    ) -> str:
        """Format a full LLM-based code review response with header."""
        return (
            f"## 🔍 代码审查\n\n"
            f"**文件**: {file_path or '未指定'}\n"
            f"**分析**: LLM 深度分析\n\n"
            f"---\n\n"
            f"{llm_response}"
        )
