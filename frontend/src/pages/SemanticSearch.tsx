import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, Sparkles, BookOpen, Layers, Copy, Check,
  MessageSquare, Loader2, AlertCircle, ExternalLink, HelpCircle
} from 'lucide-react';
import { searchApi, subjectsApi } from '../services/api';
import type { SemanticSearchResult, Subject } from '../types';

const SAMPLE_QUERIES = [
  'What is Two-Phase Locking (2PL) and strict 2PL?',
  'Explain ACID atomicity and durability in database transactions.',
  'Deadlock detection vs deadlock prevention algorithms.',
  'Difference between clustered and non-clustered B+ Tree indexes.',
  'Explain 3NF vs BCNF normalization with functional dependencies.',
];

export default function SemanticSearch() {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(10);
  const [results, setResults] = useState<SemanticSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    subjectsApi.list().then(setSubjects).catch(() => {});
  }, []);

  const handleSearch = async (searchQueryText?: string) => {
    const q = searchQueryText !== undefined ? searchQueryText : query;
    if (!q.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const data = await searchApi.semantic(
        q.trim(),
        selectedSubjectId || undefined,
        topK
      );
      setResults(data);
    } catch (err: any) {
      setError(err.message || 'Semantic search failed. Is PostgreSQL with pgvector active?');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-indigo-600" />
          Semantic Vector Search
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Perform cosine similarity searches over your lecture notes using sentence-transformers and PostgreSQL pgvector.
        </p>
      </div>

      {/* Search Bar & Options */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="flex flex-col sm:flex-row items-center gap-3"
        >
          <div className="relative flex-1 w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search concepts, definitions, or exam questions..."
              className="w-full pl-12 pr-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 text-sm font-medium transition-all"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            {/* Subject Selector */}
            <select
              value={selectedSubjectId}
              onChange={(e) => setSelectedSubjectId(e.target.value)}
              className="input-field text-xs py-3 max-w-[160px]"
            >
              <option value="">All Subjects</option>
              {subjects.map((s) => (
                <option key={s.subject_id} value={s.subject_id}>
                  {s.name}
                </option>
              ))}
            </select>

            {/* Top-K Selector */}
            <select
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="input-field text-xs py-3 max-w-[100px]"
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
            </select>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="btn-primary py-3 px-5 text-sm inline-flex items-center gap-2 flex-shrink-0"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Search
            </button>
          </div>
        </form>

        {/* Quick Sample Queries */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
          <span className="text-xs font-semibold text-slate-400">Try asking:</span>
          {SAMPLE_QUERIES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setQuery(sample);
                handleSearch(sample);
              }}
              className="text-xs px-2.5 py-1 rounded-full bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 transition-colors"
            >
              {sample}
            </button>
          ))}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results List */}
      {loading ? (
        <div className="bg-white p-16 rounded-2xl border border-slate-200 text-center">
          <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">Generating 384-d Query Vector</h3>
          <p className="text-sm text-slate-500 mt-1">Ranking notes via pgvector cosine distance...</p>
        </div>
      ) : results.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>Found <strong>{results.length}</strong> semantically relevant chunks</span>
            <span>Sorted by highest cosine similarity</span>
          </div>

          <div className="space-y-3">
            {results.map((res) => {
              const simPercent = Math.round(res.similarity * 100);
              const isCopied = copiedId === res.chunk_id;

              return (
                <div
                  key={res.chunk_id}
                  className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-indigo-300 transition-all duration-150 space-y-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="badge-primary font-bold">
                        {simPercent}% Match
                      </span>
                      <span className="text-xs font-semibold text-slate-700">
                        {res.subject_name}
                      </span>
                      <span className="text-xs text-slate-400">
                        • {res.document_filename} (Chunk #{res.position})
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleCopy(res.chunk_id, res.content)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors inline-flex items-center gap-1 text-xs"
                        title="Copy excerpt"
                      >
                        {isCopied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                        <span className="hidden sm:inline">{isCopied ? 'Copied' : 'Copy'}</span>
                      </button>
                      <button
                        onClick={() => {
                          const p = `Explain this topic from my notes: "${res.content.slice(0, 150)}..."`;
                          navigate(`/chat?prompt=${encodeURIComponent(p)}`);
                        }}
                        className="p-1.5 rounded-lg text-indigo-600 hover:bg-indigo-50 transition-colors inline-flex items-center gap-1 text-xs font-semibold"
                        title="Ask AI"
                      >
                        <MessageSquare className="w-4 h-4" />
                        <span className="hidden sm:inline">Ask AI</span>
                      </button>
                    </div>
                  </div>

                  <p className="text-sm text-slate-800 leading-relaxed font-sans bg-slate-50/80 p-3.5 rounded-lg border border-slate-100 whitespace-pre-wrap">
                    {res.content}
                  </p>

                  <div className="text-[11px] text-slate-400 flex items-center gap-3">
                    <span>{res.word_count} words</span>
                    <span>•</span>
                    <span>Vector: all-MiniLM-L6-v2</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : query && !loading ? (
        <div className="bg-white p-12 rounded-2xl border border-dashed border-slate-200 text-center">
          <HelpCircle className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-base font-semibold text-slate-700">No matching chunks found</p>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            Try a different conceptual phrase or ensure note documents have generated embeddings.
          </p>
        </div>
      ) : null}
    </div>
  );
}
