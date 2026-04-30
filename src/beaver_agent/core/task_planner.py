"""Beaver Agent Task Planner v2 - With LLM tools"""

from typing import List, Dict, Any

import structlog

logger = structlog.get_logger()


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

    def plan(self, user_input: str, intent: str) -> List[Dict[str, Any]]:
        """Plan tasks for given intent and user input"""

        tasks = self.INTENT_TASKS.get(intent, [])

        # Extract parameters from user input
        params = self._extract_params(user_input, intent)

        # Build task list with extracted parameters
        planned_tasks = []
        for task in tasks:
            task_copy = task.copy()
            task_copy["params"].update(params)
            planned_tasks.append(task_copy)

        logger.debug("tasks_planned", intent=intent, task_count=len(planned_tasks))

        return planned_tasks

    def _extract_params(self, user_input: str, intent: str) -> Dict[str, Any]:
        """Extract parameters from user input"""

        params: Dict[str, Any] = {}

        # For code generation, save the full description
        if intent == "code_generation":
            params["description"] = user_input

        # Extract file paths
        import re
        file_patterns = [
            r"/[\w/.-]+\.(py|js|ts|go|rs|java|cpp|c|h)",  # Unix paths
            r"[A-Za-z]:\\[\w\\.-]+\.(py|js|ts|go|rs|java)",  # Windows paths
            r"[\w-]+/[\w/-]+\.(py|js|ts|go|rs|java)",  # Relative paths
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, user_input)
            if matches:
                params["file_path"] = matches[0]
                break

        # Extract language hints
        languages = ["python", "javascript", "typescript", "go", "rust", "java", "c++", "c"]
        for lang in languages:
            if lang in user_input.lower():
                params["language"] = lang
                break

        # Default to python if no language detected
        if "language" not in params:
            params["language"] = "python"

        # Extract error messages
        error_patterns = [
            r"Error:\s*(.+?)(?:\n|$)",
            r"Exception:\s*(.+?)(?:\n|$)",
            r"Traceback\s*(.+?)(?:\n\n|$)",
            r"报错[：:]\s*(.+?)(?:\n|$)",
        ]

        for pattern in error_patterns:
            matches = re.findall(pattern, user_input, re.DOTALL)
            if matches:
                params["error"] = matches[0].strip()
                break

        # Extract GitHub references
        gh_patterns = [
            r"([\w-]+)/([\w-]+)",  # owner/repo
            r"#(\d+)",  # issue or PR number
            r"issue\s*#?(\d+)",  # explicit issue
            r"pr\s*#?(\d+)",  # explicit PR
        ]

        for pattern in gh_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            if matches:
                if "/" in pattern and isinstance(matches[0], tuple):
                    params["repo"] = f"{matches[0][0]}/{matches[0][1]}"
                elif "#" in pattern:
                    params["number"] = int(matches[0][0] if isinstance(matches[0], tuple) else matches[0])
                break

        return params

    def validate_plan(self, tasks: List[Dict[str, Any]]) -> bool:
        """Validate that a task plan is executable"""
        if not tasks:
            return False

        for task in tasks:
            if "tool" not in task or "action" not in task:
                return False

        return True
