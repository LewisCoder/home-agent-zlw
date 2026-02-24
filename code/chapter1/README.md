# FirstAgentTest - 智能旅行助手

这是一个基于 ReAct 框架的智能 Agent，能够查询天气并推荐旅游景点。

## 📋 功能说明

这个 Agent 可以：
1. 查询指定城市的实时天气（使用 wttr.in API）
2. 根据天气情况推荐合适的旅游景点（使用 Tavily Search API）
3. 使用 ReAct (Reasoning + Acting) 框架进行思考和行动

## 🔧 运行前准备

### 1. 安装依赖


pip install openai tavily-python requests


或者使用 requirements.txt：


pip install -r requirements.txt


### 2. 配置 API 密钥

您需要配置两个 API 密钥：

#### (1) LLM API 密钥（必需）

文件中已配置了阿里云通义千问，您需要修改第 144-146 行：


API_KEY = "sk-your-api-key-here"  # 替换成你的 API Key
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ID = "qwen-turbo"


**获取方式：**
- 阿里云通义千问: https://dashscope.aliyun.com/
- 或使用 DeepSeek: https://platform.deepseek.com/
- 或使用智谱 AI: https://open.bigmodel.cn/

**其他 LLM 配置示例：**


# DeepSeek
API_KEY = "sk-your-deepseek-key"
BASE_URL = "https://api.deepseek.com/v1"
MODEL_ID = "deepseek-chat"

# 智谱 AI
API_KEY = "your-zhipu-key"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
MODEL_ID = "glm-4"


#### (2) Tavily API 密钥（必需）

文件中第 147 行需要配置：


os.environ['TAVILY_API_KEY'] = "tvly-your-api-key-here"


**获取方式：**
- 访问: https://tavily.com/
- 注册账号并获取免费 API Key

### 3. 修改用户请求（可选）

第 156 行可以修改用户的请求内容：


user_prompt = "你好,请帮我查询一下今天北京的天气,然后根据天气推荐一个合适的旅游景点。"


## 🚀 运行程序


python code/chapter1/FirstAgentTest.py


或者在项目根目录：


python code\chapter1\FirstAgentTest.py


## 📊 运行示例

程序运行后会输出类似以下内容：


用户输入: 你好,请帮我查询一下今天北京的天气,然后根据天气推荐一个合适的旅游景点。
========================================
--- 循环 1 ---

正在调用大语言模型...
大语言模型响应成功。
模型输出:
Thought: 用户想要了解北京今天的天气,并根据天气情况推荐旅游景点。首先,我需要查询北京的天气。
Action: get_weather(city="北京")

Observation: 北京当前天气:晴朗,气温25摄氏度
========================================
--- 循环 2 ---

正在调用大语言模型...
大语言模型响应成功。
模型输出:
Thought: 现在我知道了北京的天气是晴朗,气温25摄氏度。接下来,我需要根据这个天气情况推荐合适的旅游景点。
Action: get_attraction(city="北京", weather="晴朗,气温25摄氏度")

Observation: [景点推荐内容...]
========================================
--- 循环 3 ---

任务完成,最终答案: 今天北京天气晴朗,气温25摄氏度,非常适合户外活动...


## 🔍 代码结构

- **AGENT_SYSTEM_PROMPT**: Agent 的系统提示词,定义了 ReAct 框架
- **get_weather()**: 查询天气的工具函数
- **get_attraction()**: 搜索景点的工具函数
- **OpenAICompatibleClient**: LLM 客户端封装
- **主循环**: 实现 ReAct 框架的核心逻辑

## ⚠️ 注意事项

1. 确保网络连接正常（需要访问外部 API）
2. API 密钥必须有效且有剩余额度
3. 程序最多循环 5 次,如果未完成会自动停止
4. 城市名称建议使用中文（如"北京"、"上海"）

## 🐛 常见问题

### 1. 提示 "错误:未配置TAVILY_API_KEY"
需要在代码中配置 Tavily API Key（第 147 行）

### 2. 提示 "调用LLM API时发生错误"
检查 API_KEY、BASE_URL 和 MODEL_ID 是否正确

### 3. 天气查询失败
可能是城市名称不正确,尝试使用英文城市名（如 "Beijing"）

### 4. 缺少依赖包
运行: `pip install openai tavily-python requests`

## 📚 相关资源

- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Tavily API 文档](https://docs.tavily.com/)
- [wttr.in 天气 API](https://wttr.in/)
- [ReAct 论文](https://arxiv.org/abs/2210.03629)
