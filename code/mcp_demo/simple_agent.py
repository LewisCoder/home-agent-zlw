#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的账单查询 Agent
使用 LangGraph 构建,包含 3 个节点:意图理解、MCP调用、答案生成
"""

from langgraph.graph import StateGraph, START, END
from agent_state import State
from agent_nodes import AgentNodes


def build_workflow():
    """构建 LangGraph 工作流"""
    # 初始化节点类
    nodes = AgentNodes()

    # 创建工作流
    workflow = StateGraph(State)

    # 添加 3 个节点
    workflow.add_node("understand", nodes.understand_intent)
    workflow.add_node("mcp_call", nodes.call_mcp)
    workflow.add_node("generate", nodes.generate_answer)

    # 添加静态边连接
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "mcp_call")
    workflow.add_edge("mcp_call", "generate")
    workflow.add_edge("generate", END)

    # 编译工作流
    return workflow.compile(), nodes


def main():
    """主函数"""
    print("=" * 70)
    print("🤖 账单查询智能助手")
    print("=" * 70)
    print("\n💡 使用说明:")
    print("   - 查询账单信息: GBILL260202111424630037")
    print("   - 查询操作记录: 查询账单 GBILL260202111424630037 的操作记录")
    print("   - 输入 'quit' 或 'exit' 退出\n")

    # 构建工作流
    app, nodes = build_workflow()

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
                "user_input": user_input,
                "bill_code": "",
                "query_type": "",
                "mcp_result": "",
                "final_answer": ""
            })

            # 输出最终答案
            print("\n" + "=" * 70)
            print("🤖 助手回答:")
            print("=" * 70)
            print(result["final_answer"])
            print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n👋 再见!")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        nodes.cleanup()


if __name__ == "__main__":
    main()
