import React, { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { Send, Bot, User, Loader2 } from 'lucide-react'

const API_BASE = 'http://localhost:8000/api'

function ChatPanel({ onMessage }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m TraceLoop Assistant. You can tell me about material transactions like:\n\n• "Purchased 300kg PET from GreenCorp yesterday"\n• "Dispatched 200kg to PlastiCo"\n• "Show all batches"\n• "How much material was dispatched last week?"'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await axios.post(`${API_BASE}/chat`, { text: userMessage })
      
      const assistantMessage = response.data.message || 
        (response.data.success ? 'Transaction recorded successfully!' : 'Something went wrong.')
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: assistantMessage,
        data: response.data
      }])
      
      if (response.data.success && onMessage) {
        onMessage()
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I couldn\'t process that. Please try again.' 
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-200px)]">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-emerald-400" />
              </div>
            )}
            
            <div
              className={`max-w-2xl p-4 rounded-2xl ${
                msg.role === 'user'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-700 text-slate-100'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              
              {msg.data?.parsed && (
                <div className="mt-3 p-3 bg-slate-800/50 rounded-lg text-sm">
                  <p className="text-slate-400 mb-2">Extracted:</p>
                  <div className="space-y-1">
                    {msg.data.parsed.entities?.quantity_kg && (
                      <p><span className="text-slate-400">Quantity:</span> {msg.data.parsed.entities.quantity_kg} kg</p>
                    )}
                    {msg.data.parsed.entities?.material_type && (
                      <p><span className="text-slate-400">Material:</span> {msg.data.parsed.entities.material_type}</p>
                    )}
                    {msg.data.parsed.entities?.vendor && (
                      <p><span className="text-slate-400">Vendor:</span> {msg.data.parsed.entities.vendor}</p>
                    )}
                    {msg.data.batch_id && (
                      <p><span className="text-slate-400">Batch ID:</span> {msg.data.batch_id}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
            
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-blue-400" />
              </div>
            )}
          </div>
        ))}
        
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
              <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
            </div>
            <div className="bg-slate-700 p-4 rounded-2xl">
              <p className="text-slate-400">Processing...</p>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-slate-700">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message or transaction..."
            className="flex-1 input-chat"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatPanel
