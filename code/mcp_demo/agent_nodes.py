#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 节点定义（优化版）
使用 LangGraph 的 ToolNode 和 tools_condition 实现工具调用
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agent_state import State
from config import config
from mcp_tools import mcp_tools


class AgentNodes:
    """Agent 节点类，包含所有节点函数"""

    def __init__(self):
        """初始化节点类"""
        # 创建绑定了工具的 LLM
        self.llm = ChatOpenAI(
            model=config.llm_model_id,
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            temperature=0
        )

        # 将工具绑定到 LLM
        self.llm_with_tools = self.llm.bind_tools(mcp_tools)

        # 系统提示词
        self.system_prompt = """你是一个专业的账单查询助手，同时具备公司知识库检索能力。

你有以下工具可用:
1. query_bill            - 根据账单代码查询账单详细信息
2. query_operate_log     - 查询账单的操作记录/变更日志
3. search_knowledge_base - 在本地知识库中检索公司内部文档（RAG）

工具使用规则:
- 当用户提供账单代码（GBILL开头）并询问账单信息/详情时，使用 query_bill
- 当用户询问账单的操作记录、变更历史、日志时，使用 query_operate_log
- 当用户询问公司政策、规章制度、业务规范、操作流程等内部文档内容时，使用 search_knowledge_base
- 账单代码格式: GBILL开头后跟数字，例如 GBILL260202111424630037
- 可以组合使用多个工具，例如先查账单信息再查操作记录

请根据用户问题选择合适的工具，并给出专业、友好的回答。"""

    def call_model(self, state: State) -> State:
        """
        调用模型节点

        这个节点会:
        1. 接收用户输入和历史消息
        2. 使用绑定了工具的 LLM 进行推理
        3. 决定是否需要调用工具，或直接返回答案
        """
        messages = state["messages"]

        # 如果是第一条消息，添加系统提示
        if len(messages) == 1 or not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=self.system_prompt)] + messages

        print(f"\n🤖 正在调用模型...")
        print(f"   消息数量: {len(messages)}")

        # 调用 LLM（已绑定工具）
        response = self.llm_with_tools.invoke(messages)

        # 检查是否有工具调用
        if response.tool_calls:
            print(f"   ✓ 模型决定调用 {len(response.tool_calls)} 个工具")
            for tool_call in response.tool_calls:
                print(f"      - {tool_call['name']}: {tool_call['args']}")
        else:
            print(f"   ✓ 模型直接返回答案")

        # 返回更新后的状态（add_messages 会自动追加消息）
        return {"messages": [response]}

