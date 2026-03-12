#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 检索模块
负责加载知识库文档并提供向量相似度检索功能
"""

from typing import Optional

from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter

from config import config


class RAGRetriever:
    """RAG 检索器，负责文档加载、向量化和检索"""

    def __init__(self):
        self.vectorstore: Optional[FAISS] = None
        self.embeddings: Optional[DashScopeEmbeddings] = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        初始化检索器：加载文档并构建向量索引

        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True

        # 检查知识库文件是否存在
        doc_path = config.knowledge_doc_path
        if not doc_path.exists():
            print(f"⚠️  知识库文件不存在: {doc_path}")
            print(f"   请将知识库文档放置到: {doc_path}")
            return False

        try:
            print(f"📦 正在加载知识库: {doc_path.name}...")

            # 初始化 Embedding 模型
            self.embeddings = DashScopeEmbeddings(
                model=config.embedding_model,
                dashscope_api_key=config.llm_api_key
            )

            # 加载文档
            loader = Docx2txtLoader(str(doc_path))
            documents = loader.load()

            # 文档切分
            splitter = CharacterTextSplitter(
                chunk_size=config.rag_chunk_size,
                chunk_overlap=config.rag_chunk_overlap
            )
            texts = splitter.split_documents(documents)

            # 构建向量索引
            self.vectorstore = FAISS.from_documents(texts, self.embeddings)
            self._initialized = True

            print(f"✅ 知识库加载完成，共 {len(texts)} 个文本块")
            return True

        except Exception as e:
            print(f"❌ 知识库初始化失败: {e}")
            return False

    def retrieve(self, query: str) -> str:
        """
        根据查询语句检索相关文档

        Args:
            query: 查询语句

        Returns:
            检索到的相关文档内容，未找到时返回提示信息
        """
        if not self._initialized:
            success = self.initialize()
            if not success:
                return "❌ 知识库未初始化，无法检索"

        try:
            # 带相似度分数的检索
            docs_with_scores = self.vectorstore.similarity_search_with_score(
                query,
                k=config.rag_top_k
            )

            # 按阈值过滤（分数越小越相似）
            filtered = [
                doc for doc, score in docs_with_scores
                if score < config.rag_score_threshold
            ][:2]  # 最多返回 2 个文档块

            if not filtered:
                return "未在知识库中找到与该问题相关的内容"

            # 拼接结果
            results = []
            for i, doc in enumerate(filtered, 1):
                results.append(f"【文档片段 {i}】\n{doc.page_content}")

            print(f"   ✓ RAG 检索到 {len(filtered)} 个相关文档块")
            return "\n\n".join(results)

        except Exception as e:
            return f"❌ 知识库检索失败: {e}"

    @property
    def is_available(self) -> bool:
        """检索器是否可用"""
        return self._initialized


# 全局检索器实例（懒加载，首次调用时才初始化）
_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    """获取全局 RAG 检索器实例"""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever
