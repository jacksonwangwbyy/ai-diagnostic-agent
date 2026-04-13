import { useState, useRef, useEffect } from 'react'
import './App.css'

interface Message {
  role: 'user' | 'assistant' | 'tool-call' | 'tool-result' | 'error'
  content: string
  tool?: string
}

const EXAMPLES = [
  '制冰机报错 E03，怎么回事？',
  '查一下所有设备状态',
  '咖啡机无法初始化，如何排查？',
  '机械臂碰撞后怎么恢复？',
]

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'agent' | 'chat'>('agent')
  const [provider, setProvider] = useState<'claude' | 'openai'>('claude')
  const [useMultiAgent, setUseMultiAgent] = useState(false)
  const [lastError, setLastError] = useState<string | null>(null)
  const [lastInput, setLastInput] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text?: string) => {
    const userMessage = text || input.trim()
    if (!userMessage || loading) return

    setInput('')
    setLastInput(userMessage)
    setLastError(null)
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    if (mode === 'agent') {
      await sendAgentDiagnose(userMessage)
    } else {
      await sendChatStream(userMessage)
    }

    setLoading(false)
  }

  const retry = () => {
    if (lastInput) {
      setMessages(prev => prev.slice(0, -1)) // remove last error
      sendMessage(lastInput)
    }
  }

  const clearSession = async () => {
    setMessages([])
    setLastError(null)
    try {
      await fetch('/api/session/default', { method: 'DELETE' })
    } catch {}
  }

  const exportReport = () => {
    const text = messages
      .filter(m => m.role === 'assistant')
      .map(m => m.content)
      .join('\n\n---\n\n')
    if (!text) return
    navigator.clipboard.writeText(text).then(() => {
      alert('诊断报告已复制到剪贴板')
    })
  }

  const sendChatStream = async (text: string) => {
    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, provider }),
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.token) {
              setMessages(prev => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (last.role === 'assistant') last.content += data.token
                return updated
              })
            }
            if (data.error) {
              setLastError(data.error)
              setMessages(prev => [...prev, { role: 'error', content: data.error }])
            }
          } catch {}
        }
      }
    } catch (err: any) {
      const msg = `请求失败: ${err.message}`
      setLastError(msg)
      setMessages(prev => [...prev, { role: 'error', content: msg }])
    }
  }

  const sendAgentDiagnose = async (text: string) => {
    try {
      const response = await fetch('/api/diagnose/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text, provider, use_multi_agent: useMultiAgent }),
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'tool_call') {
              setMessages(prev => [...prev, {
                role: 'tool-call',
                content: `调用工具: ${data.tool}(${JSON.stringify(data.args)})`,
                tool: data.tool,
              }])
            } else if (data.type === 'tool_result') {
              setMessages(prev => [...prev, {
                role: 'tool-result',
                content: data.result,
                tool: data.tool,
              }])
            } else if (data.type === 'answer') {
              setMessages(prev => [...prev, { role: 'assistant', content: data.content }])
            } else if (data.type === 'error') {
              setLastError(data.message)
              setMessages(prev => [...prev, { role: 'error', content: data.message }])
            }
          } catch {}
        }
      }
    } catch (err: any) {
      const msg = `请求失败: ${err.message}`
      setLastError(msg)
      setMessages(prev => [...prev, { role: 'error', content: msg }])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const hasAssistantMessages = messages.some(m => m.role === 'assistant')

  return (
    <div className="app">
      {/* Header */}
      <div className="header">
        <h1>SMYZE 设备故障诊断 Agent</h1>
        <div className="header-right">
          <div className="mode-toggle">
            <button className={mode === 'agent' ? 'active' : ''} onClick={() => setMode('agent')}>
              Agent 诊断
            </button>
            <button className={mode === 'chat' ? 'active' : ''} onClick={() => setMode('chat')}>
              普通对话
            </button>
          </div>
          <select
            value={provider}
            onChange={e => setProvider(e.target.value as 'claude' | 'openai')}
            title="选择模型"
          >
            <option value="claude">Claude</option>
            <option value="openai">OpenAI</option>
          </select>
          {mode === 'agent' && (
            <label className="toggle-label" title="启用多 Agent 协作（诊断+维修+监控）">
              <input
                type="checkbox"
                checked={useMultiAgent}
                onChange={e => setUseMultiAgent(e.target.checked)}
              />
              多 Agent
            </label>
          )}
          {hasAssistantMessages && (
            <button className="icon-btn" onClick={exportReport} title="复制诊断报告">
              导出
            </button>
          )}
          {messages.length > 0 && (
            <button className="icon-btn" onClick={clearSession} title="清除会话">
              清除
            </button>
          )}
          <div className="status-dot" title="服务在线" />
        </div>
      </div>

      {/* Messages */}
      <div className="messages">
        {messages.length === 0 ? (
          <div className="welcome">
            <h2>设备故障诊断助手</h2>
            <p>
              {mode === 'agent'
                ? '描述故障现象，Agent 会自动查询设备状态、读取日志、检索知识库，给出诊断报告。'
                : '直接和 AI 对话，讨论设备相关问题。'}
            </p>
            <div className="examples">
              {EXAMPLES.map((ex, i) => (
                <button key={i} onClick={() => sendMessage(ex)}>{ex}</button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                {msg.role === 'tool-call' && <div className="label">工具调用</div>}
                {msg.role === 'tool-result' && <div className="label">{msg.tool} 返回</div>}
                {msg.role === 'error' && (
                  <div className="error-actions">
                    <span>错误</span>
                    <button onClick={retry}>重试</button>
                  </div>
                )}
                {msg.content}
              </div>
            ))}
            {loading && (
              <div className="typing-indicator">
                <span>.</span><span>.</span><span>.</span> {mode === 'agent' ? 'Agent 正在推理' : '思考中'}
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-area">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={mode === 'agent' ? '描述设备故障现象...' : '输入消息...'}
          disabled={loading}
        />
        <button onClick={() => sendMessage()} disabled={loading || !input.trim()}>
          发送
        </button>
      </div>
    </div>
  )
}

export default App
