---
title: "实验室智能体系统落地部署指南：2×RTX 2080Ti + Docker Hermes + WeKnora"
date: 2026-05-15 10:00:00 +0800
categories: [AI, Agent]
tags: [部署, 2080Ti, Hermes Agent, WeKnora, Qwen3.6, Docker, 落地实践]
---

> **作者**：江江  
> **背景**：实验室服务器配置为 2×RTX 2080Ti（11GB 显存/卡）、32核CPU、128GB RAM、Ubuntu 22.04。本文提供完整的落地部署方案，覆盖各组件安装配置、资源分配策略、性能预期与运维要点。

---

## 一、整体部署架构

```
┌─────────────────────────────────────┐
│           实验室服务器               │
│   (2×RTX 2080Ti / 32核 / 128GB)    │
│                                     │
│  ┌─────────┐  ┌──────────────────┐  │
│  │ Docker  │  │ WeKnora (裸机)   │  │
│  │ ─────── │  │ ──────────────── │  │
│  │ Hermes  │  │ llama.cpp/vLLM   │  │
│  │ Agent   │  │ Qwen3.6-27B Q4   │  │
│  │ DeepSeek│  │ ← 2×2080Ti 推理 →│  │
│  │ V4 API  │  │ BGE Embedding    │  │
│  └────┬────┘  └────────┬─────────┘  │
│       │                │            │
│       └── MCP 协议 ────┘            │
└─────────────────────────────────────┘
```

### 组件部署方式一览

| 组件 | 部署方式 | 理由 |
|------|---------|------|
| **Hermes Agent** | Docker 容器 | 官方推荐，持久化卷挂载，方便迁移与版本管理 |
| **WeKnora 知识库** | 裸机直接部署 | 需要直接访问 GPU，Docker GPU 透传复杂 |
| **Qwen3.6-27B 推理** | 裸机 llama.cpp/vLLM | 直接挂载 GPU，性能损失最小 |
| **DeepSeek V4 API** | 远程调用 | 无需 GPU，即开即用 |
| **BGE Embedding** | 裸机或 CPU 推理 | 对 GPU 要求低，CPU 亦可 |

---

## 二、核心问题：2×RTX 2080Ti 能否跑 Qwen3.6-27B？

### 2.1 显存预算分析

RTX 2080Ti 的关键参数：

| 参数 | 值 |
|------|-----|
| **显存** | 11GB GDDR6（单卡） |
| **双卡合计** | 22GB |
| **CUDA 核心** | 4352/卡 |
| **Tensor Core** | 544/卡（一代，不支持 FP8） |
| **NVLink** | ✅ 支持（50GB/s 双向） |
| **PCIe** | 3.0 x16 |

**⚠️ 2080Ti 不支持 FP8！** 这很关键，因为：
- vLLM 的 NVFP4 量化只在 Ada Lovelace（RTX 40xx）及以上架构支持
- 2080Ti 是 Turing 架构，只支持 FP16/INT8/INT4
- 因此 **vLLM 的高吞吐优化对 2080Ti 效果有限**
- **推荐使用 llama.cpp GGUF 量化**

### 2.2 Qwen3.6-27B 在 2×2080Ti 上的可行性

参考社区实测数据（有人用 2×RTX 5060 Ti 16GB 成功部署）：

| 量化等级 | 模型大小 | 是否放入 2×11GB=22GB | 性能预期 |
|---------|---------|-------------------|---------|
| **Q4_K_M** | ~17GB | ✅ 可放，剩 5GB 给 KV cache | 推荐首选 |
| Q5_K_M | ~19GB | ✅ 略紧张 | 质量略好，上下文受限 |
| Q3_K_L | ~14GB | ✅ 充足 | 质量有损 |
| Q2_K | ~11GB | ✅ 单卡即可 | 质量严重下降，不推荐 |

**结论：Qwen3.6-27B Q4_K_M（~17GB）可以放入 2×2080Ti 的合计 22GB 显存中**，并通过 `split-mode=layer` 让 llama.cpp 将模型层均匀分配到两张卡。

### 2.3 上下文窗口预期

参考同等级硬件（2×RTX 5060 Ti 16GB）的实测数据：

| 推理引擎 | 最大上下文窗口 | 吞吐量 |
|---------|--------------|--------|
| **llama.cpp + split-mode=layer** | **~32K tokens**（TurboQuant 加持可达 43K） | 8-12 tok/s |
| vLLM + TP=2 | ~16K tokens | 仅在 Ada 架构有优势 |
| llama.cpp + CPU offload | 可达 128K+ | 速度大幅下降 |

