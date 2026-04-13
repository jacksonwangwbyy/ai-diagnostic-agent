"""测试：search_knowledge_base 工具"""
from unittest.mock import patch
from langchain_core.documents import Document
from src.tools.knowledge_search import search_knowledge_base


class TestSearchKnowledgeBase:

    def test_no_results(self):
        """检索无结果"""
        with patch("src.tools.knowledge_search.search_with_scores", return_value=[]):
            result = search_knowledge_base.invoke({"query": "不存在的内容"})
            assert "没有找到" in result

    def test_results_with_headers(self):
        """检索结果包含标题层级"""
        doc = Document(
            page_content="制冰机需要定期除霜维护",
            metadata={"filename": "ice-manual.md", "h1": "设备维护", "h2": "制冰机"},
        )
        with patch("src.tools.knowledge_search.search_with_scores", return_value=[(doc, 0.85)]):
            result = search_knowledge_base.invoke({"query": "制冰机维护"})
            assert "ice-manual.md" in result
            assert "设备维护 > 制冰机" in result
            assert "制冰机需要定期除霜维护" in result

    def test_results_without_headers(self):
        """检索结果没有标题信息"""
        doc = Document(
            page_content="操作说明内容",
            metadata={"filename": "guide.pdf"},
        )
        with patch("src.tools.knowledge_search.search_with_scores", return_value=[(doc, 0.7)]):
            result = search_knowledge_base.invoke({"query": "操作说明"})
            assert "guide.pdf" in result
            assert "操作说明内容" in result

    def test_multiple_results(self):
        """多个检索结果"""
        docs = [
            (Document(page_content=f"文档内容 {i}", metadata={"filename": f"doc{i}.md"}), 0.9 - i * 0.1)
            for i in range(3)
        ]
        with patch("src.tools.knowledge_search.search_with_scores", return_value=docs):
            result = search_knowledge_base.invoke({"query": "搜索"})
            assert "[1]" in result
            assert "[2]" in result
            assert "[3]" in result

    def test_content_truncation(self):
        """长内容截断到 500 字符"""
        long_content = "A" * 1000
        doc = Document(page_content=long_content, metadata={"filename": "long.md"})
        with patch("src.tools.knowledge_search.search_with_scores", return_value=[(doc, 0.5)]):
            result = search_knowledge_base.invoke({"query": "test"})
            # page_content[:500] 应该只有 500 个 A
            content_after_header = result.split("\n")[-1]
            assert len(content_after_header) == 500
