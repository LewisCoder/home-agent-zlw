#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 工具包装器
将 MCP 工具转换为 LangChain 工具，支持 LangGraph 的 ToolNode
包含：账单查询工具（MCP）+ 知识库检索工具（RAG）
"""

import sys
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool
from mcp_client import MCPClient
from rag_retriever import get_retriever


class MCPToolWrapper:
    """MCP 工具包装器，管理 MCP 客户端和工具"""

    def __init__(self):
        """初始化 MCP 工具包装器"""
        # 初始化 MCP 客户端
        mcp_server_path = Path(__file__).parent / "bill_mcp_server.py"
        self.mcp_client = MCPClient([sys.executable, str(mcp_server_path)])
        self.mcp_connected = self.mcp_client.connect()

        if not self.mcp_connected:
            print("⚠️ MCP 服务器未连接,工具功能将受限")

    def cleanup(self):
        """清理资源"""
        if self.mcp_connected:
            self.mcp_client.disconnect()
            print("\n🔌 MCP 连接已关闭")


# 全局 MCP 工具包装器实例
_mcp_wrapper = MCPToolWrapper()


@tool
def query_bill(bill_code: str) -> str:
    """
    根据账单代码查询账单详细信息

    Args:
        bill_code: 账单代码，例如: GBILL260202111424630037

    Returns:
        账单详细信息的 JSON 字符串
    """
    if not _mcp_wrapper.mcp_connected:
        return "❌ MCP 服务未连接"

    if not bill_code:
        return "❌ 账单代码不能为空"

    print(f"   🔍 正在查询账单: {bill_code}")
    result = _mcp_wrapper.mcp_client.call_tool("query_bill", {
        "billCode": bill_code
    })
    return result


@tool
def query_operate_log(
    business_key: str,
    current_page: Optional[int] = 1,
    page_size: Optional[int] = 10
) -> str:
    """
    查询账单的操作记录日志

    Args:
        business_key: 业务键(账单代码)，例如: GBILL260202111424630037
        current_page: 当前页码，默认为 1
        page_size: 每页大小，默认为 10

    Returns:
        操作记录的 JSON 字符串
    """
    if not _mcp_wrapper.mcp_connected:
        return "❌ MCP 服务未连接"

    if not business_key:
        return "❌ 业务键不能为空"

    print(f"   📋 正在查询操作记录: {business_key}")
    result = _mcp_wrapper.mcp_client.call_tool("query_operate_log", {
        "businessKey": business_key,
        "currentPage": current_page,
        "pageSize": page_size
    })
    return result


@tool
def search_knowledge_base(query: str) -> str:
    """
    在本地知识库中检索与问题相关的文档内容（RAG）

    适用场景:
    - 查询公司内部政策、规章制度
    - 查询员工手册、福利待遇、补贴标准
    - 查询业务流程、操作规范等内部文档

    Args:
        query: 查询问题，例如: "出差补贴标准是什么"

    Returns:
        知识库中与问题最相关的文档片段
    """
    print(f"   📚 正在检索知识库: {query}")
    retriever = get_retriever()
    return retriever.retrieve(query)


# 导出工具列表（MCP 账单工具 + RAG 知识库工具）
mcp_tools = [query_bill, query_operate_log, search_knowledge_base]


def get_mcp_wrapper() -> MCPToolWrapper:
    """获取全局 MCP 工具包装器实例"""
    return _mcp_wrapper


