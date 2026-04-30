.PHONY: help setup init run test lint fmt type-check clean doctor

# 自动检测项目根目录
SCRIPT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PROJECT_ROOT := $(SCRIPT_DIR)

help:
	@echo "🦫 Beaver Agent"
	@echo ""
	@echo "  make setup       首次安装 (创建 venv + 安装 + .env)"
	@echo "  make run         启动 CLI"
	@echo "  make run ARGS='-q \"问题\"'  单次查询"
	@echo "  make test        运行测试"
	@echo "  make lint        代码检查"
	@echo "  make fmt         格式化代码"
	@echo "  make type-check  类型检查"
	@echo "  make doctor      环境检查"
	@echo "  make clean       清理缓存"

# ── 安装 ─────────────────────────────────────────────

setup:
	@echo "📦 初始化 Beaver Agent..."
	@if [ ! -f "$(PROJECT_ROOT)/pyproject.toml" ]; then \
		echo "❌ pyproject.toml not found"; exit 1; \
	fi
	@if [ ! -d "$(PROJECT_ROOT)/.venv" ]; then \
		echo "  创建虚拟环境..."; \
		python3 -m venv .venv; \
	fi
	@.venv/bin/python -m pip install -e ".[dev]"
	@beaver setup --force
	@echo "✅ 安装完成 — 运行 'beaver run' 开始"

# ── 运行 ─────────────────────────────────────────────

run:
	@beaver run $(ARGS)

# ── 测试 ─────────────────────────────────────────────

test:
	@.venv/bin/python -m pytest tests/ -v --ignore=tests/test_cli.py

# ── 代码质量 ─────────────────────────────────────────

lint:
	@.venv/bin/python -m ruff check src/

fmt:
	@.venv/bin/python -m ruff format src/ tests/

type-check:
	@.venv/bin/python -m mypy src/

# ── 环境检查 ─────────────────────────────────────────

doctor:
	@echo "🔍 环境检查..."
	@echo ""
	@echo "Python: $$('.venv/bin/python' --version 2>/dev/null || python3 --version)"
	@echo ""
	@echo "已安装:"
	@.venv/bin/python -m pip list 2>/dev/null | grep -E "beaver|typer|rich|pydantic" || echo "  (use 'make setup' first)"
	@echo ""
	@echo "配置文件:"
	@if [ -f .env ]; then echo "  ✅ .env"; else echo "  ⚠️  .env 不存在 (make setup)"; fi
	@if [ -f config/settings.yaml ]; then echo "  ✅ config/settings.yaml"; else echo "  ❌ config/settings.yaml 缺失"; fi

# ── 清理 ─────────────────────────────────────────────

clean:
	@echo "🧹 清理..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .coverage htmlcov/
	@echo "✅ 完成"
