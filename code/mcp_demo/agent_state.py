#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 状态定义
定义 LangGraph 工作流中使用的状态结构
"""

from typing import TypedDict


class State(TypedDict):
    """Agent 状态定义

    用于 LangGraph 工作流中节点间传递的数据结构
    """
    user_input: str  # 用户输入
    bill_code: str  # 提取的账单代码
    query_type: str  # 查询类型: "bill_info" 或 "operate_log"
    mcp_result: str  # MCP 调用结果
    final_answer: str  # 最终答案