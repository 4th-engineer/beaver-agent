"""Beaver Agent File Tool"""

import os
from pathlib import Path
from typing import Optional, List

import structlog

logger = structlog.get_logger()


class FileTool:
    """Tool for file operations"""

    def __init__(self, config):
        self.config = config

    def read_file(self, file_path: str, limit: Optional[int] = None) -> str:
        """Read the contents of a file.

        Args:
            file_path: Path to the file to read (supports ~ expansion).
            limit: Optional maximum number of lines to read. If provided,
                   only the first `limit` lines are returned.

        Returns:
            A string containing the file contents with a header showing
            the file path and line count, or an error message if reading
            fails.
        """
        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                return f"File not found: {file_path}"

            if not path.is_file():
                return f"Not a file: {file_path}"

            # Security: prevent path traversal
            try:
                root = self.config.file_tool.root_path
                path.resolve().relative_to(root)
            except ValueError:
                return "Access denied: path is outside current directory"

            with open(path, "r", encoding="utf-8") as f:
                if limit:
                    lines = [f.readline() for _ in range(limit)]
                    return f"📄 {path} (前{limit}行):\n" + "".join(lines)
                content = f.read()
                return f"📄 {path} ({len(content.splitlines())} 行):\n{content}"

        except Exception as e:
            logger.error("read_file_failed", path=file_path, error=str(e))
            return f"Error reading file: {e}"

    def write_file(self, file_path: str, content: str) -> str:
        """Write content to a file, creating parent directories as needed.

        Args:
            file_path: Path to the file to write (supports ~ expansion).
                       Parent directories are created automatically if they
                       don't exist.
            content: The text content to write to the file.

        Returns:
            A success message with the file path, or an error message
            if writing fails.
        """
        try:
            path = Path(file_path).expanduser()

            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"✅ File written: {path}"

        except Exception as e:
            logger.error("write_file_failed", path=file_path, error=str(e))
            return f"Error writing file: {e}"

    def list_directory(self, dir_path: str = ".") -> str:
        """List the contents of a directory.

        Args:
            dir_path: Path to the directory to list (supports ~ expansion).
                      Defaults to the current directory (".").

        Returns:
            A string listing each item in the directory with its type
            icon (📁 for directories, 📄 for files) and file size.
        """
        try:
            path = Path(dir_path).expanduser()
            if not path.exists():
                return f"Directory not found: {dir_path}"

            items = []
            for item in sorted(path.iterdir()):
                size = item.stat().st_size if item.is_file() else "-"
                item_type = "📁" if item.is_dir() else "📄"
                items.append(f"{item_type} {item.name} ({size})")

            return f"📂 {path}:\n" + "\n".join(items)

        except Exception as e:
            logger.error("list_directory_failed", path=dir_path, error=str(e))
            return f"Error listing directory: {e}"

    def search_files(self, pattern: str, path: str = ".") -> str:
        """Search for files matching a glob pattern.

        Args:
            pattern: Glob pattern to match file names against (e.g., "*.py",
                    "**/*.json"). Supports fnmatch patterns.
            path: Root directory to search from (supports ~ expansion).
                  Defaults to current directory.

        Returns:
            A string listing matched file paths (up to 20), or a message
            indicating no files matched.
        """
        try:
            import fnmatch
            matches = []
            search_path = Path(path).expanduser()

            for item in search_path.rglob("*"):
                if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                    matches.append(str(item))

            if matches:
                return f"🔍 Found {len(matches)} files:\n" + "\n".join(matches[:20])
            else:
                return f"No files matching '{pattern}' found"

        except Exception as e:
            logger.error("search_files_failed", pattern=pattern, path=path, error=str(e))
            return f"Error searching files: {e}"

    def search_content(self, query: str, path: str = ".", file_pattern: str = "*") -> str:
        """Search for text content within files.

        Args:
            query: Text string to search for (case-insensitive).
            path: Root directory to search from (supports ~ expansion).
                  Defaults to current directory.
            file_pattern: Glob pattern to filter which files to search.
                          Defaults to "*" (all files).

        Returns:
            A string listing matching lines with file path and line number
            (up to 30 matches), or a message indicating no matches found.
        """
        try:
            import fnmatch
            matches = []
            search_path = Path(path).expanduser()
            query_lower = query.lower()

            for item in search_path.rglob(file_pattern):
                if item.is_file():
                    try:
                        with open(item, "r", encoding="utf-8") as f:
                            for i, line in enumerate(f, 1):
                                if query_lower in line.lower():
                                    matches.append(f"{item}:{i}: {line.rstrip()}")
                    except (UnicodeDecodeError, PermissionError):
                        continue

            if matches:
                return f"🔍 Found {len(matches)} matches:\n" + "\n".join(matches[:30])
            else:
                return f"No matches for '{query}' found"

        except Exception as e:
            return f"Error searching content: {e}"

    def check_project_structure(self, path: str = ".") -> str:
        """Check project structure"""
        try:
            path = Path(path).expanduser()
            important_files = [
                "pyproject.toml", "setup.py", "requirements.txt",
                "package.json", "Cargo.toml", "go.mod",
                ".git", "README.md", "src/", "tests/"
            ]

            found = []
            missing = []
            for item in important_files:
                item_path = path / item
                if item_path.exists() or (path / item.rstrip("/")).exists():
                    found.append(item)
                else:
                    missing.append(item)

            result = [f"📂 Project: {path}"]
            if found:
                result.append(f"\n✅ Found: {', '.join(found)}")
            if missing:
                result.append(f"\n❌ Missing: {', '.join(missing)}")

            return "\n".join(result)

        except Exception as e:
            logger.error("check_project_structure_failed", path=path, error=str(e))
            return f"Error checking project: {e}"
