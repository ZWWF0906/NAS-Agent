# NAS-Agent

> 将普通 NAS 升级为可被 AI 管理的个人家庭服务器节点。

基于 **FastAPI + Docker + DeepSeek API** 构建的智能 NAS 管理代理系统。

通过统一 RESTful API，将系统监控、容器管理、安全检测等能力开放给 AI 大模型，实现自然语言驱动的服务器运维。

---

## ✨ 项目介绍

NAS-Agent 是一个面向个人 Homelab 环境设计的 AI 运维代理。

它连接普通 NAS 与 AI 大模型，使用户能够通过自然语言：

- 查询服务器状态
- 分析系统健康情况
- 查看 Docker 服务日志
- 检测磁盘与网络状态
- 获取智能运维建议

目标：

> 让普通家庭服务器具备 AI 管理能力。

---

# 🚀 功能特性

## 📊 系统监控

| 功能 | 描述 |
|------|------|
| 本地状态监控 | 获取 CPU、内存、磁盘、Docker 等基础状态 |
| NAS 远程监控 | 通过 SSH 获取 NAS 运行状态 |
| 磁盘健康监控 | 读取 S.M.A.R.T 数据，提前发现磁盘风险 |
| 温度监控 | 实时检测系统温度传感器 |
| 网络检测 | 检测网关、NAS、公网 DNS 连通性与延迟 |
| 磁盘 I/O | 统计磁盘读写负载 |

## 🐳 服务管理

| 功能 | 描述 |
|------|------|
| 服务健康检查 | 检测 Web 服务 HTTP 状态和响应时间 |
| Docker 日志 | 获取指定容器运行日志 |
| 命令执行 | 基于白名单的安全命令执行 |

## 🔐 安全检测

- SSH 登录失败统计
- API Key 身份认证
- Tailscale 私有网络访问
- 命令执行白名单限制

## 🤖 AI 对话

支持：

- 中文自然语言查询
- 系统健康综合分析
- 多模块数据汇总
- AI 运维建议

---

# 🏗 系统架构

    用户
      │
      ├── Tailscale 安全网络
      │
      └── NAS-Agent
            │
            ├── 存储层 (NAS)
            │
            └── 应用层 (Docker + Agent)

---

# 🛠 技术栈

| 分类 | 技术 |
|------|------|
| 操作系统 | Debian 13 |
| 容器平台 | Docker |
| 后端框架 | Python FastAPI |
| 网络访问 | Tailscale |
| AI 模型 | DeepSeek API |
| 通信方式 | RESTful API |

---

# 📦 快速开始

## 克隆项目

    git clone https://github.com/ZWWF0906/NAS-Agent.git
    cd NAS-Agent

## 配置密钥

修改：

- `docker-compose.yml`
- `ai_agent.py`

配置：

- `API_KEY`
- `DEEPSEEK_API_KEY`
- `AGENT_API_KEY`

**请勿提交真实密钥到 GitHub。**

## 启动服务

    docker compose up -d

## 启动 AI 对话

    export DEEPSEEK_API_KEY="你的DeepSeek密钥"
    export AGENT_API_KEY="你的Agent密钥"
    python3 ai_agent.py

输入：

    全面检查系统健康状态

即可开始 AI 运维。

---

# 📡 API 文档

所有接口需要：

    Authorization: Bearer <API_KEY>

## 基础接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/status` | GET | 本地系统状态 |
| `/api/nas/status` | GET | NAS 远程状态 |
| `/api/execute` | POST | 执行白名单命令 |
| `/api/logs/{service}` | GET | 获取 Docker 服务日志 |

## 健康检查

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/health/disks` | GET | 磁盘 SMART 信息 |
| `/api/health/services` | GET | Web 服务健康状态 |
| `/api/health/temperature` | GET | 系统温度检测 |
| `/api/health/network` | GET | 网络连通性检测 |
| `/api/health/diskio` | GET | 磁盘 I/O 状态 |

## 安全检测

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/security/sshd` | GET | SSH 登录失败统计 |

---

# 📁 项目结构

    NAS-Agent
    ├── agent/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── app/
    │       └── main.py
    ├── ai_agent.py
    ├── docker-compose.yml
    ├── .gitignore
    ├── LICENSE
    └── README.md

---

# 🔒 安全设计

## 网络隔离
Agent 默认运行于 Tailscale 私有网络环境，避免直接暴露公网。

## API认证
所有接口需要 API Key 验证。

## 命令保护
系统命令执行采用白名单机制，防止误操作。

## 数据保护
建议：

- 定期备份 NAS 数据
- 保存重要配置文件
- 定期检查磁盘健康状态

---

# 📚 依赖

- fastapi
- uvicorn
- docker
- paramiko
- psutil
- aiohttp
- openai

完整依赖见 `agent/requirements.txt`。

---

# 🤝 合作伙伴

- **DeepSeek** — AI 模型能力支持
- **TGW_Sakikoo** — 项目联合发起，技术支持

---

# 📄 License

本项目采用 MIT License。

---

# ⭐ 项目愿景

NAS-Agent 探索：

> AI + Homelab + 自动化运维

让个人服务器不仅能够存储数据，还能理解需求、主动发现问题，并协助用户维护自己的数字世界。
