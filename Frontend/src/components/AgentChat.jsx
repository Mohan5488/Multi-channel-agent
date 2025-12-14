import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import MarkdownRenderer from './MarkdownRenderer';

export default function AgentChat({setLoggedIn}) {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [waitingForFeedback, setWaitingForFeedback] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const chatBoxRef = useRef(null);
  const { id } = useParams();
  const navigate = useNavigate();
  const Token = localStorage.getItem("token")

  const handleChange = (e) => setQuery(e.target.value);
  const handleFeedbackChange = (e) => setFeedbackMessage(e.target.value);

  const handleKeyDownChange = (e) => {
    if (e.key === 'Enter' && !waitingForFeedback) {
      handleSubmit(e);
    }
  };

  console.log("ID OUTSIDE -", id)

  useEffect(() => {
    if (!id) {
      setMessages([]);
      setThreadId(null);
    }
  }, [id])

  useEffect(()=>{
    if (!id) return;
    setThreadId(id)
    const fetchData = async ()=>{
      console.log("ID IN FUNCTION -", id)
      const res = await fetch(`http://127.0.0.1:8000/v1/threads/${id}/history/`, {
        method : "GET",
        headers: { 
          'Content-Type': 'application/json',
          "Authorization": `Token ${Token}`,
        },
      });
      if (!res.ok) throw new Error('Failed to fetch data');

      const response = await res.json();
      console.log(response)
      const history = Array.isArray(response?.history) ? response.history : [];
      const normalized = history
        .map((item) => ({
          type: item?.type || (item?.role === 'user' ? 'HumanMessage' : 'AIMessage'),
          content: String(item?.content ?? '')
        }))
        .filter((m) => m.type !== 'AIMessage' || m.content.trim() !== '');
      setMessages(normalized)
    }
    fetchData()
  }, [id])

  const handleFeedbackKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleFeedbackSubmit(e);
    }
  };

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages, loading]);

  // -- network logic kept the same --
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setMessages((prev) => [...prev, { type: 'HumanMessage', content: query }]);
    setLoading(true);
    setQuery('');

    try {
      const url = threadId
        ? `http://127.0.0.1:8000/v1/messages/?thread_id=${threadId}`
        : 'http://127.0.0.1:8000/v1/messages/';

      const res = await fetch(url, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          "Authorization": `Token ${Token}`,
        },
        body: JSON.stringify({ user_prompt: query }),
      });

      if (!res.ok) throw new Error('Failed to fetch data');

      const response = await res.json();
      if (response.thread_id && !threadId) setThreadId(response.thread_id);
      if (response.thread_id && !id) {
        navigate(`/chat/${response.thread_id}`);
      }

      let botReply = '';
      let isInterrupt = false;

      if (response.status === 'interrupt') {
        isInterrupt = true;
        setWaitingForFeedback(true);
        // Build a clear interrupt message once
        botReply = `${response.message}${response.interrupt?.message ? `\n\n${response.interrupt.message}` : ''}`;
        if (response.interrupt?.preview) {
          botReply += `\n\n📋 Preview:\n${response.interrupt.preview}`;
        }
      } else if (response.status === 'success' || response.status === 'completed') {
        if (response.result) {
          if (response.result.message) botReply += `${response.result.message}`;
          if (response.result.content) botReply += `\n${response.result.content}`;
        } else {
          botReply = `${response.message || 'Done'}`;
        }
      } else {
        botReply = `${response.message || 'Workflow completed'}`;
      }

      if (String(botReply).trim() !== '') {
        setMessages((prev) => [...prev, { type: 'AIMessage', content: botReply, isInterrupt }]);
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { type: 'AIMessage', content: 'Sorry, something went wrong. Please try again.' }]);
    }

    setLoading(false);
  };

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!feedbackMessage.trim() || !threadId) return;

    setMessages((prev) => [...prev, { type: 'HumanMessage', content: `Feedback: ${feedbackMessage}` }]);
    setLoading(true);
    setFeedbackMessage('');
    setWaitingForFeedback(false);

    try {
      const res = await fetch(`http://127.0.0.1:8000/v1/resume/?thread_id=${threadId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: feedbackMessage }),
      });

      if (!res.ok) throw new Error('Failed to resume workflow');

      const response = await res.json();
      let botReply = '';

      if (response.status === 'interrupt') {
        setWaitingForFeedback(true);
        botReply = `${response.message}\n\n${response.interrupt?.message || ''}`;
        if (response.state?.preview) botReply += `\n\n${response.state.preview}`;
        if (response.interrupt?.preview) botReply += `\n\n📋 Preview:\n${response.interrupt.preview}`;
      } else if (response.status === 'success' || response.status === 'completed') {
        if (response.result) {
          if (response.result.message) botReply += `\n\n${response.result.message}`;
          if (response.result.content) botReply += `\n\n${response.result.content}`;
        }
      } else {
        botReply = `🤖 ${response.message || 'Workflow completed'}`;
      }

      if (String(botReply).trim() !== '') {
        setMessages((prev) => [...prev, { type : 'AIMessage', content: botReply, isInterrupt: response.status === 'interrupt' }]);
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { type: 'AIMessage', content: 'Sorry, something went wrong resuming the workflow.' }]);
    }

    setLoading(false);
  };

  // render helpers
  const renderBubble = (msg) => {
    const content = String(msg.content);
    const cls = `bubble ${msg.type === 'HumanMessage' ? 'bubble-user' : msg.isInterrupt ? 'bubble-interrupt' : 'bubble-bot'}`;
    
    // Use MarkdownRenderer for AI messages, plain text for user messages
    if (msg.type === 'AIMessage') {
      return (
        <div className={cls}>
          <MarkdownRenderer content={content} />
        </div>
      );
    }
    
    // For user messages, keep the simple line-by-line rendering
    const lines = content.split('\n').map((line, index) => {
      // Handle empty lines
      if (line.trim() === '') {
        return <br key={index} />;
      }
      return <div key={index}>{line}</div>;
    });
    
    return <div className={cls}>{lines}</div>;
  };

  
  const handleLogout = () => {
    localStorage.removeItem('token');

    setThreadId(null);
    setLoggedIn(false);
    setMessages([]);
    setWaitingForFeedback(false);

    navigate('/login');
  };

  const shouldShowLoading = loading && (messages.length === 0 || messages[messages.length - 1].type === 'HumanMessage');

  return (
    <div className="cgpt-bg">
      <div className="cgpt-shell">
        {/* Header */}
        <header className="cgpt-header">
          <div className="cgpt-left">
            <div className="logo">AI</div>
            <div className="meta">
              <div className="title">Multichannel Agent</div>
              <div className="subtitle">Compose emails, LinkedIn posts, search the web and more.</div>
            </div>
          </div>
          <div>
          <div className="thread">{threadId ? `Thread: ${threadId}` : ''}</div>
          </div>
        </header>

        {/* Chat area */}
        <main className="cgpt-main" ref={chatBoxRef}>
          {messages.length === 0 && (
            <div className="welcome">
              <h2>Welcome to Multichannel Agent</h2>
              <p>Ask me to compose emails, social posts, or run multi-step workflows.</p>
            </div>
          )}

          <div className="msg-list">
            {messages.map((msg, idx) => (
              <div key={idx} className={`msg ${msg.content === 'HumanMessage' ? 'msg-right' : 'msg-left'}`}>
                {msg.type !== 'HumanMessage' && <div className="avatar">B</div>}
                {renderBubble(msg)}
              </div>
            ))}

            {shouldShowLoading && (
              <div className="msg msg-left">
                <div className="avatar">B</div>
                <div className="bubble bubble-bot loading">
                  <span className="three-dots">
                    <span />
                    <span />
                    <span />
                  </span>
                </div>
              </div>
            )}
          </div>
        </main>

        {/* Footer / Input */}
        <footer className="cgpt-footer">
          {waitingForFeedback ? (
            <form onSubmit={handleFeedbackSubmit} className="input-form">
              <input
                aria-label="feedback-input"
                placeholder="Provide your feedback..."
                onChange={handleFeedbackChange}
                value={feedbackMessage}
                onKeyDown={handleFeedbackKeyDown}
                required
                readOnly={loading}
              />
              <button className="send-btn feedback">Send feedback</button>
            </form>
          ) : (
            <form onSubmit={handleSubmit} className="input-form">
              <input
                aria-label="message-input"
                placeholder="Type your message..."
                onChange={handleChange}
                value={query}
                onKeyDown={handleKeyDownChange}
                required
                readOnly={loading}
              />
              <button className="send-btn">Send</button>
            </form>
          )}
        </footer>
      </div>

      <style>{`
        /* Page background similar to ChatGPT */
        .cgpt-bg { height:100vh; background:linear-gradient(135deg,#5b6be6 0%, #7b5fd8 100%); padding:28px; display:flex; align-items:center; justify-content:center; }

        /* Shell */
        .cgpt-shell { width:100%; max-width:1120px; height:calc(100vh - 56px); background:#ffffff; border-radius:12px; box-shadow:0 20px 50px rgba(2,6,23,0.35); overflow:hidden; display:flex; flex-direction:column; border:1px solid rgba(15,23,42,0.06); }

        /* Header */
        .cgpt-header { display:flex; align-items:center; justify-content:space-between; padding:18px 20px; border-bottom:1px solid #eef2ff; backdrop-filter :blur(40px)}
        .cgpt-left { display:flex; align-items:center; gap:14px; }
        .logo { width:44px; height:44px; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; background:linear-gradient(135deg,#2f3bd6,#7c3aed); }
        .meta .title { font-size:16px; font-weight:700; color:#0b1220; }
        .meta .subtitle { font-size:13px; color:#6b7280; margin-top:2px; }
        .thread { font-size:13px; color:#94a3b8; }

        /* Main chat area */
        .cgpt-main { flex:1; padding:28px 32px; overflow-y:auto; overflow-x:hidden; background:linear-gradient(180deg,#fbfdff 0%, #ffffff 100%); min-height:0; }
        .welcome { color:#0f172a; margin-bottom:10px; }
        .welcome h2 { margin:0 0 6px 0; font-size:20px; }
        .welcome p { margin:0; color:#64748b; }

        .msg-list { display:flex; flex-direction:column; gap:18px; margin-top:16px; }
        .msg { display:flex; gap:12px; align-items:flex-end; }
        .msg-left { justify-content:flex-start; }
        .msg-right { justify-content:flex-end; flex-direction:row-reverse; }

        .avatar { width:36px; height:36px; border-radius:6px; background:#eef2ff; display:flex; align-items:center; justify-content:center; color:#334155; font-weight:600; }

        .bubble { max-width:72%; padding:14px 16px; border-radius:12px; font-size:15px; line-height:1.5; box-shadow:0 6px 18px rgba(2,6,23,0.06); }
        .bubble-bot { background:#f8fafc; border:1px solid #eef2ff; color:#051224; }
        .bubble-user { background:linear-gradient(90deg,#2563eb,#7c3aed); color:#fff; border:none; }
        .bubble-interrupt { background:#fff7ed; border:1px solid #ffedd5; color:#92400e; }

        /* Markdown content styling */
        .markdown-content {
          line-height: 1.6;
          color: inherit;
        }

        .markdown-content p {
          margin: 0 0 12px 0;
        }

        .markdown-content p:last-child {
          margin-bottom: 0;
        }

        .markdown-content strong {
          font-weight: 700;
        }

        .markdown-content em {
          font-style: italic;
        }

        .markdown-content code {
          background: rgba(0, 0, 0, 0.1);
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 0.9em;
        }

        .markdown-content pre {
          background: rgba(0, 0, 0, 0.05);
          padding: 12px;
          border-radius: 8px;
          overflow-x: auto;
          margin: 12px 0;
        }

        .markdown-content pre code {
          background: none;
          padding: 0;
        }

        .markdown-content ul, .markdown-content ol {
          margin: 8px 0;
          padding-left: 20px;
        }

        .markdown-content li {
          margin: 4px 0;
        }

        .markdown-content blockquote {
          border-left: 4px solid #e2e8f0;
          padding-left: 16px;
          margin: 12px 0;
          color: #64748b;
          font-style: italic;
        }

        .markdown-content h1, .markdown-content h2, .markdown-content h3, 
        .markdown-content h4, .markdown-content h5, .markdown-content h6 {
          margin: 16px 0 8px 0;
          font-weight: 700;
          line-height: 1.3;
        }

        .markdown-content h1 { font-size: 1.5em; }
        .markdown-content h2 { font-size: 1.3em; }
        .markdown-content h3 { font-size: 1.2em; }
        .markdown-content h4 { font-size: 1.1em; }
        .markdown-content h5 { font-size: 1em; }
        .markdown-content h6 { font-size: 0.9em; }

        /* Table styling */
        .table-wrapper {
          overflow-x: auto;
          margin: 12px 0;
          border-radius: 8px;
          border: 1px solid #e2e8f0;
        }

        .markdown-content table {
          width: 100%;
          border-collapse: collapse;
          background: white;
          font-size: 14px;
        }

        .markdown-content thead {
          background: #f8fafc;
        }

        .markdown-content th {
          padding: 12px 16px;
          text-align: left;
          font-weight: 600;
          color: #374151;
          border-bottom: 2px solid #e2e8f0;
          white-space: nowrap;
        }

        .markdown-content td {
          padding: 12px 16px;
          border-bottom: 1px solid #f1f5f9;
          color: #4b5563;
        }

        .markdown-content tr:hover {
          background: #f8fafc;
        }

        .markdown-content tr:last-child td {
          border-bottom: none;
        }

        /* Responsive table adjustments */
        @media (max-width: 768px) {
          .markdown-content table {
            font-size: 13px;
          }
          
          .markdown-content th, .markdown-content td {
            padding: 8px 12px;
          }
        }

        @media (max-width: 480px) {
          .markdown-content table {
            font-size: 12px;
          }
          
          .markdown-content th, .markdown-content td {
            padding: 6px 8px;
          }
        }

        /* Loading 3 dots */
        .three-dots { display:inline-flex; gap:6px; align-items:center; }
        .three-dots span { width:8px; height:8px; background:#94a3b8; border-radius:50%; display:inline-block; animation:dot 1.2s infinite ease-in-out; }
        .three-dots span:nth-child(2) { animation-delay:0.15s; }
        .three-dots span:nth-child(3) { animation-delay:0.3s; }
        @keyframes dot { 0% { transform:translateY(0); opacity:0.3 } 50% { transform:translateY(-6px); opacity:1 } 100% { transform:translateY(0); opacity:0.3 } }

        /* Footer / input area like ChatGPT */
        .cgpt-footer { padding:18px 20px; border-top:1px solid #eef2ff; background:linear-gradient(180deg,#fff,#fbfdff); }
        .input-form { display:flex; gap:12px; align-items:center; }
        .input-form input { flex:1; padding:14px 16px; border-radius:999px; border:1px solid #e6eef8; outline:none; font-size:15px; background:#ffffff; box-shadow:0 4px 18px rgba(2,6,23,0.04) inset; }
        .input-form input:focus { box-shadow:0 6px 20px rgba(99,102,241,0.12); border-color:rgba(99,102,241,0.45); }
        .send-btn { padding:10px 18px; border-radius:999px; background:linear-gradient(90deg,#2563eb,#7c3aed); color:white; border:none; font-weight:700; cursor:pointer; }
        .send-btn.feedback { background:linear-gradient(90deg,#059669,#10b981); }

        /* Responsive styles */
        @media (max-width: 1024px) {
          .cgpt-shell { max-width: 95%; margin: 0 auto; }
        }

        @media (max-width: 880px) {
          .bubble { max-width: 85%; }
          .cgpt-shell { margin: 0 12px; height: calc(100vh - 24px); }
          .cgpt-main { padding: 20px 24px; }
          .cgpt-header { padding: 14px 16px; }
          .meta .subtitle { display: none; } /* hide subtitle on mobile */
          .cgpt-footer { padding: 14px 16px; }
        }

        @media (max-width: 600px) {
          .cgpt-bg { padding: 12px; }
          .cgpt-shell { 
            margin: 0; 
            border-radius: 8px; 
            height: calc(100vh - 24px);
          }
          .cgpt-header { 
            padding: 12px 16px; 
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }
          .cgpt-left { gap: 10px; }
          .logo { width: 36px; height: 36px; font-size: 14px; }
          .meta .title { font-size: 14px; }
          .cgpt-main { 
            padding: 16px 20px; 
            font-size: 14px;
          }
          .bubble { 
            max-width: 90%; 
            padding: 12px 14px; 
            font-size: 14px; 
          }
          .cgpt-footer { 
            padding: 12px 16px; 
            position: sticky;
            bottom: 0;
            background: #fff;
            border-top: 1px solid #eef2ff;
          }
          .input-form input { 
            font-size: 14px; 
            padding: 12px 14px; 
          }
          .send-btn { 
            padding: 8px 16px; 
            font-size: 14px; 
          }
        }

        @media (max-width: 480px) {
          .cgpt-bg { padding: 8px; }
          .cgpt-shell { 
            height: calc(100vh - 16px);
            border-radius: 6px;
          }
          .cgpt-header { padding: 10px 12px; }
          .cgpt-main { padding: 12px 16px; }
          .bubble { 
            max-width: 95%; 
            padding: 10px 12px; 
          }
          .cgpt-footer { 
            padding: 10px 12px; 
            flex-direction: column;
            gap: 8px;
          }
          .input-form { 
            flex-direction: column; 
            gap: 8px; 
          }
          .send-btn { 
            width: 100%; 
            padding: 10px 16px;
          }
        }

        @media (max-width: 380px) {
          .cgpt-bg { padding: 4px; }
          .cgpt-shell { 
            height: calc(100vh - 8px);
            border-radius: 4px;
          }
          .cgpt-header { padding: 8px 10px; }
          .cgpt-main { padding: 10px 12px; }
          .bubble { 
            max-width: 98%; 
            padding: 8px 10px; 
            font-size: 13px;
          }
          .cgpt-footer { padding: 8px 10px; }
          .input-form input { 
            font-size: 13px; 
            padding: 10px 12px; 
          }
          .send-btn { 
            font-size: 13px; 
            padding: 8px 12px;
          }
        }
      `}</style>
    </div>
  );
}
