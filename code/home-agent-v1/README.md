# 账单查询智能助手

基于 LangGraph 和 MCP 协议构建的简单账单查询 Agent。

## 项目结构


mcp_demo/
├── simple_agent.py         # 主程序 - 3节点Agent
├── bill_mcp_server.py      # MCP服务器 - 账单查询API封装
├── test_mcp_server.py      # 测试脚本
├── requirements.txt        # 依赖列表
├── .env.example           # 环境变量示例
├── run.bat                # Windows启动脚本
├── test.bat               # Windows测试脚本
└── README.md              # 本文件


## 功能特性

- **3节点工作流**: 意图理解 → MCP调用 → 答案生成
- **静态边连接**: 简单清晰的线性流程
- **MCP协议**: 标准化的工具调用接口
- **多工具支持**: 账单查询、操作记录查询
- **自然语言交互**: 支持多种输入方式

## 工作流程


用户输入
   ↓
[节点1: 意图理解]
   ├─ 提取账单代码
   ↓
[节点2: MCP调用]
   ├─ 调用账单查询API
   ↓
[节点3: 答案生成]
   ├─ 生成友好回答
   ↓
输出结果


## 快速开始

### 1. 安装依赖


cd code/mcp_demo
pip install -r requirements.txt


### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置:


cp .env.example .env


编辑 `.env`:


LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_ID=qwen3.5-flash


### 3. 测试 MCP 服务器


# Windows
test.bat

# Linux/Mac
python test_mcp_server.py


### 4. 运行 Agent


# Windows
run.bat

# Linux/Mac
python simple_agent.py


## 使用示例

### 示例 1: 直接输入账单代码


👤 请输入账单代码或问题: GBILL260202111424630037

🧠 节点1: 理解用户意图
   用户输入: GBILL260202111424630037
   ✓ 提取到账单代码: GBILL260202111424630037

🔌 节点2: 调用 MCP 查询账单
   账单代码: GBILL260202111424630037
   正在查询账单信息...
   ✓ MCP 调用完成

💡 节点3: 生成最终答案
   正在生成答案...
   ✓ 答案生成完成

======================================================================
🤖 助手回答:
======================================================================
账单查询成功!
账单代码: GBILL260202111424630037
[显示账单详细信息...]
======================================================================


### 示例 2: 自然语言提问


👤 请输入账单代码或问题: 帮我查询一下账单GBILL260202111424630037的信息

[处理流程相同...]


## 技术架构

### 1. MCP 服务器 (bill_mcp_server.py)

**功能**: 封装账单查询 API

**API 配置**:
- URL: `http://utopia-atom.offline-beta.ttb.test.ke.com/api/inner/base`
- 方法: POST
- 参数: `{"billCode": "账单代码"}`

**MCP 工具**:
- 工具名: `query_bill`
- 参数: `billCode` (必填)
- 返回: JSON 格式的账单信息

### 2. Agent 工作流 (simple_agent.py)

**状态定义**:

class State(TypedDict):
    user_input: str      # 用户输入
    bill_code: str       # 提取的账单代码
    mcp_result: str      # MCP 调用结果
    final_answer: str    # 最终答案


**节点说明**:

#### 节点1: understand_intent
- **功能**: 从用户输入中提取账单代码
- **输入**: `user_input`
- **输出**: `bill_code`
- **实现**: 使用 LLM 理解自然语言,提取账单代码

#### 节点2: call_mcp
- **功能**: 调用 MCP 服务查询账单
- **输入**: `bill_code`
- **输出**: `mcp_result`
- **实现**: 通过 MCP 协议调用 `query_bill` 工具

#### 节点3: generate_answer
- **功能**: 生成友好的回答
- **输入**: `user_input`, `mcp_result`
- **输出**: `final_answer`
- **实现**: 使用 LLM 总结和格式化结果

## 自定义配置

### 修改 API 地址

编辑 `bill_mcp_server.py`:


class BillQueryMCPServer:
    def __init__(self):
        # 修改 API URL
        self.api_url = "http://your-api-url.com/api/endpoint"
        
        # 修改请求头
        self.default_headers = {
            "Cookie": "your-cookie",
            "ucid": "your-ucid",
            # ...
        }


### 修改 LLM 模型

编辑 `.env`:


LLM_MODEL_ID=gpt-4  # 或其他模型
LLM_BASE_URL=https://api.openai.com/v1


## 错误处理

程序包含完善的错误处理:

1. **网络错误**: 连接超时、连接失败
2. **API 错误**: HTTP 错误、响应格式错误
3. **参数错误**: 账单代码未找到或格式错误
4. **MCP 错误**: 服务未连接、工具调用失败

## 故障排查

### 问题: MCP 服务器连接失败

**解决方案**:
1. 检查 `bill_mcp_server.py` 文件是否存在
2. 检查 Python 环境和依赖是否安装
3. 查看控制台错误信息

### 问题: API 调用失败

**解决方案**:
1. 检查网络连接
2. 验证 API URL 和请求头配置
3. 确认账单代码格式正确
4. 检查 API 服务是否可访问

### 问题: 无法提取账单代码

**解决方案**:
1. 使用更明确的输入格式
2. 直接输入账单代码(如: GBILL260202111424630037)
3. 检查 LLM API 配置是否正确

## 依赖说明

- **langchain-openai**: LLM 调用
- **langchain-core**: LangChain 核心功能
- **langgraph**: 工作流编排
- **python-dotenv**: 环境变量管理
- **requests**: HTTP 请求

## 许可证

MIT License

