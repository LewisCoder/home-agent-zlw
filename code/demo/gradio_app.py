# -*- coding: utf-8 -*-
"""
RAG智能助手 Gradio Web界面 - 美化版
功能: RAG + 记忆 + 多工具调用 + 条件路由
支持外网访问
"""

import json
import os
import re
import sys

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
import gradio as gr

# 配置API
os.environ["LLM_API_KEY"] = "sk-58cf0319fa5747aeb8e0a196afa5b3c5"
os.environ["LLM_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ["LLM_MODEL_ID"] = "qwen3.5-flash"
os.environ["TAVILY_API_KEY"] = "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"

# 初始化
print("🚀 正在初始化智能助手...")
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
print(f"✅ 已加载 {len(texts)} 个文本块到向量数据库")

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

def calculator_func(expression: str) -> str:
    result = eval(expression)
    return f"计算结果: {result}"

def get_time_func() -> str:
    now = datetime.datetime.now()
    return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"

def string_length_func(text: str) -> str:
    return f"字符串长度: {len(text)}"

TOOLS = {
    "calculator": Tool("计算器", "计算数学表达式", calculator_func),
    "get_time": Tool("时间查询", "获取当前时间", get_time_func),
    "string_length": Tool("字符串长度", "计算字符串长度", string_length_func)
}

# 定义状态
class State(TypedDict):
    messages: list
    intent: str
    local_docs: str
    web_result: str
    tool_result: str

# 节点定义
def understand_intent(state: State) -> State:
    question = state["messages"][-1].content
    print("🧠 正在理解用户意图...")

    intent_prompt = f"""分析用户问题的真实意图,并以JSON格式返回:

用户问题: {question}

可用资源:
1. 本地知识库: 包含公司政策、规章制度、员工手册、福利待遇、出差补贴、住房补贴等内部文档
2. 网络搜索: 实时信息,如天气、新闻、最新动态等
3. 工具调用:
   - calculator: 计算数学表达式 (如: 123+456)
   - get_time: 获取当前时间 (如: 现在几点、今天日期)
   - string_length: 计算字符串长度

请分析:
1. 需要查询本地知识库吗? (knowledge: true/false)
   - 如果问题涉及公司政策、规定、福利、补贴、制度等内部信息,设为 true
   - 如果问题是关于贝壳、公司相关的政策文档,设为 true
2. 需要搜索网络吗? (web: true/false)
   - 如果需要实时信息、新闻、天气等外部信息,设为 true
3. 需要调用工具吗? 哪些工具? (tools: [])
4. 问题类型: (type: "知识库查询"/"网络查询"/"计算"/"时间查询"/"闲聊"/等)
5. 核心意图简述: (summary: "...")

重要: 只返回纯JSON,不要有任何额外文字或markdown标记!
格式如下:
{{
  "knowledge": true,
  "web": false,
  "tools": [],
  "type": "知识库查询",
  "summary": "用户想了解公司的住房补贴政策"
}}"""

    response = llm.invoke([SystemMessage(content=intent_prompt)])
    intent_text = response.content.strip()

    if "" in intent_text:
        intent_text = intent_text.replace("", "").replace("", "").strip()

    if '{' in intent_text and '}' in intent_text:
        start = intent_text.find('{')
        end = intent_text.rfind('}') + 1
        intent_text = intent_text[start:end]

    state["intent"] = intent_text
    return state

def retrieve_local(state: State) -> State:
    question = state["messages"][-1].content
    print("📚 正在检索本地知识库...")

    docs_with_scores = vectorstore.similarity_search_with_score(question, k=3)
    filtered_docs = [doc for doc, score in docs_with_scores if score < 1][:2]

    if filtered_docs:
        state["local_docs"] = "\n\n---\n\n".join([doc.page_content for doc in filtered_docs])
        print(f"   ✓ 找到 {len(filtered_docs)} 个相关文档块")
    else:
        state["local_docs"] = ""
        print("   ✗ 未找到相关文档")

    return state

def search_web(state: State) -> State:
    question = state["messages"][-1].content
    print("🔍 正在搜索网络...")
    result = search.search(query=question, max_results=2)
    content = "\n".join([item.get('content', '') for item in result.get("results", [])[:2]])
    state["web_result"] = content
    return state

def check_tool(state: State) -> State:
    question = state["messages"][-1].content
    tool_results = []

    if any(op in question for op in ['+', '-', '*', '/', '计算', '等于']):
        print("🔧 调用工具: 计算器")
        match = re.search(r'(\d+[\+\-\*/]\d+)', question)
        if match:
            result = TOOLS["calculator"].run(match.group(1))
            tool_results.append(result)

    if any(kw in question for kw in ['时间', '几点', '日期', '今天']):
        print("🔧 调用工具: 时间查询")
        result = TOOLS["get_time"].run()
        tool_results.append(result)

    if any(kw in question for kw in ['长度', '多少字', '字符数']):
        print("🔧 调用工具: 字符串长度")
        match = re.search(r'[\'"](.+?)[\'"]', question)
        if match:
            result = TOOLS["string_length"].run(match.group(1))
            tool_results.append(result)

    state["tool_result"] = "\n".join(tool_results) if tool_results else ""
    return state

def generate(state: State) -> State:
    history_text = ""
    if len(state["messages"]) > 1:
        history_text = "\n【对话历史】\n"
        for msg in state["messages"][:-1]:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            history_text += f"{role}: {msg.content}\n"

    question = state["messages"][-1].content

    prompt = f"""你是一个专业、友好的智能助手。请基于以下信息回答用户问题:

{history_text}

📝 **当前问题:** {question}

📚 **知识库信息:**
{state['local_docs'] if state['local_docs'] else '(无相关知识库内容)'}

🌐 **网络信息:**
{state['web_result'] if state['web_result'] else '(无网络搜索结果)'}

🔧 **工具执行结果:**
{state['tool_result'] if state['tool_result'] else '(未调用工具)'}

---

💡 **回答指南:**
1. **优先级:** 工具结果 > 知识库 > 网络信息 > 通用知识
2. **准确性:** 基于提供的信息作答,不确定时明确说明
3. **简洁性:** 直接回答核心问题,避免冗余
4. **专业性:** 使用准确术语,逻辑清晰
5. **友好性:** 语气亲切自然,必要时使用emoji增强表达
6. **上下文:** 如有对话历史,保持话题连贯性

请现在回答用户的问题:"""

    print("💡 正在生成回答...")
    full_answer = ""
    for chunk in llm.stream([SystemMessage(content=prompt)]):
        full_answer += chunk.content

    state["messages"].append(AIMessage(content=full_answer))
    # 将流式内容存储到状态中,供后续使用
    state["streaming_answer"] = full_answer
    return state

# 路由函数
def route_after_understand(state: State) -> Literal["retrieve", "search", "tool", "generate"]:
    try:
        intent_json = json.loads(state["intent"])
        if intent_json.get("knowledge", False):
            return "retrieve"
        elif intent_json.get("web", False):
            return "search"
        elif intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            return "tool"
        else:
            return "generate"
    except:
        return "retrieve"

def route_after_retrieve(state: State) -> Literal["search", "tool", "generate"]:
    try:
        intent_json = json.loads(state["intent"])
        if intent_json.get("web", False):
            return "search"
        elif intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            return "tool"
        else:
            return "generate"
    except:
        return "generate"

def route_after_search(state: State) -> Literal["tool", "generate"]:
    try:
        intent_json = json.loads(state["intent"])
        if intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            return "tool"
        else:
            return "generate"
    except:
        return "generate"

# 构建工作流
workflow = StateGraph(State)
workflow.add_node("understand", understand_intent)
workflow.add_node("retrieve", retrieve_local)
workflow.add_node("search", search_web)
workflow.add_node("tool", check_tool)
workflow.add_node("generate", generate)

workflow.add_edge(START, "understand")
workflow.add_conditional_edges("understand", route_after_understand,
    {"retrieve": "retrieve", "search": "search", "tool": "tool", "generate": "generate"})
workflow.add_conditional_edges("retrieve", route_after_retrieve,
    {"search": "search", "tool": "tool", "generate": "generate"})
workflow.add_conditional_edges("search", route_after_search,
    {"tool": "tool", "generate": "generate"})
workflow.add_edge("tool", "generate")
workflow.add_edge("generate", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

print("✅ 工作流编译完成\n")

# ========== Gradio 界面 ==========

def chat(message, history):
    """处理聊天消息 - 流式输出"""
    if not message.strip():
        yield ""
        return

    thread_id = "gradio_session"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        current_state = app.get_state(config)
        existing_messages = current_state.values.get("messages", []) if current_state.values else []

        # 构建带执行过程的响应
        process_info = "🔄 **执行过程:**\n\n"

        # 先收集所有执行步骤
        for event in app.stream({
            "messages": existing_messages + [HumanMessage(content=message)],
            "intent": "",
            "local_docs": "",
            "web_result": "",
            "tool_result": ""
        }, config):

            # 获取当前执行的节点名称
            for node_name, node_state in event.items():
                if node_name == "understand":
                    process_info += "✅ **步骤 1:** 🧠 理解用户意图\n"
                    if "intent" in node_state and node_state["intent"]:
                        try:
                            intent_data = json.loads(node_state["intent"])
                            process_info += f"   - 问题类型: `{intent_data.get('type', '未知')}`\n"
                            process_info += f"   - 意图: {intent_data.get('summary', '分析中...')}\n"
                            if intent_data.get('knowledge'):
                                process_info += f"   - 需要查询知识库: ✓\n"
                            if intent_data.get('web'):
                                process_info += f"   - 需要网络搜索: ✓\n"
                            if intent_data.get('tools'):
                                process_info += f"   - 需要调用工具: {', '.join(intent_data.get('tools', []))}\n"
                        except:
                            pass
                    process_info += "\n"
                    # 实时输出执行过程
                    yield process_info

                elif node_name == "retrieve":
                    step_info = "✅ **步骤 2:** 📚 检索本地知识库\n"
                    if "local_docs" in node_state and node_state["local_docs"]:
                        doc_preview = node_state["local_docs"][:100] + "..." if len(node_state["local_docs"]) > 100 else node_state["local_docs"]
                        step_info += f"   - 找到相关文档: {len(node_state['local_docs'].split('---'))} 个文档块\n"
                        step_info += f"   - 内容预览: {doc_preview}\n"
                    else:
                        step_info += "   - 未找到相关文档\n"
                    step_info += "\n"
                    process_info += step_info
                    yield process_info

                elif node_name == "search":
                    step_info = "✅ **步骤 3:** 🔍 搜索网络信息\n"
                    if "web_result" in node_state and node_state["web_result"]:
                        web_preview = node_state["web_result"][:100] + "..." if len(node_state["web_result"]) > 100 else node_state["web_result"]
                        step_info += f"   - 获取网络信息成功\n"
                        step_info += f"   - 内容预览: {web_preview}\n"
                    else:
                        step_info += "   - 未获取到网络信息\n"
                    step_info += "\n"
                    process_info += step_info
                    yield process_info

                elif node_name == "tool":
                    step_info = "✅ **步骤 4:** 🔧 调用工具\n"
                    if "tool_result" in node_state and node_state["tool_result"]:
                        step_info += f"   - 工具执行结果: {node_state['tool_result']}\n"
                    else:
                        step_info += "   - 未执行任何工具\n"
                    step_info += "\n"
                    process_info += step_info
                    yield process_info

                elif node_name == "generate":
                    step_info = "✅ **步骤 5:** 💡 生成最终回答\n\n---\n\n**🤖 回答:**\n\n"
                    process_info += step_info
                    yield process_info

                    # 流式输出最终答案 - 按词组输出
                    if "messages" in node_state and len(node_state["messages"]) > 0:
                        final_answer = node_state["messages"][-1].content

                        # 按字符分组输出,每次输出2-5个字符
                        import time
                        accumulated_answer = ""
                        i = 0
                        while i < len(final_answer):
                            # 每次输出2-5个字符,模拟自然打字速度
                            chunk_size = 3 if i % 2 == 0 else 2
                            accumulated_answer += final_answer[i:i+chunk_size]
                            yield process_info + accumulated_answer
                            i += chunk_size
                            # 添加微小延迟,让流式效果更自然
                            time.sleep(0.02)

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        yield f"抱歉,处理您的请求时出现错误: {str(e)}"

# 自定义CSS样式
custom_css = """
/* 全局样式 - 占屏幕80% */
.gradio-container {
    max-width: 80vw !important;
    width: 80vw !important;
    margin: auto !important;
    font-family: 'Arial', 'Microsoft YaHei', sans-serif !important;
}

/* 主内容区域宽度优化 */
.contain {
    max-width: 100% !important;
    width: 100% !important;
}

/* 聊天界面容器宽度 */
.chatbot-container {
    width: 100% !important;
    max-width: 100% !important;
}

/* Blocks容器 */
.gradio-blocks {
    width: 100% !important;
}

/* 标题样式 */
.main-header {
    text-align: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1.2rem;
    border-radius: 12px;
    margin-bottom: 1rem;
    box-shadow: 0 8px 20px rgba(0,0,0,0.1);
}

.main-header h1 {
    margin: 0;
    font-size: 2rem;
    font-weight: bold;
}

.main-header p {
    margin: 0.3rem 0 0 0;
    font-size: 0.95rem;
    opacity: 0.9;
}

/* 功能卡片 */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.8rem;
    margin: 1rem 0;
}

.feature-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 0.8rem;
    border-radius: 10px;
    text-align: center;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.feature-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.feature-icon {
    font-size: 1.8rem;
    margin-bottom: 0.3rem;
}

.feature-title {
    font-weight: bold;
    font-size: 0.9rem;
    margin-bottom: 0.2rem;
    color: #333;
}

.feature-desc {
    font-size: 0.75rem;
    color: #666;
    line-height: 1.3;
}

/* 聊天界面美化 */
.chatbot {
    border-radius: 15px !important;
    box-shadow: 0 8px 20px rgba(0,0,0,0.1) !important;
    min-height: 600px !important;
    height: 600px !important;
    width: 100% !important;
}

/* 聊天消息容器 */
.message-wrap {
    width: 100% !important;
}

/* 聊天输入区域 */
.input-wrap {
    width: 100% !important;
    max-width: 100% !important;
}

/* 示例按钮美化 */
.examples {
    margin-top: 1rem;
}

.examples button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 20px !important;
    padding: 0.8rem 1.5rem !important;
    margin: 0.3rem !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
}

.examples button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
}

/* 输入框美化 */
.input-box {
    border-radius: 25px !important;
    border: 2px solid #667eea !important;
    padding: 1rem !important;
}

/* 发送按钮美化 */
.send-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border-radius: 50% !important;
    width: 50px !important;
    height: 50px !important;
}

/* 页脚样式 */
.footer {
    text-align: center;
    margin-top: 2rem;
    padding: 1.5rem;
    background: #f8f9fa;
    border-radius: 10px;
    color: #666;
}

.footer-badge {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 0.3rem 0.8rem;
    border-radius: 15px;
    margin: 0.2rem;
    font-size: 0.85rem;
}

/* 响应式设计 - PC端占80%宽度 */
@media (min-width: 768px) {
    .gradio-container {
        max-width: 80vw !important;
        width: 80vw !important;
    }
    
    .chatbot {
        width: 100% !important;
    }
}

/* 移动端适配 */
@media (max-width: 767px) {
    .gradio-container {
        max-width: 95vw !important;
        width: 95vw !important;
        padding: 0.5rem !important;
    }
    
    .main-header h1 {
        font-size: 1.5rem;
    }
    
    .feature-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
"""

# 创建美化的 Gradio 界面
with gr.Blocks(title="🤖 RAG智能助手") as demo:

    # 顶部标题区域
    gr.HTML("""
    <div class="main-header">
        <h1>🤖 RAG 智能助手</h1>
        <p>基于 LangGraph 的企业级智能对话系统</p>
    </div>
    """)

    # 功能特性展示
    gr.HTML("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">📚</div>
            <div class="feature-title">知识库检索</div>
            <div class="feature-desc">FAISS向量检索<br/>精准匹配文档</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🔍</div>
            <div class="feature-title">网络搜索</div>
            <div class="feature-desc">Tavily实时搜索<br/>获取最新信息</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🔧</div>
            <div class="feature-title">工具调用</div>
            <div class="feature-desc">计算器·时间查询<br/>字符串处理</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <div class="feature-title">智能路由</div>
            <div class="feature-desc">意图理解<br/>条件执行</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">💾</div>
            <div class="feature-title">对话记忆</div>
            <div class="feature-desc">多轮对话<br/>上下文保持</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">高效优化</div>
            <div class="feature-desc">Token优化<br/>快速响应</div>
        </div>
    </div>
    """)

    # 聊天界面
    gr.Markdown("### 💬 开始对话")

    chatbot = gr.ChatInterface(
        fn=chat,
        examples=[
            ["介绍下贝壳的年假制度"],
            ["贝壳员工出差有补贴吗？"],
            ["33*88等于多少?"],
            ["北京今天天气怎么样?"]
        ],
    )

    # 使用说明
    with gr.Accordion("📖 使用说明", open=False):
        gr.Markdown("""
        ### 功能介绍
        
        **1. 📚 知识库查询**
        - 提问关于公司政策、规定、文档内容的问题
        - 示例: "出差补贴标准是什么?"
        
        **2. 🔍 网络搜索**
        - 查询实时信息,如天气、新闻等
        - 示例: "北京今天天气怎么样?"
        
        **3. 🔧 工具调用**
        - **计算器**: 数学计算,如 "123+456等于多少?"
        - **时间查询**: 获取当前时间,如 "现在几点了?"
        - **字符串处理**: 计算长度,如 "'hello'有多少字?"
        
        **4. 💬 闲聊对话**
        - 日常对话,如 "你好"、"谢谢"
        
        ### 技术特点
        - ✅ 智能意图理解,自动选择执行路径
        - ✅ 条件路由优化,跳过不必要的节点
        - ✅ 多轮对话记忆,保持上下文连贯
        - ✅ 相似度过滤,减少token消耗
        """)

# 启动服务
if __name__ == "__main__":
    print("🌐 正在启动 Gradio 服务...")
    print("=" * 60)

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
        css=custom_css
    )











