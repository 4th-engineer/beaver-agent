---
name: mcp-config
category: system
description: 自动配置 MCP 服务器 - 用户说"配置xxx MCP"时自动创建配置文件
trigger: 配置
---

# MCP Config Skill

当用户请求配置 MCP 服务器时，自动生成并写入配置文件到 `mcp_configs/` 目录。

## 触发条件

用户说以下类型的话时触发：
- "配置 xxx MCP"
- "添加 xxx MCP server"
- "我想用 xxx MCP"
- "帮我配置一个 xxx 服务器"

## 支持的 MCP 服务器模板

### GitHub
```yaml
command: "npx"
args:
  - "-y"
  - "@modelcontextprotocol/server-github"
env:
  GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
```

### Filesystem
```yaml
command: "npx"
args:
  - "-y"
  - "@modelcontextprotocol/server-filesystem"
  - "/home/user/projects"
```

### Time
```yaml
command: "uvx"
args:
  - "mcp-server-time"
```

### Brave Search
```yaml
command: "npx"
args:
  - "-y"
  - "@modelcontextprotocol/server-brave-search"
env:
  BRAVE_API_KEY: "${BRAVE_API_KEY}"
```

### Slack
```yaml
command: "npx"
args:
  - "-y"
  - "@modelcontextprotocol/server-slack"
env:
  SLACK_BOT_TOKEN: "${SLACK_BOT_TOKEN}"
```

## 执行步骤

1. 解析用户请求，识别要配置的 MCP 服务器名称
2. 根据服务器类型选择对应模板
3. 检查 `mcp_configs/` 目录是否存在，如不存在则创建
4. 检查配置文件是否已存在，如已存在则询问用户是否覆盖
5. 写入配置文件到 `mcp_configs/{server_name}.yaml`
6. 返回成功消息，告知用户需要重启智能体或触发重新加载

## 配置参数

用户可以通过在请求中指定参数来定制：
- 工作目录（如 "配置 GitHub MCP，工作目录是 /home/user/project"）
- 环境变量（如 "配置 Slack MCP，token 是 xoxb-xxx"）

## 返回格式

成功时：
```
✅ MCP 服务器配置完成！

📦 服务器: {server_name}
📁 配置文件: mcp_configs/{server_name}.yaml
🔄 下一步: 重启智能体或发送 "/reload mcp" 重新加载
```

失败时：
```
❌ 配置失败: {原因}
💡 提示: {建议}
```
