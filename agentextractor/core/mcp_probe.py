"""MCP Probe - dynamically query running MCP servers for their capabilities.

Uses the MCP protocol's built-in methods:
- tools/list: Get all tools exposed by the server
- resources/list: Get all resources
- prompts/list: Get all prompt templates
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class MCPTool:
    name: str = ""
    description: str = ""
    input_schema: dict = field(default_factory=dict)


@dataclass
class MCPResource:
    uri: str = ""
    name: str = ""
    description: str = ""
    mime_type: str = ""


@dataclass
class MCPPrompt:
    name: str = ""
    description: str = ""
    arguments: list = field(default_factory=list)


@dataclass
class MCPServerCapabilities:
    """MCP Server 的完整能力描述"""
    name: str = ""
    transport: str = "stdio"
    command: str = ""
    args: list = field(default_factory=list)
    tools: List[MCPTool] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)
    prompts: List[MCPPrompt] = field(default_factory=list)
    error: str = ""
    reachable: bool = False


class MCPProbe:
    """MCP 探针：向运行中的 MCP Server 发送协议请求获取能力"""

    def probe_from_config(self, mcp_config_path: Path) -> List[MCPServerCapabilities]:
        """从 MCP 配置文件中读取所有 server，逐个探测"""
        results = []
        try:
            data = json.loads(mcp_config_path.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            for name, cfg in servers.items():
                cap = MCPServerCapabilities(
                    name=name,
                    transport=cfg.get("transport", "stdio"),
                    command=cfg.get("command", ""),
                    args=cfg.get("args", []),
                )
                # 只探测 stdio 类型的本地 server
                if cap.transport == "stdio" and cap.command:
                    self._probe_stdio(cap, cfg.get("env", {}))
                results.append(cap)
        except Exception as e:
            results.append(MCPServerCapabilities(name="error", error=str(e)))
        return results

    def _probe_stdio(self, cap: MCPServerCapabilities, env: dict):
        """通过 stdio 协议探测 MCP server 能力"""
        # 构建 JSON-RPC 请求
        init_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agentextractor-probe", "version": "0.1.0"}
            }
        }) + "\n"

        tools_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }) + "\n"

        try:
            # 合并环境变量
            proc_env = os.environ.copy()
            proc_env.update(env)

            # 启动 MCP server 进程
            cmd = [cap.command] + cap.args
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=proc_env,
                timeout=10,
            )

            # 发送 initialize + tools/list
            stdout, stderr = proc.communicate(
                input=(init_request + tools_request).encode(),
                timeout=10,
            )

            cap.reachable = True
            output = stdout.decode("utf-8", errors="replace")

            # 解析响应（可能有多行 JSON）
            for line in output.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    resp = json.loads(line)
                    if resp.get("id") == 2 and "result" in resp:
                        # tools/list response
                        tools_data = resp["result"].get("tools", [])
                        for t in tools_data:
                            cap.tools.append(MCPTool(
                                name=t.get("name", ""),
                                description=t.get("description", ""),
                                input_schema=t.get("inputSchema", {}),
                            ))
                except json.JSONDecodeError:
                    continue

        except subprocess.TimeoutExpired:
            cap.error = "探测超时（10s）"
        except FileNotFoundError:
            cap.error = f"命令不存在: {cap.command}"
        except Exception as e:
            cap.error = str(e)

    def probe_summary(self, capabilities: List[MCPServerCapabilities]) -> dict:
        """生成探测摘要"""
        total = len(capabilities)
        reachable = sum(1 for c in capabilities if c.reachable)
        total_tools = sum(len(c.tools) for c in capabilities)

        servers = []
        for c in capabilities:
            servers.append({
                "name": c.name,
                "transport": c.transport,
                "command": f"{c.command} {' '.join(c.args[:2])}".strip(),
                "reachable": c.reachable,
                "tools_count": len(c.tools),
                "tools": [{"name": t.name, "description": t.description[:60]} for t in c.tools],
                "error": c.error,
            })

        return {
            "total_servers": total,
            "reachable": reachable,
            "total_tools": total_tools,
            "servers": servers,
        }
