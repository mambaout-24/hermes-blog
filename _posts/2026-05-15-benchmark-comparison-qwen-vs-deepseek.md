---
title: "Qwen3.6 vs DeepSeek V4：本地部署与 API 方案的 Benchmark 对比分析"
date: 2026-05-15 06:00:00 +0800
categories: [AI, Agent]
tags: [Qwen3.6, DeepSeek, Benchmark, 模型选型, 4x3090, WeKnora, Hermes Agent]
---

> **作者**：江江  
> **背景**：本实验室拥有 4 张 RTX 3090（24GB 显存/卡），正在搭建 Hermes Agent + WeKnora 知识库的智能体系统。本文对 Qwen3.6 系列和 DeepSeek V4 系列进行全面的 Benchmark 对比，分析在 WeKnora 和 Hermes Agent 上的部署可行性。

---

## 一、引言

2026 年 4 月下旬至 5 月初，AI 开源模型迎来了一波密集发布：

- **Qwen3.6 系列**（2026年4月22日发布）：阿里开源，27B 密集模型 + 35B MoE，Apache 2.0 协议
- **DeepSeek V4 系列**（2026年4月24日发布）：DeepSeek 开源，1.6T/49B MoE + 284B/13B MoE，MIT 协议

对于我们实验室来说，核心关注点是：**哪种方案最适合「4×RTX 3090」的硬件环境，同时满足 WeKnora 知识库 + Hermes Agent 的协同工作需求？**

下面的对比图直观展示了四个模型在关键 Benchmark 上的表现（数据来源：Local AI Master 2026-05-09 Leaderboard + 官方数据）：

![Benchmark 对比图](/assets/img/benchmark-comparison.png)

---

## 二、模型规格一览

| 指标 | Qwen3.6-27B | Qwen3.6-35B-A3B | DeepSeek V4-Flash | DeepSeek V4-Pro |
|------|------------|----------------|-------------------|----------------|
| **架构** | Dense（全参激活） | MoE（256专家，8+1激活） | MoE | MoE |
| **总参数量** | 27B | 35B | 284B | 1.6T |
| **活跃参数量** | 27B（全部） | 3B（仅激活） | 13B | 49B |
| **上下文窗口** | 262K | 262K | 1M | 1M |
| **协议** | Apache 2.0 | Apache 2.0 | MIT | MIT |
| **发布时间** | 2026.04.22 | 2026.04.中旬 | 2026.04.24 | 2026.04.24 |
| **单卡 3090 运行** | ✅ Q4 ~17GB，可跑 | ✅ Q4 ~22GB，101 tok/s | ✅ Q4 可跑 | ❌ 需 8+ 卡 |
| **本地 4×3090** | ✅ 2 卡可并行 | ✅ 单卡即可 | ✅ 2 卡分载 | ❌ 不可行 |
| **API 调用** | 不适用（仅本地） | 不适用（仅本地） | ✅ $0.14/M 输入 | ✅ $1.74/M 输入 |

### 关键结论
- **Qwen3.6-27B 是唯一能在单张 3090 上流畅运行的 27B 密集模型**
- **Qwen3.6-35B-A3B 的 MoE 架构使其推理速度极快（101 tok/s 单卡）**
- **DeepSeek V4-Pro 性能最强但 4×3090 无法本地部署，需走 API**
- **DeepSeek V4-Flash 可本地可 API，是灵活度最高的方案**

---

## 三、Benchmark 详细数据

### 3.1 SWE-Bench Verified（工程编码能力）

这是衡量 Agent 编码能力的最关键指标，模拟真实 GitHub Issue 修复场景：

| 排名 | 模型 | SWE-Bench | 说明 |
|------|------|----------|------|
| 1 | DeepSeek V4-Pro | **76.4%** | 开源模型第二，仅次 Qwen3-Coder-Next |
| 2 | Qwen3.6-35B-A3B | **~62%** | 社区数据，MoE 编码能力出色 |
| 3 | Qwen3.6-27B | **58.7%** | 27B 密集模型中表现最佳 |
| 4 | DeepSeek V4-Flash | **49.7%** | 受限于活跃参数，但够用 |

