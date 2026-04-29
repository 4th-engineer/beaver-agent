---
name: vertical-slice
category: engineering
description: 垂直切片开发 — 从端到端实现一个完整的小功能，而不是横向铺开
trigger: 切片
when_to_use: |
  当需要构建一个较大功能时使用。不要一次性写完所有层
  （先写完 schema、再写 API、再写 UI），
  而是要按功能垂直切片：每一片都包含从 schema 到 UI 的完整链路。
phases:
  - name: 选择切片
    instruction: |
      从需求中识别可以独立交付的最小功能切片。
      一个好的切片是：用户能感知到它有用。
    steps:
      - instruction: "识别最小可用的功能子集"
        check: "这个切片完成了，用户能用来做什么？"
      - instruction: "确保切片不依赖未完成的功能"
        check: "切片之间没有循环依赖"
  - name: 实现端到端
    instruction: |
      这一次只实现选中的切片，完整地实现：
      Schema → API → Tests → UI（如果涉及）。
    steps:
      - instruction: "定义数据结构（schema/model）"
        check: "数据结构满足这个切片的需求"
      - instruction: "实现 API 端点（CRUD + 业务逻辑）"
        check: "API 端点可用，输入输出清晰"
      - instruction: "为这一层写测试"
        check: "测试覆盖正常路径"
      - instruction: "如果涉及 UI，实现这一片的界面"
        check: "界面可交互，数据流正确"
  - name: 验证切片
    instruction: |
      这一片完成了，验证它可以独立工作。
    steps:
      - instruction: "运行所有测试，确认通过"
        check: "端到端测试通过"
      - instruction: "手动验证功能符合预期"
        check: "用户体验符合原始需求"
checklist:
  - 每个切片都是端到端可用的
  - 切片之间无循环依赖
  - 每个切片完成后都能验证
  - 不在一个切片内混合多个功能
examples:
  - "做一个电商系统" → 先做一个"用户注册"切片（schema + API + DB + 邮件验证）
  - "做一个博客" → 先做一个"发表文章"切片，而不是先建完所有表
---
