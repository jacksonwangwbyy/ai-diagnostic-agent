"""测试：混合检索（BM25 + RRF + 查询改写）"""
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from src.rag.hybrid_search import (
    BM25Index,
    rrf_fuse,
    rewrite_query,
    enhanced_search,
    _tokenize,
)


class TestTokenize:

    def test_chinese_text(self):
        tokens = _tokenize("制冰机故障")
        assert "制" in tokens
        assert "制冰" in tokens
        assert "故障" in tokens

    def test_english_text(self):
        tokens = _tokenize("docker restart")
        assert "docker" in tokens
        assert "restart" in tokens

    def test_mixed_text(self):
        tokens = _tokenize("bar_middleware 中间件")
        # 下划线会被分割为两个 token
        assert "bar" in tokens
        assert "middleware" in tokens
        assert "中" in tokens


class TestBM25Index:

    def test_build_and_search(self):
        docs = [
            Document(page_content="制冰机压缩机温度过高导致停机", metadata={"filename": "a.md"}),
            Document(page_content="咖啡机水温不达标需要检查加热元件", metadata={"filename": "b.md"}),
            Document(page_content="机械臂归零失败请检查限位开关", metadata={"filename": "c.md"}),
        ]
        index = BM25Index(docs)
        results = index.search("制冰机温度", k=2)
        assert len(results) <= 2
        # 第一个结果应该是制冰机相关
        assert "制冰" in results[0].page_content

    def test_search_empty_index(self):
        index = BM25Index([])
        results = index.search("任何查询", k=5)
        assert results == []

    def test_search_k_larger_than_docs(self):
        docs = [Document(page_content="唯一文档内容", metadata={})]
        index = BM25Index(docs)
        results = index.search("文档", k=10)
        assert len(results) <= 1


class TestRRFFuse:

    def test_fuse_two_lists(self):
        doc_a = Document(page_content="A", metadata={"id": "a"})
        doc_b = Document(page_content="B", metadata={"id": "b"})
        doc_c = Document(page_content="C", metadata={"id": "c"})

        list1 = [doc_a, doc_b, doc_c]
        list2 = [doc_c, doc_a, doc_b]

        fused = rrf_fuse([list1, list2], k=60, top_k=3)
        assert len(fused) == 3

    def test_fuse_empty_lists(self):
        result = rrf_fuse([[], []], k=60, top_k=5)
        assert result == []

    def test_fuse_single_list(self):
        docs = [Document(page_content=f"doc{i}", metadata={}) for i in range(3)]
        result = rrf_fuse([docs], k=60, top_k=3)
        assert len(result) == 3


class TestRewriteQuery:

    def test_rewrite_returns_string(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="制冰机 出冰量不足 故障排查")

        result = rewrite_query("冰不够了", mock_llm)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_rewrite_fallback_on_error(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API error")

        result = rewrite_query("冰不够了", mock_llm)
        assert result == "冰不够了"

    def test_rewrite_no_llm(self):
        result = rewrite_query("原始查询", llm=None)
        assert result == "原始查询"


class TestEnhancedSearch:

    def test_enhanced_search_returns_results(self):
        mock_doc = Document(page_content="结果1", metadata={"filename": "a.md"})
        mock_results = [(mock_doc, 0.9)]

        with patch("src.rag.hybrid_search.search_with_scores", return_value=mock_results):
            with patch("src.rag.hybrid_search._get_bm25_index") as mock_bm25:
                mock_bm25_inst = MagicMock()
                mock_bm25_inst.search.return_value = [mock_doc]
                mock_bm25.return_value = mock_bm25_inst

                with patch("src.rag.hybrid_search.rerank", side_effect=lambda q, d, top_k: d[:top_k]):
                    results = enhanced_search("制冰机故障", k=5)
                    assert len(results) >= 1
                    assert isinstance(results[0], tuple)
                    assert isinstance(results[0][0], Document)

    def test_enhanced_search_no_bm25(self):
        """BM25 索引不可用时仅用向量检索"""
        mock_doc = Document(page_content="结果", metadata={})
        mock_results = [(mock_doc, 0.8)]

        with patch("src.rag.hybrid_search.search_with_scores", return_value=mock_results):
            with patch("src.rag.hybrid_search._get_bm25_index", return_value=None):
                with patch("src.rag.hybrid_search.rerank", side_effect=lambda q, d, top_k: d[:top_k]):
                    results = enhanced_search("查询", k=5)
                    assert len(results) >= 1
