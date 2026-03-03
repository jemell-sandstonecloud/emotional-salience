import React, { useState, useRef, useEffect, useCallback } from 'react';
import { chatSplit, submitRating, newSession } from '../api';
import RatingDrawer from '../components/RatingDrawer';

function MessageBubble({ role, content }) {
  const isUser = role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[85%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
          isUser
            ? 'bg-sand-700 text-white rounded-br-sm'
            : 'bg-gray-800 text-gray-200 rounded-bl-sm'
        }`}
      >
        {content}
      </div>
    </div>
  );
}

function ChatPanel({ label, color, messages, loading }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <div className={`text-xs font-semibold uppercase tracking-widest px-3 py-2 border-b border-gray-800 ${color}`}>
        {label}
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} />
        ))}
        {loading && (
          <div className="flex justify-start mb-3">
            <div className="bg-gray-800 px-3 py-2 rounded-xl text-sm text-gray-500 animate-pulse rounded-bl-sm">
              Thinking...
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

export default function Chat({ user }) {
  const [input, setInput] = useState('');
  const [messagesA, setMessagesA] = useState([]);
  const [messagesB, setMessagesB] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showRating, setShowRating] = useState(false);
  const [sessionNumber, setSessionNumber] = useState(1);
  const [exchangeNumber, setExchangeNumber] = useState(0);
  const [lastExchange, setLastExchange] = useState(null);
  const [activeTab, setActiveTab] = useState('A'); // Mobile tab
  const inputRef = useRef(null);

  // Inactivity timer — 30 min auto-close
  const timerRef = useRef(null);
  const resetTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      alert('Session closed due to inactivity.');
    }, 30 * 60 * 1000);
  }, []);

  useEffect(() => { resetTimer(); return () => clearTimeout(timerRef.current); }, [resetTimer]);

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');
    resetTimer();

    // Add user message to both panels
    const userMsg = { role: 'user', content: msg };
    setMessagesA((prev) => [...prev, userMsg]);
    setMessagesB((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await chatSplit(msg, undefined, sessionNumber);

      setMessagesA((prev) => [...prev, { role: 'assistant', content: data.response_a }]);
      setMessagesB((prev) => [...prev, { role: 'assistant', content: data.response_b }]);
      setSessionNumber(data.session_number);
      setExchangeNumber(data.exchange_number);

      setLastExchange({
        message_text: msg,
        response_a_text: data.response_a,
        response_b_text: data.response_b,
        session_number: data.session_number,
        exchange_number: data.exchange_number,
        model_id: data.model_id,
      });

      // Show rating drawer
      setShowRating(true);
    } catch (err) {
      setMessagesA((prev) => [...prev, { role: 'assistant', content: `[Error: ${err.message}]` }]);
      setMessagesB((prev) => [...prev, { role: 'assistant', content: `[Error: ${err.message}]` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleRatingSubmit = async (ratingData) => {
    if (!lastExchange) return;
    try {
      await submitRating({ ...lastExchange, ...ratingData });
    } catch {
      // Non-critical — continue
    }
    setShowRating(false);
    setLastExchange(null);
    inputRef.current?.focus();
  };

  const handleNewSession = async () => {
    try {
      const data = await newSession();
      setSessionNumber(data.session_number);
      setExchangeNumber(0);
      setMessagesA([]);
      setMessagesB([]);
    } catch {}
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-40px)]">
      {/* Session bar */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-gray-900 border-b border-gray-800 text-xs text-gray-500">
        <span>Session {sessionNumber} · Exchange {exchangeNumber}</span>
        <button onClick={handleNewSession} className="text-gray-500 hover:text-sand-400 transition">
          New Session
        </button>
      </div>

      {/* Mobile tabs */}
      <div className="md:hidden flex border-b border-gray-800">
        <button
          onClick={() => setActiveTab('A')}
          className={`flex-1 py-2 text-xs font-medium text-center transition ${
            activeTab === 'A' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-500'
          }`}
        >
          Response A
        </button>
        <button
          onClick={() => setActiveTab('B')}
          className={`flex-1 py-2 text-xs font-medium text-center transition ${
            activeTab === 'B' ? 'text-emerald-400 border-b-2 border-emerald-400' : 'text-gray-500'
          }`}
        >
          Response B
        </button>
      </div>

      {/* Split-screen panels */}
      <div className="flex-1 flex overflow-hidden">
        {/* Desktop: side-by-side */}
        <div className={`hidden md:flex flex-1`}>
          <div className="flex-1 border-r border-gray-800">
            <ChatPanel label="Response A" color="text-blue-400" messages={messagesA} loading={loading} />
          </div>
          <div className="flex-1">
            <ChatPanel label="Response B" color="text-emerald-400" messages={messagesB} loading={loading} />
          </div>
        </div>

        {/* Mobile: tabbed */}
        <div className="md:hidden flex-1">
          {activeTab === 'A' && (
            <ChatPanel label="Response A" color="text-blue-400" messages={messagesA} loading={loading} />
          )}
          {activeTab === 'B' && (
            <ChatPanel label="Response B" color="text-emerald-400" messages={messagesB} loading={loading} />
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 bg-gray-900 p-3">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading || showRating}
            placeholder={showRating ? 'Rate both responses to continue...' : 'Type your message...'}
            rows={1}
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm resize-none focus:outline-none focus:border-sand-500 disabled:opacity-40"
          />
          <button
            onClick={handleSend}
            disabled={loading || showRating || !input.trim()}
            className="px-4 py-2 bg-sand-600 hover:bg-sand-500 text-white rounded-xl text-sm font-medium transition disabled:opacity-30"
          >
            Send
          </button>
        </div>
      </div>

      {/* Rating drawer */}
      <RatingDrawer
        visible={showRating}
        onSubmit={handleRatingSubmit}
        onClose={() => setShowRating(false)}
      />
    </div>
  );
}
