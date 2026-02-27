"""
最简单的LangGraph智能助手 - 适合小白学习

功能: 理解问题 → 搜索信息 → 生成回答
"""

import os
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from tavily import TavilyClient

# 配置API
os.environ["LLM_API_KEY"] = "sk-58cf0319fa5747aeb8e0a196afa5b3c5"
os.environ["LLM_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ["LLM_MODEL_ID"] = "qwen3.5-flash"
os.environ["TAVILY_API_KEY"] = "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"

# 初始化
llm = ChatOpenAI(
    model=os.environ["LLM_MODEL_ID"],
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"]
)
search = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# 定义状态
class State(TypedDict):
    question: str      # 用户问题
    search_query: str  # 搜索词
    search_result: str # 搜索结果
    answer: str        # 最终答案

# 节点1: 理解问题
def understand(state: State) -> State:
    """提取搜索关键词"""
    prompt = f"从这个问题中提取搜索关键词: {state['question']}\n只返回关键词,不要其他内容"
    response = llm.invoke([SystemMessage(content=prompt)])
    state["search_query"] = response.content
    print(f"🔍 搜索词: {state['search_query']}")
    return state

# 节点2: 搜索信息
def search_info(state: State) -> State:
    """搜索相关信息"""
    result = search.search(query=state["search_query"], max_results=2)
    # 提取搜索结果
    content = ""
    for item in result.get("results", [])[:2]:
        content += f"{item.get('title', '')}\n{item.get('content', '')}\n\n"
    state["search_result"] = content
    print(f"✅ 找到 {len(result.get('results', []))} 条结果")
    return state

# 节点3: 生成答案
def generate_answer(state: State) -> State:
    prompt = f"""
        问题: {state['question']}
        参考信息:{state['search_result']}
        请简洁回答问题
    """
    print(f"{state['question']}\n{state['search_result']}\n正在生成答案...")
    for chunk in llm.stream([SystemMessage(content=prompt)]):
        print(chunk.content, end="", flush=True)
    return state

# 构建工作流
workflow = StateGraph(State)
workflow.add_node("understand", understand)
workflow.add_node("search", search_info)
workflow.add_node("answer", generate_answer)

workflow.add_edge(START, "understand")
workflow.add_edge("understand", "search")
workflow.add_edge("search", "answer")
workflow.add_edge("answer", END)

app = workflow.compile()

# 运行
if __name__ == "__main__":
    print("🤖 智能助手已启动!\n")

    question = input("请输入问题: ")

    result = app.invoke({
        "question": question,
        "search_query": "",
        "search_result": "",
        "answer": ""
    })

