"""
使用LangGraph官方记忆模块的RAG智能助手

功能: 读取Word文档 → 检索 → 搜索网络 → 生成带引用的回答 → 持久化记忆
"""

import os
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

# 从Word文档加载知识库
print("📦 正在从Word文档加载知识库...")
loader = Docx2txtLoader("knowledge.docx")
documents = loader.load()

splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
texts = splitter.split_documents(documents)
vectorstore = FAISS.from_documents(texts, embeddings)
print(f"✅ 已加载 {len(texts)} 个文本块到向量数据库\n")

# 定义状态
class State(TypedDict):
    messages: list  # LangGraph记忆模块使用messages
    local_docs: str
    web_result: str

# 节点1: 检索本地文档
def retrieve_local(state: State) -> State:
    # 获取最新用户消息
    question = state["messages"][-1].content
    print("📚 正在检索本地知识库...")
    docs = vectorstore.similarity_search(question, k=3)
    state["local_docs"] = "\n".join([d.page_content for d in docs])
    return state

# 节点2: 搜索网络
def search_web(state: State) -> State:
    question = state["messages"][-1].content
    print("🔍 正在搜索网络...")
    result = search.search(query=question, max_results=2)
    content = "\n".join([item.get('content', '') for item in result.get("results", [])[:2]])
    state["web_result"] = content
    return state

# 节点3: 生成答案
def generate(state: State) -> State:
    # 获取历史对话
    history_text = ""
    if len(state["messages"]) > 1:
        history_text = "\n【对话历史】\n"
        for msg in state["messages"][:-1]:  # 除了最新的
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            history_text += f"{role}: {msg.content}\n"

    question = state["messages"][-1].content

    prompt = f"""请基于以下信息回答问题:

{history_text}

当前问题: {question}

【本地知识库】
{state['local_docs']}

【网络补充信息】
{state['web_result']}

回答要求:
1. 结合对话历史回答用户问题
2. 优先使用本地知识库的信息,如果是聊天式问题,可以自由发挥
3. 回答要专业简洁、准确，不要回答任何和问题无关的信息
"""

    print("💡 回答: ", end="", flush=True)
    full_answer = ""
    for chunk in llm.stream([SystemMessage(content=prompt)]):
        print(chunk.content, end="", flush=True)
        full_answer += chunk.content

    # 添加AI回复到messages
    state["messages"].append(AIMessage(content=full_answer))
    return state

# 构建工作流(使用MemorySaver)
workflow = StateGraph(State)
workflow.add_node("retrieve", retrieve_local)
workflow.add_node("search", search_web)
workflow.add_node("generate", generate)
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "search")
workflow.add_edge("search", "generate")
workflow.add_edge("generate", END)

# 使用LangGraph官方记忆模块
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 多轮对话主循环
if __name__ == "__main__":
    print("🤖 智能助手已启动! (使用LangGraph记忆模块)")
    print("💾 对话会自动保存\n")

    # 会话ID
    thread_id = "user-session-001"
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        question = input("\n👤 您: ").strip()

        if question in ['退出', 'quit', 'exit', 'q']:
            print("👋 再见! 对话已保存")
            break

        if not question:
            continue

        # 获取历史状态(从 MemorySaver 加载)
        current_state = app.get_state(config)

        # 如果有历史记录,追加新消息;否则创建新的
        if current_state.values:
            existing_messages = current_state.values.get("messages", [])
        else:
            existing_messages = []

        # 调用工作流(自动保存到记忆)
        result = app.invoke({
            "messages": existing_messages + [HumanMessage(content=question)],
            "local_docs": "",
            "web_result": ""
        }, config)

        print()








