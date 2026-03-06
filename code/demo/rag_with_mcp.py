# -*- coding: utf-8 -*-
"""
带 MCP 功能的 RAG 智能助手
功能: RAG + 记忆 + 多工具调用 + MCP 外部服务调用
"""

import os
import re
import json
import subprocess
import sys
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

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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

# ========== MCP 客户端 ==========
class MCPClient:
    """简化的 MCP 客户端 - 通过 stdio 与 MCP 服务器通信"""

    def __init__(self, server_command: list):
        """
        初始化 MCP 客户端

        Args:
            server_command: MCP 服务器启动命令,例如:
                ["node", "path/to/mcp-server.js"]
                ["python", "path/to/mcp_server.py"]
        """
        self.server_command = server_command
        self.process = None
        self.tools = {}

    def connect(self):
        """连接到 MCP 服务器"""
        try:
            print(f"🔌 正在连接 MCP 服务器: {' '.join(self.server_command)}")

            # 启动 MCP 服务器进程
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1
            )

            # 发送初始化请求
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "rag-agent",
                        "version": "1.0.0"
                    }
                }
            }

            self._send_request(init_request)
            response = self._read_response()

            if response and "result" in response:
                print("✅ MCP 服务器连接成功")

                # 获取可用工具列表
                self._list_tools()
                return True
            else:
                print(f"❌ MCP 初始化失败: {response}")
                return False

        except Exception as e:
            print(f"❌ MCP 连接失败: {e}")
            return False

    def _send_request(self, request: dict):
        """发送 JSON-RPC 请求"""
        if self.process and self.process.stdin:
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

    def _read_response(self) -> dict:
        """读取 JSON-RPC 响应"""
        if self.process and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if line:
                    return json.loads(line.strip())
            except Exception as e:
                print(f"⚠️ 读取响应失败: {e}")
        return {}

    def _list_tools(self):
        """获取 MCP 服务器提供的工具列表"""
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        self._send_request(list_request)
        response = self._read_response()

        if response and "result" in response:
            tools = response["result"].get("tools", [])
            for tool in tools:
                self.tools[tool["name"]] = tool
            print(f"📋 发现 {len(self.tools)} 个 MCP 工具: {list(self.tools.keys())}")

    def call_tool(self, tool_name: str, arguments: dict = None) -> str:
        """调用 MCP 工具"""
        if tool_name not in self.tools:
            return f"❌ 工具 '{tool_name}' 不存在"

        try:
            call_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }

            self._send_request(call_request)
            response = self._read_response()

            if response and "result" in response:
                content = response["result"].get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")

            return f"⚠️ MCP 调用无返回结果"

        except Exception as e:
            return f"❌ MCP 调用失败: {e}"

    def disconnect(self):
        """断开 MCP 连接"""
        if self.process:
            self.process.terminate()
            self.process = None
            print("🔌 MCP 连接已断开")

