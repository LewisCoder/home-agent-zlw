#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 状态定义
定义 LangGraph 工作流中使用的状态结构
"""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    """Agent 状态定义

    用于 LangGraph 工作流中节点间传递的数据结构
    """
    # 使用 messages 字段存储对话历史，支持 LangGraph 的工具调用
    messages: Annotated[list, add_messages]