**推荐配置**：使用 **llama.cpp**（`split-mode=layer`）+ **Q4_K_M 量化**，上下文窗口设置为 **16K-32K**（根据 WeKnora 的实际查询场景，16K 已足够）。

### 2.4 推荐部署命令

```bash
# 1. 下载 Qwen3.6-27B Q4_K_M GGUF
wget https://huggingface.co/unsloth/Qwen3.6-27B-GGUF/resolve/main/qwen3.6-27b-q4_k_m.gguf

# 2. 用 llama.cpp 启动 OpenAI 兼容服务（双卡分载）
./llama-server \
  -m qwen3.6-27b-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -ngl 99 \
  --split-mode layer \
  -c 16384

# 参数说明：
# -ngl 99     : 全部层放到 GPU
# --split-mode layer : 逐层分配给两张卡
# -c 16384    : 上下文窗口 16K tokens
```

---

## 三、WeKnora 本地部署方案

### 3.1 安装步骤

WeKnora 推荐 Docker Compose 部署，但需要注意模型推理服务（llama.cpp）是裸机运行的：

```bash
# 1. 克隆 WeKnora 仓库
git clone https://github.com/Tencent/WeKnora.git
cd WeKnora

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，配置模型指向本地 llama.cpp 服务
# LLM_BASE_URL=http://localhost:8080/v1
# LLM_MODEL=qwen3.6-27b
# LLM_API_KEY=not-needed

# 3. 启动 WeKnora（核心服务，不包含 LLM）
docker compose up -d

# 4. 访问 Web UI
# http://服务器IP:8081
```

### 3.2 WeKnora 配置关键点

```yaml
# docker-compose.yml 关键配置
services:
  app:
    image: wechatopenai/weknora-app:latest
    ports:
      - "8081:8080"
    environment:
      - LLM_PROVIDER=openai_compatible    # 使用 OpenAI 兼容接口
      - LLM_BASE_URL=http://host.docker.internal:8080  # 指向宿主机 llama.cpp
      - LLM_MODEL=qwen3.6-27b
      - EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5  # 中文 embedding
    volumes:
      - ./data:/app/data
      - ./config:/app/config
```

> ⚠️ **关键注意**：由于 llama.cpp 跑在宿主机（非 Docker 内），WeKnora 容器需要通过 `host.docker.internal` 或宿主机 IP 访问。如果使用 Linux，需要在 `docker-compose.yml` 中添加 `extra_hosts: - "host.docker.internal:host-gateway"`。

### 3.3 WeKnora 资源需求

| 资源 | 需求 | 实验室可用 |
|------|------|-----------|
| CPU | 4 核 | ✅ 32 核 |
| 内存 | 8GB | ✅ 128GB |
| 磁盘 | 20GB+（文档存储） | ✅ 充足 |
| GPU | 不需要（LLM 由外部提供） | ✅ 省下给推理 |

---

## 四、Hermes Agent Docker 部署与持久化方案

### 4.1 拉取镜像

```bash
# 拉取官方镜像（国内可用加速镜像）
docker pull nousresearch/hermes-agent:latest

# 或使用国内加速源
docker pull docker.xuanyuan.me/nousresearch/hermes-agent:latest
```

### 4.2 创建持久化目录

```bash
# 创建本地数据目录（容器删除后数据不丢失）
mkdir -p /opt/hermes/{config,data,memories,sessions,logs}

# config.yaml 和 .env 放在 config 目录
# data 目录存放持久化数据
# memories 目录存放长期记忆
# sessions 目录存放会话记录
# logs 目录存放日志
```

### 4.3 初始化配置

```bash
# 首次运行需要进行初始化配置
docker run -it --rm \
  -v /opt/hermes/config:/hermes/config \
  -v /opt/hermes/data:/hermes/data \
  -v /opt/hermes/memories:/hermes/memories \
  -v /opt/hermes/sessions:/hermes/sessions \
  -v /opt/hermes/logs:/hermes/logs \
  nousresearch/hermes-agent:latest \
  hermes init
```

初始化过程中选择：
- Provider: **DeepSeek**（或 **OpenAI 兼容**）
- Model: **deepseek-v4-flash**（或 **deepseek-v4-pro**）
- 输入 DeepSeek API Key

### 4.4 Docker Compose 持久化启动

创建 `docker-compose.yml`：

