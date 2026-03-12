#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """全局配置类"""

    def __init__(self):
        # 加载环境变量
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)

        # LLM 配置
        self.llm_model_id = os.getenv('LLM_MODEL_ID', 'qwen3.5-flash')
        self.llm_api_key = os.getenv('LLM_API_KEY')
        self.llm_base_url = os.getenv('LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')

        # API 配置
        self.bill_api_url = "http://utopia-atom.offline-beta.ttb.test.ke.com/api/inner/base"
        self.operate_log_api_url = "http://utopia-atom.offline-beta.ttb.test.ke.com/common/operate-log/query-page"

        # API 请求头
        self.default_headers = {
            "Cookie": "lianjia_uuid=26e8b33a-65b2-4f24-8cdc-d4d329de4dc1",
            "ucid": "1000000030598910",
            "displayName": "test",
            "account": "zhongliwen002",
            "User-Agent": "MCP-Agent/1.0.0",
            "Content-Type": "application/json"
        }

        # MCP 配置
        self.mcp_server_path = Path(__file__).parent / "bill_mcp_server.py"

        # 超时配置
        self.api_timeout = 30

        # 分页配置
        self.default_page_size = 10

        # RAG 配置
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-v3')
        self.knowledge_doc_path = Path(__file__).parent / os.getenv('KNOWLEDGE_DOC', 'knowledge.docx')
        self.rag_chunk_size = int(os.getenv('RAG_CHUNK_SIZE', '500'))
        self.rag_chunk_overlap = int(os.getenv('RAG_CHUNK_OVERLAP', '50'))
        self.rag_top_k = int(os.getenv('RAG_TOP_K', '3'))
        self.rag_score_threshold = float(os.getenv('RAG_SCORE_THRESHOLD', '1.0'))

    def validate(self) -> bool:
        """验证配置是否完整"""
        if not self.llm_api_key:
            print("⚠️ 警告: LLM_API_KEY 未配置")
            return False
        return True


# 全局配置实例
config = Config()

