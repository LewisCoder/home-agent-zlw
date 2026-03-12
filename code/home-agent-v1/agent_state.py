#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 状态定义
定义 LangGraph 工作流中使用的状态结构
"""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

# 保留最近 N 轮对话（1轮 = 1条 HumanMessage + 1条 AIMessage）
# 调整此值可控制 token 消耗，设为 0 表示不保留历史（每次独立对话）
MAX_HISTORY_TURNS = 5


class State(TypedDict):
    """Agent 状态定义

    用于 LangGraph 工作流中节点间传递的数据结构
    """
    # 使用 messages 字段存储对话历史，支持 LangGraph 的工具调用
    # add_messages 确保消息追加而非覆盖
    messages: Annotated[list, add_messages]