```yaml
version: "3.8"

services:
  hermes-agent:
    image: nousresearch/hermes-agent:latest
    container_name: hermes-agent
    restart: always
    ports:
      - "3000:3000"   # Web UI
    volumes:
      - /opt/hermes/config:/hermes/config
      - /opt/hermes/data:/hermes/data
      - /opt/hermes/memories:/hermes/memories
      - /opt/hermes/sessions:/hermes/sessions
      - /opt/hermes/logs:/hermes/logs
    environment:
      - TZ=Asia/Shanghai
      # 如果 DeepSeek API 需要代理
      - HTTP_PROXY=
      - HTTPS_PROXY=
```

```bash
# 启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down

# 升级（拉取新镜像后重启）
docker compose pull && docker compose up -d
```

### 4.5 Hermes Agent 的 MCP 配置（连接 WeKnora）

编辑 `/opt/hermes/config/config.yaml`，添加 WeKnora MCP 配置：

```yaml
mcpServers:
  weknora:
    command: python
    args:
      - -m
      - iflow_mcp_weknora_mcp_server
    env:
      WEKNORA_BASE_URL: "http://宿主机IP:8081"
      WEKNORA_API_KEY: "your-weknora-api-key"
```

或者如果 WeKnora 未提供 Python MCP Server，可以直接配置为 REST 工具调用：

```yaml
tools:
  - name: weknora-search
    description: "搜索 WeKnora 知识库"
    url: "http://宿主机IP:8081/api/v1/search"
    method: POST
    headers:
      Content-Type: application/json
    body:
      query: "{query}"
      knowledge_base_id: "lab-papers"
      top_k: 5
```

---

## 五、完整资源分配方案

### 5.1 GPU 分配方案

由于 WeKnora 本身不占用 GPU，实验室的 **2×RTX 2080Ti 全部用于 Qwen3.6-27B 推理**：

| 资源 | 分配 | 说明 |
|------|------|------|
| **GPU 0（11GB）** | Qwen3.6-27B 部分层 | llama.cpp split-mode=layer 自动分配 |
| **GPU 1（11GB）** | Qwen3.6-27B 剩余层 | 两张卡同时推理 |
| **CPU 32核** | WeKnora + Hermes | 绰绰有余 |
| **RAM 128GB** | 全部服务 | 富余量巨大 |
| **Embedding 模型** | CPU 运行 | BGE-large-zh-v1.5 约 2GB 内存 |

### 5.2 各组件端口规划

| 组件 | 端口 | 说明 |
|------|------|------|
| llama.cpp (Qwen3.6) | 8080 | OpenAI 兼容 API |
| WeKnora Web UI | 8081 | 知识库管理后台 |
| WeKnora API | 8082 | 内部 API |
| Hermes WebUI | 3000 | Agent 管理界面 |
| （可选）飞书 Webhook | 8088 | 飞书消息接收 |

### 5.3 启动顺序

```
1. 启动 llama.cpp (Qwen3.6-27B 推理服务)
       ↓
2. 启动 WeKnora 知识库 (Docker)
       ↓
3. 启动 Hermes Agent (Docker, 含 MCP 配置)
       ↓
4. 验证：WeKnora 问答、Hermes 对话、飞书接入
```

---

## 六、其他关注事项

### 6.1 网络与防火墙

- **服务器内部通信**：Hermes → WeKnora 通过 `host.docker.internal` 或内网 IP
- **DeepSeek API 外网访问**：确保服务器能访问 `api.deepseek.com`
- **飞书回调**：需要公网 IP 或域名配置 HTTPS 回调（推荐使用 Caddy 反向代理）
- **防火墙**：开放内部端口（8080-8088），外部端口仅开放 3000（WebUI）和 443（HTTPS）

### 6.2 数据安全与备份

- **知识库文档**：WeKnora 的数据卷（`./data`）定期备份到远程存储
- **Hermes 记忆**：`/opt/hermes/memories` 目录定期打包备份
- **配置备份**：`/opt/hermes/config` 和 WeKnora 的 `.env` 定期备份
- **推荐策略**：
  - 每日自动备份到 NAS 或对象存储（如阿里云 OSS）
  - 每周全量备份到移动硬盘
  - 每次重大配置变更前手动快照

### 6.3 监控与运维

| 监控项 | 工具/方式 | 告警阈值 |
|-------|-----------|---------|
| GPU 显存占用 | `nvidia-smi` / Prometheus + nvidia-exporter | > 90% 告警 |
| GPU 温度 | `nvidia-smi` | > 85°C 告警 |
| 模型推理延迟 | 自定义脚本 | > 5秒 告警 |
| 磁盘空间 | `df -h` | > 85% 告警 |
| 容器运行状态 | `docker ps` | 容器退出告警 |
| DeepSeek API 健康 | curl 测试 | 连续 3 次失败告警 |

