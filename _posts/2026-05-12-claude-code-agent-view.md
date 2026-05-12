---
title: "Anthropic 发布 Claude Code Agent View：AI 编码进入多 Agent 并行时代"
date: 2026-05-12 12:00:00 +0800
categories: ["AI", "学习笔记"]
tags: ["Anthropic", "Claude Code", "AI Agent", "多Agent", "开发者工具"]
---

2026 年 5 月 11 日，Anthropic 正式为 Claude Code 推出 **Agent View** 功能（Research Preview），在 CLI 终端中提供了一个统一仪表盘，让开发者能够同时启动、监控、交互和管理多个并行的 AI 编码 Agent 会话。这标志着 AI 编码工具从"单 Agent 单任务"模式正式迈入"多 Agent 并行协作"时代。

![Claude Code Agent View 仪表盘截图 - 官方展示](https://cdn.prod.website-files.com/68a44d4040f98a4adf2207b6/6a02147d18cd3a9a9fe18c4f_aef149a9.png)

## Agent View 是什么？为什么重要？

过去，开发者在 Claude Code 中运行多个并行 Agent 时，需要手动管理多个终端标签页，借助 tmux 等工具进行屏幕分割，还要在脑中维护一份"待办清单"来追踪每个 Agent 的进度。这种体验随着 Agent 数量的增加迅速变得不可持续。

Agent View 正是为解决这个痛点而生的。它将所有 Claude Code 会话（Session）集中在一个 CLI 表格中展示，每个条目清晰地标明：

- **状态**：运行中（Running）、等待用户输入（Waiting）、暂停（Paused）或已完成（Completed）
- **最近交互内容**：最后一条对话摘要
- **下次触发时间**：对于 PR 监控、仪表盘更新等长期任务，直接显示下次执行时间
- **是否需要开发者介入**：一目了然地识别出哪些 Agent 在等待你的决策

这实际上是把开发者大脑中"哪个 Agent 该处理了""哪个 PR 已经产生了"这类心智负担，搬到了 UI 上。状态指示器配合 Peek 预览界面，让开发者可以快速扫过所有会话的进度，极大地降低了上下文切换成本。

## 如何使用 Agent View

Agent View 的入口非常直觉，提供多种激活方式：

```bash
# 方式一：从终端直接打开
claude agents

# 方式二：在任意活跃会话中按左方向键（←）切入
# 按右方向键（→）返回原来的会话

# 方式三：直接从 Shell 启动后台会话
claude --bg "your task description"

# 方式四：在已有会话中将其发送到后台
# 输入 /bg 命令
```

### 快捷键导航

Agent View 提供了完整的键盘操作支持：

| 快捷键 | 功能 |
|--------|------|
| Tab | 切换焦点区域 |
| 方向键 ↑/↓ | 选择会话 |
| Enter | 附加（Attach）到所选会话，查看完整对话记录 |
| Esc | 退出 Agent View，会话继续在后台运行 |

当某个会话正在等待开发者决策时，用户可以直接在 Agent View 中**内联回复**（Inline Reply），该会话随即自动继续执行，无需真正"进入"该会话。这种设计将交互摩擦降到了最低。

## 后台化与 /goal 自主执行

Agent View 的核心设计理念之一是"将 Agent 视为可后台化的工作者"。通过 `/bg` 命令或 `claude --bg` 启动方式，开发者可以：

- **批量派发**：把多个想法分头丢给不同的 Agent，每个 Agent 可搭配对应的 Skill（技能），最终回到清单审视一批可供 Review 的 Pull Request
- **监控长期任务**：PR 守望者、仪表盘更新等长时间运行的任务，直接显示下次触发时间
- **跨会话穿梭**：在某个会话中按左方向键跳出，处理另一个相关问题或快速查询代码，再用右方向键回到原工作

此外，支持 `/goal` 命令的会话可以让 Agent 自主规划并执行目标，进一步减少了人工干预的需求。

## 可用性与配置

Agent View 即日起以 Research Preview 形式提供，无需额外注册即可使用：

- **支持方案**：Pro、Max、Team、Enterprise 以及 Claude API 用户
- **版本要求**：Claude Code v2.1.139+
- **常规速率限制照常适用**

对于 Team 和 Enterprise 的组织管理员，可以通过配置 `disableAgentView` 设置来关闭此功能，以满足企业内部的安全与合规要求。

## 从 Code with Claude 2026 看 Anthropic 的 Agent 战略

Agent View 的发布紧随 Anthropic 在 5 月 6 日举办的 **Code with Claude 2026** 开发者大会。在那场横跨旧金山、伦敦和东京的活动中，Anthropic 没有发布新模型，而是集中发布了五项 Agent 能力：

1. **Dreaming（梦境）**：Agent 能够在空闲时自动回顾过往会话，自我改进，生成新的 Memory Store
2. **Outcomes（结果导向）**：以结果为导向的 Agent 评估体系
3. **Multi-Agent Orchestration**：多 Agent 编排能力——Agent View 正是这一能力的 CLI 前端体现
4. **Claude Finance**：面向金融行业的 10 个预构建 Agent 模板
5. **Add-ins（插件系统）**：可扩展的插件生态

Agent View 的推出，将多 Agent 编排能力从后台 API 扩展到了开发者日常使用的终端界面。它代表了一个更深层的趋势：当 AI Agent 不再是单次对话的工具，而是成为可以并行工作的协作伙伴时，**开发者工具界面必须随之进化**。

## 结语

Claude Code Agent View 是 AI 编码工具界面范式转变的一个重要信号。"并行 Agent" 不再是 API 层面才有的高级能力——现在每个开发者都可以在终端中轻松编排多个 AI 编码助手，像管理一个微型开发团队一样管理它们。

对于日常处理复杂编码任务的开发者来说，Agent View 意味着更少的心智负担、更流畅的上下文切换，以及更高的生产力。而这，可能只是 Anthropic 多 Agent 战略的开端。

---

## 参考链接

1. [Agent view in Claude Code - Anthropic 官方博客](https://claude.com/blog/agent-view-in-claude-code)
2. [Anthropic adds Agent View to Claude Code CLI interface - Testing Catalog](https://www.testingcatalog.com/anthropic-adds-agent-view-for-claude-code-for-parralel-work/)
3. [Claude Code推出Agent View！一個畫面掌控所有AI編碼任務 - 數位時代](https://www.bnext.com.tw/article/90906/anthropic-claude-code-agent-view-multi-session-management)
4. [Code with Claude 2026: 5 New Agent Features - MindStudio](https://www.mindstudio.ai/blog/code-with-claude-2026-new-agent-features)
