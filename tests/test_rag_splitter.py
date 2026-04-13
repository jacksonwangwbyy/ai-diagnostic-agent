"""测试：文本切分器"""
from langchain_core.documents import Document
from src.rag.splitter import create_text_splitter, create_markdown_splitter, split_documents


class TestCreateTextSplitter:

    def test_default_params(self):
        splitter = create_text_splitter()
        assert splitter._chunk_size == 1000
        assert splitter._chunk_overlap == 200

    def test_custom_params(self):
        splitter = create_text_splitter(chunk_size=500, chunk_overlap=50)
        assert splitter._chunk_size == 500
        assert splitter._chunk_overlap == 50


class TestCreateMarkdownSplitter:

    def test_split_by_headers(self):
        splitter = create_markdown_splitter()
        text = "# 标题\n\n内容一\n\n## 子标题\n\n内容二"
        chunks = splitter.split_text(text)
        assert len(chunks) >= 1


class TestSplitDocuments:

    def test_split_markdown_doc(self):
        doc = Document(
            page_content="# 标题\n\n内容段落一。\n\n## 子标题\n\n内容段落二。",
            metadata={"source": "test.md", "filename": "test.md", "file_type": "markdown"},
        )
        chunks = split_documents([doc], chunk_size=100, chunk_overlap=20)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.metadata["filename"] == "test.md"

    def test_split_text_doc(self):
        doc = Document(
            page_content="这是一段很长的文本。" * 100,
            metadata={"source": "test.txt", "filename": "test.txt", "file_type": "text"},
        )
        chunks = split_documents([doc], chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1

    def test_short_doc_no_split(self):
        doc = Document(
            page_content="很短的文档",
            metadata={"source": "short.txt", "filename": "short.txt", "file_type": "text"},
        )
        chunks = split_documents([doc], chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 1

    def test_markdown_headers_in_metadata(self):
        doc = Document(
            page_content="# 一级标题\n\n内容\n\n## 二级标题\n\n更多内容",
            metadata={"source": "test.md", "filename": "test.md", "file_type": "markdown"},
        )
        chunks = split_documents([doc], chunk_size=1000, chunk_overlap=200)
        has_header = any("h1" in c.metadata or "h2" in c.metadata for c in chunks)
        assert has_header
