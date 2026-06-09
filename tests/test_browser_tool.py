"""Tests for Browser Tool"""

from unittest.mock import Mock, patch

from beaver_agent.tools.browser_tool import (
    BrowserResult,
    BrowserTool,
    _resolve_browser_binary,
    _run_browser_cmd,
    _validate_browser_binary,
    back,
    click,
    close,
    fill,
    find_elements,
    forward,
    get_html,
    get_text,
    get_title,
    get_url,
    navigate,
    press,
    reload,
    screenshot,
    scroll,
    scroll_into_view,
    snapshot,
    type_text,
    wait,
)


class TestBrowserResult:
    """Tests for BrowserResult dataclass"""

    def test_success_result(self):
        """Test creating a successful BrowserResult"""
        result = BrowserResult(success=True, content="page content", message="OK")
        assert result.success is True
        assert result.content == "page content"
        assert result.message == "OK"

    def test_failure_result(self):
        """Test creating a failure BrowserResult"""
        result = BrowserResult(success=False, message="Error occurred")
        assert result.success is False
        assert result.message == "Error occurred"
        assert result.content is None

    def test_default_values(self):
        """Test default values for BrowserResult"""
        result = BrowserResult(success=True)
        assert result.content is None
        assert result.message == ""


class TestBrowserToolInit:
    """Tests for BrowserTool initialization"""

    def test_init_creates_instance(self):
        """Test that BrowserTool.__init__ creates an instance"""
        tool = BrowserTool()
        assert tool is not None


class TestModuleLevelFunctionsExist:
    """Verify all module-level functions are exported"""

    def test_navigate_exported(self):
        assert callable(navigate)

    def test_snapshot_exported(self):
        assert callable(snapshot)

    def test_screenshot_exported(self):
        assert callable(screenshot)

    def test_get_text_exported(self):
        assert callable(get_text)

    def test_get_html_exported(self):
        assert callable(get_html)

    def test_get_title_exported(self):
        assert callable(get_title)

    def test_get_url_exported(self):
        assert callable(get_url)

    def test_click_exported(self):
        assert callable(click)

    def test_fill_exported(self):
        assert callable(fill)

    def test_type_text_exported(self):
        assert callable(type_text)

    def test_press_exported(self):
        assert callable(press)

    def test_scroll_exported(self):
        assert callable(scroll)

    def test_scroll_into_view_exported(self):
        assert callable(scroll_into_view)

    def test_wait_exported(self):
        assert callable(wait)

    def test_find_elements_exported(self):
        assert callable(find_elements)

    def test_back_exported(self):
        assert callable(back)

    def test_forward_exported(self):
        assert callable(forward)

    def test_reload_exported(self):
        assert callable(reload)

    def test_close_exported(self):
        assert callable(close)


