"""
API 路由

学习要点：
1. APIRouter - 模块化路由管理
2. SSE (StreamingResponse) - 流式输出，前端可以逐 token 展示
3. 会话管理 - Redis 持久化（降级到内存），通过 session_id 维护多轮对话
4. 错误处理 - 统一的错误响应格式
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from src.api.models import (
    ChatRequest, ChatResponse,
    DiagnoseRequest, DiagnoseResponse,
    RAGQueryRequest, RAGQueryResponse,
)
from src.rag.chain import rag_query
from src.agent.diagnostic_agent import create_diagnostic_agent
from src.utils.session_store import create_session_store

router = APIRouter()

# 会话存储（优先 Redis，连接失败自动降级到内存）
_store = create_session_store()


# ==================== 普通对话 ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """普通对话（非流式）"""
    try:
        session = _store.get(req.session_id, req.provider)
        answer = session.chat(req.message)
        # 对话后保存到 Redis
        if hasattr(_store, 'save'):
            _store.save(req.session_id)
        return ChatResponse(
            answer=answer,
            provider=session.provider_name,
            session_id=req.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """普通对话（SSE 流式输出）"""
    session = _store.get(req.session_id, req.provider)

    async def event_generator():
        try:
            for token in session.stream_chat(req.message):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            # 流式结束后保存
            if hasattr(_store, 'save'):
                _store.save(req.session_id)
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# ==================== Agent 诊断 ====================

@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(req: DiagnoseRequest):
    """Agent 诊断（工具调用 + 多步推理）"""
    try:
        agent = create_diagnostic_agent(req.provider)
        result = agent.invoke({
            "messages": [HumanMessage(content=req.question)],
        })

        messages = result["messages"]

        tools_used = []
        steps = []
        for msg in messages:
            msg_type = type(msg).__name__
            if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tools_used.append(tc["name"])
                    steps.append({
                        "type": "tool_call",
                        "tool": tc["name"],
                        "args": tc["args"],
                    })
            elif msg_type == "ToolMessage":
                steps.append({
                    "type": "tool_result",
                    "tool": msg.name,
                    "result": msg.content[:300],
                })

        final_content = messages[-1].content
        if isinstance(final_content, list):
            final_content = "".join(
                block["text"] for block in final_content
                if isinstance(block, dict) and block.get("type") == "text"
            )

        return DiagnoseResponse(
            result=final_content,
            tools_used=list(set(tools_used)),
            steps=steps,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diagnose/stream")
async def diagnose_stream(req: DiagnoseRequest):
    """Agent 诊断（SSE 流式）"""
    agent = create_diagnostic_agent(req.provider)

    async def event_generator():
        try:
            for event in agent.stream(
                {"messages": [HumanMessage(content=req.question)]},
                stream_mode="updates",
            ):
                for node_name, node_output in event.items():
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        msg_type = type(msg).__name__
                        if msg_type == "AIMessage":
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': tc['name'], 'args': tc['args']}, ensure_ascii=False)}\n\n"
                            elif msg.content:
                                content = msg.content
                                if isinstance(content, list):
                                    content = "".join(
                                        block["text"] for block in content
                                        if isinstance(block, dict) and block.get("type") == "text"
                                    )
                                yield f"data: {json.dumps({'type': 'answer', 'content': content}, ensure_ascii=False)}\n\n"
                        elif msg_type == "ToolMessage":
                            yield f"data: {json.dumps({'type': 'tool_result', 'tool': msg.name, 'result': msg.content[:300]}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# ==================== RAG 检索 ====================

@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_search(req: RAGQueryRequest):
    """RAG 知识库检索问答"""
    try:
        result = rag_query(req.query, k=req.top_k)
        return RAGQueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 会话管理 ====================

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清除指定会话的历史"""
    deleted = _store.delete(session_id)
    if deleted:
        return {"message": f"会话 {session_id} 已清除"}
    return {"message": f"会话 {session_id} 不存在"}


@router.get("/sessions")
async def list_sessions():
    """列出所有活跃会话"""
    return {"sessions": _store.list_sessions()}
