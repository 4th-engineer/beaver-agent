"""Beaver Agent tools exposed as LangGraph Tool nodes.

Each tool is wrapped as a ``langchain_core.tools.BaseTool`` so the
StateGraph can call them during the ReAct executor loop without any
changes to the underlying tool implementations.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

import structlog
from langchain_core.tools import BaseTool, tool

from beaver_agent.core.config import BeaverConfig
from beaver_agent.core.tool_router import ToolRouter

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ─── Tool Router singleton (lazily created per process) ────────────────────────

_router: ToolRouter | None = None


def _get_router() -> ToolRouter:
    global _router
    if _router is None:
        _router = ToolRouter(BeaverConfig.from_env())
    return _router


# ─── Internal helper ───────────────────────────────────────────────────────────


def _run_beaver_tool(tool_name: str, action: str, params: dict[str, Any]) -> dict[str, Any]:
    """Call Beaver's ToolRouter and return a serialisable result dict.

    Args:
        tool_name:  Beaver tool identifier (e.g. "file_tool", "github_tool").
        action:     Tool action label (e.g. "read_file", "operate").
        params:    Arbitrary kwargs forwarded into the tool.

    Returns:
        A dict with at minimum ``success`` (bool) and either ``data`` or ``error``.
    """
    router = _get_router()
    task = {"tool": tool_name, "action": action, "params": params}
    try:
        result = router.route(task)
        return result
    except Exception as exc:
        logger.error("tool_execution_failed", tool=tool_name, action=action, exc=exc)
        return {"success": False, "tool": tool_name, "error": str(exc)}


# ─── Individual LangGraph Tools ─────────────────────────────────────────────────


@tool
def read_file_tool(path: str, offset: int = 1, limit: int = 500) -> str:
    """Read the contents of a source file.

    Args:
        path:    Absolute or relative file path.
        offset:  1-indexed starting line (default 1).
        limit:   Maximum lines to read (default 500).
    """
    result = _run_beaver_tool("file_tool", "read_file", {"path": path, "offset": offset, "limit": limit})
    if result.get("success"):
        data = result.get("data", "")
        return json.dumps({"path": path, "content": data}, ensure_ascii=False)
    raise RuntimeError(result.get("error", "read_file failed"))


@tool
def write_file_tool(path: str, content: str) -> str:
    """Overwrite a file with new content (used after code generation).

    Args:
        path:    Target file path.
        content: Full file content as a string.
    """
    result = _run_beaver_tool("file_tool", "write_file", {"path": path, "content": content})
    if result.get("success"):
        return f"Written to {path}"
    raise RuntimeError(result.get("error", "write_file failed"))


@tool
def code_gen_tool(description: str, language: str = "python", file_path: str | None = None) -> str:
    """Generate source code from a natural-language description.

    Args:
        description: What the code should do.
        language:    Target language (python / javascript / typescript / go / rust / java).
        file_path:    Optional path to write the generated code to.
    """
    result = _run_beaver_tool(
        "code_gen",
        "generate",
        {"description": description, "language": language, "file_path": file_path},
    )
    if result.get("success"):
        return json.dumps(result.get("data", {}), ensure_ascii=False)
    raise RuntimeError(result.get("error", "code_gen failed"))


@tool
def code_review_tool(path: str) -> str:
    """Perform a code review on a given file.

    Args:
        path: File path to review.
    """
    result = _run_beaver_tool("code_review", "review", {"path": path})
    if result.get("success"):
        return json.dumps(result.get("data", {}), ensure_ascii=False)
    raise RuntimeError(result.get("error", "code_review failed"))


@tool
def debugger_tool(error: str, file_path: str | None = None) -> str:
    """Analyse an error message and suggest a fix.

    Args:
        error:     The error message or traceback text.
        file_path: Optional file where the error originated.
    """
    result = _run_beaver_tool("debugger", "analyze", {"error": error, "file_path": file_path})
    if result.get("success"):
        return json.dumps(result.get("data", {}), ensure_ascii=False)
    raise RuntimeError(result.get("error", "debugger failed"))


@tool
def github_tool(operation: str, repo: str | None = None, number: int | None = None, **kwargs: Any) -> str:
    """Perform a GitHub operation (issue / PR / repo info).

    Args:
        operation: Action label (e.g. "get_issue", "create_pr", "list_releases").
        repo:      Owner/repo string (e.g. "owner/repo").
        number:    Issue or PR number.
        **kwargs: Additional parameters forwarded to the GitHub tool.
    """
    params = {"operation": operation, "repo": repo, "number": number, **kwargs}
    result = _run_beaver_tool("github_tool", "operate", params)
    if result.get("success"):
        return json.dumps(result.get("data", {}), ensure_ascii=False)
    raise RuntimeError(result.get("error", "github_tool failed"))


@tool
def terminal_tool(command: str, timeout: int = 60, workdir: str | None = None) -> str:
    """Execute a shell command and return its stdout.

    Args:
        command:  Shell command string.
        timeout:  Max seconds to wait (default 60).
        workdir:  Working directory for the command.
    """
    params = {"command": command, "timeout": timeout, "workdir": workdir}
    result = _run_beaver_tool("terminal_tool", "execute", params)
    if result.get("success"):
        return json.dumps(result.get("data", {}), ensure_ascii=False)
    raise RuntimeError(result.get("error", "terminal_tool failed"))


@tool
def code_analyzer_tool(path: str, depth: int = 2) -> str:
    """Perform static analysis on a code repository.

    Args:
        path:  Root directory or file to analyse.
        depth: Analysis depth (1=files, 2=imports, 3=full AST).
    """
    result = _run_beaver_tool("code_analyzer", "analyze", {"path": path, "depth": depth})
    if result.get("success"):
        return json.dumps(result.get("data", {}), ensure_ascii=False)
    raise RuntimeError(result.get("error", "code_analyzer failed"))


# ─── Tool registry ─────────────────────────────────────────────────────────────


BEAVER_TOOLS: list[BaseTool] = [
    read_file_tool,
    write_file_tool,
    code_gen_tool,
    code_review_tool,
    debugger_tool,
    github_tool,
    terminal_tool,
    code_analyzer_tool,
]


def get_tool(name: str) -> BaseTool | None:
    """Find a Beaver LangGraph tool by its function name."""
    for t in BEAVER_TOOLS:
        if t.name == name:
            return t
    return None
