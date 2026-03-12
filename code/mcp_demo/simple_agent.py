#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的账单查询 Agent（优化版）
使用 LangGraph 的 ToolNode 和 tools_condition 实现自动化工具调用
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage
from agent_state import State
from agent_nodes import AgentNodes
from mcp_tools import mcp_tools, get_mcp_wrapper


def build_workflow():
    """构建 LangGraph 工作流"""
    # 初始化节点类
    nodes = AgentNodes()

    # 创建工作流
    workflow = StateGraph(State)

    # 添加节点
    # 1. agent 节点：调用 LLM，决定是否使用工具
    workflow.add_node("agent", nodes.call_model)

    # 2. tools 节点：自动执行工具调用
    workflow.add_node("tools", ToolNode(mcp_tools))

    # 添加边
    # 从 START 到 agent
    workflow.add_edge(START, "agent")

    # 从 agent 使用条件边：
    # - 如果 LLM 返回了 tool_calls，则路由到 tools 节点
    # - 否则，路由到 END
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
    )

    # 从 tools 回到 agent（形成循环，直到 LLM 不再调用工具）
    workflow.add_edge("tools", "agent")

    # 编译工作流
    return workflow.compile(), nodes


def main():
    """主函数"""
    print("=" * 70)
    print("🤖 账单查询智能助手（优化版 - 使用 ToolNode）")
    print("=" * 70)
    print("\n💡 使用说明:")
    print("   - 查询账单信息: GBILL260202111424630037")
    print("   - 查询操作记录: 查询账单 GBILL260202111424630037 的操作记录")
    print("   - 输入 'quit' 或 'exit' 退出\n")

    # 构建工作流
    app, nodes = build_workflow()

    # 获取 MCP 工具包装器
    mcp_wrapper = get_mcp_wrapper()

    try:
        while True:
            # 获取用户输入
            user_input = input("👤 请输入账单代码或问题: ").strip()

            # 退出命令
            if user_input.lower() in ['quit', 'exit', 'q', '退出']:
                print("\n👋 再见!")
                break

            # 空输入跳过
            if not user_input:
                continue

            print("\n" + "=" * 70)

            # 调用工作流
            result = app.invoke({
                "messages": [HumanMessage(content=user_input)]
            })

            # 输出最终答案
            print("\n" + "=" * 70)
            print("🤖 助手回答:")
            print("=" * 70)

            # 获取最后一条消息（AI 的回复）
            final_message = result["messages"][-1]
            print(final_message.content)
            print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n👋 再见!")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        mcp_wrapper.cleanup()


if __name__ == "__main__":
    main()

