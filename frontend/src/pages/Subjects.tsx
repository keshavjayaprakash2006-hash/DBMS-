import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BookOpen, Plus, Search, Edit3, Trash2, FlameKindling,
  FileText, HelpCircle, ArrowRight, AlertCircle, CheckCircle,
  Loader2, RefreshCw, X
} from 'lucide-react';
import { subjectsApi, analysisApi, dashboardApi } from '../services/api';
import type { Subject } from '../types';

interface SubjectOverview {
  subject_id: string;
  name: string;
  course_code?: string;
  doc_count: number;
  chunk_count: number;
  pyq_count: number;
  embedded_chunks: number;
  embedded_pyqs: number;
  has_analysis: boolean;
  latest_analysis_id?: string;
  ready_for_analysis: boolean;
}

export default function Subjects() {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [overviewMap, setOverviewMap] = useState<Record<string, SubjectOverview>>({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [analyzingSubjectId, setAnalyzingSubjectId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState<Subject | null>(null);
  const [formData, setFormData] = useState({ name: '', course_code: '', description: '' });
  const [saving, setSaving] = useState(false);

  // Delete Confirm State
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchSubjects = async () => {
    try {
      setLoading(true);
      const [subs, overviewData] = await Promise.all([
        subjectsApi.list(),
        dashboardApi.subjectsOverview(),
      ]);
      setSubjects(subs);
      const map: Record<string, SubjectOverview> = {};
      (overviewData.subjects || []).forEach((s: SubjectOverview) => {
        map[s.subject_id] = s;
      });
      setOverviewMap(map);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to load subjects' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  const openCreateModal = () => {
    setEditingSubject(null);
    setFormData({ name: '', course_code: '', description: '' });
    setIsModalOpen(true);
  };

  const openEditModal = (sub: Subject) => {
    setEditingSubject(sub);
    setFormData({
      name: sub.name,
      course_code: sub.course_code || '',
      description: sub.description || '',
    });
    setIsModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    try {
      setSaving(true);
      if (editingSubject) {
        await subjectsApi.update(editingSubject.subject_id, {
          name: formData.name.trim(),
          course_code: formData.course_code.trim() || undefined,
          description: formData.description.trim() || undefined,
        });
        setNotification({ type: 'success', message: `Subject '${formData.name}' updated successfully` });
      } else {
        await subjectsApi.create({
          name: formData.name.trim(),
          course_code: formData.course_code.trim() || undefined,
          description: formData.description.trim() || undefined,
        });
        setNotification({ type: 'success', message: `Subject '${formData.name}' created successfully` });
      }
      setIsModalOpen(false);
      fetchSubjects();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to save subject' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      setDeleting(true);
      await subjectsApi.delete(deleteId);
      setNotification({ type: 'success', message: 'Subject deleted successfully' });
      setDeleteId(null);
      fetchSubjects();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to delete subject' });
    } finally {
      setDeleting(false);
    }
  };

  const handleTriggerAnalysis = async (subId: string) => {
    try {
      setAnalyzingSubjectId(subId);
      const res = await analysisApi.trigger(subId);
      setNotification({
        type: 'success',
        message: 'Analysis initiated! Background worker is computing vector similarities.',
      });
      fetchSubjects();
      if (res.analysis_id) {
        setTimeout(() => navigate(`/heatmap?analysis_id=${res.analysis_id}`), 1200);
      }
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to trigger analysis' });
    } finally {
      setAnalyzingSubjectId(null);
    }
  };

  const filteredSubjects = subjects.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (s.course_code && s.course_code.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Academic Subjects</h1>
          <p className="text-sm text-slate-500 mt-1">
            Organize study materials, notes documents, and PYQ libraries per course.
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="btn-primary inline-flex items-center gap-2 self-start"
        >
          <Plus className="w-4 h-4" />
          New Subject
        </button>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div
          className={`flex items-center justify-between p-4 rounded-xl text-sm transition-all animate-fade-in ${
            notification.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? (
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-slate-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search & Stats Bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search subjects or course code..."
            className="input-field pl-10"
          />
        </div>
        <button
          onClick={fetchSubjects}
          title="Refresh subjects"
          className="p-2.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Grid of Subjects */}
      {loading && subjects.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-16 bg-white rounded-xl border border-slate-200">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-sm text-slate-500 mt-3 font-medium">Loading subjects...</p>
        </div>
      ) : filteredSubjects.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-16 bg-white rounded-xl border border-dashed border-slate-300 text-center">
          <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4 text-indigo-600">
            <BookOpen className="w-7 h-7" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">No subjects found</h3>
          <p className="text-sm text-slate-500 max-w-sm mt-1 mb-5">
            {searchQuery
              ? `No subjects match "${searchQuery}". Try a different keyword.`
              : 'Get started by creating your first academic subject or course module.'}
          </p>
          <button onClick={openCreateModal} className="btn-primary inline-flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Create First Subject
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredSubjects.map((sub) => {
            const ov = overviewMap[sub.subject_id] || {
              doc_count: 0,
              chunk_count: 0,
              pyq_count: 0,
              embedded_chunks: 0,
              embedded_pyqs: 0,
              has_analysis: false,
              ready_for_analysis: false,
            };

            const isAnalyzing = analyzingSubjectId === sub.subject_id;

            return (
              <div
                key={sub.subject_id}
                className="bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all duration-200 flex flex-col justify-between overflow-hidden"
              >
                <div className="p-5">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      {sub.course_code && (
                        <span className="badge-primary mb-1.5 inline-block">
                          {sub.course_code}
                        </span>
                      )}
                      <h3 className="text-lg font-bold text-slate-900 leading-snug">
                        {sub.name}
                      </h3>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => openEditModal(sub)}
                        className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                        title="Edit Subject"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteId(sub.subject_id)}
                        className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                        title="Delete Subject"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <p className="text-sm text-slate-600 line-clamp-2 mb-4">
                    {sub.description || 'No description provided.'}
                  </p>

                  {/* Resource Badges */}
                  <div className="grid grid-cols-3 gap-2 py-3 border-y border-slate-100 text-center">
                    <div className="bg-slate-50 p-2 rounded-lg">
                      <p className="text-xs text-slate-400 font-medium">Docs</p>
                      <p className="text-base font-bold text-slate-800">{ov.doc_count}</p>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-lg">
                      <p className="text-xs text-slate-400 font-medium">Chunks</p>
                      <p className="text-base font-bold text-slate-800">{ov.chunk_count}</p>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-lg">
                      <p className="text-xs text-slate-400 font-medium">PYQs</p>
                      <p className="text-base font-bold text-slate-800">{ov.pyq_count}</p>
                    </div>
                  </div>

                  {/* Status Indicator */}
                  <div className="mt-4 flex items-center justify-between text-xs">
                    <span className="text-slate-500">Vector Embeddings:</span>
                    <span
                      className={`font-semibold flex items-center gap-1 ${
                        ov.embedded_chunks > 0 && ov.embedded_pyqs > 0
                          ? 'text-emerald-600'
                          : 'text-amber-600'
                      }`}
                    >
                      {ov.embedded_chunks > 0 && ov.embedded_pyqs > 0 ? (
                        <>
                          <CheckCircle className="w-3.5 h-3.5" /> Ready for AI
                        </>
                      ) : (
                        <>
                          <AlertCircle className="w-3.5 h-3.5" /> Needs Embeddings
                        </>
                      )}
                    </span>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/notes?subject_id=${sub.subject_id}`)}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 transition-colors inline-flex items-center gap-1"
                    >
                      <FileText className="w-3.5 h-3.5 text-blue-500" />
                      Notes
                    </button>
                    <button
                      onClick={() => navigate(`/pyqs?subject_id=${sub.subject_id}`)}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 transition-colors inline-flex items-center gap-1"
                    >
                      <HelpCircle className="w-3.5 h-3.5 text-purple-500" />
                      PYQs
                    </button>
                  </div>

                  {ov.ready_for_analysis ? (
                    <button
                      onClick={() => handleTriggerAnalysis(sub.subject_id)}
                      disabled={isAnalyzing}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-colors inline-flex items-center gap-1 shadow-sm"
                    >
                      {isAnalyzing ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Analyzing...
                        </>
                      ) : (
                        <>
                          <FlameKindling className="w-3.5 h-3.5 text-amber-300" />
                          Run Analysis
                        </>
                      )}
                    </button>
                  ) : (
                    ov.has_analysis && (
                      <button
                        onClick={() => navigate(`/heatmap?subject_id=${sub.subject_id}`)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors inline-flex items-center gap-1"
                      >
                        <FlameKindling className="w-3.5 h-3.5" />
                        Heatmap
                      </button>
                    )
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-100 overflow-hidden animate-scale-up">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-900">
                {editingSubject ? 'Edit Subject' : 'Create New Subject'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 rounded-lg p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSave} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Subject Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Operating Systems"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Course Code
                </label>
                <input
                  type="text"
                  placeholder="e.g. CS204 or DBMS-301"
                  value={formData.course_code}
                  onChange={(e) => setFormData({ ...formData, course_code: e.target.value })}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Overview of curriculum, syllabus topics, or textbook references..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input-field resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !formData.name.trim()}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingSubject ? 'Update Subject' : 'Create Subject'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteId && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-100 animate-scale-up">
            <div className="w-12 h-12 bg-rose-50 rounded-xl flex items-center justify-center text-rose-600 mb-4">
              <Trash2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-1">Delete this Subject?</h3>
            <p className="text-sm text-slate-500 mb-6">
              All linked documents, paragraph chunks, and analysis heatmap runs will be permanently removed.
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteId(null)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 rounded-lg text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 transition-colors inline-flex items-center gap-2 shadow-sm"
              >
                {deleting && <Loader2 className="w-4 h-4 animate-spin" />}
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
