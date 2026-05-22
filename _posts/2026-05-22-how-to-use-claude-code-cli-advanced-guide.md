---
title: 如何「优雅地」使用 Claude Code CLI——非小白写给非小白的深度指南
date: 2026-05-22 10:00:00 +0800
categories: [AI, 开发工具]
tags: [Claude Code, AI Agent, CLI, 最佳实践, 工作流, 开发效率]
---

## 前言

写下这篇文章的契机，来自一个很朴素的困惑：网上铺天盖地的 Claude Code 教程，大多数停留在「安装、配置、写个 hello world」的阶段。但如果你已经会用了——你知道怎么装它、能跑起来、也看过官方文档——你想要的是什么呢？是那些真正让效率起飞、让开发体验丝滑的**进阶技巧**。

这文章不是教程，是一份实战踩坑记录。内容来自过去几个月社区里最优质的中英文资料梳理（附参考链接），加上一些我自己的理解。目标是：**让一个已经会用 Claude Code 的开发者，看完后能立刻改进自己的工作流。**

---

## 第一部分：核心认知——Claude Code 是怎么工作的

很多人在第 100 次对话后仍然把 Claude Code 当「超级 ChatGPT + 终端」用。这个理解在带宽够用的时候没问题，但一旦进入复杂项目，瓶颈立刻暴露。

理解 Claude Code 的本质很重要：它是一个 **agentic while 循环**。大致流程是：

1. 接收你的输入
2. 调用 LLM 生成回复
3. 如果回复中要求调用工具（Bash、文件编辑、搜索等），执行工具并拿到结果
4. 把工具结果送回 LLM
5. 重复步骤 2-4，直到任务完成

这套循环的瓶颈只有一个：**上下文窗口是你最珍贵的资源**。

**对应原则**：每轮对话保持原子化。不是「帮我重构这个模块然后写测试然后部署」，而是「帮我写重构计划」→「好，执行重构」→「现在加测例」→「部署」。这不只是 best practice，而是如果你不这么做，Claude 会在第 10 轮对话后忘记第 3 行的变量名。

Habr 上有一篇很透彻的文章（Daniil Okhlopkov，TON Foundation 的 Analytics Lead）总结了这个模式为三步：

1. **讨论idea**：让 Claude 读当前项目文件，问问题，你纠偏
2. **写执行计划**：在 Plan Mode 里写下详细步骤（`Shift+Tab` 进入 Plan Mode）
3. **执行 + 测试**：开新对话，按计划执行

这个流的核心就是**把规划和执行解耦**。很多人的失败在于试图在一个 prompt 里同时完成构思和落地。

---

## 第二部分：CLAUDE.md——你的第二个大脑

CLAUDE.md 是 Claude Code 的「项目记忆」。放在项目根目录下，每次开新会话自动加载。但很多人对它的理解只停留在「放点项目说明」，这是巨大的浪费。

### 深度用法

**1. 放「验证自己的方法」**

Claude Code 的创始人在多个场合提到过最重要的一条技巧：**永远给 Claude 一种验证自己工作的方法**。

```markdown
## 验证指南
- 每次修改后，运行 `npm run test` 确认已有测试通过
- 添加新功能后，在 `tests/` 加对应的单元测试
- 修改 API 后，运行 `npm run api-test` 验证
```

这条看似简单，但实践中效果极好——Claude 拿到任务后，会自动走「改代码→跑测试→修复→再跑」的循环，不需要你来回发消息。

**2. 放「禁止清单」**

Claude Code 没有安全感，给它明确的边界能大幅减少事故：

```markdown
## 安全规范
## 禁止事项
- ❌ 在代码中硬编码密钥
- ❌ 在 CLAUDE.md 中记录密码
- ❌ 修改 `config/production.yaml`（除非明确要求）
## 推荐做法
- ✅ 使用环境变量
- ✅ 优先使用 typescript 而非 any
- ✅ 所有公共函数必须写 JSDoc
```

**3. 放「当前工作上下文」**

CLAUDE.md 不止是静态的，你可以在做复杂 task 时手动更新它来当「工作记忆」：

```markdown
## 当前工作
- 我们在重构 auth 模块（2026-05-20）
- 已完成：userService.ts 提取，tokenMiddleware 重写
- 进行中：sessionManager.ts 的测试覆盖
- 下一步：ProfileController 的依赖注入改造
- 关键决策：使用 zod 做请求校验，不在 controller 层写手动校验
```

这比让 Claude 在对话里回顾「我们刚才做了什么」高效得多。

