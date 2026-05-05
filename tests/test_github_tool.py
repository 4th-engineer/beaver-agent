"""Tests for GitHubTool"""

import pytest
from unittest.mock import MagicMock, patch


class MockGitHubConfig:
    """Mock GitHub config for testing"""
    def __init__(self, token="test-token", owner="test-owner", repo="test-repo"):
        self.token = token
        self.owner = owner
        self.repo = repo


class MockBeaverConfig:
    """Mock BeaverConfig with GitHub subconfig for testing"""
    def __init__(self, token="test-token", owner="test-owner", repo="test-repo"):
        self.github = MockGitHubConfig(token, owner, repo)


class TestGitHubToolInit:
    """Tests for GitHubTool.__init__"""

    def test_init_with_full_config(self):
        """Test initialization with complete GitHub config"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="my-token", owner="my-owner", repo="my-repo")
        tool = GitHubTool(config)
        assert tool.token == "my-token"
        assert tool.owner == "my-owner"
        assert tool.repo == "my-repo"

    def test_init_with_missing_github_attr(self):
        """Test initialization when config has no github attribute"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MagicMock()
        del config.github
        tool = GitHubTool(config)
        assert tool.token is None
        assert tool.owner is None
        assert tool.repo is None

    def test_init_with_partial_github_attr(self):
        """Test initialization with partial GitHub attributes"""
        from beaver_agent.tools.github_tool import GitHubTool

        class PartialConfig:
            class PartialGitHub:
                token = "only-token"
            github = PartialGitHub()

        tool = GitHubTool(PartialConfig())
        assert tool.token == "only-token"
        assert tool.owner is None
        assert tool.repo is None

    def test_init_with_empty_token(self):
        """Test initialization with empty token"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="", owner="owner", repo="repo")
        tool = GitHubTool(config)
        assert tool.token == ""
        assert tool.owner == "owner"
        assert tool.repo == "repo"


class TestGitHubToolCheckConfig:
    """Tests for GitHubTool._check_config"""

    def test_check_config_all_present(self):
        """Test _check_config returns True when all fields present"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="tok", owner="own", repo="rep")
        tool = GitHubTool(config)
        assert tool._check_config() is True

    def test_check_config_missing_token(self):
        """Test _check_config returns False when token missing"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="", owner="own", repo="rep")
        tool = GitHubTool(config)
        assert tool._check_config() is False

    def test_check_config_missing_owner(self):
        """Test _check_config returns False when owner missing"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="tok", owner="", repo="rep")
        tool = GitHubTool(config)
        assert tool._check_config() is False

    def test_check_config_missing_repo(self):
        """Test _check_config returns False when repo missing"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="tok", owner="own", repo="")
        tool = GitHubTool(config)
        assert tool._check_config() is False


class TestGitHubToolOperate:
    """Tests for GitHubTool.operate"""

    def test_operate_unknown_action(self):
        """Test operate returns error for unknown action"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)
        result = tool.operate("unknown_action")
        assert result == "Unknown action: unknown_action"

    def test_operate_uses_instance_owner_repo(self):
        """Test operate uses instance owner/repo when not provided"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        with patch.object(tool, 'get_repo_info', return_value="mocked") as mock_get:
            result = tool.operate("info")
            mock_get.assert_called_once_with("test-owner", "test-repo")
            assert result == "mocked"

    def test_operate_accepts_override_owner_repo(self):
        """Test operate accepts override owner/repo parameters"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        with patch.object(tool, 'get_repo_info', return_value="mocked") as mock_get:
            result = tool.operate("info", "other-owner", "other-repo")
            mock_get.assert_called_once_with("other-owner", "other-repo")

    def test_operate_dispatches_create_issue(self):
        """Test operate dispatches to create_issue"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        with patch.object(tool, 'create_issue', return_value="mocked") as mock_create:
            result = tool.operate("create_issue", "o", "r", title="Bug", body="desc")
            mock_create.assert_called_once_with("o", "r", "Bug", "desc")
            assert result == "mocked"

    def test_operate_dispatches_list_issues(self):
        """Test operate dispatches to list_issues (state uses default 'open')"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        with patch.object(tool, 'list_issues', return_value="mocked") as mock_list:
            result = tool.operate("list_issues", "o", "r")
            # Note: state is NOT passed through operate; list_issues uses its own default
            mock_list.assert_called_once_with("o", "r")

    def test_operate_dispatches_get_issue(self):
        """Test operate dispatches to get_issue"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        with patch.object(tool, 'get_issue', return_value="mocked") as mock_get:
            result = tool.operate("get_issue", "o", "r", number=42)
            mock_get.assert_called_once_with("o", "r", 42)
            assert result == "mocked"

    def test_operate_dispatches_create_pr(self):
        """Test operate dispatches to create_pr"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        with patch.object(tool, 'create_pr', return_value="mocked") as mock_pr:
            result = tool.operate("create_pr", "o", "r", title="PR", body="desc", head="feature", base="main")
            mock_pr.assert_called_once_with("o", "r", "PR", "desc", "feature", "main")
            assert result == "mocked"


