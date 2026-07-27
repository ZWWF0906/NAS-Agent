import os
import json
import requests
from openai import OpenAI

# ============ 配置 ============
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-AI-api-key")
AGENT_API_URL = "http://100.100.138.38:5050"
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "your-agent-api-key")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# ============ Agent API 封装 ============
def call_agent(endpoint, method="GET", json_data=None):
    headers = {"Authorization": f"Bearer {AGENT_API_KEY}"}
    url = f"{AGENT_API_URL}{endpoint}"
    if method == "GET":
        resp = requests.get(url, headers=headers, timeout=10)
    else:
        resp = requests.post(url, headers=headers, json=json_data, timeout=10)
    return resp.json() if resp.status_code == 200 else {"error": resp.text}

def get_full_status():
    """一次获取所有状态"""
    return {
        "local_status": call_agent("/api/status"),
        "nas_status": call_agent("/api/nas/status"),
        "disk_health": call_agent("/api/health/disks"),
        "services_health": call_agent("/api/health/services"),
        "ssh_security": call_agent("/api/security/sshd"),
        "temperature": call_agent("/api/health/temperature"),
        "network": call_agent("/api/health/network"),
        "disk_io": call_agent("/api/health/diskio")
    }

# ============ 主逻辑 ============
SYSTEM_PROMPT = """
你是一个 NAS 和 Docker 管理助手。你会收到一份 JSON 格式的实时系统数据，请根据数据用自然语言回复用户。

数据包含以下字段：
- local_status: 笔记本状态（CPU/内存/磁盘/容器/运行时间/CPU温度）
- nas_status: 台式机 NAS 状态（在线状态、系统信息、SMART原始数据）
- disk_health: 本地和 NAS 磁盘的 SMART 关键指标摘要（温度、健康状态、坏扇区数、SATA速率等）
- services_health: Web 服务的 HTTP 状态码和响应延迟
- ssh_security: SSH 暴力破解尝试统计
- temperature: 所有温度传感器读数
- network: 网络连通性（网关、NAS、公网DNS）
- disk_io: 磁盘 I/O 负载情况

请综合所有信息，全面分析系统健康状态，指出任何潜在风险。
"""

def chat():
    print("=" * 50)
    print("Agent NAS AI 助手 (DeepSeek)")
    print("输入 'quit' 退出")
    print("=" * 50)
    
    while True:
        user_input = input("\n你: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            break
        if not user_input.strip():
            continue
        
        try:
            print("⏳ 正在获取系统状态...")
            status_data = get_full_status()
            status_str = json.dumps(status_data, ensure_ascii=False, indent=2)
            
            response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"请根据以下系统状态数据回答用户问题。\n\n用户问题：{user_input}\n\n系统状态数据：\n{status_str}"}
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            reply = response.choices[0].message.content
            print(f"\n🤖 助手:\n{reply}\n")
            print(f"📊 原始数据已获取，长度: {len(status_str)} 字节")
            
        except Exception as e:
            print(f"❌ 出错: {e}")

if __name__ == "__main__":
    chat()
