# API 集成指南

## 基础信息

- 服务地址：`http://localhost:8000`
- Swagger 文档：`http://localhost:8000/docs`
- 内容类型：`application/json`

## 限流规则

| 端点 | 限制 |
|------|------|
| `/api/chat`, `/api/chat/stream` | 30 次/分钟/IP |
| `/api/diagnose`, `/api/diagnose/stream` | 10 次/分钟/IP |
| `/api/rag/query` | 20 次/分钟/IP |

超限返回 `429 Too Many Requests`。

## 端点说明

### 普通对话（非流式）

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "制冰机不出冰怎么办？",
    "provider": "claude",
    "session_id": "user-001"
  }'
```

响应：
```json
{
  "answer": "...",
  "provider": "claude",
  "session_id": "user-001"
}
```

### Agent 诊断（单 Agent）

```bash
curl -X POST http://localhost:8000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "question": "制冰机报错 E03",
    "provider": "claude",
    "use_multi_agent": false
  }'
```

### Agent 诊断（多 Agent 协作）

```bash
curl -X POST http://localhost:8000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "question": "制冰机故障了，怎么修",
    "use_multi_agent": true,
    "use_llm_routing": false
  }'
```

响应新增字段：
```json
{
  "result": "...",
  "route": "diagnose+repair",
  "agents_used": ["diagnostic", "repair"]
}
```

### SSE 流式诊断

```javascript
const response = await fetch('/api/diagnose/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: '设备故障', provider: 'claude' }),
})

const reader = response.body.getReader()
// 事件类型: tool_call | tool_result | answer | error | done
```

### RAG 知识库检索

```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "制冰机维护", "top_k": 5}'
```

### 会话管理

```bash
# 列出会话
curl http://localhost:8000/api/sessions

# 清除会话
curl -X DELETE http://localhost:8000/api/session/user-001
```

## 多 Agent 路由规则

| 请求关键词 | 路由 | 使用的 Agent |
|-----------|------|-------------|
| 故障/报错/不工作 | `diagnose` | 诊断 Agent |
| 维修/怎么修/备件 | `repair` | 维修 Agent |
| 状态/健康/检查 | `monitor` | 监控 Agent |
| 故障 + 维修 | `diagnose+repair` | 诊断 → 维修 |
