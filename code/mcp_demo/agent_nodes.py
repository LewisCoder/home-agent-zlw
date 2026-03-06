#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 节点定义
定义 LangGraph 工作流中的各个节点函数
"""

import json
import sys
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from agent_state import State
from config import config
from mcp_client import MCPClient


class AgentNodes:
    """Agent 节点类，包含所有节点函数"""

    def __init__(self):
        """初始化节点类"""
        self.llm = ChatOpenAI(
            model=config.llm_model_id,
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )

        # 初始化 MCP 客户端
        mcp_server_path = Path(__file__).parent / "bill_mcp_server.py"
        self.mcp_client = MCPClient([sys.executable, str(mcp_server_path)])
        self.mcp_connected = self.mcp_client.connect()

        if not self.mcp_connected:
            print("⚠️ MCP 服务器未连接,Agent 功能将受限")

    def understand_intent(self, state: State) -> State:
        """
        节点1: 理解用户意图,提取账单代码和查询类型
        """
        user_input = state["user_input"]
        print(f"\n🧠 节点1: 理解用户意图")
        print(f"   用户输入: {user_input}")

        # 构建提示词
        prompt = f"""请分析用户输入,提取账单代码并判断查询类型。

用户输入: {user_input}

可用的MCP工具:
1. query_bill - 查询账单详细信息
2. query_operate_log - 查询账单的操作记录/日志

请分析用户想要:
- 如果用户想查询"账单信息"、"账单详情"、"账单数据",则使用 query_bill
- 如果用户想查询"操作记录"、"操作日志"、"操作历史"、"变更记录"、"日志",则使用 query_operate_log

账单代码格式: GBILL开头,后跟数字,例如 GBILL260202111424630037

请按以下JSON格式返回,不要有任何额外文字:
{{
  "billCode": "提取到的账单代码,如果没有则返回空字符串",
  "queryType": "bill_info 或 operate_log"
}}"""

        response = self.llm.invoke([SystemMessage(content=prompt)])
        result_text = response.content.strip()

        # 清理可能的markdown标记
        if "" in result_text:
            result_text = result_text.replace("", "").replace("", "").strip()

        # 提取JSON
        if '{' in result_text and '}' in result_text:
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            result_text = result_text[start:end]

        try:
            result = json.loads(result_text)
            bill_code = result.get("billCode", "")
            query_type = result.get("queryType", "bill_info")

            print(f"   ✓ 提取到账单代码: {bill_code}")
            print(f"   ✓ 查询类型: {query_type}")

            state["bill_code"] = bill_code
            state["query_type"] = query_type
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON解析失败: {e}")
            print(f"   原始响应: {result_text}")
            # 默认值
            state["bill_code"] = ""
            state["query_type"] = "bill_info"

        return state

    def call_mcp(self, state: State) -> State:
        """
        节点2: 根据查询类型调用相应的 MCP 工具
        """
        bill_code = state["bill_code"]
        query_type = state["query_type"]

        print(f"\n🔌 节点2: 调用 MCP 工具")
        print(f"   账单代码: {bill_code}")
        print(f"   查询类型: {query_type}")

        if not self.mcp_connected:
            state["mcp_result"] = "❌ MCP 服务未连接"
            return state

        if not bill_code:
            state["mcp_result"] = "❌ 未能从输入中提取到有效的账单代码"
            return state

        # 根据查询类型调用不同的工具
        if query_type == "operate_log":
            print(f"   正在查询操作记录...")
            result = self.mcp_client.call_tool("query_operate_log", {
                "businessKey": bill_code,
                "currentPage": 1,
                "pageSize": 10
            })
        else:  # bill_info
            print(f"   正在查询账单信息...")
            result = self.mcp_client.call_tool("query_bill", {
                "billCode": bill_code
            })

        print(f"   ✓ MCP 调用完成")
        state["mcp_result"] = result
        return state

    def generate_answer(self, state: State) -> State:
        """
        节点3: 基于 MCP 结果生成最终答案
        """
        user_input = state["user_input"]
        mcp_result = state["mcp_result"]

        print(f"\n💡 节点3: 生成最终答案")

        # 构建提示词
        prompt = f"""你是一个专业的账单查询助手。请基于以下信息回答用户问题:

用户问题: {user_input}

MCP工具调用结果:
{mcp_result}

请用友好、专业的语气回答用户,如果查询成功,请总结关键信息;如果查询失败,请说明原因并给出建议。"""

        print(f"   正在生成答案...")
        response = self.llm.invoke([SystemMessage(content=prompt)])
        final_answer = response.content

        print(f"   ✓ 答案生成完成")
        state["final_answer"] = final_answer
        return state

    def cleanup(self):
        """清理资源"""
        if self.mcp_connected:
            self.mcp_client.disconnect()
            print("\n🔌 MCP 连接已关闭")