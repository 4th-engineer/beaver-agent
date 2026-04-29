---
name: tdd
category: engineering
description: 测试驱动开发 — 红绿重构循环，确保每个功能可验证
trigger: 测试
when_to_use: |
  当需要实现一个新功能或修复一个 bug 时使用。
  遵循 Red-Green-Refactor 循环：先写一个失败的测试，
  然后写最少量代码让它通过，最后重构改进。
phases:
  - name: Red — 写一个失败的测试
    instruction: |
      先写一个会失败的测试，明确你要实现的功能的行为。
      不要写实现代码，只写测试。
    steps:
      - instruction: "描述期望的行为（Given-When-Then 格式）"
        check: "测试描述的是行为，不是实现细节"
      - instruction: "写出第一个输入和期望输出"
        check: "测试数据足够简单，能快速运行"
      - instruction: "运行测试，确认它失败"
        check: "失败信息清晰，能指出哪里不符合预期"
  - name: Green — 写最少量代码通过测试
    instruction: |
      现在写最少量、最简单的代码让测试通过。
      不要想着完美，先让它工作。
    steps:
      - instruction: "用最直接的方式实现功能"
        check: "代码能跑就行，不要过度设计"
      - instruction: "再次运行测试，确认全部通过"
        check: "所有测试都是绿色的"
  - name: Refactor — 重构改进
    instruction: |
      测试通过后，回头审视代码，识别可以改进的地方。
      每次重构后都要确保测试仍然通过。
    steps:
      - instruction: "识别重复代码，提取函数或模块"
        check: "没有明显的代码重复"
      - instruction: "检查命名是否清晰表达意图"
        check: "变量和函数名自解释，不需要注释"
      - instruction: "检查边界条件和错误处理"
        check: "有空输入、错误输入的测试覆盖"
checklist:
  - 每个新功能都有对应的测试
  - 测试描述的是行为，不是实现
  - 先写测试再写实现（Red → Green）
  - 每次重构后测试仍然通过
  - 测试覆盖正常路径和边界路径
examples:
  - 修复 bug → 先写一个能复现 bug 的测试，运行失败，然后修复
  - 新功能 → 先写测试描述期望行为，再实现让它通过
  - 重构 → 先确保有测试覆盖，然后边重构边运行测试
---
