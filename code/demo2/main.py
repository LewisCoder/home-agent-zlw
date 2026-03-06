"""
RAG智能助手主程序
功能: RAG + 记忆 + 多工具调用 + 条件路由
"""

import traceback
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from config import config
from nodes import State, understand_intent, retrieve_local, search_web, check_tool, generate
from router import route_after_understand, route_after_retrieve, route_after_search
from tools import TOOLS


def build_workflow():
    """构建工作流"""
    workflow = StateGraph(State)

    # 添加节点
    workflow.add_node("understand", understand_intent)
    workflow.add_node("retrieve", retrieve_local)
    workflow.add_node("search", search_web)
    workflow.add_node("tool", check_tool)
    workflow.add_node("generate", generate)

    # 添加边
    workflow.add_edge(START, "understand")

    # 从 understand 节点根据意图路由
    workflow.add_conditional_edges(
        "understand",
        route_after_understand,
        {
            "retrieve": "retrieve",
            "search": "search",
            "tool": "tool",
            "generate": "generate"
        }
    )

    # 从 retrieve 节点路由
    workflow.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "search": "search",
            "tool": "tool",
            "generate": "generate"
        }
    )

    # 从 search 节点路由
    workflow.add_conditional_edges(
        "search",
        route_after_search,
        {
            "tool": "tool",
            "generate": "generate"
        }
    )

    # tool 节点后直接生成答案
    workflow.add_edge("tool", "generate")
    workflow.add_edge("generate", END)

    # 编译工作流
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def print_welcome():
    """打印欢迎信息"""
    print("🤖 智能助手已启动! (支持多工具调用 + 条件路由)")
    print("📋 可用工具:")
    for tool_id, tool in TOOLS.items():
        print(f"   - {tool.name}: {tool.description}")
    print("\n💡 试试问:")
    print("   - '123+456等于多少?' (只执行tool节点)")
    print("   - '出差补贴是多少?' (只执行retrieve节点)")
    print("   - '现在几点了?' (只执行tool节点)")
    print("   - '你好' (直接生成回答)\n")


def main():
    """主函数"""
    # 初始化配置和服务
    config.initialize_services()

    # 构建工作流
    app = build_workflow()

    # 打印欢迎信息
    print_welcome()

    # 会话配置
    session_config = {"configurable": {"thread_id": "default"}}

    # 主循环
    while True:
        try:
            question = input("\n👤 您: ").strip()

            # 退出命令
            if question in ['退出', 'quit', 'exit', 'q']:
                print("👋 再见!")
                break

            # 空输入跳过
            if not question:
                continue

            # 获取历史消息
            current_state = app.get_state(session_config)
            existing_messages = current_state.values.get("messages", []) if current_state.values else []

            # 调用工作流
            result = app.invoke({
                "messages": existing_messages + [HumanMessage(content=question)],
                "intent": "",
                "local_docs": "",
                "web_result": "",
                "tool_result": ""
            }, session_config)

            print()

        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 执行出错: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
