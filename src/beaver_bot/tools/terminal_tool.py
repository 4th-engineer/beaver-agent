"""Beaver Bot Terminal Tool"""

import subprocess
from typing import Optional, Dict, Any

import structlog

logger = structlog.get_logger()


class TerminalTool:
    """Tool for executing terminal commands"""

    # Commands that are blocked for security
    BLOCKED_COMMANDS = [
        "rm -rf /", "rm -rf ~", ":(){ :|:& };:",  # Dangerous commands
        "mkfs", "dd if=", "> /dev/sd",  # Disk operations
    ]

    def __init__(self, config):
        self.config = config

    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 60,
        shell: bool = True
    ) -> str:
        """Execute a terminal command"""
        try:
            # Security check
            if self._is_blocked(command):
                return "❌ Command blocked for security reasons"

            logger.info("executing_command", command=command, cwd=cwd)

            result = subprocess.run(
                command,
                shell=shell,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = []
            if result.stdout:
                output.append(f"stdout:\n{result.stdout}")
            if result.stderr:
                output.append(f"stderr:\n{result.stderr}")
            if result.returncode != 0:
                output.append(f"exit code: {result.returncode}")

            if output:
                return "\n".join(output)
            else:
                return "✅ Command executed successfully (no output)"

        except subprocess.TimeoutExpired:
            return f"❌ Command timed out after {timeout}s"
        except Exception as e:
            logger.error("command_execution_failed", command=command, error=str(e))
            return f"❌ Error: {e}"

    def _is_blocked(self, command: str) -> bool:
        """Check if command contains blocked patterns"""
        command_lower = command.lower()
        for blocked in self.BLOCKED_COMMANDS:
            if blocked.lower() in command_lower:
                return True
        return False

    def get_error_log(self, lines: int = 50) -> str:
        """Get recent error log entries"""
        try:
            # Try common log locations
            log_files = [
                "/var/log/syslog",
                "/var/log/messages",
                "~/.local/share/Logs",
            ]

            for log_file in log_files:
                import os
                path = os.path.expanduser(log_file)
                if os.path.exists(path):
                    with open(path, "r") as f:
                        all_lines = f.readlines()
                        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                        # Filter for error lines
                        errors = [l for l in recent if "error" in l.lower() or "exception" in l.lower()]
                        if errors:
                            return "".join(errors)
                    return f"No errors found in {path}"

            return "No log files found"

        except Exception as e:
            return f"Error reading log: {e}"

    def run_tests(self, test_command: Optional[str] = None) -> str:
        """Run tests (auto-detect test framework)"""
        import os

        # Auto-detect test framework
        if test_command:
            return self.execute(test_command)

        test_commands = [
            ("pytest", "pytest -v"),
            ("python -m pytest", "python -m pytest -v"),
            ("npm test", "npm test"),
            ("cargo test", "cargo test"),
            ("go test", "go test ./..."),
        ]

        cwd = os.getcwd()
        for name, cmd in test_commands:
            if os.path.exists(os.path.join(cwd, name)):
                return self.execute(cmd)

        return "❌ No test framework detected"
