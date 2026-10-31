import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  MessageSquare, Send, Sparkles, BookOpen, Layers, HelpCircle,
  AlertCircle, CheckCircle, Loader2, Plus, Trash2, ChevronDown,
  ChevronUp, ExternalLink, Bot, User, Clock, Terminal
} from 'lucide-react';
import { chatApi, subjectsApi, healthApi } from '../services/api';
import type { ChatSession, Subject } from '../types';

interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: {
    chunks?: Array<{ chunk_id: string; content: string; document_filename: string; similarity: number }>;
    pyqs?: Array<{ pyq_id: string; question: string; exam_year: number; marks: number }>;
    error?: string;
  };
  created_at?: string;
}

export default function AIAssistant() {
  const [searchParams] = useSearchParams();
  const initialPrompt = searchParams.get('prompt') || '';
  const initialSubjectId = searchParams.get('subject_id') || '';

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>(initialSubjectId);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState(initialPrompt);
  const [sending, setSending] = useState(false);
  const [aiStatus, setAiStatus] = useState<any>(null);
  const [expandedSources, setExpandedSources] = useState<Record<number, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Check AI Service status
  useEffect(() => {
    healthApi.ai().then(setAiStatus).catch(() => {
      setAiStatus({ status: 'unconfigured', error: 'Gemini API not configured' });
    });
    subjectsApi.list().then(setSubjects).catch(() => {});
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await chatApi.getSessions();
      setSessions(data);
    } catch {
      // ignore
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    try {
      setActiveSessionId(sessionId);
      const res = await chatApi.getSession(sessionId);
      const formatted: Message[] = (res.messages || []).map((m: any) => ({
        id: m.message_id,
        role: m.role,
        content: m.content,
        sources: m.sources,
        created_at: m.created_at,
      }));
      setMessages(formatted);
      if (res.session?.subject_id) {
        setSelectedSubjectId(res.session.subject_id);
      }
    } catch {
      // ignore
    }
  };

  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setInputText('');
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    try {
      await chatApi.deleteSession(sessionId);
      if (activeSessionId === sessionId) {
        handleNewChat();
      }
      loadSessions();
    } catch {
      // ignore
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || sending) return;

    const question = inputText.trim();
    setInputText('');

    // Add user message to UI immediately
    const userMsg: Message = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    try {
      const res = await chatApi.send(
        question,
        activeSessionId || undefined,
        selectedSubjectId || undefined
      );

      if (res.session_id && !activeSessionId) {
        setActiveSessionId(res.session_id);
        loadSessions();
      }

      const assistantMsg: Message = {
        role: 'assistant',
        content: res.answer,
        sources: {
          chunks: res.sources || [],
          error: res.error,
        },
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Unable to complete chat request: ${err.message}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const toggleSource = (idx: number) => {
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col md:flex-row gap-4">
      {/* Sessions Sidebar */}
      <div className="w-full md:w-64 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden flex-shrink-0">
        <div className="p-3 border-b border-slate-100 flex items-center justify-between">
          <button
            onClick={handleNewChat}
            className="w-full btn-primary py-2 text-xs font-semibold inline-flex items-center justify-center gap-2"
          >
            <Plus className="w-3.5 h-3.5" />
            New Chat Session
          </button>
        </div>

        <div className="p-3 border-b border-slate-100">
          <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
            Filter Context by Subject
          </label>
          <select
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="input-field text-xs py-1.5"
          >
            <option value="">All Subjects (Global RAG)</option>
            {subjects.map((s) => (
              <option key={s.subject_id} value={s.subject_id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-8">No past sessions</p>
          ) : (
            sessions.map((sess) => (
              <div
                key={sess.session_id}
                onClick={() => handleSelectSession(sess.session_id)}
                className={`p-2.5 rounded-xl text-xs font-medium cursor-pointer transition-colors flex items-center justify-between group ${
                  activeSessionId === sess.session_id
                    ? 'bg-indigo-50 text-indigo-900 border border-indigo-100'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <div className="truncate flex-1 pr-2">
                  <p className="truncate font-semibold">{sess.title}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    {sess.message_count || 0} messages
                  </p>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(e, sess.session_id)}
                  className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 p-1 rounded"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat Pane */}
      <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
        {/* Gemini Status Alert Banner if unconfigured or error */}
        {aiStatus && aiStatus.status !== 'ok' && (
          <div className="p-3 bg-amber-50 border-b border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span>
                <strong>AI Assistant Status:</strong> {aiStatus.error || 'Gemini API not configured'}. Set{' '}
                <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[11px]">GEMINI_API_KEY</code> on Render backend to enable AI study answers.
              </span>
            </div>
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noreferrer"
              className="text-amber-800 underline font-semibold flex items-center gap-1 flex-shrink-0"
            >
              Get Gemini Key <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto p-6">
              <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mb-4">
                <Bot className="w-8 h-8" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                RAG-Powered Academic Assistant
              </h3>
              <p className="text-xs text-slate-500 mt-1 mb-6 leading-relaxed">
                Ask questions about your uploaded lecture notes, textbook chapters, or exam patterns. Responses are grounded in your course materials using vector embeddings.
              </p>
              <div className="space-y-2 w-full text-left">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Example questions:
                </p>
                {[
                  'What are the ACID properties in database management?',
                  'Explain Two-Phase Locking and how it avoids cascading aborts.',
                  'Summarize the deadlock detection algorithms from my notes.',
                ].map((q, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInputText(q);
                    }}
                    className="w-full text-left text-xs p-2.5 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-slate-50 text-slate-700 font-medium transition-colors"
                  >
                    "{q}"
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 mt-1">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-none'
                      : 'bg-slate-50 text-slate-800 border border-slate-200 rounded-bl-none shadow-sm'
                  }`}
                >
                  <p className="whitespace-pre-wrap font-sans">{m.content}</p>

                  {/* Sources Citations Accordion */}
                  {m.sources?.chunks && m.sources.chunks.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-200">
                      <button
                        onClick={() => toggleSource(idx)}
                        className="text-xs font-semibold text-indigo-700 hover:text-indigo-800 flex items-center gap-1"
                      >
                        <Layers className="w-3.5 h-3.5" />
                        <span>Cited Notes & Documents ({m.sources.chunks.length})</span>
                        {expandedSources[idx] ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {expandedSources[idx] && (
                        <div className="mt-2 space-y-2 text-xs">
                          {m.sources.chunks.map((chk, cIdx) => (
                            <div
                              key={cIdx}
                              className="p-2.5 rounded-lg bg-white border border-slate-200 text-slate-700 space-y-1"
                            >
                              <div className="flex items-center justify-between text-[11px] font-semibold text-indigo-900">
                                <span>{chk.document_filename}</span>
                                <span className="badge-primary text-[10px]">
                                  {Math.round(chk.similarity * 100)}% match
                                </span>
                              </div>
                              <p className="line-clamp-2 text-slate-600 italic">
                                "{chk.content}"
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {m.role === 'user' && (
                  <div className="w-8 h-8 rounded-lg bg-slate-800 text-white flex items-center justify-center flex-shrink-0 mt-1">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {sending && (
            <div className="flex gap-3 justify-start items-center">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs text-slate-500 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                <span>Searching vector notes and generating response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-200 bg-white">
          <form onSubmit={handleSendMessage} className="flex items-center gap-2">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask anything about your notes or exam topics..."
              className="flex-1 input-field py-2.5 text-sm"
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !inputText.trim()}
              className="btn-primary py-2.5 px-4 text-sm inline-flex items-center gap-1.5 flex-shrink-0"
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
