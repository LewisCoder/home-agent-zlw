"""
节点逻辑模块
定义工作流中的所有节点处理函数
"""

import re
import json
from typing import TypedDict
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import config
from tools import TOOLS


class State(TypedDict):
    """工作流状态定义"""
    messages: list
    intent: str
    local_docs: str
    web_result: str
    tool_result: str


def understand_intent(state: State) -> State:
    """
    节点0: 理解用户意图
    分析用户问题,判断需要执行的操作
    """
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

    response = config.llm.invoke([SystemMessage(content=intent_prompt)])
    intent_text = response.content

    # 清理返回内容,提取JSON
    intent_text = intent_text.strip()

    # 移除markdown代码块标记
    if "" in intent_text:
        intent_text = intent_text.replace("", "").replace("", "")
        intent_text = intent_text.strip()

    # 强制提取JSON对象
    if '{' in intent_text and '}' in intent_text:
        start = intent_text.find('{')
        end = intent_text.rfind('}') + 1
        intent_text = intent_text[start:end]

    # 验证JSON格式
    try:
        json.loads(intent_text)
        print(f"   ✓ 意图JSON解析成功")
    except json.JSONDecodeError as e:
        print(f"   ⚠️  JSON格式异常: {e}")
        print(f"   清理后内容: {intent_text[:200]}")

    # 保存意图分析结果
    state["intent"] = intent_text
    print(f"   意图: {intent_text[:100]}...")

    return state


def retrieve_local(state: State) -> State:
    """
    节点1: 检索本地文档
    从向量数据库中检索相关文档
    """
    question = state["messages"][-1].content
    print("📚 正在检索本地知识库...")

    if not config.vectorstore:
        print("   ⚠️  向量数据库未初始化")
        state["local_docs"] = ""
        return state

    # 检索时带上相似度分数
    docs_with_scores = config.vectorstore.similarity_search_with_score(question, k=5)

    # 过滤相似度低的文档 (分数越小越相似)
    filtered_docs = [
        doc for doc, score in docs_with_scores
        if score < config.similarity_threshold
    ][:config.max_retrieve_docs]

    if filtered_docs:
        state["local_docs"] = "\n\n---\n\n".join([d.page_content for d in filtered_docs])
        print(f"   ✓ 找到 {len(filtered_docs)} 个相关文档块")
    else:
        state["local_docs"] = ""
        print("   ✗ 未找到相关文档")

    return state


def search_web(state: State) -> State:
    """
    节点2: 搜索网络
    使用Tavily搜索引擎获取网络信息
    """
    question = state["messages"][-1].content
    print("🔍 正在搜索网络...")

    if not config.search:
        print("   ⚠️  搜索服务未初始化")
        state["web_result"] = ""
        return state

    try:
        result = config.search.search(query=question, max_results=2)
        content = "\n".join([item.get('content', '') for item in result.get("results", [])[:2]])
        state["web_result"] = content
        print(f"   ✓ 获取到网络搜索结果")
    except Exception as e:
        print(f"   ❌ 搜索失败: {e}")
        state["web_result"] = ""

    return state


def check_tool(state: State) -> State:
    """
    节点3: 智能工具调用
    根据问题智能选择并调用工具
    """
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


def generate(state: State) -> State:
    """
    节点4: 生成答案
    基于所有收集的信息生成最终答案
    """
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

    for chunk in config.llm.stream([SystemMessage(content=prompt)]):
        print(chunk.content, end="", flush=True)
        full_answer += chunk.content

    state["messages"].append(AIMessage(content=full_answer))
    return state
