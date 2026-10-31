import React, { useEffect, useState } from 'react';
import {
  Settings as SettingsIcon, Database, Cpu, Bot, CheckCircle,
  AlertCircle, RefreshCw, Terminal, ExternalLink, Copy, Check,
  Sliders, Shield, Server, HardDrive, Cloud, Key
} from 'lucide-react';
import { healthApi } from '../services/api';

export default function Settings() {
  const [dbHealth, setDbHealth] = useState<any>(null);
  const [embHealth, setEmbHealth] = useState<any>(null);
  const [aiHealth, setAiHealth] = useState<any>(null);
  const [storageHealth, setStorageHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const [db, emb, ai, st] = await Promise.allSettled([
        healthApi.database(),
        healthApi.embedding(),
        healthApi.ai ? healthApi.ai() : healthApi.ollama(),
        healthApi.storage(),
      ]);
      setDbHealth(db.status === 'fulfilled' ? db.value : { status: 'error', error: 'Connection refused' });
      setEmbHealth(emb.status === 'fulfilled' ? emb.value : { status: 'error', error: 'Service error' });
      setAiHealth(ai.status === 'fulfilled' ? ai.value : { status: 'unconfigured', error: 'Not configured' });
      setStorageHealth(st.status === 'fulfilled' ? st.value : { status: 'local', provider: 'local' });
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
            System Status & Cloud Configuration
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time status of PostgreSQL + pgvector, semantic embeddings, Google Gemini AI, and cloud object storage.
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
            <h3 className="font-bold text-slate-900 text-sm">PostgreSQL Database</h3>
            <p className="text-xs text-slate-500 mt-1">
              Neon Cloud PostgreSQL with pgvector relational storage.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">pgvector:</span>
              <span className="font-semibold text-emerald-700">
                {dbHealth?.pgvector_enabled ? 'Enabled' : 'Pending'}
              </span>
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
              {embHealth?.status === 'ok' ? (
                <span className="badge-success inline-flex items-center gap-1 text-[11px]">
                  <CheckCircle className="w-3 h-3" /> Ready
                </span>
              ) : (
                <span className="badge-warning inline-flex items-center gap-1 text-[11px]">
                  <AlertCircle className="w-3 h-3" /> Degraded
                </span>
              )}
            </div>
            <h3 className="font-bold text-slate-900 text-sm">Semantic Embeddings</h3>
            <p className="text-xs text-slate-500 mt-1">
              Dense vector generator for semantic search and PYQ correlation.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Model:</span>
              <span className="font-mono text-[11px] font-semibold text-indigo-700 truncate max-w-[120px]" title={embHealth?.model}>
                {embHealth?.model || 'text-embedding-004'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Dimension:</span>
              <span className="font-semibold">{embHealth?.dimension || 384} dims</span>
            </div>
          </div>
        </div>

        {/* AI Assistant Health Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="p-2.5 rounded-xl bg-purple-50 text-purple-600">
                <Bot className="w-5 h-5" />
              </span>
              {aiHealth?.status === 'ok' ? (
                <span className="badge-success inline-flex items-center gap-1 text-[11px]">
                  <CheckCircle className="w-3 h-3" /> Connected
                </span>
              ) : aiHealth?.status === 'unconfigured' ? (
                <span className="badge-warning inline-flex items-center gap-1 text-[11px]">
                  <AlertCircle className="w-3 h-3" /> Key Missing
                </span>
              ) : (
                <span className="badge-danger inline-flex items-center gap-1 text-[11px]">
                  <AlertCircle className="w-3 h-3" /> Error
                </span>
              )}
            </div>
            <h3 className="font-bold text-slate-900 text-sm">AI Study Assistant</h3>
            <p className="text-xs text-slate-500 mt-1">
              Google Gemini API with RAG context grounding.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Model:</span>
              <span className="font-mono text-[11px] font-semibold text-purple-700 truncate max-w-[120px]">
                {aiHealth?.model || aiHealth?.configured_model || 'gemini-2.5-flash'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Status:</span>
              <span className="font-semibold text-slate-700">
                {aiHealth?.status === 'ok' ? 'Online' : 'Unconfigured'}
              </span>
            </div>
          </div>
        </div>

        {/* Cloud Object Storage Health Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="p-2.5 rounded-xl bg-amber-50 text-amber-600">
                <HardDrive className="w-5 h-5" />
              </span>
              {storageHealth?.status === 'ok' ? (
                <span className="badge-success inline-flex items-center gap-1 text-[11px]">
                  <CheckCircle className="w-3 h-3" /> Persistent
                </span>
              ) : (
                <span className="badge-neutral inline-flex items-center gap-1 text-[11px]">
                  Local Disk
                </span>
              )}
            </div>
            <h3 className="font-bold text-slate-900 text-sm">Document Storage</h3>
            <p className="text-xs text-slate-500 mt-1">
              Persistent storage for uploaded notes (PDF, DOCX, TXT).
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Provider:</span>
              <span className="font-semibold text-slate-700 uppercase text-[11px]">
                {storageHealth?.provider || 'Supabase'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Bucket:</span>
              <span className="font-mono text-[11px]">
                {storageHealth?.bucket || 'documents'}
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
            Runtime Configuration & Vector Parameters
          </h3>
        </div>
        <div className="divide-y divide-slate-100 text-xs">
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">Embedding Vector Dimension</p>
              <p className="text-slate-400">Dense float vector size configured in database schema and vector extension</p>
            </div>
            <code className="bg-slate-100 px-2.5 py-1 rounded text-indigo-700 font-mono font-bold">384</code>
          </div>
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">Vector Distance Metric</p>
              <p className="text-slate-400">PostgreSQL pgvector cosine distance operator with HNSW indexing</p>
            </div>
            <code className="bg-slate-100 px-2.5 py-1 rounded text-slate-700 font-mono">&lt;=&gt; (Cosine Distance)</code>
          </div>
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">Semantic Top-K Matches</p>
              <p className="text-slate-400">Number of nearest chunks matched per Previous Year Question in Heatmap</p>
            </div>
            <code className="bg-slate-100 px-2.5 py-1 rounded text-slate-700 font-mono">3 - 5 matches</code>
          </div>
          <div className="p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">RAG Context Grounding</p>
              <p className="text-slate-400">Retrieved course notes chunks + exam question distribution sent to Gemini API</p>
            </div>
            <span className="badge-primary">Strict Academic Grounding</span>
          </div>
        </div>
      </div>

      {/* Cloud Architecture Summary */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Cloud className="w-5 h-5 text-indigo-600" />
          Production Cloud Architecture (Zero-Cost Free Tier)
        </h3>
        <p className="text-xs text-slate-500 leading-relaxed">
          This system is engineered to run permanently on cloud infrastructure without requiring local laptop execution or local Ollama processes:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50 space-y-1">
            <p className="font-bold text-slate-800">Frontend (Render Static Site)</p>
            <p className="text-slate-500">React + TypeScript SPA built with Vite, served globally on Render CDN with client-side SPA routing.</p>
          </div>
          <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50 space-y-1">
            <p className="font-bold text-slate-800">Backend (Render Web Service)</p>
            <p className="text-slate-500">FastAPI backend running with Uvicorn on Linux container, bound to dynamic port with automatic SSL.</p>
          </div>
          <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50 space-y-1">
            <p className="font-bold text-slate-800">Database (Neon PostgreSQL)</p>
            <p className="text-slate-500">Managed cloud PostgreSQL with native pgvector extension and persistent HNSW vector indexes.</p>
          </div>
          <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50 space-y-1">
            <p className="font-bold text-slate-800">AI & Embeddings (Google Gemini API)</p>
            <p className="text-slate-500">Gemini 2.5 Flash for contextual answers + Text-Embedding-004 generating 384-dimensional dense vectors.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
