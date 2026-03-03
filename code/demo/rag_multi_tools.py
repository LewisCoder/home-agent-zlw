"""
带工具集调用的RAG智能助手
功能: RAG + 记忆 + 多工具调用
"""

import os
import re
import json
from typing import TypedDict, Callable, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import Docx2txtLoader
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from tavily import TavilyClient
import datetime

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

# ========== 工具集定义 ==========
class Tool:
    """工具基类"""
    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func

    def run(self, *args, **kwargs) -> str:
        try:
            return self.func(*args, **kwargs)
        except Exception as e:
            return f"[{self.name}] 执行错误: {e}"

# 工具1: 计算器
def calculator_func(expression: str) -> str:
    result = eval(expression)
    return f"计算结果: {result}"

# 工具2: 获取当前时间
def get_time_func() -> str:
    now = datetime.datetime.now()
    return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"

# 工具3: 字符串长度
def string_length_func(text: str) -> str:
    return f"字符串长度: {len(text)}"

# 注册工具集
TOOLS = {
    "calculator": Tool(
        name="计算器",
        description="计算数学表达式,如: 123+456",
        func=calculator_func
    ),
    "get_time": Tool(
        name="时间查询",
        description="获取当前时间",
        func=get_time_func
    ),
    "string_length": Tool(
        name="字符串长度",
        description="计算字符串的长度",
        func=string_length_func
    )
}

# 定义状态
class State(TypedDict):
    messages: list
    intent: str  # 新增: 用户意图分析
    local_docs: str
    web_result: str
    tool_result: str

# 节点0: 理解用户意图
def understand_intent(state: State) -> State:
    """分析用户真实意图"""
    question = state["messages"][-1].content
    print("🧠 正在理解用户意图...")

    # 构建意图分析prompt
    intent_prompt = f"""分析用户问题的真实意图,并以JSON格式返回:

用户问题: {question}

可用工具:
- calculator: 计算数学表达式 (如: 123+456)
- get_time: 获取当前时间 (如: 现在几点、今天日期)
- string_length: 计算字符串长度

请分析:
1. 需要查询本地知识库吗? (knowledge: true/false) - 如果问题涉及公司规定、政策、文档内容
2. 需要搜索网络吗? (web: true/false) - 如果需要实时信息如天气、新闻
3. 需要调用工具吗? 哪些工具? (tools: []) - 如果需要计算、时间查询、字符串处理
4. 问题类型: (type: "事实查询"/"计算"/"时间查询"/"闲聊"/等)
5. 核心意图简述: (summary: "...")

重要: 只返回纯JSON,不要有任何额外文字或markdown标记!
格式如下:
{{
  "knowledge": false,
  "web": false,
  "tools": ["get_time"],
  "type": "时间查询",
  "summary": "用户想知道当前时间"
}}"""

    response = llm.invoke([SystemMessage(content=intent_prompt)])
    intent_text = response.content

    # 清理返回内容,提取JSON
    intent_text = intent_text.strip()

    # 方法1: 移除markdown代码块标记 (更可靠的方式)
    if "```" in intent_text:
        # 移除所有 ```json 或 ``` 标记
        intent_text = intent_text.replace("```json", "").replace("```", "")
        intent_text = intent_text.strip()

    # 方法2: 强制提取JSON对象 (最可靠)
    if '{' in intent_text and '}' in intent_text:
        start = intent_text.find('{')
        end = intent_text.rfind('}') + 1
        intent_text = intent_text[start:end]

    # 验证JSON格式
    try:
        json.loads(intent_text)  # 测试是否能解析
        print(f"   ✓ 意图JSON解析成功")
    except json.JSONDecodeError as e:
        print(f"   ⚠️  JSON格式异常: {e}")
        print(f"   清理后内容: {intent_text[:200]}")

    # 保存意图分析结果
    state["intent"] = intent_text
    print(f"   意图: {intent_text[:100]}...")

    return state

# 节点1: 检索本地文档
def retrieve_local(state: State) -> State:
    question = state["messages"][-1].content
    print("📚 正在检索本地知识库...")

    # 检索时带上相似度分数
    docs_with_scores = vectorstore.similarity_search_with_score(question, k=5)

    # 过滤相似度低的文档 (分数越小越相似,通常0-2之间)
    filtered_docs = [
        doc for doc, score in docs_with_scores
        if score < 0.5  # 只保留相似度高的
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

# 节点3: 智能工具调用
def check_tool(state: State) -> State:
    """根据问题智能选择并调用工具"""
    question = state["messages"][-1].content
    tool_results = []

    # 规则1: 计算器
    if any(op in question for op in ['+', '-', '*', '/', '计算', '等于']):
        print("🔧 调用工具: 计算器")
        match = re.search(r'(\d+[\+\-\*/]\d+)', question)
        if match:
            expr = match.group(1)
            result = TOOLS["calculator"].run(expr)
            tool_results.append(result)

    # 规则2: 时间查询
    if any(kw in question for kw in ['时间', '几点', '日期', '今天']):
        print("🔧 调用工具: 时间查询")
        result = TOOLS["get_time"].run()
        tool_results.append(result)

    # 规则3: 字符串长度
    if any(kw in question for kw in ['长度', '多少字', '字符数']):
        print("🔧 调用工具: 字符串长度")
        # 提取引号内的文本
        match = re.search(r'[\'"](.+?)[\'"]', question)
        if match:
            text = match.group(1)
            result = TOOLS["string_length"].run(text)
            tool_results.append(result)

    # 合并结果
    state["tool_result"] = "\n".join(tool_results) if tool_results else ""
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
    # 打印提示词以便调试
    print(f"输入大模型的提示词", prompt)
    print("💡 回答: ", end="", flush=True)
    full_answer = ""
    for chunk in llm.stream([SystemMessage(content=prompt)]):
        print(chunk.content, end="", flush=True)
        full_answer += chunk.content

    state["messages"].append(AIMessage(content=full_answer))
    return state

# ========== 条件路由函数 ==========
def route_after_understand(state: State) -> Literal["retrieve", "search", "tool", "generate"]:
    """根据意图分析决定下一步执行哪个节点"""
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
    """检索后决定是否需要搜索网络或调用工具"""
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
    """搜索后决定是否需要调用工具"""
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

# 构建工作流
workflow = StateGraph(State)
workflow.add_node("understand", understand_intent)
workflow.add_node("retrieve", retrieve_local)
workflow.add_node("search", search_web)
workflow.add_node("tool", check_tool)
workflow.add_node("generate", generate)

# 使用条件路由替代静态边
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

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 主循环
if __name__ == "__main__":
    print("🤖 智能助手已启动! (支持多工具调用 + 条件路由)")
    print("📋 可用工具:")
    for tool_id, tool in TOOLS.items():
        print(f"   - {tool.name}: {tool.description}")
    print("\n💡 试试问:")
    print("   - '123+456等于多少?' (只执行tool节点)")
    print("   - '出差补贴是多少?' (只执行retrieve节点)")
    print("   - '现在几点了?' (只执行tool节点)")
    print("   - '你好' (直接生成回答)\n")

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
        try:
            result = app.invoke({
                "messages": existing_messages + [HumanMessage(content=question)],
                "intent": "",
                "local_docs": "",
                "web_result": "",
                "tool_result": ""
            }, config)

            print()
        except Exception as e:
            print(f"\n❌ 执行出错: {e}")
            import traceback
            traceback.print_exc()