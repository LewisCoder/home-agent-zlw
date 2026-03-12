#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账单查询 Agent（优化版）
使用 LangGraph 的 ToolNode 和 tools_condition 实现自动化工具调用
使用 MemorySaver checkpointer 实现多轮对话记忆
使用滑动窗口截断历史消息，控制 token 消耗
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from agent_state import State, MAX_HISTORY_TURNS
from agent_nodes import AgentNodes
from mcp_tools import mcp_tools, get_mcp_wrapper


def build_workflow():
    """构建 LangGraph 工作流"""
    nodes = AgentNodes()

    workflow = StateGraph(State)

    # agent 节点：调用 LLM，决定是否使用工具
    workflow.add_node("agent", nodes.call_model)

    # tools 节点：自动执行工具调用
    workflow.add_node("tools", ToolNode(mcp_tools))

    workflow.add_edge(START, "agent")

    # 条件边：有 tool_calls 则去 tools，否则结束
    workflow.add_conditional_edges("agent", tools_condition)

    # 工具执行完毕后回到 agent，继续推理
    workflow.add_edge("tools", "agent")

    # 启用 MemorySaver：跨轮次保存消息历史
    # 配合 agent_nodes.py 中的 _trim_messages 控制 token 消耗
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory), nodes


def main():
    """主函数"""
    print("=" * 70)
    print("🤖 账单查询智能助手")
    print("=" * 70)
    print(f"\n💡 使用说明:")
    print(f"   - 查询账单信息: GBILL260202111424630037")
    print(f"   - 查询操作记录: 查询账单 GBILL260202111424630037 的操作记录")
    print(f"   - 查询知识库: 出差补贴标准是什么")
    print(f"   - 输入 'new' 开启新会话（清空历史）")
    print(f"   - 输入 'quit' 或 'exit' 退出")
    print(f"\n⚙️  当前配置: 保留最近 {MAX_HISTORY_TURNS} 轮对话历史\n")

    app, nodes = build_workflow()
    mcp_wrapper = get_mcp_wrapper()

    # thread_id 标识会话，相同 thread_id 共享消息历史
    thread_id = "session_1"
    config = {"configurable": {"thread_id": thread_id}}
    turn = 0

    try:
        while True:
            user_input = input("👤 请输入问题: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q', '退出']:
                print("\n👋 再见!")
                break

            if not user_input:
                continue

            # 开启新会话：换一个 thread_id 即可清空历史
            if user_input.lower() in ['new', '新会话', '清空']:
                turn = 0
                thread_id = f"session_{id(user_input)}"
                config = {"configurable": {"thread_id": thread_id}}
                print("🔄 已开启新会话，历史已清空\n")
                continue

            turn += 1
            print(f"\n{'=' * 70}")
            print(f"[第 {turn} 轮对话]")

            # checkpointer 会自动加载该 thread_id 的历史消息
            # 只需传入本轮新消息即可
            result = app.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config
            )

            print(f"\n{'=' * 70}")
            print("🤖 助手回答:")
            print("=" * 70)
            print(result["messages"][-1].content)
            print("=" * 70)

            # 打印当前历史消息数，方便观察 token 消耗
            total_msgs = len(result["messages"])
            print(f"📊 当前会话消息总数: {total_msgs} 条\n")

    except KeyboardInterrupt:
        print("\n\n👋 再见!")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mcp_wrapper.cleanup()


if __name__ == "__main__":
    main()

