"""
RAG智能助手Web界面 - 最快部署方案
功能: Gradio界面 + 内网穿透(ngrok/frpc)
"""
import os
from typing import TypedDict

from gradio import ChatInterface
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_text_splitters import CharacterTextSplitter
from langgraph.graph import StateGraph, START, END
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import Docx2txtLoader

# 配置
os.environ["LLM_API_KEY"] = "sk-58cf0319fa5747aeb8e0a196afa5b3c5"
os.environ["LLM_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ["LLM_MODEL_ID"] = "qwen3.5-flash"

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

# 加载知识库
print("加载知识库...")
loader = Docx2txtLoader("knowledge.docx")
documents = loader.load()
splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
texts = splitter.split_documents(documents)
vectorstore = FAISS.from_documents(texts, embeddings)

# 定义状态
class State(TypedDict):
    messages: list

# 节点
def chat_node(state: State) -> State:
    # 获取历史
    history_text = ""
    if len(state["messages"]) > 1:
        for msg in state["messages"][:-1]:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            history_text += f"{role}: {msg.content}\n"

    question = state["messages"][-1].content

    # 检索
    docs = vectorstore.similarity_search(question, k=3)
    local_docs = "\n".join([d.page_content for d in docs])

    # 构建prompt
    prompt = f"""请基于以下信息回答:

【对话历史】
{history_text}

当前问题: {question}

【知识库】
{local_docs}

要求:简洁准确,结合历史回答"""

    # 生成回答
    response = llm.invoke([SystemMessage(content=prompt)])
    state["messages"].append(AIMessage(content=response.content))
    return state

# 构建工作流(Gradio自带history,不需要checkpointer)
workflow = StateGraph(State)
workflow.add_node("chat", chat_node)
workflow.add_edge(START, "chat")
workflow.add_edge("chat", END)

app = workflow.compile()

def predict(message, history=[]):
    """处理用户消息"""
    # 合并历史(Gradio的history参数已经包含历史)
    all_messages = []
    for h in history:
        if h.get("role") == "user":
            all_messages.append(HumanMessage(content=h["content"]))
        elif h.get("role") == "assistant":
            all_messages.append(AIMessage(content=h["content"]))

    # 添加新消息
    all_messages.append(HumanMessage(content=message))

    # 调用
    result = app.invoke({
        "messages": all_messages,
    })

    return result["messages"][-1].content

# 启动Gradio
print("\n" + "="*50)
print("🚀 启动Web界面...")
print("="*50 + "\n")

demo = ChatInterface(
    fn=predict,
    title="RAG智能助手",
    description="基于LangGraph + RAG的智能助手,支持记忆和多轮对话"
)

# 启动
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=False  # 局域网访问,如需公网用cpolar
)
