'use client';
import { apiAsk } from '@/lib/api';
import React from 'react';

type Message = {
  role: 'user' | 'assistant';
  content: string;
  citations?: { title: string; section?: string }[];
  chunks?: { title: string; section?: string; text: string }[];
};

export default function Chat() {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [q, setQ] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const send = async () => {
    if (!q.trim()) return;
    const my = { role: 'user' as const, content: q };
    setMessages((m) => [...m, my]);
    setQ('');
    setLoading(true);
    try {
      const res = await apiAsk(q);
      const ai: Message = {
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        chunks: res.chunks,
      };
      setMessages((m) => [...m, ai]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: 'Error: ' + e.message },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='card'>
      <h2 style={{ margin: '0 0 1rem 0', color: '#2d3748', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        💬 Chat
      </h2>
      
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>👋 Hi! I'm your AI assistant. Ask me about policies, products, shipping, or returns.</p>
            <div className="suggested-questions">
              <p><strong>Try asking:</strong></p>
              <button 
                className="suggestion-btn"
                onClick={() => setQ("Can a customer return a damaged blender after 20 days?")}
              >
                "Can a customer return a damaged blender after 20 days?"
              </button>
              <button 
                className="suggestion-btn"
                onClick={() => setQ("What's the shipping SLA to East Malaysia for bulky items?")}
              >
                "What's the shipping SLA to East Malaysia for bulky items?"
              </button>
            </div>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <div className="message-header">
              <span className="message-role">
                {m.role === 'user' ? '👤 You' : '🤖 AI Assistant'}
              </span>
            </div>
            <div 
              className="message-content" 
              dangerouslySetInnerHTML={{ 
                __html: m.content
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\n/g, '<br>')
              }} 
            />
            
            {m.citations && m.citations.length > 0 && (
              <div className="citations">
                <div className="citations-label">📚 Sources:</div>
                {m.citations.map((c, idx) => (
                  <span key={idx} className='badge' title={c.section || 'Document source'}>
                    {c.title}
                  </span>
                ))}
              </div>
            )}
            
            {m.chunks && m.chunks.length > 0 && (
              <details className="chunks-details">
                <summary className="chunks-summary">🔍 View supporting text ({m.chunks.length} sources)</summary>
                <div className="chunks-container">
                  {m.chunks.map((c, idx) => (
                    <div key={idx} className='chunk-card'>
                      <div className="chunk-header">
                        📄 <strong>{c.title}</strong>
                        {c.section && <span className="chunk-section"> → {c.section}</span>}
                      </div>
                      <div className="chunk-text">{c.text}</div>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}
        
        {loading && (
          <div className="message assistant">
            <div className="message-header">
              <span className="message-role">🤖 AI Assistant</span>
            </div>
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input">
        <input
          type="text"
          placeholder='Ask about policies, products, shipping, returns...'
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="chat-input-field"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !loading && q.trim()) send();
          }}
        />
        <button
          onClick={send}
          disabled={loading || !q.trim()}
          className="btn-primary chat-send-btn"
        >
          {loading ? '⏳' : '📤'}
        </button>
      </div>
    </div>
  );
}
