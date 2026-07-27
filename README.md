# NAS-Agent

一个具备远程访问、服务托管、自动维护能力，并且可以接入 AI Agent 的个人家庭服务器节点。

## 功能特性

- **远程安全访问**：基于 Tailscale 组网，无需公网 IP 即可安全连接
- **Docker 服务自动化部署**：一键启动 Portainer、Alist、Gitea、Vaultwarden
- **AI Agent 系统监控**：实时监控 CPU、内存、磁盘、容器状态
- **硬盘健康检测**：读取 S.M.A.R.T. 数据，提前预警磁盘故障
- **Web 服务响应监控**：检查 Alist、Gitea、Vaultwarden 的 HTTP 状态
- **SSH 安全事件统计**：统计暴力破解尝试次数
- **白名单命令执行**：允许安全地远程管理容器

## 架构

\`\`\`
用户 → Tailscale 安全网络 → NAS-Agent
                              ├── 存储层 (NAS)
                              └── 应用层 (Docker + Agent)
\`\`\`

## 快速开始

1. 克隆仓库
   \`\`\`bash
   git clone https://github.com/ZWWF0906/NAS-Agent.git
   \`\`\`

2. 修改配置文件
   - 将 `docker-compose.yml` 中的 `API_KEY` 替换为你自己的密钥
   - 将 `ai_agent.py` 中的 `DEEPSEEK_API_KEY` 和 `AGENT_API_KEY` 替换为你的真实密钥

3. 启动服务
   \`\`\`bash
   cd NAS-Agent
   docker compose up -d
   \`\`\`

4. 运行 AI 对话脚本
   \`\`\`bash
   export DEEPSEEK_API_KEY="你的DeepSeek密钥"
   export AGENT_API_KEY="你的Agent密钥"
   python3 ai_agent.py
   \`\`\`

## 目录结构

\`\`\`
├── agent/            # Agent 核心代码
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py   # FastAPI 应用
├── ai_agent.py       # AI 对话脚本
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
\`\`\`

## 技术栈

- Debian 13 + Docker
- Python FastAPI
- Tailscale
- DeepSeek API

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。