---

## 第三部分：Hooks——被低估的自动化利器

Claude Code 的 hooks 系统是一个**事件驱动的 pipeline**。支持三个生命周期的钩子：

- `PostToolUse`：工具执行后触发
- `PreToolUse`：工具执行前触发
- `AfterCompletion`：整轮对话结束后触发

配置在 `~/.claude/settings.json` 或项目根目录的 `.claude/settings.local.json` 中。

### 实战场景

**自动格式化（PostToolUse）：**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write \"$CLAUDE_FILE_PATH\" 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

每次 Claude 改完代码，自动跑 prettier。不在 hook 清单里的文件不碰，开销几乎为零。

**危险命令拦截（PreToolUse）：**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"$TOOL_INPUT\" | grep -qE 'rm -rf|drop table|truncate'; then echo 'BLOCKED' >&2; exit 2; fi"
          }
        ]
      }
    ]
  }
}
```

不过这属于强制约束。更优雅的方式是只给 `/permissions allow-list` 指定许可命令，而不是事后拦截。

**错误自动检测（PostToolUse）：**

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write|Bash",
      "hooks": [
        {
          "type": "command",
          "command": "if echo \"$TOOL_RESULT\" | grep -qE 'Error|Failed|Exception|Traceback'; then echo '⚠️ 检测到错误，建议验证'; fi"
        }
      ]
    }
  ]
}
```

---

## 第四部分：Skills 系统——把你的工作流变成可复用的「咒语」

Skills 是 Claude Code 2.0 引入的最重要的特性。它把 slash commands、CLAUDE.md 的一部分职责、以及可复用 prompt 三者合一了。

### 理解 Skills 和 CLAUDE.md 的区别

| 维度 | CLAUDE.md | Skills |
|------|-----------|--------|
| 加载时机 | 每次对话自动加载 | 通过 `/skill` 或匹配触发 |
| 作用域 | 项目全局 | 按需加载/触发 |
| 主要用途 | 项目常量、安全规范、通用指导 | 可复用工作流、模板 prompt |
| 更新频率 | 稳定（项目结构变化时更新） | 高频（发现新 pattern 就加） |

### 实用的技巧

