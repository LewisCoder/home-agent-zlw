"""
带RAG功能的简单智能助手 (使用DashScope Embeddings)

功能: 从本地文档检索 → 搜索网络 → 生成回答
"""

import os
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langgraph.graph import StateGraph, START, END
from tavily import TavilyClient

# 配置API
os.environ["LLM_API_KEY"] = "sk-58cf0319fa5747aeb8e0a196afa5b3c5"
os.environ["LLM_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ["LLM_MODEL_ID"] = "qwen3.5-flash"
os.environ["TAVILY_API_KEY"] = "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"
os.environ["DASHSCOPE_API_KEY"] = os.environ["LLM_API_KEY"]  # DashScope用这个

# 初始化
llm = ChatOpenAI(
    model=os.environ["LLM_MODEL_ID"],
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"]
)

# 使用阿里云专用的Embeddings
embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=os.environ["LLM_API_KEY"]
)

search = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# 准备本地知识库
documents = [
    "贝壳员工出差的补贴标准是500元每人每天,包含住宿和餐饮费用。",
    "应届生入职贝壳时，公司会提供2500元的入职住房补贴，随下月工资一起发放，连续发放12个月，总计30000元。"
]

# 创建向量数据库
print("📦 正在创建向量数据库...")
splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=20)
texts = splitter.create_documents(documents)
vectorstore = FAISS.from_documents(texts, embeddings)
print("✅ 向量数据库创建完成!\n")

# 定义状态
class State(TypedDict):
    question: str       # 用户问题
    local_docs: str     # 本地文档
    web_result: str     # 网络搜索
    answer: str         # 最终答案

# 节点1: 检索本地文档
def retrieve_local(state: State) -> State:
    """从向量数据库检索"""
    docs = vectorstore.similarity_search(state["question"], k=2)
    state["local_docs"] = "\n".join([d.page_content for d in docs])
    print(f"📚 检索到的本地文档: {docs}")
    return state

# 节点2: 搜索网络
def search_web(state: State) -> State:
    """搜索网络信息"""
    result = search.search(query=state["question"], max_results=2)
    content = ""
    for item in result.get("results", [])[:2]:
        content += f"{item.get('content', '')}\n"
    state["web_result"] = content
    print(f"🌐 网络结果: {result.get('results', [])}")
    return state

# 节点3: 生成答案
def generate(state: State) -> State:
    """综合本地和网络信息回答"""
    prompt = f"""问题: {state['question']}

本地知识:
{state['local_docs']}

网络信息:
{state['web_result']}

请综合以上信息简洁回答"""

    print("\n💡 回答生成中: ", end="", flush=True)
    full_answer = ""
    for chunk in llm.stream([SystemMessage(content=prompt)]):
        print(chunk.content, end="", flush=True)
        full_answer += chunk.content
    print("\n")

    state["answer"] = full_answer
    return state

# 构建工作流
workflow = StateGraph(State)
workflow.add_node("retrieve", retrieve_local)
workflow.add_node("search", search_web)
workflow.add_node("generate", generate)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "search")
workflow.add_edge("search", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()

# 运行
if __name__ == "__main__":
    print("🤖 带RAG的智能助手已启动!\n")

    question = input("请输入问题: ")

    app.invoke({
        "question": question,
        "local_docs": "",
        "web_result": "",
        "answer": ""
    })

