---
name: project-analyzer
category: analysis
description: 分析项目结构、代码量、技术栈
trigger: 分析项目
required_commands: []
---

# Project Analyzer Skill

分析项目结构，生成项目概览报告。

## 功能

- 统计代码行数（LOC）
- 分析技术栈
- 生成目录树
- 检查依赖关系

## 使用方法

当用户说 "分析项目"、"看看项目结构" 时触发。

## 执行步骤

1. 扫描项目目录结构
2. 统计各语言代码行数
3. 分析依赖配置文件（package.json, requirements.txt, pyproject.toml 等）
4. 生成报告

## 输出格式

```
📊 项目分析报告

🏗️ 项目结构:
[目录树]

📈 代码统计:
- Python: XXX 行
- JavaScript: XXX 行
- ...

🛠️ 技术栈:
- 框架: xxx
- 依赖: xxx

📦 依赖包:
- package1: version
- package2: version
```
