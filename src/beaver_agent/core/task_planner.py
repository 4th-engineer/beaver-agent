"""Beaver Agent Task Planner - LLM-powered task decomposition."""

import re
from typing import Any

import structlog

logger = structlog.get_logger()

__all__ = ["TaskPlanner"]


class TaskPlanner:
    """Plan and decompose tasks based on intent"""

    # Task templates for different intents
    INTENT_TASKS = {
        "code_generation": [
            {"tool": "code_gen", "action": "generate", "params": {}},
        ],
        "code_review": [
            {"tool": "file_tool", "action": "read_file", "params": {}},
            {"tool": "code_review", "action": "review", "params": {}},
        ],
        "debug": [
            {"tool": "debugger", "action": "analyze", "params": {}},
        ],
        "github_operation": [
            {"tool": "github_tool", "action": "operate", "params": {}},
        ],
        "file_operation": [
            {"tool": "file_tool", "action": "read_file", "params": {}},
        ],
        "terminal_operation": [
            {"tool": "terminal_tool", "action": "execute", "params": {}},
        ],
    }

    # Compiled regex patterns for _extract_params (class-level, compiled once)
    # File-extraction patterns — must be anchored after whitespace or line start
    # to avoid partial-word matches.  Use a capture group; leading whitespace
    # (if any) is stripped by the group so we get the clean path.
    _FILE_PATTERNS = [
        r"(?:^|\s)([^\s,;]*\/[^\s,;]*\.[a-z]+)",   # relative or absolute, anchored
    ]
    _ERROR_PATTERNS = [
        r"Error:\s*(.+?)(?:\n|$)",
        r"Exception:\s*(.+?)(?:\n|$)",
        r"Traceback\s*(.+?)(?:\n\n|$)",
        r"报错[：:]\s*(.+?)(?:\n|$)",
    ]
    _GH_PATTERNS = [
        r"([\w-]+)/([\w-]+)",  # owner/repo
        r"#(\d+)",  # issue or PR number
        r"issue\s*#?(\d+)",  # explicit issue
        r"pr\s*#?(\d+)",  # explicit PR
    ]

    # Tool → which param names this tool actually consumes
    _TOOL_ACCEPTS: dict[str, set[str]] = {
        "file_tool": {"file_path", "limit"},
        "code_gen": {"description", "language", "file_path"},
        "code_review": {"path"},
        "debugger": {"error", "file_path"},
        "github_tool": {"repo", "number", "operation"},
        "terminal_tool": {"command", "timeout", "workdir"},
        "code_analyzer": {"path", "depth"},
    }

    # Map extracted "path" key to the actual param name each tool uses
    _PATH_PARAM: dict[str, str] = {
        "file_tool": "file_path",
        "code_review": "file_path",
        "code_analyzer": "path",
        "debugger": "file_path",
        "code_gen": "file_path",
    }

    def plan(self, user_input: str, intent: str) -> list[dict[str, Any]]:
        """Plan tasks for a given intent and user input.

        Uses the intent type to look up predefined task templates, then
        enriches each task with parameters extracted from the user input
        (file paths, language hints, error messages, GitHub references).

        Args:
            user_input: Raw user input string describing the task. Used
                by ``_extract_params`` to pull out structured parameters
                like file paths and language preferences.
            intent: Intent type string such as ``"code_generation"``,
                ``"code_review"``, ``"debug"``, etc. Determines which
                task template from ``INTENT_TASKS`` is used.

        Returns:
            A list of task dictionaries, each containing ``tool``,
            ``action``, and ``params`` keys. Parameters are populated
            by ``_extract_params`` from the user input.

        Example:
            >>> planner = TaskPlanner()
            >>> tasks = planner.plan("帮我写一个快排算法", "code_generation")
            >>> tasks[0]["tool"]
            'code_gen'
            >>> "description" in tasks[0]["params"]
            True
        """

        tasks = self.INTENT_TASKS.get(intent, [])

        # Build task list — params are tool-specific, not global
        planned_tasks = []
        for task in tasks:
            task_copy = task.copy()
            tool_name = task_copy.get("tool", "")
            params = self._extract_params(user_input, intent, tool_name)
            task_copy["params"].update(params)
            planned_tasks.append(task_copy)

        logger.debug("tasks_planned", intent=intent, task_count=len(planned_tasks))

        return planned_tasks

    def _extract_params(
        self, user_input: str, intent: str, tool: str = ""
    ) -> dict[str, Any]:
        """Extract structured parameters from user input for a specific tool.

        Unlike the old implementation that returned a global dict of all possible
        parameters for the intent, this version is tool-aware: it only returns
        the parameters relevant to the named tool, avoiding spurious kwarg errors.

        Args:
            user_input: Raw user input string to parse.
            intent:     The intent type (e.g. "code_generation", "code_review").
            tool:       The tool name this params dict is being prepared for
                        (e.g. "file_tool", "code_review"). Controls which keys
                        are included in the returned dict.

        Returns:
            A dict containing only the parameters accepted by ``tool``.
        """
        params: dict[str, Any] = {}
        accepts = self._TOOL_ACCEPTS.get(tool, set())

        if "description" in accepts or "error" in accepts:
            params["description"] = user_input

        # File path — extract raw, then map to the tool's actual param name
        if {"path", "file_path"} & accepts:
            for pattern in self._FILE_PATTERNS:
                matches = re.findall(pattern, user_input)
                if matches:
                    raw_path = matches[0]
                    actual_key = self._PATH_PARAM.get(tool, "path")
                    params[actual_key] = raw_path
                    break

        # Language — only for code_gen
        if "language" in accepts:
            languages = ["python", "javascript", "typescript", "go", "rust", "java", "c++", "c"]
            for lang in languages:
                if lang in user_input.lower():
                    params["language"] = lang
                    break
            if "language" not in params:
                params["language"] = "python"

        # Error message — only for debugger
        if "error" in accepts:
            for pattern in self._ERROR_PATTERNS:
                matches = re.findall(pattern, user_input, re.DOTALL)
                if matches:
                    params["error"] = matches[0].strip()
                    break

        # GitHub references — only for github_tool
        if {"repo", "number"} & accepts:
            for pattern in self._GH_PATTERNS:
                matches = re.findall(pattern, user_input, re.IGNORECASE)
                if matches:
                    if "/" in pattern and isinstance(matches[0], tuple):
                        params["repo"] = f"{matches[0][0]}/{matches[0][1]}"
                    elif "#" in pattern:
                        params["number"] = int(
                            matches[0][0] if isinstance(matches[0], tuple) else matches[0]
                        )
                    break

        return params

    def validate_plan(self, tasks: list[dict[str, Any]]) -> bool:
        """Validate that a task plan is executable.

        Checks that the task list is non-empty and that each task dict
        contains both ``tool`` and ``action`` keys required for execution.

        Args:
            tasks: A list of task dictionaries, each representing a step
                in the execution plan (e.g., ``[{"tool": "file_tool",
                "action": "read_file", ...}, ...]``).

        Returns:
            True if the plan is valid (non-empty and all tasks have
            ``tool`` and ``action`` fields); False otherwise.

        Example:
            >>> planner = TaskPlanner()
            >>> planner.validate_plan([])
            False
            >>> planner.validate_plan([{"tool": "file_tool", "action": "read"}])
            True
            >>> planner.validate_plan([{"tool": "file_tool"}])
            False
        """
        if not tasks:
            return False

        for task in tasks:
            if "tool" not in task or "action" not in task:
                return False

        return True
