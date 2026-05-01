"""Browser Tool - Web scraping, screenshots, and browser automation using agent-browser CLI"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


AGENT_BROWSER_BIN = "/home/agentuser/.hermes/hermes-agent/node_modules/.bin/agent-browser"


@dataclass
class BrowserResult:
    success: bool
    content: Any = None
    message: str = ""
AGENT_BROWSER_BIN = None  # Resolved on first use via _resolve_browser_binary()


def _resolve_browser_binary() -> Optional[str]:
    """Locate agent-browser binary, platform-aware.

    Searches in order:
    1. AGENT_BROWSER_BIN env var (user override)
    2. npm global bin dir (platform-specific)
    3. Common install locations per platform
    """
    import platform
    import os
    import shutil

    # 1. User override via environment
    env_path = os.environ.get("AGENT_BROWSER_BIN")
    if env_path and Path(env_path).exists():
        return env_path

    # 2. Try npm global bin
    try:
        result = subprocess.run(
            ["npm", "root", "-g"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            global_npm_root = Path(result.stdout.strip())
            candidate = global_npm_root / "bin" / "agent-browser"
            if candidate.exists():
                return str(candidate)
            # Also check .bin directly (some npm setups)
            dot_bin = global_npm_root.parent / ".bin" / "agent-browser"
            if dot_bin.exists():
                return str(dot_bin)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # 3. Platform-specific search paths
    system = platform.system().lower()

    if system == "darwin":
        # macOS: Homebrew node, nvm, or standard install
        search_paths = [
            Path("/opt/homebrew/bin/agent-browser"),        # Apple Silicon Homebrew
            Path("/usr/local/bin/agent-browser"),            # Intel Homebrew / standard
            Path.home() / ".nvm/versions/node/*/bin/agent-browser",
            Path.home() / ".local/bin/agent-browser",
            Path.home() / ".npm-global/bin/agent-browser",
        ]
    elif system == "linux":
        search_paths = [
            Path("/usr/local/bin/agent-browser"),
            Path("/usr/bin/agent-browser"),
            Path.home() / ".local/bin/agent-browser",
            Path.home() / ".npm-global/bin/agent-browser",
        ]
    elif system == "windows":
        search_paths = [
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "nodejs" / "agent-browser.cmd",
            Path(os.environ.get("APPDATA", "")) / "npm" / "agent-browser.cmd",
        ]
    else:
        search_paths = [Path.home() / ".local/bin" / "agent-browser"]

    for path in search_paths:
        # Handle glob patterns (for nvm versioned paths)
        if "*" in str(path):
            matches = list(path.parent.glob(path.name))
            if matches:
                return str(matches[0])
        elif path.exists():
            return str(path)

    # 4. Fall back to whatever `which` finds
    try:
        result = subprocess.run(
            ["which", "agent-browser"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def _validate_browser_binary() -> Optional[str]:
    """Check if agent-browser binary exists. Returns error message if not."""
    global AGENT_BROWSER_BIN
    if AGENT_BROWSER_BIN is None:
        AGENT_BROWSER_BIN = _resolve_browser_binary()

    if not AGENT_BROWSER_BIN:
        return (
            "agent-browser not found. "
            "Install with: npm install -g @agent-browser/cli"
        )
    if not Path(AGENT_BROWSER_BIN).exists():
        return (
            f"agent-browser not found at {AGENT_BROWSER_BIN}. "
            "Install with: npm install -g @agent-browser/cli"
        )
    return None


def _run_browser_cmd(cmd: str, timeout: int = 30) -> BrowserResult:
    """Run agent-browser command and return result"""
    if error := _validate_browser_binary():
        return BrowserResult(success=False, error=error)
    try:
        result = subprocess.run(
            f"{AGENT_BROWSER_BIN} {cmd}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return BrowserResult(success=True, content=result.stdout, message=result.stdout.strip())
        else:
            return BrowserResult(success=False, error=result.stderr.strip() or result.stdout.strip())
    except subprocess.TimeoutExpired:
        return BrowserResult(success=False, error=f"Command timed out after {timeout}s")
    except Exception as e:
        return BrowserResult(success=False, error=str(e))


def navigate(url: str, timeout: int = 30) -> BrowserResult:
    """Navigate to a URL"""
    return _run_browser_cmd(f"open {url}", timeout=timeout)


def snapshot(interactive_only: bool = True, compact: bool = True, depth: int = 10) -> BrowserResult:
    """Get page accessibility tree snapshot"""
    cmd = "snapshot"
    if interactive_only:
        cmd += " -i"
    if compact:
        cmd += " -c"
    cmd += f" -d {depth}"
    return _run_browser_cmd(cmd)


def screenshot(path: Optional[str] = None, full_page: bool = False, annotate: bool = False) -> BrowserResult:
    """Take screenshot of current page"""
    if path is None:
        path = tempfile.mktemp(suffix=".png")

    cmd = f"screenshot {path}"
    if full_page:
        cmd += " --full"
    if annotate:
        cmd += " --annotate"

    result = _run_browser_cmd(cmd)
    if result.success:
        result.content = path
        result.message = f"Screenshot saved to {path}"
    return result


def get_text(selector: str = None) -> BrowserResult:
    """Get text content from page or element"""
    cmd = f"get text" if selector is None else f"get text {selector}"
    return _run_browser_cmd(cmd)


def get_html(selector: str = None) -> BrowserResult:
    """Get HTML content from page or element"""
    cmd = f"get html" if selector is None else f"get html {selector}"
    return _run_browser_cmd(cmd)


def get_title() -> BrowserResult:
    """Get page title"""
    return _run_browser_cmd("get title")


def get_url() -> BrowserResult:
    """Get current URL"""
    return _run_browser_cmd("get url")


def click(selector: str) -> BrowserResult:
    """Click an element by selector or @ref"""
    return _run_browser_cmd(f"click {selector}")


def fill(selector: str, text: str) -> BrowserResult:
    """Fill input field with text"""
    escaped_text = text.replace('"', '\\"')
    return _run_browser_cmd(f'fill {selector} "{escaped_text}"')


def type_text(selector: str, text: str) -> BrowserResult:
    """Type text into element (character by character)"""
    escaped_text = text.replace('"', '\\"')
    return _run_browser_cmd(f'type {selector} "{escaped_text}"')


def press(key: str) -> BrowserResult:
    """Press keyboard key"""
    return _run_browser_cmd(f"press {key}")


def scroll(direction: str, pixels: int = 300) -> BrowserResult:
    """Scroll page: up, down, left, right"""
    return _run_browser_cmd(f"scroll {direction} {pixels}")


def scroll_into_view(selector: str) -> BrowserResult:
    """Scroll element into view"""
    return _run_browser_cmd(f"scrollintoview {selector}")


def wait(selector_or_ms: str) -> BrowserResult:
    """Wait for element or time in ms"""
    return _run_browser_cmd(f"wait {selector_or_ms}")


def find_elements(role: str, value: str, action: str = "click", name: str = None) -> BrowserResult:
    """Find elements by role, text, label, etc."""
    cmd = f"find {role} {value} {action}"
    if name:
        cmd += f" --name {name}"
    return _run_browser_cmd(cmd)


def back() -> BrowserResult:
    """Go back in browser history"""
    return _run_browser_cmd("back")


def forward() -> BrowserResult:
    """Go forward in browser history"""
    return _run_browser_cmd("forward")


def reload() -> BrowserResult:
    """Reload current page"""
    return _run_browser_cmd("reload")


def close() -> BrowserResult:
    """Close browser"""
    return _run_browser_cmd("close")


def fetch_content(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Fetch URL and return structured content including title, snapshot, and page state.
    
    Args:
        url: The URL to navigate to and fetch content from.
        timeout: Maximum time in seconds to wait for page load (default: 30).
    
    Returns:
        Dict with keys: success (bool), url (str), title (str), snapshot (str), message (str).
        On failure, includes 'error' key instead of content fields.
    
    Example:
        >>> result = fetch_content("https://example.com")
        >>> if result["success"]:
        ...     print(result["title"])
    """
    # Navigate to URL
    nav_result = navigate(url, timeout=timeout)
    if not nav_result.success:
        return {"success": False, "error": nav_result.error, "url": url}

    # Wait for page to load
    wait("networkidle")

    # Get page info
    title_result = get_title()
    url_result = get_url()
    snapshot_result = snapshot()

    return {
        "success": True,
        "url": url_result.content or url,
        "title": title_result.content,
        "snapshot": snapshot_result.content,
        "message": "Page fetched successfully"
    }


