"""
请求/响应数据模型
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """普通对话请求"""
    message: str = Field(..., description="用户消息")
    provider: str = Field(default="claude", description="模型 provider: claude / openai")
    session_id: str = Field(default="default", description="会话 ID，用于多轮对话")


class ChatResponse(BaseModel):
    """普通对话响应"""
    answer: str
    provider: str
    session_id: str


class DiagnoseRequest(BaseModel):
    """Agent 诊断请求"""
    question: str = Field(..., description="故障描述")
    provider: str = Field(default="claude", description="模型 provider")
    device_id: str = Field(default="BAR-001", description="设备编号")
    use_multi_agent: bool = Field(default=False, description="是否使用多 Agent 协作")
    use_llm_routing: bool = Field(default=False, description="多 Agent 模式下使用 LLM 精确路由")


class DiagnoseResponse(BaseModel):
    """Agent 诊断响应"""
    result: str
    tools_used: list[str] = []
    steps: list[dict] = []
    route: str = ""
    agents_used: list[str] = []


class RAGQueryRequest(BaseModel):
    """RAG 检索请求"""
    query: str = Field(..., description="查询内容")
    top_k: int = Field(default=5, description="返回结果数量")


class RAGQueryResponse(BaseModel):
    """RAG 检索响应"""
    answer: str
    sources: list[str]
    context_count: int