推荐使用 **Docker Compose + Healthcheck** 实现自动恢复：

```yaml
services:
  hermes-agent:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: always
```

### 6.4 DeepSeek API 成本控制

| 模型 | 输入价格 | 输出价格 | 日估算费用（1000次对话） |
|------|---------|---------|----------------------|
| DeepSeek V4-Flash | $0.14/M tokens | $0.28/M tokens | ~3-10 元 |
| DeepSeek V4-Pro | $1.74/M tokens | $3.48/M tokens | ~30-100 元 |

**成本优化策略**：
- **默认使用 V4-Flash**，满足 90% 的日常对话需求
- **复杂任务降级到 V4-Pro**（通过 Hermes 的 `fallback` 机制）
- 设置**月度预算上限**（如 200 元/月）
- 配合本地 Qwen 模型进一步降低 API 调用量

### 6.5 潜在风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| Qwen3.6-27B Q4 在 2×2080Ti 上 OOM | 中 | 推理服务崩溃 | 降低上下文窗口至 8K；降级到 Q3_K_L；开启 CPU offload |
| DeepSeek API 访问不稳定 | 中 | Agent 不可用 | 配置 fallback 到本地 Qwen 模型；重试机制 |
| WeKnora 容器访问宿主机 GPU 失败 | 低 | 无法调用 LLM | 使用 `host.docker.internal` 或 `--network host` |
| 飞书回调网络不通 | 中 | 无法使用飞书 | 使用 Caddy + 域名；备选 Telegram |
| 双卡显存负载不均衡 | 低 | 推理效率下降 | 调整 `split-mode` 参数；实验不同分配策略 |

### 6.6 升级与版本管理

| 组件 | 版本策略 | 升级方式 |
|------|---------|---------|
| Hermes Agent | 锁定版本标签 | `docker compose pull && up -d` |
| WeKnora | 锁定版本标签 | `git pull && docker compose up -d --build` |
| llama.cpp | 保持最新稳定 | git pull 重编译 |
| Qwen 模型 | 按需更新 | 下载新版 GGUF 文件 |

---

## 七、部署验证清单

### 初始化阶段

- [ ] Docker 安装并运行正常
- [ ] llama.cpp 编译完成，双卡分配正常
- [ ] Qwen3.6-27B Q4_K_M 下载完成
- [ ] WeKnora Docker 启动成功，Web UI 可访问
- [ ] Hermes Agent Docker 初始化完成

### 连通性验证

- [ ] llama.cpp 服务返回 `curl http://localhost:8080/v1/models` 正常
- [ ] WeKnora 可调用本地 Qwen 模型（知识库问答）
- [ ] Hermes Agent 可连接 DeepSeek API（对话正常）
- [ ] Hermes Agent MCP 连接 WeKnora（知识检索正常）

### 功能验证

- [ ] WeKnora 上传论文 PDF，提问能正确回答
- [ ] Hermes Agent 记忆持久化（重启后记忆不丢失）
- [ ] 飞书机器人接入，多用户 session 隔离

---

## 八、参考链接

1. [Hermes Agent Docker 部署完整教程（阿里云）](https://developer.aliyun.com/article/1734664)
2. [Hermes Agent Docker 安装指南（中文社区）](https://hermesagent.org.cn/docs/user-guide/docker)
3. [Hermes Agent 官方 Docker Hub](https://hub.docker.com/r/nousresearch/hermes-agent)
4. [WeKnora GitHub 仓库](https://github.com/Tencent/WeKnora)
5. [WeKnora Docker 部署指南 (DeepWiki)](https://deepwiki.com/Tencent/WeKnora/9.1-docker-deployment)
6. [Qwen3.6-27B Unsloth GGUF](https://huggingface.co/unsloth/Qwen3.6-27B-GGUF)
7. [Qwen3.6-27B on 2×RTX 5060 Ti 实测 (Dev.to)](https://dev.to/defilan/we-ran-qwen36-27b-on-800-of-consumer-gpus-day-one-llamacpp-vs-vllm-mg1)
8. [llama.cpp GitHub](https://github.com/ggml-org/llama.cpp) - 推理引擎
9. [BGE-large-zh-v1.5 - Hugging Face](https://huggingface.co/BAAI/bge-large-zh-v1.5)
10. [DeepSeek V4 API 文档](https://api-docs.deepseek.com/)
11. [Hermes Agent + DeepSeek V4 配置指南](https://blog.csdn.net/qq_37703224/article/details/160593199)

---

*本文由 Hermes Agent 自动撰写并发布*
