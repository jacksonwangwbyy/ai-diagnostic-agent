"""测试：文档加载器"""
from src.rag.loader import load_markdown, load_directory


class TestLoadMarkdown:

    def test_load_markdown_file(self, tmp_markdown_file):
        docs = load_markdown(str(tmp_markdown_file))
        assert len(docs) == 1
        assert "标题一" in docs[0].page_content
        assert docs[0].metadata["file_type"] == "markdown"
        assert docs[0].metadata["filename"] == "test_doc.md"

    def test_load_markdown_metadata(self, tmp_markdown_file):
        docs = load_markdown(str(tmp_markdown_file))
        assert "source" in docs[0].metadata
        assert "filename" in docs[0].metadata


class TestLoadDirectory:

    def test_load_directory_mixed(self, tmp_path):
        """加载包含多种格式的目录"""
        (tmp_path / "doc1.md").write_text("# Markdown 文档\n\n内容", encoding="utf-8")
        (tmp_path / "doc2.txt").write_text("纯文本文档", encoding="utf-8")
        (tmp_path / "ignore.json").write_text("{}", encoding="utf-8")
        docs = load_directory(str(tmp_path))
        assert len(docs) == 2

    def test_load_empty_directory(self, tmp_path):
        docs = load_directory(str(tmp_path))
        assert len(docs) == 0

    def test_load_subdirectory(self, tmp_path):
        """递归加载子目录"""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.md").write_text("# 嵌套文档", encoding="utf-8")
        docs = load_directory(str(tmp_path))
        assert len(docs) == 1
        assert "嵌套文档" in docs[0].page_content
