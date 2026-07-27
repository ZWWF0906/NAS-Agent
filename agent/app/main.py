from fastapi import FastAPI, HTTPException, Depends, Header
import docker
import psutil
import time
import subprocess
import paramiko
import os
import re
import shlex
import json
from typing import Optional

app = FastAPI()
API_KEY = os.getenv("API_KEY", "changeme")
NAS_IP = os.getenv("NAS_IP", "100.93.189.99")
NAS_USER = os.getenv("NAS_USER", "root")

def verify_key(authorization: str = Header(None)):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=403, detail="Invalid API Key")

client = docker.from_env()

# ---------- 命令白名单 ----------
ALLOWED_COMMANDS = {
    "docker ps": {"args": [], "description": "List containers"},
    "docker stats": {"args": ["--no-stream"], "description": "Container stats (no stream)"},
    "docker logs": {"args": ["<container_name>"], "safe_container_list": ["alist", "gitea", "vaultwarden", "agent"], "description": "Fetch container logs"},
    "docker restart": {"args": ["<container_name>"], "safe_container_list": ["alist", "agent"], "description": "Restart a safe container"},
    "df -h": {"args": [], "description": "Disk usage"},
    "free -m": {"args": [], "description": "Memory usage"},
    "uptime": {"args": [], "description": "System uptime"},
    "cat /etc/os-release": {"args": [], "description": "OS version"},
    "ls -l": {"args": ["<path>"], "allowed_paths": ["/opt/docker", "/var/log", "/tmp"], "description": "List directory"},
    "systemctl status": {"args": ["<service_name>"], "allowed_services": ["docker", "tailscaled", "ssh"], "description": "Service status (read-only)"},
}

def is_command_allowed(command_str: str) -> bool:
    parts = shlex.split(command_str)
    if not parts:
        return False
    for allowed, rule in ALLOWED_COMMANDS.items():
        allowed_parts = shlex.split(allowed)
        if parts[:len(allowed_parts)] == allowed_parts:
            rest = parts[len(allowed_parts):]
            if not rest:
                return True
            if "safe_container_list" in rule:
                if len(rest) == 1 and rest[0] in rule["safe_container_list"]:
                    return True
            if "allowed_paths" in rule:
                if len(rest) == 1 and rest[0].startswith(tuple(rule["allowed_paths"])):
                    return True
            if "allowed_services" in rule:
                if len(rest) == 1 and rest[0] in rule["allowed_services"]:
                    return True
            if "args" in rule and rest == rule["args"]:
                return True
    return False

# ---------- 基础端点 ----------

@app.get("/api/status", dependencies=[Depends(verify_key)])
async def local_status():
    containers = []
    for c in client.containers.list(all=True):
        containers.append({"name": c.name, "status": c.status})
    
    cpu_temp = None
    try:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                cpu_temp = round(int(f.read().strip()) / 1000, 1)
    except:
        pass
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_count": psutil.cpu_count(),
        "cpu_temp": cpu_temp,
        "memory": dict(psutil.virtual_memory()._asdict()),
        "disk": dict(psutil.disk_usage('/')._asdict()),
        "containers": containers,
        "uptime": time.time() - psutil.boot_time(),
        "boot_time": psutil.boot_time()
    }

@app.get("/api/nas/status", dependencies=[Depends(verify_key)])
async def nas_status():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(NAS_IP, username=NAS_USER, key_filename="/app/id_rsa", timeout=5)
        
        cmd = (
            "echo '=== SYSTEM ===' && top -bn1 | head -5 && "
            "echo '=== MEMORY ===' && cat /proc/meminfo | head -3 && "
            "echo '=== DISK ===' && df -h / && "
            "echo '=== SMART ===' && for dev in /dev/sd[a-z]; do "
            "  if [ -b $dev ]; then "
            "    echo '---DISK:' $dev '---'; "
            "    smartctl -a $dev 2>&1 | head -40; "
            "  fi; done"
        )
        stdin, stdout, stderr = ssh.exec_command(cmd)
        data = stdout.read().decode()
        ssh.close()
        return {"online": True, "raw_info": data}
    except Exception as e:
        return {"online": False, "error": str(e)}

@app.get("/api/logs/{service}", dependencies=[Depends(verify_key)])
async def get_logs(service: str, lines: int = 50):
    try:
        container = client.containers.get(service)
        logs = container.logs(tail=lines).decode("utf-8")
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/execute", dependencies=[Depends(verify_key)])
async def execute_command(payload: dict):
    command = payload.get("command", "")
    timeout = payload.get("timeout", 10)
    if not command:
        raise HTTPException(status_code=400, detail="No command provided")
    if not is_command_allowed(command):
        raise HTTPException(status_code=403, detail="Command not allowed")
    if re.search(r"[;&|`$(){}\[\]]", command):
        raise HTTPException(status_code=403, detail="Forbidden characters")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- 健康检测端点 ----------