**自定义状态栏**：社区有一个很实用的脚本 [context-bar.sh](https://github.com/ykdojo/claude-code-tips/blob/main/scripts/context-bar.sh)，能在底部状态栏显示模型名称、当前目录、git 分支、未提交文件数、token 使用量的可视化进度条。10 种颜色主题可选。

**快速设置脚本**：创建一个 `setup.sh`，把你常用的 alias、hooks、skills 一键部署：

```bash
#!/bin/bash
# 添加 alias
echo "alias cc='claude'" >> ~/.zshrc
echo "alias cc-plan='claude --plan'" >> ~/.zshrc
# 初始化 settings.json
mkdir -p ~/.claude
cat > ~/.claude/settings.json << 'EOF'
{
  "attribution": { "commit": "", "pr": "" },
  "hooks": { ... }
}
EOF
```

---

## 第五部分：MCP——Claude Code 的「万能插座」

MCP（Model Context Protocol）是 Claude Code 连接外部世界的标准接口。官方支持 `/mcp` 命令管理 MCP 服务器。

### 值得一试的 MCP 场景

- **浏览器自动化 MCP**：让 Claude Code 操作浏览器做集成测试、截图验证 UI
- **Telegram MCP**：让 Agent 直接发消息到 TG 频道
- **Ollama Herd 路由**：如果你有自建模型，通过 MCP 把 Ollama 暴露给 Claude Code，实现本地私密推理

### 权限管理

Claude Code 的权限模型有三个层级：

- `/permissions allow`：逐条批准（默认）
- `/permissions auto`：自动批准（效率最高，适合可信项目）
- `/permissions allow-list`：只允许指定命令列表（平衡方案）

小技巧：对 PR 创建这类高风险操作，设置 `auto-mode: planner` 让 Claude 先写计划你再确认，而不是直接执行。

---

## 第六部分：那些让日常使用丝滑的小细节

### 1. 上下文管理

- **新话题开新对话**：Claude Code 在每次新对话中表现最好。随着对话变长，性能下降。定期 `Ctrl+A` → `/clear` 重置。这在 Claude Code 创始人的多次分享中被反复强调
- **搜索历史**：Claude Code 默认保存历史对话，用关键词可以搜索
- **克隆对话**：`/clone` 命令可以复制当前对话，在不丢失上下文的情况下做分支探索

### 2. Git 工作流

- 让 Claude Code 处理 Git 操作（提交、分支、推送），但**只允许自动拉取不允许自动推送**
- 多用草稿 PR：Claude 创建 Draft PR，你审查后再标记 ready
- 禁用署名：`~/.claude/settings.json` 中设置 `"attribution": {"commit": "", "pr": ""}`

### 3. 实用斜杠命令

| 命令 | 用途 |
|------|------|
| `/usage` | 查看速率限制和 token 用量 |
| `/chrome` | 切换浏览器集成 |
| `/stats` | GitHub 风格的活动统计图 |
| `/mcp` | 管理 MCP 服务器 |
| `/clear` | 重置对话 |
| `/clone` | 克隆当前对话 |
| `/permissions` | 调整权限模式 |

### 4. 验证你的工作

Claude Code 的创始人在采访中反复提到核心原则：**永远有一种方法来验证工作**。不只是「写测试」，而是确保每次修改后，Claude 自己能跑一个命令来确认改对了。把这个验证命令写进 CLAUDE.md，它就会自动用上。

### 5. 指数退避检查长时间任务

对于 Docker 构建、CI 运行等长时间任务，让 Claude Code 以递增间隔检查状态：

```
// 让 Claude 每隔 30 秒检查一次构建状态，完成后通知我
// 第一次等 30 秒，第二次等 1 分钟，第三次等 2 分钟...
```

这样你不会被中途的更新刷屏，Claude 也不会浪费上下文在无用的状态轮询上。

---

## 第七部分：配置文件的优先级（踩坑预警）

Claude Code 的加载顺序决定了谁覆盖谁，这个顺序让你可以精细控制不同层级的配置：

1. `~/.claude/settings.json`（全局默认）
2. `~/.claude/projects/<项目目录哈希>/settings.json`（项目级覆盖）
3. `./.claude/settings.local.json`（团队级，应被 .gitignore）
4. 项目根目录的 CLAUDE.md
5. 斜杠命令（运行时覆盖）

常见坑：`attribution` 配置如果在 `~/.claude/settings.json` 中设置了空字符串，但在 project 级 settings 中保留了默认值，AI 仍然会加署名。**检查顺序，确保低优先级的配置没有被高优先级覆盖。**

---

## 结语

Claude Code CLI 是一款工具，但用好它需要改变你的工作流思维。核心就三句话：

1. **把上下文当最宝贵的资源**——每轮对话聚焦一件事，规划和执行分离
2. **把配置当成代码来维护**——CLAUDE.md、Hooks、Skills、MCP 都是可组合的积木
3. **永远给 Claude 一条验证自己工作的路径**——这是让你从「写 prompt」进化到「管理 Agent」的关键一步

如果你还有自己的独门技巧，欢迎交流。工具在进步，工作流也在演进，没有「终极配置」，只有「当下最适合你的配置」。

---

## 参考链接

1. [Cranot/claude-code-guide - GitHub](https://github.com/Cranot/claude-code-guide) — 每两天自动更新的 Claude Code 完整指南
2. [50个 Claude Code 日常使用技巧与最佳实践 - 阿里云开发者社区](https://developer.aliyun.com/article/1728645)
3. [Claude Code в 2026: гайд для тех, кто еще пишет код руками - Habr](https://habr.com/ru/articles/987382/) （Daniil Okhlopkov，TON Foundation）
4. [45 个 Claude Code 技巧：从入门到精通 - Michael.Pan](https://www.michaelapp.com/posts/2026/2026-02-28-45-%E4%B8%AA-Claude-Code-%E6%8A%80%E5%B7%A7%E4%BB%8E%E5%85%A5%E9%97%A8%E5%88%B0%E7%B2%BE%E9%80%9A/)
5. [Claude Code 最佳实践 - 官方中文文档](https://code.claude.com/docs/zh-CN/best-practices)
6. [Claude Code 进阶指南：用 Everything Claude Code 打造最强 AI 编程助手 - CSDN](https://blog.csdn.net/Little_Carter/article/details/158037936)
7. [Claude Code 完全指南：使用方式、技巧与最佳实践 - 博客园/knqiufan](https://www.cnblogs.com/knqiufan/p/19449849)
8. [context-bar.sh - 自定义状态栏脚本](https://github.com/ykdojo/claude-code-tips/blob/main/scripts/context-bar.sh)
9. [Everything Claude Code - Anthropic Hackathon 冠军项目](https://github.com/ameeraws/Everything-Claude-Code)