class TestGitHubToolGetRepoInfo:
    """Tests for GitHubTool.get_repo_info"""

    def test_get_repo_info_config_not_set(self):
        """Test get_repo_info returns error when config not set"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="", owner="", repo="")
        tool = GitHubTool(config)
        result = tool.get_repo_info("o", "r")
        assert "❌ GitHub token not configured" in result

    @patch("requests.get")
    def test_get_repo_info_success(self, mock_get):
        """Test get_repo_info returns formatted info on success"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stargazers_count": 100,
            "forks_count": 20,
            "watchers_count": 50,
            "open_issues_count": 5,
            "language": "Python",
            "description": "A test repo",
            "html_url": "https://github.com/test/repo"
        }
        mock_get.return_value = mock_response

        result = tool.get_repo_info("test-owner", "test-repo")

        assert "🐙 GitHub 仓库信息" in result
        assert "test-owner/test-repo" in result
        assert "⭐ Stars: 100" in result
        assert "🍴 Forks: 20" in result
        assert "👁️ Watchers: 50" in result
        assert "📝 Issues: 5" in result
        assert "🏷️ Language: Python" in result
        assert "📖 Description: A test repo" in result

    @patch("requests.get")
    def test_get_repo_info_api_error(self, mock_get):
        """Test get_repo_info returns error on non-200 response"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        result = tool.get_repo_info("test-owner", "test-repo")

        assert "❌ Failed to get repo info: 404" in result

    @patch("requests.get")
    def test_get_repo_info_request_exception(self, mock_get):
        """Test get_repo_info handles request exceptions"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_get.side_effect = Exception("Network error")

        result = tool.get_repo_info("test-owner", "test-repo")

        assert "❌ Error: Check logs for details." in result


class TestGitHubToolCreateIssue:
    """Tests for GitHubTool.create_issue"""

    def test_create_issue_config_not_set(self):
        """Test create_issue returns error when config not set"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="", owner="", repo="")
        tool = GitHubTool(config)
        result = tool.create_issue("o", "r", "Title", "Body")
        assert "❌ GitHub token not configured" in result

    @patch("requests.post")
    def test_create_issue_success(self, mock_post):
        """Test create_issue returns success message on 201"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 42,
            "title": "Bug Report",
            "html_url": "https://github.com/test/repo/issues/42"
        }
        mock_post.return_value = mock_response

        result = tool.create_issue("o", "r", "Bug Report", "Description")

        assert "✅ Issue 创建成功" in result
        assert "#42" in result
        assert "Bug Report" in result

    @patch("requests.post")
    def test_create_issue_api_error(self, mock_post):
        """Test create_issue returns error on non-201 response"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        result = tool.create_issue("o", "r", "Title", "Body")

        assert "❌ Failed to create issue: 403" in result

    @patch("requests.post")
    def test_create_issue_request_exception(self, mock_post):
        """Test create_issue handles request exceptions"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_post.side_effect = Exception("Network error")

        result = tool.create_issue("o", "r", "Title", "Body")

        assert "❌ Error: Check logs for details." in result


