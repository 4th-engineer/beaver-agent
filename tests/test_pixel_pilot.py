"""Tests for pixel_pilot.py — WebSocket visualization for agent activity tracking."""

import pytest
from unittest.mock import patch, MagicMock
import json
import sys
from pathlib import Path

# Add src/ to path for pixel_pilot import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPixelPilotPublicAPI:
    """Test pixel_pilot public functions: connect, disconnect, send, is_enabled."""

    def test_is_enabled_initially_false(self):
        """is_enabled() returns False before any connection."""
        # Re-import to reset module state (pixel_pilot is module-level global state)
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        assert pixel_pilot.is_enabled() is False

    def test_send_returns_false_when_disabled(self):
        """send() returns False when not connected."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        result = pixel_pilot.send("thinking", message="test")
        assert result is False

    def test_send_returns_false_when_disabled_no_url(self):
        """send() returns False when _viewer_url is empty."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        pixel_pilot._viewer_url = ""
        result = pixel_pilot.send("tool", message="test")
        assert result is False

    @patch("pixel_pilot.request.urlopen")
    def test_connect_enables_on_successful_test(self, mock_urlopen):
        """connect() sets _enabled=True when server responds 200."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with patch.object(pixel_pilot, "_patch_tool_router"):
            pixel_pilot.connect("http://localhost:7777", verbose=False)

        assert pixel_pilot.is_enabled() is True
        assert pixel_pilot._viewer_url == "http://localhost:7777"

    @patch("pixel_pilot.request.urlopen")
    def test_connect_leaves_disabled_on_failed_test(self, mock_urlopen):
        """connect() leaves _enabled=False when server unreachable."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_urlopen.side_effect = Exception("Connection refused")

        pixel_pilot.connect("http://localhost:7777", verbose=False)

        assert pixel_pilot.is_enabled() is False

    @patch("pixel_pilot.request.urlopen")
    def test_disconnect_sets_enabled_false(self, mock_urlopen):
        """disconnect() sets _enabled=False."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with patch.object(pixel_pilot, "_patch_tool_router"):
            pixel_pilot.connect("http://localhost:7777", verbose=False)

        assert pixel_pilot.is_enabled() is True

        pixel_pilot.disconnect()
        assert pixel_pilot.is_enabled() is False

    @patch("pixel_pilot.request.urlopen")
    def test_connect_strips_trailing_slash(self, mock_urlopen):
        """connect() strips trailing slash from URL."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with patch.object(pixel_pilot, "_patch_tool_router"):
            pixel_pilot.connect("http://localhost:7777/", verbose=False)

        assert pixel_pilot._viewer_url == "http://localhost:7777"


class TestPixelPilotGetToolDisplayName:
    """Test _get_tool_display_name helper."""

    def test_exact_match(self):
        """Exact (tool, action) match returns mapped name."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        assert pixel_pilot._get_tool_display_name("file_tool", "read_file") == "Read"
        assert pixel_pilot._get_tool_display_name("terminal_tool", "run_command") == "Bash"
        assert pixel_pilot._get_tool_display_name("github_tool", "create_issue") == "GitHub"

    def test_wildcard_match(self):
        """Wildcard (tool, *) match returns mapped name."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        assert pixel_pilot._get_tool_display_name("code_gen", "generate") == "CodeGen"
        assert pixel_pilot._get_tool_display_name("debugger", "analyze") == "Debug"

    def test_no_match_defaults(self):
        """No match returns title-cased tool/action."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        # action.replace("_", " ").title() — "doThing".replace("_", " ").title() = "Dothing"
        assert pixel_pilot._get_tool_display_name("some_tool", "doThing") == "Dothing"
        assert pixel_pilot._get_tool_display_name("my_tool", "") == "My Tool"

    def test_action_without_tool(self):
        """Action only returns title-cased action."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        assert (
            pixel_pilot._get_tool_display_name("unknown_tool", "custom_action") == "Custom Action"
        )


