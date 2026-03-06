"""
配置管理模块
负责加载环境变量和初始化各种服务
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from tavily import TavilyClient


class Config:
    """配置类"""

    def __init__(self):
        # 加载环境变量
        env_path = Path(__file__).parent / '.env'
        load_dotenv(env_path)

        # LLM配置
        self.llm_api_key = os.getenv('LLM_API_KEY', '')
        self.llm_base_url = os.getenv('LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.llm_model_id = os.getenv('LLM_MODEL_ID', 'qwen3.5-flash')

        # Tavily配置
        self.tavily_api_key = os.getenv('TAVILY_API_KEY', '')

        # 知识库配置
        self.knowledge_file = os.getenv('KNOWLEDGE_FILE', 'knowledge.docx')
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '500'))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', '50'))
        self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', '0.5'))
        self.max_retrieve_docs = int(os.getenv('MAX_RETRIEVE_DOCS', '2'))

        # 初始化服务
        self.llm = None
        self.embeddings = None
        self.search = None
        self.vectorstore = None

    def initialize_services(self):
        """初始化所有服务"""
        print("🔧 正在初始化服务...")

        # 初始化LLM
        self.llm = ChatOpenAI(
            model=self.llm_model_id,
            api_key=self.llm_api_key,
            base_url=self.llm_base_url
        )
        print("   ✓ LLM初始化完成")

        # 初始化Embeddings
        self.embeddings = DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key=self.llm_api_key
        )
        print("   ✓ Embeddings初始化完成")

        # 初始化搜索服务
        if self.tavily_api_key:
            self.search = TavilyClient(api_key=self.tavily_api_key)
            print("   ✓ Tavily搜索服务初始化完成")
        else:
            print("   ⚠️  未配置Tavily API Key,网络搜索功能不可用")

        # 加载知识库
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """加载知识库"""
        knowledge_path = Path(__file__).parent.parent / 'demo' / self.knowledge_file

        if not knowledge_path.exists():
            print(f"   ⚠️  知识库文件不存在: {knowledge_path}")
            return

        print(f"📦 正在从Word文档加载知识库: {self.knowledge_file}")

        try:
            loader = Docx2txtLoader(str(knowledge_path))
            documents = loader.load()

            splitter = CharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            texts = splitter.split_documents(documents)

            self.vectorstore = FAISS.from_documents(texts, self.embeddings)
            print(f"   ✅ 已加载 {len(texts)} 个文本块到向量数据库\n")
        except Exception as e:
            print(f"   ❌ 加载知识库失败: {e}\n")


# 全局配置实例
config = Config()