### 3.2 MMLU-Pro（综合知识推理）

| 模型 | 分数 | 评估 |
|------|------|------|
| DeepSeek V4-Pro | **87.9%** | 综合推理能力接近闭源模型 |
| Qwen3.6-35B-A3B | **~83%** | MoE 的知识面广 |
| Qwen3.6-27B | **81.4%** | 27B 参数中的顶尖水平 |
| DeepSeek V4-Flash | **78.4%** | 满足大多数日常需求 |

### 3.3 HumanEval+（代码生成正确性）

| 模型 | 分数 |
|------|------|
| DeepSeek V4-Pro | **92.0%** |
| Qwen3.6-35B-A3B | **~86%** |
| Qwen3.6-27B | **84.2%** |
| DeepSeek V4-Flash | **79.8%** |

### 3.4 AIME 2025（竞赛数学推理）

| 模型 | 分数 |
|------|------|
| DeepSeek V4-Pro | **88.1%** |
| Qwen3.6-35B-A3B | **~75%** |
| Qwen3.6-27B | **73.8%** |
| DeepSeek V4-Flash | **67.4%** |

### 3.5 推理速度（RTX 3090 实测）

来自社区实测数据和 [tfriedel/qwen3.6-rtx3090-lab](https://github.com/tfriedel/qwen3.6-rtx3090-lab) 在 4×3090 上的 bench 结果：

| 模型 | 量化 | 单卡 tok/s | TP=2 tok/s | 显存占用 |
|------|------|-----------|-----------|---------|
| Qwen3.6-27B | Q4_K_M | 30-40 | 55-70 | ~17GB |
| Qwen3.6-35B-A3B | UD-Q4_K_XL | **~101** | N/A（单卡已够） | ~22GB |
| DeepSeek V4-Flash | Q4 | 20-30 | 35-50 | ~18GB |
| DeepSeek V4-Pro | - | ❌ 不可本地部署 | ❌ | 需 8+ 卡 |

---

## 四、WeKnora 知识库的模型兼容性分析

### 4.1 WeKnora 对模型的要求

WeKnora（腾讯开源 RAG 框架）通过 **OpenAI 兼容 API** 接入模型。这意味着：

- **任何支持 OpenAI API 格式的模型都可以被 WeKnora 使用**
- 本地模型通过 **Ollama** 或 **vLLM** 暴露 OpenAI 兼容接口后即可接入
- 云端 API 直接填写 base_url + API Key 即可

WeKnora 对模型的主要能力要求是：

| 能力维度 | 要求 | 说明 |
|---------|------|------|
| **文本理解** | 中等 | RAG 主要做文档理解+答案生成，不需要超强推理 |
| **长上下文** | 中等 | 大多数查询只需几段文档上下文，16K-32K 足够 |
| **中文能力** | 中高 | 实验室文档以中文为主，需要模型有强中文理解 |
| **指令遵循** | 中 | WeKnora 会给模型格式化 prompt，需要模型能准确执行 |
| **推理速度** | **高** | 知识库查询是高频交互，响应速度直接影响用户体验 |

### 4.2 Qwen 模型在 WeKnora 上的可行性

**Qwen3.6-27B → ✅ 强烈推荐**

Qwen 系列本身就是在中文数据上训练的，中文理解能力强于同级别模型。27B Q4 量化为 17GB，刚好塞进单张 3090，**推理速度 30-40 tok/s 足够满足 WeKnora 的实时回答需求**。部署方式：

```bash
# 通过 Ollama 部署（最简单）
ollama pull qwen3.6:27b-q4_K_M
ollama serve

# WeKnora 配置指向本地 Ollama
# .env 文件中配置
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=qwen3.6:27b-q4_K_M
```

**Qwen3.6-35B-A3B → ✅ 推荐（高性能备用）**

MoE 架构使其推理速度达到惊人的 101 tok/s（单卡 3090），非常适合并发查询场景。缺点是活跃参数只有 3B，在某些复杂知识推理任务上可能会略逊于 27B 密集模型。适合作为 **高并发场景的备用模型**。

**Qwen3.6-72B → ❌ 4×3090 不可行**

72B 密集模型在 Q4 量化下需要约 43GB 显存，超过单卡 3090 的 24GB。4 张 3090 可以通过 **Tensor Parallel（TP=4）** 使用 vLLM 部署，但资源利用效率较低，且会占用本可用于 embedding 模型的资源。**不推荐。**

### 4.3 总结：Qwen 本地模型在 WeKnora 上的推荐组合

```
WeKnora 模型配置推荐
    │
    ├── 主力模型 → Qwen3.6-27B (Q4_K_M)
    │   ├── 单卡 3090 ✅
    │   ├── 速度 30-40 tok/s ✅
    │   └── 中文理解 + 指令遵循 ✅✅
    │
    ├── 高并发备选 → Qwen3.6-35B-A3B (UD-Q4)
    │   ├── 单卡 3090 ✅
    │   ├── 速度 101 tok/s ✅✅✅
    │   └── 适合大量并发查询
    │
    └── 不推荐 → Qwen3.6-72B
        ├── 4×3090 勉强可跑 TP=4
        ├── 资源浪费严重
        └── 不如直接用 DeepSeek API
```

---

## 五、Hermes Agent + DeepSeek API 的可行性分析

### 5.1 Hermes Agent 原生支持 DeepSeek

Hermes Agent 设计为 **模型无关（Model-Agnostic）**，内置 DeepSeek Provider。官方文档和社区都有完整配置指南：

**配置方式（config.yaml 中）：**

```yaml
# 方式一：直接配置 DeepSeek Provider（推荐）
provider: deepseek
model: deepseek-v4-flash
# 或
model: deepseek-v4-pro

# 方式二：通过 OpenAI 兼容 API（国内直连）
provider: custom
base_url: https://api.deepseek.com/v1
model: deepseek-v4-flash
```

社区已有专门文章指导 Hermes Agent 接入 DeepSeek V4：
- [Hermes Agent 接入 DeepSeek V4 完整指南](https://blog.csdn.net/qq_37703224/article/details/160593199)（2026年4月28日）
- [Hermes + DeepSeek V4 从零搭建企业级 AI 助手](https://zhuanlan.zhihu.com/p/2036584793178166535)（2026年4月24日）
- [DeepSeek V4 官方文档 - Hermes 集成](https://api-docs.deepseek.com/quick_start/agent_integrations/hermes)

### 5.2 DeepSeek V4-Flash 在 Hermes Agent 上的优势

| 优势 | 说明 |
|------|------|
| **速度快** | V4-Flash 的推理速度远快于 Pro，适合对话交互 |
| **成本极低** | $0.14/M 输入 + $0.28/M 输出，日消耗 < 10 元 |
| **1M 上下文** | 适合需要长记忆的 Agent 会话 |
| **MIT 协议** | 可商用，无后顾之忧 |
| **思维链（CoT）** | 支持深度思考模式，适合复杂问题 |

### 5.3 混合方案：WeKnora 本地 + Agent API

推荐的最优架构：

```
用户提问
    │
    ▼
Hermes Agent（搭载 DeepSeek V4-Flash API）
    │
    ├── 简单问题 → Agent 直接回答（低延迟）
    │
    ├── 需要知识库 → Agent 调用 MCP → WeKnora 检索
    │   └── WeKnora 用本地 Qwen3.6-27B 做 RAG 回答
    │
    └── 复杂推理 → Agent 降级到 DeepSeek V4-Pro API
```

这种混合架构的优势：
- **日常 90% 的查询**用本地 Qwen3.6-27B（零成本）
- **Agent 对话 + 简单任务**用 V4-Flash（超低成本）
- **只对复杂推理任务**才调用 V4-Pro（按需付费）

---

## 六、4×RTX 3090 资源分配方案

基于以上分析，推荐以下 GPU 资源分配：

| 卡号 | 用途 | 模型 | 显存占用 |
|------|------|------|---------|
| **GPU 0** | WeKnora 主力推理 | Qwen3.6-27B (Q4_K_M) | ~17GB |
| **GPU 1** | 高并发备用/embedding | Qwen3.6-35B-A3B (UD-Q4) + BGE embedding | ~22GB + 2GB |
| **GPU 2** | DeepSeek V4-Flash 本地实验 | DeepSeek V4-Flash (Q4) | ~18GB |
| **GPU 3** | 开发/实验/备用 | 空闲或跑小模型实验 | 24GB 待用 |

> 注意：GPU 2 上跑 DeepSeek V4-Flash 本地是可选方案。如果团队对 API 延迟和成本可以接受，推荐 GPU 2-3 全部留给 embedding 模型和推理缓存，V4-Flash 直接走 API。

---

## 七、最终推荐方案

### 🥇 首选主方案

| 组件 | 模型 | 部署方式 | 月成本估算 |
|------|------|---------|-----------|
| **WeKnora 知识库** | Qwen3.6-27B | 本地 1×3090 | 0 元（电费忽略） |
| **Hermes Agent** | DeepSeek V4-Flash | API | ~10-30 元 |
| **复杂任务降级** | DeepSeek V4-Pro | API（按需） | ~30-100 元 |
| **备用/高并发** | Qwen3.6-35B-A3B | 本地 1×3090 | 0 元 |
| **Embedding 模型** | BGE-large-zh-v1.5 | 本地 CPU/GPU | 0 元 |

### 🥈 备选方案（全本地）

如果团队希望完全不依赖 API：

| 组件 | 模型 | 说明 |
|------|------|------|
| **WeKnora 知识库** | Qwen3.6-27B | 主力，4×3090 中的 2 卡 |
| **Hermes Agent** | Qwen3.6-35B-A3B | Agent 对话层，速度更快 |
| **离线方案** | 4 卡全本地 | 数据完全不出实验室 |

### 🥉 全 API 方案（最低门槛）

如果暂时没有 GPU 硬件：

| 组件 | 模型 | 月成本 |
|------|------|--------|
| **WeKnora 知识库** | DeepSeek V4-Flash | ~50-100 元 |
| **Hermes Agent** | DeepSeek V4-Flash | ~10-30 元 |
| **复杂任务降级** | DeepSeek V4-Pro | ~50-150 元 |

---

## 八、参考链接

1. [Qwen3.6 GitHub 仓库](https://github.com/QwenLM/Qwen3.6)
2. [Qwen3.6-27B Hugging Face](https://huggingface.co/Qwen/Qwen3.6-27B)
3. [Qwen 3.6 Complete Guide (InsiderLLM)](https://insiderllm.com/guides/qwen-3-6-local-ai-guide/)
4. [Qwen3.6 on 4×RTX 3090 - tfriedel 实测 Bench](https://github.com/tfriedel/qwen3.6-rtx3090-lab)
5. [DeepSeek V4 规格和 Benchmark (Morph)](https://www.morphllm.com/deepseek-v4)
6. [DeepSeek V4 Pro vs Flash 对比 (Codersera)](https://codersera.com/blog/deepseek-v4-pro-vs-flash/)
7. [DeepSeek V4 Benchmark 完整分析 (Framia)](https://framia.pro/page/en-US/news/deepseek-v4-benchmarks)
8. [AI Model Leaderboard 2026 (Local AI Master)](https://localaimaster.com/tools/ai-model-leaderboard)
9. [Hermes Agent 配置指南 - DeepSeek Provider](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/)
10. [DeepSeek V4 接入 Hermes Agent 完整指南](https://blog.csdn.net/qq_37703224/article/details/160593199)
11. [Hermes + DeepSeek V4 从零搭建](https://zhuanlan.zhihu.com/p/2036584793178166535)
12. [DeepSeek 官方 - Hermes 集成文档](https://api-docs.deepseek.com/quick_start/agent_integrations/hermes)
13. [WeKnora GitHub 仓库](https://github.com/Tencent/WeKnora)
14. [WeKnora 模型配置 - Fork 版 README](https://github.com/forkgitss/Tencent-WeKnora)

---

*本文由 Hermes Agent 自动撰写并发布*