@app.get("/api/health/disks", dependencies=[Depends(verify_key)])
async def health_disks():
    local_disks = {}
    try:
        lsblk_output = subprocess.run(
            ["lsblk", "-dno", "NAME,TYPE,SIZE"],
            capture_output=True, text=True, timeout=5
        )
        for line in lsblk_output.stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) < 2:
                continue
            name, dtype = parts[0], parts[1]
            if dtype != 'disk' or name.startswith('loop') or name.startswith('ram'):
                continue
            try:
                smart = subprocess.run(
                    ["smartctl", "-a", f"/dev/{name}"],
                    capture_output=True, text=True, timeout=10
                )
                if smart.returncode == 0:
                    local_disks[name] = _parse_smart_data(smart.stdout)
                else:
                    local_disks[name] = {"error": "SMART unavailable"}
            except Exception as e:
                local_disks[name] = {"error": str(e)}
    except Exception as e:
        local_disks = {"error": str(e)}

    nas_disks = {}
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(NAS_IP, username=NAS_USER, key_filename="/app/id_rsa", timeout=5)
        cmd = (
            "for dev in /dev/sd[a-z]; do "
            "  if [ -b $dev ]; then "
            "    echo '---DISK:' $dev '---'; "
            "    smartctl -a $dev 2>&1 | head -40; "
            "  fi; done"
        )
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        ssh.close()
        nas_disks["raw"] = output
    except Exception as e:
        nas_disks = {"error": str(e)}

    return {"local_disks": local_disks, "nas_disks": nas_disks}

def _parse_smart_data(raw_text):
    info = {}
    lines = raw_text.split('\n')
    for line in lines:
        line = line.strip()
        if 'SMART overall-health self-assessment test result' in line:
            info['health_status'] = line.split(':')[-1].strip()
        elif 'Temperature_Celsius' in line or 'Airflow_Temperature_Cel' in line:
            parts = line.split()
            if len(parts) >= 10:
                info['temperature'] = parts[-1] + '°C'
        elif 'Power_On_Hours' in line:
            parts = line.split()
            if len(parts) >= 10:
                info['power_on_hours'] = parts[-1]
        elif 'Reallocated_Sector_Ct' in line:
            parts = line.split()
            if len(parts) >= 10:
                info['reallocated_sectors'] = parts[-1]
        elif 'Current_Pending_Sector' in line:
            parts = line.split()
            if len(parts) >= 10:
                info['pending_sectors'] = parts[-1]
        elif 'UDMA_CRC_Error_Count' in line:
            parts = line.split()
            if len(parts) >= 10:
                info['udma_crc_errors'] = parts[-1]
        elif 'SATA Version is' in line:
            info['sata_version'] = line.split(':')[-1].strip()
    if not info:
        info["raw"] = raw_text[:500]
    return info

@app.get("/api/health/services", dependencies=[Depends(verify_key)])
async def health_services():
    import aiohttp
    services = {
        "alist": "http://100.100.138.38:5244",
        "gitea": "http://100.100.138.38:3000",
        "vaultwarden": "http://100.100.138.38:8081",
    }
    health = {}
    async with aiohttp.ClientSession() as session:
        for name, url in services.items():
            try:
                start = time.monotonic()
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    latency = time.monotonic() - start
                    health[name] = {
                        "status_code": resp.status,
                        "latency_ms": round(latency * 1000),
                        "healthy": resp.status < 500
                    }
            except Exception as e:
                health[name] = {"error": str(e), "healthy": False}
    return health

@app.get("/api/security/sshd", dependencies=[Depends(verify_key)])
async def security_sshd():
    try:
        one_hour_ago = int(time.time()) - 3600
        cmd = f"journalctl -u ssh --since @{one_hour_ago} 2>/dev/null | grep 'Failed password' | wc -l"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        failed_count = int(result.stdout.strip() or 0)
        return {
            "failed_login_attempts_last_hour": failed_count,
            "warning": failed_count > 10
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health/temperature", dependencies=[Depends(verify_key)])
async def health_temperature():
    temps = {}
    try:
        if os.path.exists("/sys/class/thermal"):
            for zone in os.listdir("/sys/class/thermal"):
                if zone.startswith("thermal_zone"):
                    type_file = f"/sys/class/thermal/{zone}/type"
                    temp_file = f"/sys/class/thermal/{zone}/temp"
                    if os.path.exists(type_file) and os.path.exists(temp_file):
                        with open(type_file) as f:
                            zone_type = f.read().strip()
                        with open(temp_file) as f:
                            zone_temp = round(int(f.read().strip()) / 1000, 1)
                        temps[zone_type] = zone_temp
    except Exception as e:
        temps["error"] = str(e)
    return temps

@app.get("/api/health/network", dependencies=[Depends(verify_key)])
async def health_network():
    targets = {
        "gateway": "192.168.1.1",
        "tailscale_nas": "100.93.189.99",
        "dns_public": "8.8.8.8",
        "dns_cn": "223.5.5.5"
    }
    results = {}
    for name, ip in targets.items():
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", ip],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'time=' in line:
                        ms = line.split('time=')[1].split(' ')[0]
                        results[name] = {"reachable": True, "latency_ms": ms}
                        break
                if name not in results:
                    results[name] = {"reachable": True}
            else:
                results[name] = {"reachable": False}
        except:
            results[name] = {"reachable": False, "error": "timeout"}
    return results

@app.get("/api/health/diskio", dependencies=[Depends(verify_key)])
async def health_diskio():
    """获取本机磁盘 I/O 统计（从 /proc/diskstats 读取）"""
    io_stats = {}
    try:
        with open("/proc/diskstats", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 14:
                    continue
                device = parts[2]
                # 只关注真实磁盘，排除分区和虚拟设备
                if not device.startswith(("sd", "vd", "nvme")):
                    continue
                # 提取关键字段：读次数、读扇区、写次数、写扇区
                reads = int(parts[3])
                read_sectors = int(parts[5])
                writes = int(parts[7])
                write_sectors = int(parts[9])
                io_stats[device] = {
                    "reads": reads,
                    "read_sectors": read_sectors,
                    "writes": writes,
                    "write_sectors": write_sectors
                }
        return io_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