# 创建一个简单的 MCP 服务器示例 (用于演示)
def create_demo_mcp_server():
    """创建一个演示用的 MCP 服务器脚本"""
    server_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单的 MCP 服务器示例"""
import json
import sys

def handle_request(request):
    """处理 MCP 请求"""
    method = request.get("method")
    request_id = request.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "demo-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "get_weather",
                        "description": "获取指定城市的天气信息",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string", "description": "城市名称"}
                            },
                            "required": ["city"]
                        }
                    },
                    {
                        "name": "translate",
                        "description": "翻译文本",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "要翻译的文本"},
                                "target_lang": {"type": "string", "description": "目标语言"}
                            },
                            "required": ["text", "target_lang"]
                        }
                    }
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"].get("arguments", {})
        
        if tool_name == "get_weather":
            city = arguments.get("city", "未知城市")
            result = f"{city}的天气: 晴天, 温度 25°C, 湿度 60% (模拟数据)"
        elif tool_name == "translate":
            text = arguments.get("text", "")
            target = arguments.get("target_lang", "en")
            result = f"翻译结果 ({target}): {text} -> Translation of '{text}' (模拟翻译)"
        else:
            result = "未知工具"
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {"type": "text", "text": result}
                ]
            }
        }
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "Method not found"}
    }

if __name__ == "__main__":
    # 从 stdin 读取请求,向 stdout 输出响应
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(e)}
            }), flush=True)
'''

    server_path = "mcp_demo_server.py"
    with open(server_path, "w", encoding="utf-8") as f:
        f.write(server_code)

    print(f"✅ 已创建演示 MCP 服务器: {server_path}")
    return server_path

# 初始化 MCP 客户端
print("\n🔧 正在初始化 MCP 客户端...")
mcp_server_path = create_demo_mcp_server()
mcp_client = MCPClient([sys.executable, mcp_server_path])
mcp_connected = mcp_client.connect()

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
    mcp_result: str  # 新增: MCP 调用结果

# 节点0: 理解用户意图
def understand_intent(state: State) -> State:
    question = state["messages"][-1].content
    print("🧠 正在理解用户意图...")

    # 构建工具描述 (包含 MCP 工具)
    mcp_tools_desc = ""
    if mcp_connected and mcp_client.tools:
        mcp_tools_desc = "\n- MCP 工具:"
        for tool_name, tool_info in mcp_client.tools.items():
            mcp_tools_desc += f"\n  - {tool_name}: {tool_info.get('description', '')}"

    intent_prompt = f"""分析用户问题的真实意图,并以JSON格式返回:

用户问题: {question}

可用资源:
1. 本地知识库: 包含公司政策、规章制度、员工手册、福利待遇、出差补贴、住房补贴等内部文档
2. 网络搜索: 实时信息,如天气、新闻、最新动态等
3. 本地工具:
   - calculator: 计算数学表达式 (如: 123+456)
   - get_time: 获取当前时间 (如: 现在几点、今天日期)
   - string_length: 计算字符串长度
{mcp_tools_desc}

请分析:
1. 需要查询本地知识库吗? (knowledge: true/false)
2. 需要搜索网络吗? (web: true/false)
3. 需要调用本地工具吗? (tools: [])
4. 需要调用 MCP 工具吗? (mcp_tools: [{{"name": "tool_name", "args": {{}}}}, ...])
5. 问题类型: (type: "知识库查询"/"网络查询"/"计算"/"MCP调用"/等)
6. 核心意图简述: (summary: "...")

重要: 只返回纯JSON,不要有任何额外文字或markdown标记!
格式如下:
{{
  "knowledge": true,
  "web": false,
  "tools": [],
  "mcp_tools": [],
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
    print(f"   意图: {intent_text[:100]}...")
    return state

# 节点1: 检索本地文档
def retrieve_local(state: State) -> State:
    question = state["messages"][-1].content
    print("📚 正在检索本地知识库...")

    docs_with_scores = vectorstore.similarity_search_with_score(question, k=3)
    filtered_docs = [doc for doc, score in docs_with_scores if score < 1][:2]

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

# 节点3: 调用本地工具
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

# 节点4: 调用 MCP 工具 (新增)
def call_mcp_tools(state: State) -> State:
    """调用 MCP 外部工具"""
    if not mcp_connected:
        state["mcp_result"] = ""
        return state

    try:
        intent_json = json.loads(state["intent"])
        mcp_tools = intent_json.get("mcp_tools", [])

        if not mcp_tools:
            state["mcp_result"] = ""
            return state

        results = []
        for tool_call in mcp_tools:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})

            print(f"🔌 调用 MCP 工具: {tool_name} (参数: {tool_args})")
            result = mcp_client.call_tool(tool_name, tool_args)
            results.append(f"[{tool_name}] {result}")

        state["mcp_result"] = "\n".join(results)

    except Exception as e:
        print(f"⚠️ MCP 调用异常: {e}")
        state["mcp_result"] = ""

    return state

# 节点5: 生成答案
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

🔌 **MCP 外部服务结果:**
{state['mcp_result'] if state['mcp_result'] else '(未调用 MCP 服务)'}

---

