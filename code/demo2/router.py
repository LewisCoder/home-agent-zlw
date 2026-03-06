"""
路由逻辑模块
定义工作流中的条件路由函数
"""

import json
from typing import Literal

from nodes import State


def route_after_understand(state: State) -> Literal["retrieve", "search", "tool", "generate"]:
    """
    根据意图分析决定下一步执行哪个节点
    优先级: knowledge > web > tools > generate
    """
    try:
        intent_json = json.loads(state["intent"])
        print(f"   📍 路由决策: ", end="")

        # 优先级: knowledge > web > tools > generate
        if intent_json.get("knowledge", False):
            print("需要查询本地知识库 → retrieve")
            return "retrieve"
        elif intent_json.get("web", False):
            print("需要搜索网络 → search")
            return "search"
        elif intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            print(f"需要调用工具 {intent_json.get('tools')} → tool")
            return "tool"
        else:
            print("直接生成回答 → generate")
            return "generate"
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        print(f"   原始内容: {state['intent'][:200]}")
        print(f"   默认路由 → retrieve (执行全流程)")
        return "retrieve"
    except Exception as e:
        print(f"❌ 路由异常: {e}")
        print(f"   默认路由 → retrieve")
        return "retrieve"


def route_after_retrieve(state: State) -> Literal["search", "tool", "generate"]:
    """
    检索后决定是否需要搜索网络或调用工具
    """
    try:
        intent_json = json.loads(state["intent"])
        print(f"   📍 路由决策: ", end="")

        if intent_json.get("web", False):
            print("需要搜索网络 → search")
            return "search"
        elif intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            print(f"需要调用工具 → tool")
            return "tool"
        else:
            print("直接生成回答 → generate")
            return "generate"
    except Exception as e:
        print(f"路由失败: {e}")
        return "generate"


def route_after_search(state: State) -> Literal["tool", "generate"]:
    """
    搜索后决定是否需要调用工具
    """
    try:
        intent_json = json.loads(state["intent"])
        print(f"   📍 路由决策: ", end="")

        if intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            print(f"需要调用工具 → tool")
            return "tool"
        else:
            print("直接生成回答 → generate")
            return "generate"
    except Exception as e:
        print(f"路由失败: {e}")
        return "generate"
