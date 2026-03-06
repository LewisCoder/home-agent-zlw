# RAG智能助手 Gradio 部署指南

## 📦 文件说明

- `gradio_app.py` - Gradio Web应用主文件
- `knowledge.docx` - 本地知识库文档

## 🚀 快速启动

### 1. 安装依赖


pip install gradio


### 2. 运行应用


cd C:\Users\Administrator\IdeaProjects\hello-agents\code\demo
python gradio_app.py


### 3. 访问方式

启动后会看到两个链接:


Running on local URL:  http://127.0.0.1:7860
Running on public URL: https://xxxxxxxx.gradio.live


- **本地访问**: http://127.0.0.1:7860
- **公网访问**: https://xxxxxxxx.gradio.live (72小时有效)

## 🌐 外网访问说明

### Gradio Share 链接特点

✅ **优点:**
- 自动生成公网链接
- 无需配置服务器
- 免费使用
- 支持HTTPS

⚠️ **限制:**
- 链接有效期: 72小时
- 每次重启生成新链接
- 共享Gradio服务器带宽

### 持久化部署方案

如果需要长期稳定的公网访问,可以选择:

#### 方案1: Hugging Face Spaces (推荐)


# 1. 创建 requirements.txt
langchain
langchain-openai
langchain-community
langgraph
faiss-cpu
python-docx
tavily-python
gradio

# 2. 上传到 Hugging Face Spaces
# 访问: https://huggingface.co/spaces
# 创建新Space,选择Gradio SDK
# 上传 gradio_app.py 和 requirements.txt


#### 方案2: 云服务器部署


# 在云服务器上运行
python gradio_app.py

# 配置反向代理 (Nginx)
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}


#### 方案3: Ngrok (临时方案)


# 安装 ngrok
# 访问: https://ngrok.com/

# 启动应用
python gradio_app.py

# 新终端窗口
ngrok http 7860

# 会生成一个 https://xxxx.ngrok.io 链接


## 🎨 界面功能

### 主要特性

1. **聊天界面**: 实时对话交互
2. **示例问题**: 快速开始
3. **重试/撤销**: 便捷操作
4. **清空对话**: 重置会话

### 支持的功能

- 📚 **本地知识库查询**: "出差补贴是多少?"
- 🔍 **网络搜索**: "北京今天天气怎么样?"
- 🔧 **工具调用**:
  - 计算器: "123+456等于多少?"
  - 时间查询: "现在几点了?"
  - 字符串长度: "'hello'有多少字?"
- 💬 **闲聊**: "你好"

## 🔧 配置说明

### API 密钥配置

在 `gradio_app.py` 中修改:


os.environ["LLM_API_KEY"] = "your-api-key"
os.environ["TAVILY_API_KEY"] = "your-tavily-key"


### 端口配置


demo.launch(
    server_port=7860,  # 修改端口号
    share=True         # 是否生成公网链接
)


### 知识库配置

替换 `knowledge.docx` 文件为您自己的知识库文档。

## 🐛 常见问题

### Q1: 公网链接无法访问

**原因:** Gradio Share服务可能被墙或网络问题

**解决:**
1. 检查网络连接
2. 尝试使用VPN
3. 使用其他部署方案(Hugging Face Spaces)

### Q2: 链接过期

**原因:** Gradio Share链接72小时后自动失效

**解决:**
1. 重新启动应用生成新链接
2. 使用持久化部署方案

### Q3: 内存不足

**原因:** FAISS向量库占用内存较大

**解决:**
1. 减少知识库文档大小
2. 调整 `chunk_size` 参数
3. 使用更大内存的服务器

### Q4: 响应速度慢

**原因:** 
- 网络延迟
- 大模型API响应慢
- 向量检索耗时

**解决:**
1. 使用更快的大模型
2. 优化相似度阈值
3. 减少检索文档数量

## 📊 性能优化

### 1. 缓存优化


# 缓存向量库
@functools.lru_cache(maxsize=100)
def get_similar_docs(query):
    return vectorstore.similarity_search(query)


### 2. 异步处理


import asyncio

async def async_chat(message, history):
    # 异步处理逻辑
    pass


### 3. 批量处理


# 批量向量化
embeddings.embed_documents(texts, batch_size=32)


## 🔒 安全建议

1. **不要暴露API密钥**: 使用环境变量
2. **限制访问**: 添加身份验证
3. **速率限制**: 防止滥用
4. **日志监控**: 记录访问日志

### 添加身份验证


demo.launch(
    auth=("username", "password"),  # 添加登录验证
    share=True
)


## 📈 监控与日志

### 添加访问日志


import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

def chat(message, history):
    logging.info(f"用户提问: {message}")
    # ... 处理逻辑
    logging.info(f"回答完成")


## 🎯 下一步

1. **自定义界面**: 修改Gradio主题和布局
2. **增加功能**: 添加更多工具和能力
3. **优化性能**: 缓存、异步、批处理
4. **部署上线**: 选择合适的部署方案

## 📞 技术支持

如有问题,请查看:
- Gradio官方文档: https://gradio.app/docs/
- LangGraph文档: https://langchain-ai.github.io/langgraph/
- 项目README

---

**祝您使用愉快! 🎉**
