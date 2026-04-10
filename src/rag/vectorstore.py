"""
向量存储 - 将文档块 Embedding 后存入 ChromaDB

学习要点：
1. Embedding - 把文本转成高维向量，语义相似的文本向量距离近
2. 向量数据库 - 专门存储和检索向量的数据库，支持相似度搜索
3. ChromaDB - 轻量级向量数据库，本地运行，适合开发阶段
4. Embedding 选型 - OpenAI API（效果好，要钱）vs 本地模型（免费离线）
"""
from langchain_core.documents import Document
from langchain_chroma import Chroma
from src.config.settings import settings

COLLECTION_NAME = "device_knowledge_base"


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


def create_vector_store(
    documents: list[Document] = None,
    use_local_embedding: bool = True,
) -> Chroma:
    """
    创建或加载 ChromaDB 向量存储

    Args:
        documents: 文档块列表（None=加载已有数据）
        use_local_embedding: 是否用本地 Embedding
    """
    embedding = create_embedding(use_local=use_local_embedding)
    persist_dir = settings.CHROMA_PERSIST_DIR

    if documents:
        print(f"正在 Embedding {len(documents)} 个文档块...")
        embed_name = "本地 HuggingFace" if use_local_embedding else "OpenAI API"
        print(f"  Embedding 模型: {embed_name}")
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embedding,
            collection_name=COLLECTION_NAME,
            persist_directory=persist_dir,
        )
        print(f"✓ 已存入 ChromaDB ({persist_dir})")
        return vectorstore
    else:
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embedding,
            persist_directory=persist_dir,
        )


def search(query: str, k: int = 5) -> list[Document]:
    """相似度检索"""
    vectorstore = create_vector_store()
    return vectorstore.similarity_search(query, k=k)


def search_with_scores(query: str, k: int = 5) -> list[tuple[Document, float]]:
    """带分数的检索（分数越小越相似）"""
    vectorstore = create_vector_store()
    return vectorstore.similarity_search_with_score(query, k=k)
