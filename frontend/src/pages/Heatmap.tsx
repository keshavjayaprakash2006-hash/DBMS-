import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  FlameKindling, BookOpen, Layers, HelpCircle, Sparkles,
  Filter, ChevronRight, X, AlertCircle, Award, Calendar,
  MessageSquare, Loader2, RefreshCw, Info, ExternalLink
} from 'lucide-react';
import { analysisApi, subjectsApi, dashboardApi } from '../services/api';
import type { HeatmapData, Subject, HeatmapChunk } from '../types';

export default function Heatmap() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialSubjectId = searchParams.get('subject_id') || '';
  const initialAnalysisId = searchParams.get('analysis_id') || '';

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>(initialSubjectId);
  const [heatmapData, setHeatmapData] = useState<HeatmapData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [minScoreFilter, setMinScoreFilter] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Chunk for Evidence Drawer
  const [selectedChunk, setSelectedChunk] = useState<HeatmapChunk | null>(null);

  const fetchSubjects = async () => {
    try {
      const subs = await subjectsApi.list();
      setSubjects(subs);
      if (!selectedSubjectId && subs.length > 0) {
        setSelectedSubjectId(subs[0].subject_id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load subjects');
    }
  };

  const normalizeHeatmap = (raw: any): HeatmapData => {
    const scored: HeatmapChunk[] = (raw.scored_chunks || []).map((sc: any) => ({
      chunk_id: sc.chunk_id,
      content: sc.chunk_content || '',
      position: sc.chunk_position || 0,
      document_filename: sc.document_filename || 'Notes Document',
      importance_score: sc.importance_score || 0,
      hit_count: sc.hit_count || 0,
      matched_pyqs: sc.matched_pyqs || [],
    }));
    const unmatched: HeatmapChunk[] = (raw.unmatched_chunks || []).map((uc: any) => ({
      chunk_id: uc.chunk_id,
      content: uc.content || '',
      position: uc.position || 0,
      word_count: uc.word_count,
      document_filename: uc.document_filename || 'Notes Document',
      importance_score: 0,
      hit_count: 0,
      matched_pyqs: [],
    }));
    const allChunks = [...scored, ...unmatched].sort((a, b) => a.position - b.position);
    const maxHits = scored.reduce((max, c) => Math.max(max, c.hit_count), 0);
    return {
      ...raw,
      chunks: allChunks,
      max_hit_count: maxHits,
    };
  };

  const loadHeatmapForSubject = async (subId: string) => {
    if (!subId) return;
    try {
      setLoading(true);
      setError(null);
      const runs = await analysisApi.getRuns(subId);
      const completedRun = runs.find((r: any) => r.status === 'completed');
      if (!completedRun) {
        setHeatmapData(null);
        setError('No completed analysis run found for this subject. Please run an analysis first.');
        return;
      }
      const data = await analysisApi.getHeatmap(completedRun.analysis_id);
      setHeatmapData(normalizeHeatmap(data));
    } catch (err: any) {
      setHeatmapData(null);
      setError(err.message || 'Failed to load heatmap data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  useEffect(() => {
    if (initialAnalysisId) {
      setLoading(true);
      analysisApi.getHeatmap(initialAnalysisId)
        .then(data => {
          setHeatmapData(normalizeHeatmap(data));
          if (data.analysis?.subject_id) {
            setSelectedSubjectId(data.analysis.subject_id);
          }
        })
        .catch(err => setError(err.message || 'Failed to load analysis'))
        .finally(() => setLoading(false));
    } else if (selectedSubjectId) {
      loadHeatmapForSubject(selectedSubjectId);
    }
  }, [selectedSubjectId, initialAnalysisId]);

  const getColorClass = (score: number) => {
    if (score >= 0.7) {
      return {
        card: 'border-rose-400 bg-rose-50/70 hover:bg-rose-50',
        badge: 'bg-rose-600 text-white',
        text: 'text-rose-900',
        label: 'High Yield',
      };
    }
    if (score >= 0.4) {
      return {
        card: 'border-amber-400 bg-amber-50/70 hover:bg-amber-50',
        badge: 'bg-amber-500 text-white',
        text: 'text-amber-900',
        label: 'Medium Yield',
      };
    }
    if (score > 0.1) {
      return {
        card: 'border-yellow-300 bg-yellow-50/50 hover:bg-yellow-50',
        badge: 'bg-yellow-500 text-white',
        text: 'text-yellow-900',
        label: 'Low Yield',
      };
    }
    return {
      card: 'border-slate-200 bg-white hover:bg-slate-50',
      badge: 'bg-slate-200 text-slate-700',
      text: 'text-slate-700',
      label: 'Unmatched',
    };
  };

  const filteredChunks = (heatmapData?.chunks || []).filter((chunk) => {
    const matchesScore = (chunk.importance_score || 0) >= minScoreFilter;
    const matchesSearch =
      chunk.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      chunk.document_filename.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesScore && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FlameKindling className="w-6 h-6 text-rose-500" />
            Study Importance Heatmap
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Visual density map connecting course paragraphs to recurring exam questions via pgvector cosine similarity.
          </p>
        </div>

        {/* Subject Selector */}
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-slate-400" />
          <select
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="input-field text-sm font-semibold max-w-xs"
          >
            {subjects.map((s) => (
              <option key={s.subject_id} value={s.subject_id}>
                {s.name} {s.course_code ? `(${s.course_code})` : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Heatmap Legend Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4 text-xs font-semibold">
          <span className="text-slate-500">Yield Scale:</span>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded bg-rose-600 inline-block" />
            <span>High Priority (≥ 70%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded bg-amber-500 inline-block" />
            <span>Moderate (40 - 69%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded bg-yellow-400 inline-block" />
            <span>Low (10 - 39%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded bg-slate-300 inline-block" />
            <span>Not in PYQs (&lt; 10%)</span>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-3">
          <select
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(parseFloat(e.target.value))}
            className="input-field text-xs py-1.5 max-w-[170px]"
          >
            <option value={0}>All Chunks</option>
            <option value={0.1}>Min 10% (Matched)</option>
            <option value={0.4}>Min 40% (Medium+)</option>
            <option value={0.7}>Min 70% (High Priority Only)</option>
          </select>
          <input
            type="text"
            placeholder="Filter chunk text..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field text-xs py-1.5 max-w-[200px]"
          />
        </div>
      </div>

      {/* Main Heatmap Content */}
      {loading ? (
        <div className="bg-white p-16 rounded-2xl border border-slate-200 text-center">
          <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">Calculating Heatmap</h3>
          <p className="text-sm text-slate-500 mt-1">Retrieving vectorized chunk scores and exam links...</p>
        </div>
      ) : error ? (
        <div className="bg-white p-12 rounded-2xl border border-dashed border-slate-300 text-center max-w-lg mx-auto">
          <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">Heatmap Unavailable</h3>
          <p className="text-sm text-slate-500 mt-1 mb-5">{error}</p>
          <button
            onClick={() => navigate('/subjects')}
            className="btn-primary inline-flex items-center gap-2"
          >
            Go to Subjects & Run Analysis
          </button>
        </div>
      ) : heatmapData && heatmapData.chunks.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>
              Showing {filteredChunks.length} of {heatmapData.chunks.length} total chunks in this course.
            </span>
            <span>
              Top match hit count: <strong className="text-slate-800">{heatmapData.max_hit_count}</strong> PYQs
            </span>
          </div>

          {/* Grid of Paragraph Chunk Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredChunks.map((chunk) => {
              const style = getColorClass(chunk.importance_score);
              return (
                <div
                  key={chunk.chunk_id}
                  onClick={() => setSelectedChunk(chunk)}
                  className={`cursor-pointer rounded-xl border p-4.5 transition-all duration-200 shadow-sm hover:shadow-md flex flex-col justify-between ${style.card}`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2.5">
                      <span className="text-[11px] font-semibold text-slate-500 truncate max-w-[180px]">
                        {chunk.document_filename}
                      </span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${style.badge}`}>
                        {Math.round(chunk.importance_score * 100)}% • {style.label}
                      </span>
                    </div>

                    <p className={`text-xs leading-relaxed font-sans line-clamp-4 ${style.text}`}>
                      {chunk.content}
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-black/5 flex items-center justify-between text-[11px]">
                    <span className="text-slate-500 font-medium">
                      Matched: <strong className="text-slate-800">{chunk.hit_count}</strong> PYQs
                    </span>
                    <span className="text-indigo-600 font-semibold inline-flex items-center gap-1 hover:underline">
                      Inspect Evidence <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="bg-white p-12 rounded-xl border text-center text-slate-400">
          No chunks available.
        </div>
      )}

      {/* PYQ Evidence Panel / Drawer */}
      {selectedChunk && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex justify-end">
          <div className="bg-white w-full max-w-xl h-full shadow-2xl flex flex-col animate-slide-left">
            {/* Header */}
            <div className="p-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <FlameKindling className="w-5 h-5 text-rose-500" />
                  PYQ Evidence Inspector
                </h3>
                <p className="text-xs text-slate-500">
                  {selectedChunk.document_filename} • Chunk #{selectedChunk.position}
                </p>
              </div>
              <button
                onClick={() => setSelectedChunk(null)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Score summary */}
              <div className="p-4 rounded-xl bg-indigo-50/60 border border-indigo-100 flex items-center justify-between">
                <div>
                  <p className="text-xs text-indigo-700 font-semibold uppercase tracking-wider">
                    Calculated Importance Score
                  </p>
                  <p className="text-2xl font-bold text-indigo-950 mt-0.5">
                    {Math.round(selectedChunk.importance_score * 100)}%
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-500 font-medium">Direct PYQ Hits</p>
                  <p className="text-xl font-bold text-slate-800">{selectedChunk.hit_count} Questions</p>
                </div>
              </div>

              {/* Exact Note Excerpt */}
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-slate-400" />
                  Notes Paragraph Excerpt
                </h4>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-sm text-slate-800 leading-relaxed font-sans whitespace-pre-wrap">
                  {selectedChunk.content}
                </div>
              </div>

              {/* Matched Questions */}
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <HelpCircle className="w-4 h-4 text-purple-500" />
                  Matched Exam Questions ({selectedChunk.matched_pyqs?.length || 0})
                </h4>

                {(!selectedChunk.matched_pyqs || selectedChunk.matched_pyqs.length === 0) ? (
                  <p className="text-xs text-slate-400 italic bg-slate-50 p-4 rounded-xl border border-slate-200">
                    No individual questions matched above the vector similarity threshold for this paragraph.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {selectedChunk.matched_pyqs.map((q, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl border border-purple-100 bg-purple-50/40 space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-purple-900 inline-flex items-center gap-1">
                            <Calendar className="w-3 h-3" /> {q.exam_year} • {q.marks} Marks
                          </span>
                          <span className="badge-primary text-[10px]">
                            {Math.round(q.similarity * 100)}% Similarity
                          </span>
                        </div>
                        <p className="text-xs text-slate-800 font-medium leading-relaxed">
                          {q.question}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Footer Action: Send to AI Assistant */}
            <div className="p-4 border-t border-slate-200 bg-slate-50">
              <button
                onClick={() => {
                  const prompt = `Can you explain the key concepts in this section: "${selectedChunk.content.slice(0, 150)}..." and how to answer the related exam questions?`;
                  navigate(`/chat?subject_id=${selectedSubjectId}&prompt=${encodeURIComponent(prompt)}`);
                }}
                className="w-full btn-primary inline-flex items-center justify-center gap-2 text-sm py-2.5"
              >
                <MessageSquare className="w-4 h-4 text-indigo-200" />
                Ask AI Assistant to Explain This Topic
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
