"""Browser Tool - Web scraping, screenshots, and browser automation using agent-browser CLI"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()

__all__ = [
    "BrowserResult",
    "BrowserTool",
    "back",
    "click",
    "close",
    "fetch_content",
    "fill",
    "find_elements",
    "forward",
    "get_html",
    "get_text",
    "get_title",
    "get_url",
    "navigate",
    "press",
    "reload",
    "scroll",
    "scroll_into_view",
    "screenshot",
    "snapshot",
    "take_screenshot",
    "type_text",
    "wait",
]


@dataclass
class BrowserResult:
    """Result of a browser operation.

    Attributes:
        success: Whether the browser operation succeeded.
        content: Optional response content (e.g., page text, screenshot path).
        message: Human-readable status or error message.
    """

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
    """Run agent-browser command and return result.

    Args:
        cmd: The command string to execute via agent-browser CLI.
        timeout: Maximum seconds to wait for command completion (default: 30).

    Returns:
        BrowserResult with success=True and content=stdout on success,
        or success=False with error message on failure.
    """
    if error := _validate_browser_binary():
        return BrowserResult(success=False, message=error)
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
            return BrowserResult(success=False, message=result.stderr.strip() or result.stdout.strip())
    except subprocess.TimeoutExpired:
        return BrowserResult(success=False, message=f"Command timed out after {timeout}s")
    except Exception as e:
        logger.error("browser_command_failed", cmd=cmd, exc_info=e)
        return BrowserResult(success=False, message=str(e))


def navigate(url: str, timeout: int = 30) -> BrowserResult:
    """Navigate to a URL and return the result.

    Args:
        url: The URL to navigate to. Must be a valid http/https URL.
        timeout: Maximum time in seconds to wait for navigation to complete (default: 30).

    Returns:
        BrowserResult with success=True and content=final URL if navigation succeeded,
        or success=False and error message if navigation failed.

    Example:
        >>> result = navigate("https://github.com")
        >>> if result.success:
        ...     print(f"Loaded: {result.content}")
    """
    return _run_browser_cmd(f"open {url}", timeout=timeout)


def snapshot(interactive_only: bool = True, compact: bool = True, depth: int = 10) -> BrowserResult:
    """Get the page accessibility tree snapshot.

    Captures the current page state as an accessibility tree, which lists all
    interactive elements with their ref IDs for use with other browser functions.

    Args:
        interactive_only: If True, only include interactive elements (buttons, links,
            inputs). If False, include all elements (default: True).
        compact: If True, use compact output format with fewer newlines (default: True).
        depth: Maximum tree depth to capture, 1-20 (default: 10).

    Returns:
        BrowserResult with success=True and content=accessibility tree string,
        or success=False and error message if snapshot failed.

    Example:
        >>> result = snapshot(interactive_only=True, compact=False)
        >>> # Use @e5 from output to click: click("@e5")
    """
    cmd = "snapshot"
    if interactive_only:
        cmd += " -i"
    if compact:
        cmd += " -c"
    cmd += f" -d {depth}"
    return _run_browser_cmd(cmd)


def screenshot(path: Optional[str] = None, full_page: bool = False, annotate: bool = False) -> BrowserResult:
    """Take screenshot of current page.

    Args:
        path: File path to save screenshot. If None, a temp file is created
            with .png suffix.
        full_page: If True, capture the entire scrollable page (default: False).
        annotate: If True, overlay interactive element labels on screenshot
            (default: False).

    Returns:
        BrowserResult with success=True and content=screenshot file path,
        or success=False and error message if capture failed.

    Example:
        >>> result = screenshot()
        >>> if result.success:
        ...     print(f"Saved to {result.content}")
        >>> result = screenshot("/tmp/page.png", full_page=True)
    """
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
    """Get text content from the page or a specific element.

    Args:
        selector: Optional CSS selector or @ref ID. If None, gets all visible text
            from the page. If provided, gets text only from the matching element.

    Returns:
        BrowserResult with success=True and content=text string,
        or success=False and error message if retrieval failed.

    Example:
        >>> result = get_text()  # all page text
        >>> result = get_text("h1.title")  # text of h1 with class title
    """
    cmd = f"get text" if selector is None else f"get text {selector}"
    return _run_browser_cmd(cmd)


def get_html(selector: str = None) -> BrowserResult:
    """Get HTML content from page or a specific element.

    Args:
        selector: Optional CSS selector or @ref ID. If None, gets full page HTML.
            If provided, gets HTML of the matching element only.

    Returns:
        BrowserResult with success=True and content=HTML string,
        or success=False and error message if retrieval failed.

    Example:
        >>> result = get_html()  # full page HTML
        >>> result = get_html("div.content")  # element HTML
    """
    cmd = f"get html" if selector is None else f"get html {selector}"
    return _run_browser_cmd(cmd)


def get_title() -> BrowserResult:
    """Get the current page title.

    Returns:
        BrowserResult with success=True and content=page title string,
        or success=False and error message if retrieval failed.

    Example:
        >>> result = get_title()
        >>> print(f"Page title: {result.content}")
    """
    return _run_browser_cmd("get title")


def get_url() -> BrowserResult:
    """Get the current page URL.

    Returns:
        BrowserResult with success=True and content=URL string,
        or success=False and error message if retrieval failed.

    Example:
        >>> result = get_url()
        >>> print(f"Current URL: {result.content}")
    """
    return _run_browser_cmd("get url")


def click(selector: str) -> BrowserResult:
    """Click an element by selector or @ref.

    Args:
        selector: CSS selector or @ref ID of the element to click.

    Returns:
        BrowserResult with success=True if click succeeded,
        or success=False and error message if click failed.

    Example:
        >>> result = click("@e5")  # click by ref ID
        >>> result = click("button.submit")  # click by selector
    """
    return _run_browser_cmd(f"click {selector}")


def fill(selector: str, text: str) -> BrowserResult:
    """Fill an input field with text.

    Args:
        selector: CSS selector or @ref ID of the input field to fill.
        text: The text string to fill into the field.

    Returns:
        BrowserResult with success=True if fill succeeded,
        or success=False and error message if fill failed.

    Example:
        >>> result = fill("input[name='email']", "user@example.com")
    """
    escaped_text = text.replace('"', '\\"')
    return _run_browser_cmd(f'fill {selector} "{escaped_text}"')


def type_text(selector: str, text: str) -> BrowserResult:
    """Type text into an element character by character.

    Args:
        selector: CSS selector or @ref ID of the element to type into.
        text: The text string to type, sent as individual keypress events.

    Returns:
        BrowserResult with success=True if typing succeeded,
        or success=False and error message if typing failed.

    Example:
        >>> result = type_text("input[type='text']", "Hello world")
    """
    escaped_text = text.replace('"', '\\"')
    return _run_browser_cmd(f'type {selector} "{escaped_text}"')


def press(key: str) -> BrowserResult:
    """Press a keyboard key on the page.

    Args:
        key: Key name (e.g., 'Enter', 'Tab', 'Escape', 'ArrowDown', 'Backspace').

    Returns:
        BrowserResult with success=True if key press succeeded, or success=False
        and error message if it failed.

    Example:
        >>> press("Enter")
        >>> press("Escape")
    """
    return _run_browser_cmd(f"press {key}")


def scroll(direction: str, pixels: int = 300) -> BrowserResult:
    """Scroll the page in a direction by a specified number of pixels.

    Args:
        direction: Scroll direction - 'up', 'down', 'left', or 'right'.
        pixels: Number of pixels to scroll (default: 300). Negative values scroll
            in the opposite direction.

    Returns:
        BrowserResult with success=True if scroll succeeded, or success=False
        and error message if it failed.

    Example:
        >>> scroll("down", 500)
        >>> scroll("up", 200)
    """
    return _run_browser_cmd(f"scroll {direction} {pixels}")


def scroll_into_view(selector: str) -> BrowserResult:
    """Scroll an element into the visible viewport.

    Args:
        selector: CSS selector or @ref ID of the element to scroll into view.

    Returns:
        BrowserResult with success=True if scroll succeeded,
        or success=False and error message if scroll failed.

    Example:
        >>> result = scroll_into_view("@e10")
        >>> result = scroll_into_view("footer")
    """
    return _run_browser_cmd(f"scrollintoview {selector}")


def wait(selector_or_ms: str) -> BrowserResult:
    """Wait for an element to appear or for a time in milliseconds.

    Args:
        selector_or_ms: Either a CSS selector / @ref ID to wait for,
            or a time value in milliseconds (e.g., "1000" for 1 second).

    Returns:
        BrowserResult with success=True if wait completed,
        or success=False and error message if wait failed.

    Example:
        >>> result = wait("@e5")  # wait for element
        >>> result = wait("2000")  # wait 2 seconds
    """
    return _run_browser_cmd(f"wait {selector_or_ms}")


def find_elements(role: str, value: str, action: str = "click", name: str = None) -> BrowserResult:
    """Find elements by accessibility role and value, then optionally perform an action.

    Args:
        role: Accessibility role to search by (e.g., 'button', 'link', 'textbox').
        value: The value, text, or label to match within elements with that role.
        action: Action to perform on the first matching element (default: 'click').
            Common actions: 'click', 'hover', 'focus', 'none'.
        name: Optional accessible name to further filter elements.

    Returns:
        BrowserResult with success=True if element found and action succeeded,
        or success=False and error message if no element matched or action failed.

    Example:
        >>> result = find_elements("button", "Submit")
        >>> result = find_elements("link", "Home", action="none")
    """
    cmd = f"find {role} {value} {action}"
    if name:
        cmd += f" --name {name}"
    return _run_browser_cmd(cmd)


def back() -> BrowserResult:
    """Navigate back to the previous page in browser history.

    Returns:
        BrowserResult with success=True if navigation succeeded,
        or success=False and error message if back navigation failed.

    Example:
        >>> result = back()
    """
    return _run_browser_cmd("back")


def forward() -> BrowserResult:
    """Navigate forward in browser history.

    Returns:
        BrowserResult with success=True if navigation succeeded,
        or success=False and error message if forward navigation failed.

    Example:
        >>> result = forward()
    """
    return _run_browser_cmd("forward")


def reload() -> BrowserResult:
    """Reload the current page.

    Returns:
        BrowserResult with success=True if reload succeeded,
        or success=False and error message if reload failed.

    Example:
        >>> result = reload()
    """
    return _run_browser_cmd("reload")


def close() -> BrowserResult:
    """Close the current browser session.

    Returns:
        BrowserResult with success=True if close succeeded,
        or success=False and error message if close failed.

    Example:
        >>> result = close()
    """
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

    def __init__(self) -> None:
        """Initialize BrowserTool with default state.

        Sets up the browser session state with current_url and last_snapshot
        set to None. Callers must invoke browser binary separately via
        _run_browser_cmd for actual browser automation.
        """
        self.current_url: Optional[str] = None
        self.last_snapshot: Optional[str] = None

    def open(self, url: str) -> str:
        """Open a URL in the browser and return the page snapshot.

        Args:
            url: The URL to navigate to (http/https).

        Returns:
            Page accessibility tree snapshot as string, or error message.
        """
        result = navigate(url)
        if result.success:
            self.current_url = url
            snapshot_result = snapshot()
            self.last_snapshot = snapshot_result.content
            return snapshot_result.content or f"Opened {url}"
        return f"Error: {result.error}"

    def browse(self, url: str, action: str = "snapshot") -> str:
        """Open URL and perform a browser action.

        Args:
            url: The URL to navigate to (http/https).
            action: The action to perform after loading — one of:
                - "snapshot" (default): Return accessibility tree
                - "screenshot": Take and return screenshot path
                - "title": Return page title only

        Returns:
            Result of the specified action, or "Unknown action" if
            the action name is not recognized.
        """
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
        """Get interactive elements from the current page.

        Returns:
            Compact accessibility tree showing only interactive
            elements (buttons, links, inputs), or "No interactive
            elements" if none are found.
        """
        result = snapshot(interactive_only=True, compact=False)
        self.last_snapshot = result.content
        return result.content or "No interactive elements"

    def screenshot(self, path: str = None, full: bool = False) -> str:
        """Take a screenshot of the current page.

        Args:
            path: Optional file path to save the screenshot.
                  If None, a default path is used.
            full: If True, capture the entire scrollable page.
                  If False, capture only the visible viewport.

        Returns:
            Path where the screenshot was saved, or an error message.
        """
        result = screenshot(path, full_page=full, annotate=True)
        return result.message

    def click(self, selector: str) -> str:
        """Click an interactive element by its ref selector.

        Args:
            selector: Element ref from accessibility tree (e.g., "@e5").

        Returns:
            Updated page snapshot after the click, or error message
            if the click failed.
        """
        result = click(selector)
        if result.success:
            snap = snapshot()
            self.last_snapshot = snap.content
            return snap.content or "Clicked"
        return f"Error: {result.error}"

    def fill(self, selector: str, text: str) -> str:
        """Fill an input field with text.

        Args:
            selector: Element ref from accessibility tree (e.g., "@e5").
            text: The text string to type into the field.

        Returns:
            Status message indicating success or an error description.
        """
        result = fill(selector, text)
        return result.message if result.success else f"Error: {result.error}"

    def scroll(self, direction: str = "down", pixels: int = 300) -> str:
        """Scroll the page in a direction.

        Args:
            direction: Scroll direction — "up" or "down" (default: "down").
            pixels: Number of pixels to scroll (default: 300).

        Returns:
            Updated page snapshot after scrolling, or error message
            if the scroll failed.
        """
        result = scroll(direction, pixels)
        if result.success:
            snap = snapshot()
            self.last_snapshot = snap.content
            return snap.content or "Scrolled"
        return f"Error: {result.error}"

    def get_page_info(self) -> Dict[str, str]:
        """Get the current page title and URL.

        Returns:
            Dictionary with "title" (page title string) and "url"
            (current URL string) keys. Values are empty strings if
            the page info could not be retrieved.
        """
        title = get_title()
        url = get_url()
        return {
            "title": title.content or "",
            "url": url.content or ""
        }
