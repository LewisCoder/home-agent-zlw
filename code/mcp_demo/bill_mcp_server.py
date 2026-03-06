#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单查询 MCP 服务器
负责处理 MCP 协议请求并调用 API 服务
"""

import json
import sys
from typing import Dict

from api_service import bill_service, operate_log_service


class BillQueryMCPServer:
    """账单查询 MCP 服务器"""

    def __init__(self):
        self.server_info = {
            "name": "bill-query-mcp-server",
            "version": "1.0.0"
        }

        self.tools = [
            {
                "name": "query_bill",
                "description": "根据账单代码查询账单详细信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "billCode": {
                            "type": "string",
                            "description": "账单代码,例如: GBILL260202111424630037"
                        }
                    },
                    "required": ["billCode"]
                }
            },
            {
                "name": "query_operate_log",
                "description": "查询账单的操作记录日志",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "businessKey": {
                            "type": "string",
                            "description": "业务键(账单代码),例如: GBILL260202111424630037"
                        },
                        "currentPage": {
                            "type": "integer",
                            "description": "当前页码,默认为 1",
                            "default": 1
                        },
                        "pageSize": {
                            "type": "integer",
                            "description": "每页大小,默认为 10",
                            "default": 10
                        }
                    },
                    "required": ["businessKey"]
                }
            }
        ]

    def handle_initialize(self, request_id: int) -> dict:
        """处理初始化请求"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": self.server_info
            }
        }

    def handle_tools_list(self, request_id: int) -> dict:
        """处理工具列表请求"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": self.tools}
        }

    def handle_tools_call(self, request_id: int, tool_name: str, arguments: dict) -> dict:
        """处理工具调用请求"""
        result_text = self._call_tool(tool_name, arguments)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": result_text}]
            }
        }

    def _call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        调用具体的工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            格式化的结果文本
        """
        if tool_name == "query_bill":
            return self._handle_query_bill(arguments)
        elif tool_name == "query_operate_log":
            return self._handle_query_operate_log(arguments)
        else:
            return f"❌ 未知工具: {tool_name}"

    def _handle_query_bill(self, arguments: dict) -> str:
        """处理账单查询"""
        bill_code = arguments.get("billCode", "")

        if not bill_code:
            return "❌ 参数错误: billCode 是必填项"

        # 调用 API 服务
        api_result = bill_service.query_bill(bill_code)

        if api_result.get("success"):
            data = api_result.get("data", {})
            return f"✅ 账单查询成功\n\n账单代码: {bill_code}\n\n响应数据:\n{json.dumps(data, ensure_ascii=False, indent=2)}"
        else:
            return f"❌ 账单查询失败\n\n错误类型: {api_result.get('error_type')}\n错误信息: {api_result.get('error')}"

    def _handle_query_operate_log(self, arguments: dict) -> str:
        """处理操作记录查询"""
        business_key = arguments.get("businessKey", "")
        current_page = arguments.get("currentPage", 1)
        page_size = arguments.get("pageSize", 10)

        if not business_key:
            return "❌ 参数错误: businessKey 是必填项"

        # 调用 API 服务
        api_result = operate_log_service.query_operate_log(
            business_key, current_page, page_size
        )

        if api_result.get("success"):
            data = api_result.get("data", {})
            return f"✅ 操作记录查询成功\n\n业务键: {business_key}\n当前页: {current_page}\n每页大小: {page_size}\n\n响应数据:\n{json.dumps(data, ensure_ascii=False, indent=2)}"
        else:
            return f"❌ 操作记录查询失败\n\n错误类型: {api_result.get('error_type')}\n错误信息: {api_result.get('error')}"

    def handle_request(self, request: dict) -> dict:
        """
        处理 MCP 请求

        Args:
            request: JSON-RPC 请求

        Returns:
            JSON-RPC 响应
        """
        method = request.get("method")
        request_id = request.get("id")

        if method == "initialize":
            return self.handle_initialize(request_id)
        elif method == "tools/list":
            return self.handle_tools_list(request_id)
        elif method == "tools/call":
            tool_name = request["params"]["name"]
            arguments = request["params"].get("arguments", {})
            return self.handle_tools_call(request_id, tool_name, arguments)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "Method not found"}
            }

    def run(self):
        """运行 MCP 服务器"""
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    server = BillQueryMCPServer()
    server.run()