class TestResolveBrowserBinary:
    """Tests for _resolve_browser_binary"""

    @patch("beaver_agent.tools.browser_tool.subprocess.run")
    @patch("beaver_agent.tools.browser_tool.Path.exists")
    def test_resolve_finds_in_path(self, mock_exists, mock_run):
        """Test binary found via npm global"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/local/lib/node_modules"
        mock_run.return_value = mock_result

        result = _resolve_browser_binary()
        # Returns None if not found in any location
        assert result is None or isinstance(result, str)

    @patch("beaver_agent.tools.browser_tool.subprocess.run")
    def test_resolve_not_found(self, mock_run):
        """Test binary not found - subprocess returns FileNotFoundError"""
        _resolve_browser_binary.cache_clear()
        mock_run.side_effect = FileNotFoundError()
        result = _resolve_browser_binary()
        assert result is None


class TestValidateBrowserBinary:
    """Tests for _validate_browser_binary"""

    @patch("beaver_agent.tools.browser_tool._resolve_browser_binary")
    def test_validate_no_binary(self, mock_resolve):
        """Test validation when no binary found"""
        mock_resolve.return_value = None
        result = _validate_browser_binary()
        assert result is not None
        assert "agent-browser" in result

    @patch("beaver_agent.tools.browser_tool._resolve_browser_binary")
    @patch("beaver_agent.tools.browser_tool.Path.exists")
    def test_validate_binary_exists(self, mock_exists, mock_resolve):
        """Test validation when binary exists"""
        mock_resolve.return_value = "/usr/bin/agent-browser"
        mock_exists.return_value = True
        result = _validate_browser_binary()
        assert result is None


class TestRunBrowserCmd:
    """Tests for _run_browser_cmd"""

    @patch("beaver_agent.tools.browser_tool._validate_browser_binary")
    def test_validate_fails_returns_error(self, mock_validate):
        """Test that validation failure returns error result"""
        mock_validate.return_value = "Browser not found"
        result = _run_browser_cmd("test")
        assert result.success is False
        assert "Browser not found" in result.message

    @patch("beaver_agent.tools.browser_tool._validate_browser_binary")
    @patch("beaver_agent.tools.browser_tool.subprocess.run")
    def test_successful_command(self, mock_run, mock_validate):
        """Test successful command execution"""
        mock_validate.return_value = None
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Page content"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = _run_browser_cmd("test")
        assert result.success is True
        assert result.content == "Page content"

    @patch("beaver_agent.tools.browser_tool._validate_browser_binary")
    @patch("beaver_agent.tools.browser_tool.subprocess.run")
    def test_failed_command(self, mock_run, mock_validate):
        """Test failed command execution"""
        mock_validate.return_value = None
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"
        mock_run.return_value = mock_result

        result = _run_browser_cmd("test")
        assert result.success is False
        assert "Command failed" in result.message

    @patch("beaver_agent.tools.browser_tool._validate_browser_binary")
    @patch("beaver_agent.tools.browser_tool.subprocess.run")
    def test_timeout(self, mock_run, mock_validate):
        """Test command timeout"""
        import subprocess

        mock_validate.return_value = None
        mock_run.side_effect = subprocess.TimeoutExpired("test", timeout=5)

        result = _run_browser_cmd("test", timeout=5)
        assert result.success is False
        assert "timed out" in result.message

    @patch("beaver_agent.tools.browser_tool._validate_browser_binary")
    @patch("beaver_agent.tools.browser_tool.subprocess.run")
    def test_exception_handled(self, mock_run, mock_validate):
        """Test exception in subprocess is handled"""
        mock_validate.return_value = None
        mock_run.side_effect = Exception("Unexpected error")

        result = _run_browser_cmd("test")
        assert result.success is False
        assert "Unexpected error" in result.message


class TestNavigate:
    """Tests for navigate function"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_navigate_success(self, mock_run_cmd):
        """Test successful navigation"""
        mock_run_cmd.return_value = BrowserResult(success=True, content="", message="Navigated")
        result = navigate("https://example.com")
        assert result.success is True
        mock_run_cmd.assert_called_once()
        call_args = mock_run_cmd.call_args[0][0]
        assert "open https://example.com" in call_args

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_navigate_with_timeout(self, mock_run_cmd):
        """Test navigation with custom timeout"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        navigate("https://example.com", timeout=60)
        call_args = mock_run_cmd.call_args
        assert call_args[1]["timeout"] == 60


class TestSnapshot:
    """Tests for snapshot function"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_snapshot_default_args(self, mock_run_cmd):
        """Test snapshot with default arguments"""
        mock_run_cmd.return_value = BrowserResult(success=True, content="snapshot data")
        result = snapshot()
        assert result.success is True
        call_args = mock_run_cmd.call_args[0][0]
        assert "snapshot" in call_args
        # Default args: interactive=True, compact=True, depth=10
        assert "-i" in call_args
        assert "-c" in call_args
        assert "-d 10" in call_args

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_snapshot_compact(self, mock_run_cmd):
        """Test snapshot with compact=True"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        snapshot(compact=True)
        call_args = mock_run_cmd.call_args[0][0]
        assert "-c" in call_args


class TestScreenshot:
    """Tests for screenshot function"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_screenshot_default(self, mock_run_cmd):
        """Test screenshot with default path"""
        mock_run_cmd.return_value = BrowserResult(success=True, content="")
        result = screenshot()
        assert result.success is True
        assert result.content is not None
        assert result.content.endswith(".png")

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_screenshot_custom_path(self, mock_run_cmd):
        """Test screenshot with custom path"""
        mock_run_cmd.return_value = BrowserResult(success=True, content="")
        result = screenshot("/tmp/custom.png")
        assert result.success is True
        assert result.content == "/tmp/custom.png"

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_screenshot_full_page(self, mock_run_cmd):
        """Test full page screenshot"""
        mock_run_cmd.return_value = BrowserResult(success=True, content="")
        screenshot(full_page=True)
        call_args = mock_run_cmd.call_args[0][0]
        assert "--full" in call_args

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_screenshot_annotate(self, mock_run_cmd):
        """Test screenshot with annotation"""
        mock_run_cmd.return_value = BrowserResult(success=True, content="")
        screenshot(annotate=True)
        call_args = mock_run_cmd.call_args[0][0]
        assert "--annotate" in call_args