💡 **回答指南:**
1. **优先级:** 工具结果 > MCP 结果 > 知识库 > 网络信息 > 通用知识
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
    return state

# ========== 条件路由函数 ==========
def route_after_understand(state: State) -> Literal["retrieve", "search", "tool", "mcp", "generate"]:
    try:
        intent_json = json.loads(state["intent"])

        if intent_json.get("knowledge", False):
            return "retrieve"
        elif intent_json.get("web", False):
            return "search"
        elif intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            return "tool"
        elif intent_json.get("mcp_tools") and len(intent_json.get("mcp_tools")) > 0:
            return "mcp"
        else:
            return "generate"
    except:
        return "retrieve"

def route_after_retrieve(state: State) -> Literal["search", "tool", "mcp", "generate"]:
    try:
        intent_json = json.loads(state["intent"])

        if intent_json.get("web", False):
            return "search"
        elif intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            return "tool"
        elif intent_json.get("mcp_tools") and len(intent_json.get("mcp_tools")) > 0:
            return "mcp"
        else:
            return "generate"
    except:
        return "generate"

def route_after_search(state: State) -> Literal["tool", "mcp", "generate"]:
    try:
        intent_json = json.loads(state["intent"])

        if intent_json.get("tools") and len(intent_json.get("tools")) > 0:
            return "tool"
        elif intent_json.get("mcp_tools") and len(intent_json.get("mcp_tools")) > 0:
            return "mcp"
        else:
            return "generate"
    except:
        return "generate"

def route_after_tool(state: State) -> Literal["mcp", "generate"]:
    try:
        intent_json = json.loads(state["intent"])

        if intent_json.get("mcp_tools") and len(intent_json.get("mcp_tools")) > 0:
            return "mcp"
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
workflow.add_node("mcp", call_mcp_tools)  # 新增 MCP 节点
workflow.add_node("generate", generate)

workflow.add_edge(START, "understand")

workflow.add_conditional_edges("understand", route_after_understand,
    {"retrieve": "retrieve", "search": "search", "tool": "tool", "mcp": "mcp", "generate": "generate"})

workflow.add_conditional_edges("retrieve", route_after_retrieve,
    {"search": "search", "tool": "tool", "mcp": "mcp", "generate": "generate"})

workflow.add_conditional_edges("search", route_after_search,
    {"tool": "tool", "mcp": "mcp", "generate": "generate"})

workflow.add_conditional_edges("tool", route_after_tool,
    {"mcp": "mcp", "generate": "generate"})

workflow.add_edge("mcp", "generate")
workflow.add_edge("generate", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

print("✅ 工作流编译完成\n")

# 主循环
if __name__ == "__main__":
    print("🤖 智能助手已启动! (支持 MCP 外部服务调用)")
    print("📋 可用功能:")
    print("   - 本地工具: 计算器、时间查询、字符串长度")
    if mcp_connected:
        print(f"   - MCP 工具: {list(mcp_client.tools.keys())}")
    print("\n💡 试试问:")
    print("   - '北京的天气怎么样?' (调用 MCP get_weather)")
    print("   - '翻译 hello 到中文' (调用 MCP translate)")
    print("   - '123+456等于多少?' (本地计算器)")
    print("   - '出差补贴是多少?' (知识库查询)\n")

    config = {"configurable": {"thread_id": "default"}}

    try:
        while True:
            question = input("\n👤 您: ").strip()

            if question in ['退出', 'quit', 'exit', 'q']:
                print("👋 再见!")
                break

            if not question:
                continue

            current_state = app.get_state(config)
            existing_messages = current_state.values.get("messages", []) if current_state.values else []

            try:
                result = app.invoke({
                    "messages": existing_messages + [HumanMessage(content=question)],
                    "intent": "",
                    "local_docs": "",
                    "web_result": "",
                    "tool_result": "",
                    "mcp_result": ""
                }, config)

                print()
            except Exception as e:
                print(f"\n❌ 执行出错: {e}")
                import traceback
                traceback.print_exc()

    finally:
        # 清理 MCP 连接
        if mcp_connected:
            mcp_client.disconnect()
