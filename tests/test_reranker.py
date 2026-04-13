"""测试：CrossEncoder 重排序"""
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from src.rag.reranker import rerank


class TestRerank:

    def test_rerank_reorders_by_score(self):
        """重排序按分数降序排列"""
        docs = [
            Document(page_content="不太相关的内容", metadata={"filename": "a.md"}),
            Document(page_content="非常相关的制冰机故障", metadata={"filename": "b.md"}),
            Document(page_content="完全无关", metadata={"filename": "c.md"}),
        ]
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.2, 0.9, 0.1]

        with patch("src.rag.reranker._get_reranker", return_value=mock_model):
            result = rerank("制冰机故障", docs, top_k=2)
            assert len(result) == 2
            assert result[0][0].metadata["filename"] == "b.md"
            assert result[1][0].metadata["filename"] == "a.md"
            assert isinstance(result[0][1], float)

    def test_rerank_top_k_limit(self):
        """top_k 限制返回数量"""
        docs = [Document(page_content=f"doc {i}", metadata={}) for i in range(10)]
        mock_model = MagicMock()
        mock_model.predict.return_value = list(range(10))

        with patch("src.rag.reranker._get_reranker", return_value=mock_model):
            result = rerank("query", docs, top_k=3)
            assert len(result) == 3

    def test_rerank_empty_docs(self):
        """空文档列表"""
        result = rerank("query", [], top_k=5)
        assert result == []

    def test_rerank_fewer_than_top_k(self):
        """文档数少于 top_k"""
        docs = [Document(page_content="only one", metadata={})]
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5]

        with patch("src.rag.reranker._get_reranker", return_value=mock_model):
            result = rerank("query", docs, top_k=5)
            assert len(result) == 1
            assert result[0][1] == 0.5