class TestGitHubToolListIssues:
    """Tests for GitHubTool.list_issues"""

    def test_list_issues_config_not_set(self):
        """Test list_issues returns error when config not set"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="", owner="", repo="")
        tool = GitHubTool(config)
        result = tool.list_issues("o", "r")
        assert "❌ GitHub token not configured" in result

    @patch("requests.get")
    def test_list_issues_success(self, mock_get):
        """Test list_issues returns formatted issue list"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"number": 1, "title": "Bug 1"},
            {"number": 2, "title": "Bug 2"}
        ]
        mock_get.return_value = mock_response

        result = tool.list_issues("o", "r", state="open")

        assert "📋 Open Issues (2)" in result
        assert "#1: Bug 1" in result
        assert "#2: Bug 2" in result

    @patch("requests.get")
    def test_list_issues_empty(self, mock_get):
        """Test list_issues handles empty result"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = tool.list_issues("o", "r")

        assert "No open issues found" in result

    @patch("requests.get")
    def test_list_issues_api_error(self, mock_get):
        """Test list_issues returns error on non-200 response"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = tool.list_issues("o", "r")

        assert "❌ Failed to list issues: 500" in result

    @patch("requests.get")
    def test_list_issues_request_exception(self, mock_get):
        """Test list_issues handles request exceptions"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_get.side_effect = Exception("Network error")

        result = tool.list_issues("o", "r")

        assert "❌ Error: Check logs for details." in result


class TestGitHubToolGetIssue:
    """Tests for GitHubTool.get_issue"""

    def test_get_issue_config_not_set(self):
        """Test get_issue returns error when config not set"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="", owner="", repo="")
        tool = GitHubTool(config)
        result = tool.get_issue("o", "r", 42)
        assert "❌ GitHub token not configured" in result

    @patch("requests.get")
    def test_get_issue_success(self, mock_get):
        """Test get_issue returns formatted issue details"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": 42,
            "title": "Bug Report",
            "state": "open",
            "labels": [{"name": "bug"}, {"name": "urgent"}],
            "user": {"login": "testuser"},
            "html_url": "https://github.com/test/repo/issues/42",
            "body": "Issue description"
        }
        mock_get.return_value = mock_response

        result = tool.get_issue("o", "r", 42)

        assert "📋 Issue #42" in result
        assert "**Title**: Bug Report" in result
        assert "**State**: open" in result
        assert "bug, urgent" in result
        assert "**Author**: testuser" in result
        assert "Issue description" in result

    @patch("requests.get")
    def test_get_issue_not_found(self, mock_get):
        """Test get_issue returns error on 404"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = tool.get_issue("o", "r", 999)

        assert "❌ Issue not found: 404" in result

    @patch("requests.get")
    def test_get_issue_request_exception(self, mock_get):
        """Test get_issue handles request exceptions"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_get.side_effect = Exception("Network error")

        result = tool.get_issue("o", "r", 42)

        assert "❌ Error: Check logs for details." in result


class TestGitHubToolCreatePR:
    """Tests for GitHubTool.create_pr"""

    def test_create_pr_config_not_set(self):
        """Test create_pr returns error when config not set"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig(token="", owner="", repo="")
        tool = GitHubTool(config)
        result = tool.create_pr("o", "r", "Title", "Body", "head", "main")
        assert "❌ GitHub token not configured" in result

    @patch("requests.post")
    def test_create_pr_success(self, mock_post):
        """Test create_pr returns success message on 201"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 15,
            "title": "Feature PR",
            "html_url": "https://github.com/test/repo/pull/15"
        }
        mock_post.return_value = mock_response

        result = tool.create_pr("o", "r", "Feature PR", "Description", "feature-branch", "main")

        assert "✅ PR 创建成功" in result
        assert "#15" in result
        assert "Feature PR" in result

    @patch("requests.post")
    def test_create_pr_api_error(self, mock_post):
        """Test create_pr returns error on non-201 response"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Validation Failed"
        mock_post.return_value = mock_response

        result = tool.create_pr("o", "r", "Title", "Body", "head", "main")

        assert "❌ Failed to create PR: 422" in result

    @patch("requests.post")
    def test_create_pr_request_exception(self, mock_post):
        """Test create_pr handles request exceptions"""
        from beaver_agent.tools.github_tool import GitHubTool
        config = MockBeaverConfig()
        tool = GitHubTool(config)

        mock_post.side_effect = Exception("Network error")

        result = tool.create_pr("o", "r", "Title", "Body", "head", "main")

        assert "❌ Error: Check logs for details." in result