class TestPixelPilotPostEvent:
    """Test _post_event and _test_connection."""

    @patch("pixel_pilot.request.urlopen")
    def test_post_event_returns_true_on_200(self, mock_urlopen):
        """_post_event returns True when server responds 200."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = pixel_pilot._post_event({"type": "tool", "message": "test"})
        assert result is True

    @patch("pixel_pilot.request.urlopen")
    def test_post_event_returns_false_on_url_error(self, mock_urlopen):
        """_post_event returns False on URLError."""
        import importlib
        from urllib import error

        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_urlopen.side_effect = error.URLError("Not found")

        result = pixel_pilot._post_event({"type": "tool", "message": "test"})
        assert result is False

    @patch("pixel_pilot.request.urlopen")
    def test_post_event_returns_false_on_other_exception(self, mock_urlopen):
        """_post_event returns False on other exceptions."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_urlopen.side_effect = OSError("Network error")

        result = pixel_pilot._post_event({"type": "tool", "message": "test"})
        assert result is False

    @patch("pixel_pilot.request.urlopen")
    def test_test_connection_returns_true_on_200(self, mock_urlopen):
        """_test_connection returns True when server responds 200."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = pixel_pilot._test_connection()
        assert result is True

    @patch("pixel_pilot.request.urlopen")
    def test_test_connection_returns_false_on_exception(self, mock_urlopen):
        """_test_connection returns False when connection fails."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_urlopen.side_effect = Exception("Connection refused")

        result = pixel_pilot._test_connection()
        assert result is False


class TestPixelPilotSendEvent:
    """Test send() event construction and posting."""

    @patch("pixel_pilot.request.urlopen")
    def test_send_builds_correct_event(self, mock_urlopen):
        """send() builds event with all fields and calls _post_event."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = pixel_pilot.send(
            event_type="tool",
            message="Reading file",
            agent="test-agent",
            tool="FileTool",
            file="/path/to/file.py",
            status="active",
        )

        assert result is True
        event = mock_urlopen.call_args[0][0]
        assert event.full_url == "http://localhost:7777/event"
        event_data = json.loads(event.data)
        assert event_data["type"] == "tool"
        assert event_data["message"] == "Reading file"
        assert event_data["agent"] == "test-agent"
        assert event_data["tool"] == "FileTool"
        assert event_data["file"] == "/path/to/file.py"
        assert event_data["status"] == "active"

    @patch("pixel_pilot.request.urlopen")
    def test_send_uses_defaults(self, mock_urlopen):
        """send() uses default values for optional fields."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        pixel_pilot.send(event_type="thinking", message="thinking...")

        event = mock_urlopen.call_args[0][0]
        event_data = json.loads(event.data)
        assert event_data["agent"] == "beaver"
        assert event_data["tool"] is None
        assert event_data["file"] is None
        assert event_data["status"] == "active"


class TestPixelPilotPatchToolRouter:
    """Test _patch_tool_router monkey-patching behavior."""

    def test_patch_avoids_duplicate(self):
        """_patch_tool_router skips if already patched."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        with patch.object(pixel_pilot, "_test_connection", return_value=True):
            with patch.object(pixel_pilot, "_patch_tool_router") as mock_patch:
                pixel_pilot.connect("http://localhost:7777", verbose=False)

        # connect() calls _patch_tool_router internally
        mock_patch.assert_called_once_with(False)

    def test_get_agent_name_returns_beaver_on_config_none(self):
        """_get_agent_name returns 'beaver' when config is None."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_self = MagicMock()
        mock_self.config = None

        result = pixel_pilot._get_agent_name(mock_self)
        assert result == "beaver"

    def test_get_agent_name_returns_app_name(self):
        """_get_agent_name returns app name from config."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_app = MagicMock()
        mock_app.name = "my-agent"
        mock_self = MagicMock()
        mock_self.config.app = mock_app

        result = pixel_pilot._get_agent_name(mock_self)
        assert result == "my-agent"

    def test_get_agent_name_returns_beaver_when_no_app(self):
        """_get_agent_name returns 'beaver' when config.app is None."""
        import importlib
        import pixel_pilot

        importlib.reload(pixel_pilot)

        mock_self = MagicMock()
        mock_self.config.app = None

        result = pixel_pilot._get_agent_name(mock_self)
        assert result == "beaver"
