---
name: refactor
category: engineering
description: 渐进式重构 — 不破坏功能的前提下持续改进代码质量
trigger: 重构
when_to_use: |
  当用户要求改进现有代码、或者你觉得代码有优化空间时使用。
  重构的原则是：不改变行为，只改进结构。每次改动后都运行测试确认。
phases:
  - name: 分析现状
    instruction: |
      在动手之前，先理解当前代码的问题所在。
      识别需要重构的具体位置和原因。
    steps:
      - instruction: "阅读代码，理解当前实现"
        check: "你能用一句话描述这段代码在做什么吗？"
      - instruction: "识别问题：重复代码、过长函数、命名不清、耦合度高"
        check: "列出具体的问题点，不要模糊描述"
      - instruction: "评估风险：这个重构的收益和风险比"
        check: "这个改动会影响多少地方？"
  - name: 制定计划
    instruction: |
      重构要小步进行。每次只做一个改动，然后测试。
    steps:
      - instruction: "确定重构顺序（先高频、风险低的）"
        check: "按影响面和风险排序"
      - instruction: "确认有测试覆盖这一块"
        check: "没有测试的地方先加测试"
      - instruction: "规划每个小步骤（每步都应该能独立测试）"
        check: "每步不超过 20 行代码改动"
  - name: 执行重构
    instruction: |
      按计划执行重构，每步后运行测试。
    steps:
      - instruction: "做一个小改动（提取函数、重命名、改结构）"
        check: "运行测试确认行为没变"
      - instruction: "重复直到完成所有计划的重构点"
        check: "每步都通过测试"
      - instruction: "最后做一次全面测试和代码审查"
        check: "所有测试通过，代码质量提升"
checklist:
  - 有测试覆盖被重构的代码
  - 重构不改变程序行为
  - 每次改动都很小且可测试
  - 重构后代码更易读、更易维护
  - 无引入新的重复代码或耦合
examples:
  - "这段代码太长了" → 拆成多个小函数，每函数不超过 20 行
  - "这个命名不清楚" → 重命名为自解释的名字，全局替换
  - "有两个函数逻辑重复" → 提取公共函数，替换重复调用
---