def take_screenshot(url: str, output_path: str = None, full_page: bool = False, timeout: int = 30) -> Dict[str, Any]:
    """Navigate to URL and take a screenshot.
    
    Combines navigation, waiting for page load, and screenshot capture into a single operation.
    
    Args:
        url: The URL to navigate to.
        output_path: File path to save screenshot. If None, a temp file is created.
        full_page: If True, capture the entire scrollable page (default: False).
        timeout: Maximum time in seconds to wait for navigation (default: 30).
    
    Returns:
        Dict with keys: success (bool), path (str), url (str), error (str if failed).
    
    Example:
        >>> result = take_screenshot("https://example.com", "/tmp/ss.png")
        >>> if result["success"]:
        ...     print(f"Saved to {result['path']}")
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".png")

    # Navigate
    nav_result = navigate(url, timeout=timeout)
    if not nav_result.success:
        return {"success": False, "error": nav_result.error}

    # Wait for load
    wait("networkidle")

    # Screenshot
    ss_result = screenshot(output_path, full_page=full_page)

    return {
        "success": ss_result.success,
        "path": ss_result.content if ss_result.success else None,
        "error": ss_result.error if not ss_result.success else None,
        "url": url
    }


# Convenience class for unified interface
class BrowserTool:
    """Browser automation tool providing a high-level interface for web scraping and automation.
    
    This class wraps the module-level browser functions (navigate, snapshot, click, etc.)
    into a stateful interface that tracks current_url and last_snapshot across operations.
    
    Attributes:
        current_url: The URL of the currently open page, or None if no page is open.
        last_snapshot: The most recent accessibility tree snapshot, or None.
    
    Example:
        >>> tool = BrowserTool()
        >>> tool.open("https://example.com")
        >>> elements = tool.interactive()
        >>> tool.click("@e5")
        >>> info = tool.get_page_info()
    
    Note:
        All methods that perform actions (open, click, fill, scroll) automatically
        refresh the last_snapshot, so subsequent calls to interactive() or snapshot()
        reflect the updated page state.
    """

    def __init__(self):
        self.current_url: Optional[str] = None
        self.last_snapshot: Optional[str] = None

    def open(self, url: str) -> str:
        """Open URL and return snapshot"""
        result = navigate(url)
        if result.success:
            self.current_url = url
            snapshot_result = snapshot()
            self.last_snapshot = snapshot_result.content
            return snapshot_result.content or f"Opened {url}"
        return f"Error: {result.error}"

    def browse(self, url: str, action: str = "snapshot") -> str:
        """Open URL and perform action (snapshot, screenshot, etc.)"""
        self.open(url)
        if action == "snapshot":
            return self.last_snapshot or "No content"
        elif action == "screenshot":
            ss_result = screenshot()
            return ss_result.message
        elif action == "title":
            title_result = get_title()
            return title_result.content or "No title"
        return "Unknown action"

    def interactive(self) -> str:
        """Get interactive elements only"""
        result = snapshot(interactive_only=True, compact=False)
        self.last_snapshot = result.content
        return result.content or "No interactive elements"

    def screenshot(self, path: str = None, full: bool = False) -> str:
        """Take screenshot"""
        result = screenshot(path, full_page=full, annotate=True)
        return result.message

    def click(self, selector: str) -> str:
        """Click element"""
        result = click(selector)
        if result.success:
            snap = snapshot()
            self.last_snapshot = snap.content
            return snap.content or "Clicked"
        return f"Error: {result.error}"

    def fill(self, selector: str, text: str) -> str:
        """Fill input"""
        result = fill(selector, text)
        return result.message if result.success else f"Error: {result.error}"

    def scroll(self, direction: str = "down", pixels: int = 300) -> str:
        """Scroll page"""
        result = scroll(direction, pixels)
        if result.success:
            snap = snapshot()
            self.last_snapshot = snap.content
            return snap.content or "Scrolled"
        return f"Error: {result.error}"

    def get_page_info(self) -> Dict[str, str]:
        """Get current page info"""
        title = get_title()
        url = get_url()
        return {
            "title": title.content or "",
            "url": url.content or ""
        }
