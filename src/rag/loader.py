"""
文档加载器 - 加载各种格式的文档到 LangChain Document 对象

学习要点：
1. Document 对象 - LangChain 中文档的统一抽象，包含 page_content + metadata
2. 不同格式的 Loader - 每种文件格式有对应的加载器
3. metadata 的作用 - 记录文档来源、页码等信息，RAG 检索时用于引用溯源
"""
import os
from pathlib import Path
from langchain_core.documents import Document


def load_markdown(file_path: str) -> list[Document]:
    """
    加载 Markdown 文件为 Document 列表

    每个文件生成一个 Document，metadata 中记录来源信息。
    """
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return [Document(
        page_content=content,
        metadata={
            "source": str(path),
            "filename": path.name,
            "file_type": "markdown",
        }
    )]


def load_pdf(file_path: str) -> list[Document]:
    """
    加载 PDF 文件，每页生成一个 Document

    学习要点：pypdf 按页读取，每页是一个独立的 Document，
    metadata 中记录页码，方便检索时定位到具体页。
    """
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    documents = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            documents.append(Document(
                page_content=text,
                metadata={
                    "source": file_path,
                    "filename": Path(file_path).name,
                    "file_type": "pdf",
                    "page": i + 1,
                }
            ))

    return documents


def load_directory(directory: str) -> list[Document]:
    """
    递归加载目录下所有支持的文档

    支持格式：.md, .pdf, .txt
    """
    documents = []
    supported = {".md": load_markdown, ".pdf": load_pdf, ".txt": load_markdown}

    for root, _, files in os.walk(directory):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in supported:
                file_path = os.path.join(root, file)
                try:
                    docs = supported[ext](file_path)
                    documents.extend(docs)
                    print(f"  ✓ 加载: {file} ({len(docs)} 个文档块)")
                except Exception as e:
                    print(f"  ✗ 失败: {file} - {e}")

    print(f"\n共加载 {len(documents)} 个文档块")
    return documents
