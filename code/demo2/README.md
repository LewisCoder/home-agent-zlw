# RAG智能助手

带工具集调用的RAG智能助手,支持本地知识库检索、网络搜索、多工具调用和对话记忆功能。

## 功能特性

- **RAG检索增强**: 基于FAISS向量数据库的本地知识库检索
- **多工具调用**: 支持计算器、时间查询、字符串处理等工具
- **网络搜索**: 集成Tavily搜索引擎获取实时信息
- **智能路由**: 根据用户意图自动选择执行路径
- **对话记忆**: 基于LangGraph的会话状态管理
- **模块化设计**: 清晰的代码结构,易于扩展和维护

## 项目结构


demo2/
├── __init__.py           # 包初始化文件
├── config.py             # 配置管理模块
├── tools.py              # 工具集定义
├── nodes.py              # 工作流节点逻辑
├── router.py             # 条件路由逻辑
├── main.py               # 主程序入口
├── requirements.txt      # 依赖列表
├── .env.example          # 环境变量示例
└── README.md             # 说明文档


## 安装依赖


pip install -r requirements.txt


## 配置说明

1. 复制 `.env.example` 为 `.env`
2. 填写必要的API密钥:


# LLM配置
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_ID=qwen3.5-flash

# Tavily搜索API
TAVILY_API_KEY=your-tavily-api-key-here

# 知识库配置
KNOWLEDGE_FILE=knowledge.docx
CHUNK_SIZE=500
CHUNK_OVERLAP=50
SIMILARITY_THRESHOLD=0.5
MAX_RETRIEVE_DOCS=2


## 使用方法


python main.py


### 示例对话


👤 您: 123+456等于多少?
🧠 正在理解用户意图...
   ✓ 意图JSON解析成功
   📍 路由决策: 需要调用工具 ['calculator'] → tool
🔧 调用工具: 计算器
💡 回答: 计算结果是579。

👤 您: 出差补贴是多少?
🧠 正在理解用户意图...
   ✓ 意图JSON解析成功
   📍 路由决策: 需要查询本地知识库 → retrieve
📚 正在检索本地知识库...
   ✓ 找到 2 个相关文档块
💡 回答: 根据公司规定,出差补贴标准为...

👤 您: 现在几点了?
🧠 正在理解用户意图...
   ✓ 意图JSON解析成功
   📍 路由决策: 需要调用工具 ['get_time'] → tool
🔧 调用工具: 时间查询
💡 回答: 当前时间: 2026-03-06 14:30:00


## 工作流程


START → understand_intent (意图理解)
           ↓
    ┌──────┴──────┐
    ↓             ↓
retrieve      search/tool/generate
    ↓             ↓
search/tool   tool/generate
    ↓             ↓
tool/generate  generate
    ↓             ↓
generate       END
    ↓
   END


## 可用工具

- **计算器**: 计算数学表达式 (如: 123+456)
- **时间查询**: 获取当前时间
- **字符串长度**: 计算字符串的长度

## 扩展开发

### 添加新工具

在 `tools.py` 中定义新工具:


def your_tool_func(param: str) -> str:
    # 工具逻辑
    return "结果"

TOOLS["your_tool"] = Tool(
    name="工具名称",
    description="工具描述",
    func=your_tool_func
)


### 自定义节点

在 `nodes.py` 中添加新节点函数:


def your_node(state: State) -> State:
    # 节点逻辑
    return state


### 修改路由逻辑

在 `router.py` 中调整路由条件:


def your_router(state: State) -> Literal["node1", "node2"]:
    # 路由逻辑
    return "node1"


## 技术栈

- **LangChain**: LLM应用开发框架
- **LangGraph**: 工作流编排
- **FAISS**: 向量数据库
- **Tavily**: 网络搜索API
- **DashScope**: 阿里云大模型服务

## 注意事项

1. 确保 `knowledge.docx` 文件存在于 `demo` 文件夹中
2. API密钥需要有效且有足够的配额
3. 网络搜索功能需要配置Tavily API Key
4. 首次运行会加载知识库,需要一定时间

## 许可证

MIT License
