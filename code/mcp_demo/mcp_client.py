#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 客户端模块
负责与 MCP 服务器通信
"""

import json
import subprocess
from typing import Dict, List, Optional


class MCPClient:
    """MCP 客户端"""

    def __init__(self, server_command: List[str]):
        """
        初始化 MCP 客户端

        Args:
            server_command: MCP 服务器启动命令
        """
        self.server_command = server_command
        self.process: Optional[subprocess.Popen] = None
        self.tools: Dict[str, dict] = {}
        self.connected = False
        self._request_id = 0

    def connect(self) -> bool:
        """连接到 MCP 服务器"""
        try:
            print("🔌 正在连接 MCP 服务器...")

            # 启动 MCP 服务器进程
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1
            )

            # 发送初始化请求
            response = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "bill-query-agent",
                    "version": "1.0.0"
                }
            })

            if response and "result" in response:
                print("   ✓ MCP 服务器连接成功")
                self.connected = True
                self._list_tools()
                return True
            else:
                print(f"   ✗ MCP 初始化失败: {response}")
                return False

        except Exception as e:
            print(f"   ✗ MCP 连接失败: {e}")
            return False

    def _send_request(self, method: str, params: dict) -> dict:
        """
        发送 JSON-RPC 请求

        Args:
            method: 方法名
            params: 参数

        Returns:
            响应字典
        """
        if not self.process or not self.process.stdin:
            return {}

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }

        try:
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # 读取响应
            if self.process.stdout:
                line = self.process.stdout.readline()
                if line:
                    return json.loads(line.strip())
        except Exception as e:
            print(f"   ⚠️ 请求失败: {e}")

        return {}

    def _list_tools(self):
        """获取可用工具列表"""
        response = self._send_request("tools/list", {})

        if response and "result" in response:
            tools = response["result"].get("tools", [])
            for tool in tools:
                self.tools[tool["name"]] = tool
            print(f"   ✓ 发现 {len(self.tools)} 个 MCP 工具: {list(self.tools.keys())}")

    def call_tool(self, tool_name: str, arguments: Optional[dict] = None) -> str:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self.connected:
            return "❌ MCP 客户端未连接"

        if tool_name not in self.tools:
            return f"❌ 工具 '{tool_name}' 不存在"

        try:
            response = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments or {}
            })

            if response and "result" in response:
                content = response["result"].get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")

            return "⚠️ MCP 调用无返回结果"

        except Exception as e:
            return f"❌ MCP 调用失败: {e}"

    def disconnect(self):
        """断开 MCP 连接"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            finally:
                self.process = None
                self.connected = False

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
