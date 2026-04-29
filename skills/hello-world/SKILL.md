---
name: hello-world
category: utility
description: A simple hello world skill demonstrating the skill format
trigger: hello
---

# Hello World Skill

A simple demonstration skill that responds to "hello" triggers.

## Usage

When user says something containing "hello", this skill responds with a greeting.

## Implementation

```python
def execute(user_input: str) -> str:
    return "👋 你好！我是 beaver-bot，有什么可以帮你的吗？"
```
