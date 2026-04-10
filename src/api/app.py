"""
FastAPI 服务入口

学习要点：
1. FastAPI - 现代 Python Web 框架，自动生成 Swagger 文档
2. SSE (Server-Sent Events) - 流式输出的标准方式，比 WebSocket 更轻量
3. Pydantic Model - 请求/响应的数据模型定义，自动校验
4. 中间件 - CORS 跨域、请求日志等
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

app = FastAPI(
    title="SMYZE 设备故障诊断 Agent API",
    description="基于 LangChain + RAG 的智能设备故障诊断服务",
    version="1.0.0",
)

# CORS 跨域（允许前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "ai-diagnostic-agent"}
