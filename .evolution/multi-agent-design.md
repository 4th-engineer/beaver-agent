# Multi-Agent 协同架构设计

> 状态：**已确认**，待实现

## 核心决策

| 决策项 | 选择 |
|--------|------|
| Worker 生命周期 | 任务级（用完即销毁） |
| 并行度上限 | 无限制，按 CPU 动态调整 |
| Inbox 持久化 | 需要（断电恢复） |

---

## 架构图

```
                              ┌─────────────────────────────────────┐
                              │              Scheduler               │
                              │   1. git pull 检测新提交             │
                              │   2. 拆解任务 → Inbox               │
                              │   3. 监控进度 → Reviewer             │
                              └──────────┬──────────────────────────┘
                                         │ 任务分发
                              ┌──────────▼──────────────────────────┐
                              │              Inbox                  │
                              │   📁 JSON 文件（持久化）             │
                              │   状态: pending / running / done    │
                              └──────────┬──────────────────────────┘
                                         │ 并行动态调度
                              ┌──────────▼──────────────────────────┐
                              │           Worker Pool               │
                              │  ┌─────┐  ┌─────┐  ┌─────┐  ...     │
                              │  │ W1  │  │ W2  │  │ W3  │          │
                              │  │ RUN │  │ RUN │  │ IDLE│          │
                              │  └─────┘  └─────┘  └─────┘          │
                              │   任务级生命周期，动态启停            │
                              └──────────┬──────────────────────────┘
                                         │ 结果写入
                              ┌──────────▼──────────────────────────┐
                              │            Reviewer                 │
                              │   汇总 Worker 结果，决策是否合并     │
                              └──────────┬──────────────────────────┘
                                         │ 报告输出
                              ┌──────────▼──────────────────────────┐
                              │            Reporter                  │
                              │   生成 auto-update.log 报告         │
                              └─────────────────────────────────────┘
```

---

## 模块设计

### 1. Inbox（`core/multi_agent/inbox.py`）

持久化任务队列，JSON 文件存储，支持断电恢复。

```python
class Inbox:
    path: Path  # .evolution/inbox.json
    tasks: list[Task]

    def enqueue(task: Task)      # 追加任务
    def mark_running(task_id)    # 状态变更 + 写盘
    def mark_done(task_id, result)
    def get_pending() -> list    # 供 Worker 拉取
    def checkpoint()             # 定期刷盘（断电恢复点）
```

### 2. Bus（`core/multi_agent/bus.py`）

事件驱动消息总线，基于 Python 内置 `queue.Event` 实现。

```python
class MessageBus:
    def publish(event: Event)
    def subscribe(event_type) -> AsyncIterator[Event]
```

### 3. Protocols（`core/multi_agent/protocols.py`）

```python
@dataclass
class Task:
    id: str
    type: Literal["analyze", "test", "refactor", "review"]
    payload: dict
    status: Literal["pending", "running", "done", "failed"]
    created_at: datetime

@dataclass
class Result:
    task_id: str
    worker_id: str
    output: dict
    error: str | None

@dataclass
class Event:
    type: str  # task.enqueued / worker.started / ...
    payload: dict
```

### 4. Agent 基类（`core/multi_agent/agent.py`）

```
BaseAgent
├── Scheduler  # 主循环：git pull → 拆解 → 入队
├── Worker     # 订阅 inbox，执行任务，回报结果
├── Reviewer  # 汇总结果，决策下一步
└── Reporter  # 生成报告，输出到 auto-update.log
```

---

## 改造后的 Agent 主循环

```
旧:
  IntentParser → TaskPlanner → ToolRouter → LLM → response

新:
  Scheduler → [Worker₁ ‖ Worker₂ ‖ Worker₃ ...] → Reviewer → Reporter
```

- Worker 生命周期：**任务级** — 每完成一个任务即销毁，不维持长期进程
- 并行度上限：**无限制，按 CPU 动态调整**
- 通信机制：**共享 Inbox（JSON 文件）**，避免引入消息队列复杂性

---

## 待办

- [ ] 实现 `core/multi_agent/inbox.py`
- [ ] 实现 `core/multi_agent/bus.py`
- [ ] 实现 `core/multi_agent/protocols.py`
- [ ] 实现 `core/multi_agent/agent.py`（Base + 四个派生类）
- [ ] 修改 `BeaverAgent.run()` 主循环支持多 Agent 协作
- [ ] 集成定时自更新任务（定时任务已有，定期触发 Scheduler）
- [ ] 测试并行 Worker 执行