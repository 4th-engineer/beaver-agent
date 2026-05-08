# 🦫 Beaver Agent

> Self-evolving AI coding assistant — 让代码自己变好。

[![Tests](https://img.shields.io/badge/tests-741%20passed-blue)](https://github.com/4th-engineer/beaver-agent)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

---

## 安装

```bash
git clone https://github.com/4th-engineer/beaver-agent.git
cd beaver-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
beaver setup
```

---

## 命令

| 命令 | 说明 |
|------|------|
| `beaver run` | 启动交互式 REPL |
| `beaver chat -q "问题"` | 单次查询 |
| `beaver map` | 生成代码地图索引（AST 分析，零 LLM 调用） |
| `beaver model` | 查看/切换模型 |
| `beaver setup` | 首次配置 |
| `beaver version` | 版本信息 |

**REPL 内置命令：** `/help` `/exit` `/clear` `/model` `/status` `/debug` `/analyze` `/browse` `/screenshot` `/map`

---

## 功能

**代码智能**
- 代码生成、审查、调试
- GitHub 集成（仓库、Issue、PR）
- 网页浏览 + 截图

**自我进化**
- 每小时自动运行改进周期：代码审计 → 添加测试 → 改进文档
- 所有变更记录到 `.evolution/log.md`

**可扩展架构**
- `skills/` — 关键词触发的可插拔技能模块
- `mcp_configs/` — YAML 配置 MCP 服务器
- `src/beaver_agent/tools/` — 模块化工具系统

**代码地图**
- `beaver map` 对项目做 AST 静态分析，生成 `.beaver/` 索引
- 包含文件树、导入/导出关系、依赖图、入口点
- 纯静态分析，不调用 LLM

---

## 项目结构

```
beaver-agent/
├── src/beaver_agent/
│   ├── core/
│   │   ├── agent.py              # Agent 主循环
│   │   ├── intent_parser.py      # 意图识别
│   │   ├── task_planner.py       # 任务规划
│   │   ├── tool_router.py        # 工具路由
│   │   ├── skill_manager.py      # Skill 管理
│   │   ├── mcp_manager.py        # MCP 服务器管理
│   │   ├── llm_client.py         # LLM 客户端
│   │   ├── memory/               # 记忆系统（Session + LongTerm）
│   │   └── eval/                 # 评测框架（BeaverHarness）
│   ├── tools/
│   │   ├── code_gen.py           # 代码生成
│   │   ├── code_review.py        # 代码审查
│   │   ├── debugger.py           # 调试助手
│   │   ├── github_tool.py        # GitHub 集成
│   │   ├── browser_tool.py       # 网页浏览
│   │   ├── file_tool.py          # 文件操作
│   │   ├── terminal_tool.py      # 终端操作
│   │   ├── code_analyzer.py      # 仓库分析
│   │   └── mapper.py             # 代码地图生成
│   └── cli/
│       ├── interactive.py        # REPL 主循环
│       └── commands.py           # 内置命令
├── skills/                        # 用户可扩展 Skills
├── mcp_configs/                   # MCP 服务器配置
├── tests/                         # 741 tests

```

---

## 开发

```bash
pytest tests/ -q      # 运行测试
ruff check .         # 代码检查
ruff format .        # 格式化
mypy src/            # 类型检查
```

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| LLM | MiniMax-M2.7（Anthropic 兼容 API） |
| 日志 | structlog |
| 配置 | Pydantic + YAML + python-dotenv |
| 测试 | pytest + pytest-asyncio |
| 代码检查 | ruff + mypy |

---

## License

MIT
