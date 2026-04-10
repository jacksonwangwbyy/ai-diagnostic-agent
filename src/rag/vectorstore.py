"""
向量存储 - 支持 ChromaDB（开发）和 Milvus（生产）

学习要点：
1. Embedding - 把文本转成高维向量，语义相似的文本向量距离近
2. 向量数据库 - 专门存储和检索向量的数据库，支持相似度搜索
3. ChromaDB - 轻量级向量数据库，本地运行，适合开发阶段
4. Milvus - 生产级向量数据库，支持分布式部署，适合生产环境
5. 通过 VECTOR_DB_TYPE 配置切换：chromadb / milvus
"""
import logging
from langchain_core.documents import Document
from src.config.settings import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "device_knowledge_base"

# 模块级缓存，避免每次检索都重新初始化 embedding 模型和 vectorstore
_cached_vectorstore = None


def create_embedding(use_local: bool = True):
    """
    创建 Embedding 模型

    Args:
        use_local: True 使用本地 HuggingFace 模型（离线免费）
                   False 使用 OpenAI API（效果更好，需要 API）
    """
    if use_local:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )

    # 调用 OpenAI Embedding API 时代理已在 settings.py 统一清除
    from langchain_openai import OpenAIEmbeddings
    kwargs = {
        "model": "text-embedding-3-small",
        "openai_api_key": settings.OPENAI_API_KEY,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["openai_api_base"] = settings.OPENAI_BASE_URL
    return OpenAIEmbeddings(**kwargs)


def _create_chroma_store(embedding, documents: list[Document] = None):
    """创建或加载 ChromaDB 向量存储"""
    from langchain_chroma import Chroma

    persist_dir = settings.CHROMA_PERSIST_DIR

    if documents:
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embedding,
            collection_name=COLLECTION_NAME,
            persist_directory=persist_dir,
        )
        logger.info(f"已存入 ChromaDB ({persist_dir})，共 {len(documents)} 个文档块")
        return vectorstore

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embedding,
        persist_directory=persist_dir,
    )


def _create_milvus_store(embedding, documents: list[Document] = None):
    """创建或加载 Milvus 向量存储"""
    from langchain_milvus import Milvus

    connection_args = {
        "host": settings.MILVUS_HOST,
        "port": settings.MILVUS_PORT,
    }

    if documents:
        vectorstore = Milvus.from_documents(
            documents=documents,
            embedding=embedding,
            collection_name=COLLECTION_NAME,
            connection_args=connection_args,
        )
        logger.info(f"已存入 Milvus ({settings.MILVUS_HOST}:{settings.MILVUS_PORT})，共 {len(documents)} 个文档块")
        return vectorstore

    return Milvus(
        embedding_function=embedding,
        collection_name=COLLECTION_NAME,
        connection_args=connection_args,
    )


def create_vector_store(
    documents: list[Document] = None,
    use_local_embedding: bool = True,
):
    """
    创建或加载向量存储（根据 VECTOR_DB_TYPE 自动选择后端）

    Args:
        documents: 文档块列表（None=加载已有数据）
        use_local_embedding: 是否用本地 Embedding
    """
    embedding = create_embedding(use_local=use_local_embedding)
    db_type = settings.VECTOR_DB_TYPE

    if documents:
        embed_name = "本地 HuggingFace" if use_local_embedding else "OpenAI API"
        print(f"正在 Embedding {len(documents)} 个文档块...")
        print(f"  Embedding 模型: {embed_name}")
        print(f"  向量数据库: {db_type}")

    if db_type == "milvus":
        return _create_milvus_store(embedding, documents)
    else:
        return _create_chroma_store(embedding, documents)


def search(query: str, k: int = 5) -> list[Document]:
    """相似度检索"""
    global _cached_vectorstore
    if _cached_vectorstore is None:
        _cached_vectorstore = create_vector_store()
    return _cached_vectorstore.similarity_search(query, k=k)


def search_with_scores(query: str, k: int = 5) -> list[tuple[Document, float]]:
    """带分数的检索（分数越小越相似）"""
    global _cached_vectorstore
    if _cached_vectorstore is None:
        _cached_vectorstore = create_vector_store()
    return _cached_vectorstore.similarity_search_with_score(query, k=k)
