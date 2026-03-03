"""
带工具调用的RAG智能助手 - 最简单版本
功能: RAG + 记忆 + 工具调用(计算器)
"""

import os
import re
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import Docx2txtLoader
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
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
embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=os.environ["LLM_API_KEY"]
)
search = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# 加载知识库
print("📦 正在从Word文档加载知识库...")
loader = Docx2txtLoader("knowledge.docx")
documents = loader.load()
splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
texts = splitter.split_documents(documents)
vectorstore = FAISS.from_documents(texts, embeddings)
print(f"✅ 已加载 {len(texts)} 个文本块到向量数据库\n")

# ========== 工具定义 ==========
def calculator(expression: str) -> str:
    """计算器工具: 计算数学表达式"""
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {e}"

# 定义状态
class State(TypedDict):
    messages: list
    local_docs: str
    web_result: str
    tool_result: str  # 新增: 工具调用结果

# 节点1: 检索本地文档 (带相似度过滤)
def retrieve_local(state: State) -> State:
    question = state["messages"][-1].content
    print("📚 正在检索本地知识库...")

    # 检索时带上相似度分数
    docs_with_scores = vectorstore.similarity_search_with_score(question, k=5)

    # 过滤相似度低的文档 (分数越小越相似,通常0-2之间)
    filtered_docs = [
        doc for doc, score in docs_with_scores
        if score < 1.0  # 只保留相似度高的
    ][:2]  # 最多保留2个

    if filtered_docs:
        state["local_docs"] = "\n\n---\n\n".join([d.page_content for d in filtered_docs])
        print(f"   ✓ 找到 {len(filtered_docs)} 个相关文档块")
    else:
        state["local_docs"] = ""
        print("   ✗ 未找到相关文档")

    return state

# 节点2: 搜索网络
def search_web(state: State) -> State:
    question = state["messages"][-1].content
    print("🔍 正在搜索网络...")
    result = search.search(query=question, max_results=2)
    content = "\n".join([item.get('content', '') for item in result.get("results", [])[:2]])
    state["web_result"] = content
    return state

# 节点3: 工具调用判断
def check_tool(state: State) -> State:
    """判断是否需要调用工具"""
    question = state["messages"][-1].content

    # 简单规则: 如果包含数学运算,调用计算器
    if any(op in question for op in ['+', '-', '*', '/', '计算', '等于']):
        print("🔧 检测到计算需求,调用计算器...")
        # 提取数学表达式
        match = re.search(r'(\d+[\+\-\*/]\d+)', question)
        if match:
            expr = match.group(1)
            state["tool_result"] = calculator(expr)
        else:
            state["tool_result"] = "未找到有效的数学表达式"
    else:
        state["tool_result"] = ""

    return state

# 节点4: 生成答案
def generate(state: State) -> State:
    # 获取历史对话
    history_text = ""
    if len(state["messages"]) > 1:
        history_text = "\n【对话历史】\n"
        for msg in state["messages"][:-1]:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            history_text += f"{role}: {msg.content}\n"

    question = state["messages"][-1].content

    # 构建prompt
    prompt = f"""请基于以下信息回答问题:

{history_text}

当前问题: {question}

【本地知识库】
{state['local_docs']}

【网络补充信息】
{state['web_result']}

【工具调用结果】
{state['tool_result']}

回答要求:
1. 如果有工具调用结果,优先使用工具结果回答
2. 结合对话历史回答用户问题
3. 回答要专业简洁、准确
"""

    print("💡 回答: ", end="", flush=True)
    full_answer = ""
    for chunk in llm.stream([SystemMessage(content=prompt)]):
        print(chunk.content, end="", flush=True)
        full_answer += chunk.content

    state["messages"].append(AIMessage(content=full_answer))
    return state

# 构建工作流
workflow = StateGraph(State)
workflow.add_node("retrieve", retrieve_local)
workflow.add_node("search", search_web)
workflow.add_node("tool", check_tool)  # 新增工具节点
workflow.add_node("generate", generate)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "search")
workflow.add_edge("search", "tool")  # 先调用工具
workflow.add_edge("tool", "generate")
workflow.add_edge("generate", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 主循环
if __name__ == "__main__":
    print("🤖 智能助手已启动! (支持工具调用)")
    print("💡 试试问: '123+456等于多少?'\n")

    config = {"configurable": {"thread_id": "default"}}

    while True:
        question = input("\n👤 您: ").strip()

        if question in ['退出', 'quit', 'exit', 'q']:
            print("👋 再见!")
            break

        if not question:
            continue

        # 获取历史
        current_state = app.get_state(config)
        existing_messages = current_state.values.get("messages", []) if current_state.values else []

        # 调用工作流
        result = app.invoke({
            "messages": existing_messages + [HumanMessage(content=question)],
            "local_docs": "",
            "web_result": "",
            "tool_result": ""
        }, config)

        print()


