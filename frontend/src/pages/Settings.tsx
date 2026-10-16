import React, { useEffect, useState } from 'react';
import {
  Settings as SettingsIcon, Database, Cpu, Bot, CheckCircle,
  AlertCircle, RefreshCw, Terminal, ExternalLink, Copy, Check,
  Sliders, Shield, Server, FileCode
} from 'lucide-react';
import { healthApi } from '../services/api';

export default function Settings() {
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [dbHealth, setDbHealth] = useState<any>(null);
  const [ollamaHealth, setOllamaHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const [sys, db, ol] = await Promise.allSettled([
        healthApi.system(),
        healthApi.database(),
        healthApi.ollama(),
      ]);
      setSystemHealth(sys.status === 'fulfilled' ? sys.value : { status: 'error' });
      setDbHealth(db.status === 'fulfilled' ? db.value : { status: 'error', error: 'Connection refused' });
      setOllamaHealth(ol.status === 'fulfilled' ? ol.value : { status: 'unavailable', error: 'Not running' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleCopy = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <SettingsIcon className="w-6 h-6 text-slate-700" />
            System Status & Configuration
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Monitor offline vector database connectivity, embedding models, and local LLM runtime.
          </p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="btn-secondary inline-flex items-center gap-2 text-xs font-semibold"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Re-check Services
        </button>
      </div>

      {/* Services Health Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Database Health Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="p-2.5 rounded-xl bg-blue-50 text-blue-600">
                <Database className="w-5 h-5" />
              </span>
              {dbHealth?.status === 'ok' ? (
                <span className="badge-success inline-flex items-center gap-1 text-[11px]">
                  <CheckCircle className="w-3 h-3" /> Connected
                </span>
              ) : (
                <span className="badge-danger inline-flex items-center gap-1 text-[11px]">
                  <AlertCircle className="w-3 h-3" /> Offline
                </span>
              )}
            </div>
            <h3 className="font-bold text-slate-900">PostgreSQL + pgvector</h3>
            <p className="text-xs text-slate-500 mt-1">
              Relational metadata storage and HNSW vector similarity indexes.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">pgvector extension:</span>
              <span className="font-semibold">{dbHealth?.pgvector_enabled ? 'Enabled' : 'Pending'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Dialect:</span>
              <span className="font-mono text-[11px]">{dbHealth?.dialect || 'postgresql'}</span>
            </div>
          </div>
        </div>

        {/* Embedding Service Health Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600">
                <Cpu className="w-5 h-5" />
              </span>
              <span className="badge-success inline-flex items-center gap-1 text-[11px]">
                <CheckCircle className="w-3 h-3" /> Local PyTorch
              </span>
            </div>
            <h3 className="font-bold text-slate-900">Sentence Transformers</h3>
            <p className="text-xs text-slate-500 mt-1">
              Deterministic offline embeddings generating 384-dimensional dense vectors.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Model:</span>
              <span className="font-mono text-[11px] font-semibold text-indigo-700">all-MiniLM-L6-v2</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Dimensions:</span>
              <span className="font-semibold">384 dims</span>
            </div>
          </div>
        </div>

        {/* Ollama LLM Service Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="p-2.5 rounded-xl bg-purple-50 text-purple-600">
                <Bot className="w-5 h-5" />
              </span>
              {ollamaHealth?.status === 'ok' ? (
                <span className="badge-success inline-flex items-center gap-1 text-[11px]">
                  <CheckCircle className="w-3 h-3" /> Online
                </span>
              ) : (
                <span className="badge-warning inline-flex items-center gap-1 text-[11px]">
                  <AlertCircle className="w-3 h-3" /> Not Detected
                </span>
              )}
            </div>
            <h3 className="font-bold text-slate-900">Ollama Local LLM</h3>
            <p className="text-xs text-slate-500 mt-1">
              Local inference runtime for study explanations and RAG question answering.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Target Model:</span>
              <span className="font-mono text-[11px] font-semibold text-purple-700">
                {ollamaHealth?.configured_model || 'mistral'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Installed:</span>
              <span className="font-semibold">
                {ollamaHealth?.available_models?.length || 0} models
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration Details Panel */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100">
          <h3 className="font-bold text-slate-900 flex items-center gap-2 text-sm">
            <Sliders className="w-4 h-4 text-slate-600" />
            Runtime Configuration Parameters
          </h3>
        </div>
        <div className="divide-y divide-slate-100 text-xs">
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">Embedding Vector Dimension</p>
              <p className="text-slate-400">Dense float vector size configured in database schema</p>
            </div>
            <code className="bg-slate-100 px-2 py-1 rounded text-slate-700 font-mono">384</code>
          </div>
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">Vector Distance Metric</p>
              <p className="text-slate-400">PostgreSQL pgvector cosine distance operator</p>
            </div>
            <code className="bg-slate-100 px-2 py-1 rounded text-slate-700 font-mono">&lt;=&gt; (Cosine Distance)</code>
          </div>
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">Semantic Top-K Matches</p>
              <p className="text-slate-400">Number of nearest chunks matched per previous year question</p>
            </div>
            <code className="bg-slate-100 px-2 py-1 rounded text-slate-700 font-mono">5 matches</code>
          </div>
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">Document Chunking Strategy</p>
              <p className="text-slate-400">Paragraph-aware sliding window with semantic boundary detection</p>
            </div>
            <code className="bg-slate-100 px-2 py-1 rounded text-slate-700 font-mono">300 words (overlap: 50)</code>
          </div>
        </div>
      </div>

      {/* Setup & Local Deployment Guide */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Terminal className="w-5 h-5 text-indigo-600" />
          Offline Setup Quickstart
        </h3>

        {/* PostgreSQL Guide */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              1. PostgreSQL + pgvector Setup
            </p>
            <button
              onClick={() => handleCopy('pg', 'CREATE EXTENSION IF NOT EXISTS vector;')}
              className="text-xs text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-1"
            >
              {copiedKey === 'pg' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              Copy SQL
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Install PostgreSQL 15+ and pgvector. Then connect to your database and enable the vector extension:
          </p>
          <pre className="bg-slate-900 text-slate-100 p-3.5 rounded-xl font-mono text-xs overflow-x-auto">
{`-- Connect to PostgreSQL and create database
CREATE DATABASE pyq_analyzer;
\\c pyq_analyzer;
CREATE EXTENSION IF NOT EXISTS vector;`}
          </pre>
        </div>

        {/* Ollama Guide */}
        <div className="space-y-2 pt-3 border-t border-slate-100">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              2. Ollama Local LLM Setup
            </p>
            <button
              onClick={() => handleCopy('ollama', 'ollama pull mistral\nollama serve')}
              className="text-xs text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-1"
            >
              {copiedKey === 'ollama' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              Copy Commands
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Download Ollama from <a href="https://ollama.ai" target="_blank" rel="noreferrer" className="text-indigo-600 underline">ollama.ai</a>, then pull and run your preferred model:
          </p>
          <pre className="bg-slate-900 text-slate-100 p-3.5 rounded-xl font-mono text-xs overflow-x-auto">
{`ollama pull mistral
ollama serve`}
          </pre>
        </div>
      </div>
    </div>
  );
}