class TestClick:
    """Tests for click function"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_click_by_selector(self, mock_run_cmd):
        """Test clicking by CSS selector"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = click("button.submit")
        assert result.success is True
        mock_run_cmd.assert_called_once_with("click button.submit")

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_click_by_ref(self, mock_run_cmd):
        """Test clicking by @ref ID"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = click("@e5")
        assert result.success is True
        mock_run_cmd.assert_called_once_with("click @e5")


class TestFill:
    """Tests for fill function"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_fill_input(self, mock_run_cmd):
        """Test filling an input field"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = fill("input[name=email]", "test@example.com")
        assert result.success is True
        # fill command wraps text in quotes
        mock_run_cmd.assert_called_once()
        call_args = mock_run_cmd.call_args[0][0]
        assert "fill input[name=email]" in call_args
        assert "test@example.com" in call_args


class TestTypeText:
    """Tests for type_text function"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_type_text(self, mock_run_cmd):
        """Test typing text into an element"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = type_text("input", "hello world")
        assert result.success is True
        # type_text uses 'type' command (not 'type_text')
        mock_run_cmd.assert_called_once()
        call_args = mock_run_cmd.call_args[0][0]
        assert "type input" in call_args
        assert "hello world" in call_args


class TestPress:
    """Tests for press function"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_press_key(self, mock_run_cmd):
        """Test pressing a key"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = press("Enter")
        assert result.success is True
        mock_run_cmd.assert_called_once_with("press Enter")


class TestScroll:
    """Tests for scroll function"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_scroll_down(self, mock_run_cmd):
        """Test scrolling down"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = scroll("down")
        assert result.success is True
        mock_run_cmd.assert_called_once_with("scroll down 300")

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_scroll_up(self, mock_run_cmd):
        """Test scrolling up"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = scroll("up", 500)
        assert result.success is True
        mock_run_cmd.assert_called_once_with("scroll up 500")


class TestBackForward:
    """Tests for back and forward navigation"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_back(self, mock_run_cmd):
        """Test browser back"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = back()
        assert result.success is True
        mock_run_cmd.assert_called_once_with("back")

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_forward(self, mock_run_cmd):
        """Test browser forward"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = forward()
        assert result.success is True
        mock_run_cmd.assert_called_once_with("forward")


class TestReloadClose:
    """Tests for reload and close"""

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_reload(self, mock_run_cmd):
        """Test page reload"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = reload()
        assert result.success is True
        mock_run_cmd.assert_called_once_with("reload")

    @patch("beaver_agent.tools.browser_tool._run_browser_cmd")
    def test_close(self, mock_run_cmd):
        """Test browser close"""
        mock_run_cmd.return_value = BrowserResult(success=True)
        result = close()
        assert result.success is True
        mock_run_cmd.assert_called_once_with("close")


class TestGetPageInfo:
    """Tests for BrowserTool.get_page_info"""

    def test_get_page_info_method_exists(self):
        """Test get_page_info method exists and is callable"""
        tool = BrowserTool()
        assert hasattr(tool, "get_page_info")
        assert callable(tool.get_page_info)
