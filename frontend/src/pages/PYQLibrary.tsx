import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  HelpCircle, Plus, Upload, Trash2, Search, Filter,
  CheckCircle, AlertCircle, Loader2, Sparkles, X, FileSpreadsheet,
  Download, BookOpen, Calendar, Award
} from 'lucide-react';
import { pyqsApi, subjectsApi } from '../services/api';
import type { PYQ, Subject } from '../types';

export default function PYQLibrary() {
  const [searchParams] = useSearchParams();
  const initialSubjectId = searchParams.get('subject_id') || '';

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>(initialSubjectId);
  const [selectedYear, setSelectedYear] = useState<string>('');
  const [selectedMarks, setSelectedMarks] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [pyqs, setPyqs] = useState<PYQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Manual Add Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    subject_id: '',
    question: '',
    exam_year: new Date().getFullYear(),
    marks: 10,
    semester: 'Semester 5',
    course_code: '',
    unit_name: 'Unit 1',
  });
  const [submitting, setSubmitting] = useState(false);

  // CSV Import Modal State
  const [isCsvModalOpen, setIsCsvModalOpen] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvSubjectId, setCsvSubjectId] = useState('');
  const [importing, setImporting] = useState(false);
  const csvInputRef = useRef<HTMLInputElement>(null);

  const fetchSubjects = async () => {
    try {
      const subs = await subjectsApi.list();
      setSubjects(subs);
      if (!selectedSubjectId && subs.length > 0) {
        setSelectedSubjectId(subs[0].subject_id);
      }
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to load subjects' });
    }
  };

  const fetchPYQs = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (selectedSubjectId) params.subject_id = selectedSubjectId;
      if (selectedYear) params.exam_year = parseInt(selectedYear);
      if (selectedMarks) params.marks = parseInt(selectedMarks);
      const data = await pyqsApi.list(params);
      setPyqs(data);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to load PYQs' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  useEffect(() => {
    fetchPYQs();
  }, [selectedSubjectId, selectedYear, selectedMarks]);

  const handleManualAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.question.trim() || !formData.subject_id) return;
    try {
      setSubmitting(true);
      await pyqsApi.create({
        subject_id: formData.subject_id,
        question: formData.question.trim(),
        exam_year: Number(formData.exam_year),
        marks: Number(formData.marks),
        semester: formData.semester.trim() || undefined,
        course_code: formData.course_code.trim() || undefined,
        unit_name: formData.unit_name.trim() || undefined,
      });
      setNotification({
        type: 'success',
        message: 'Previous Year Question added! Vector embedding scheduled.',
      });
      setIsAddModalOpen(false);
      setFormData({
        subject_id: selectedSubjectId || (subjects[0]?.subject_id || ''),
        question: '',
        exam_year: new Date().getFullYear(),
        marks: 10,
        semester: '',
        course_code: '',
        unit_name: '',
      });
      fetchPYQs();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to add PYQ' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCsvImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile || !csvSubjectId) return;
    try {
      setImporting(true);
      const res = await pyqsApi.importCSV(csvSubjectId, csvFile);
      setNotification({
        type: 'success',
        message: `Successfully imported ${res.imported_count || 'all'} questions from CSV!`,
      });
      setIsCsvModalOpen(false);
      setCsvFile(null);
      fetchPYQs();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'CSV Import failed' });
    } finally {
      setImporting(false);
    }
  };

  const handleDelete = async (pyqId: string) => {
    if (!confirm('Are you sure you want to delete this question?')) return;
    try {
      await pyqsApi.delete(pyqId);
      setNotification({ type: 'success', message: 'Question removed from library' });
      fetchPYQs();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Delete failed' });
    }
  };

  const filteredPyqs = pyqs.filter((p) =>
    p.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.unit_name && p.unit_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">PYQ Question Library</h1>
          <p className="text-sm text-slate-500 mt-1">
            Store, categorize, and embed Previous Year Questions for semantic heatmap matching.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setCsvSubjectId(selectedSubjectId || (subjects[0]?.subject_id || ''));
              setIsCsvModalOpen(true);
            }}
            className="btn-secondary inline-flex items-center gap-2 text-sm"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Import CSV
          </button>
          <button
            onClick={() => {
              setFormData((prev) => ({
                ...prev,
                subject_id: selectedSubjectId || (subjects[0]?.subject_id || ''),
              }));
              setIsAddModalOpen(true);
            }}
            className="btn-primary inline-flex items-center gap-2 text-sm"
          >
            <Plus className="w-4 h-4" />
            Add Question
          </button>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div
          className={`flex items-center justify-between p-4 rounded-xl text-sm animate-fade-in ${
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
          <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search questions or unit topics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field pl-10 text-sm py-2"
          />
        </div>

        {/* Subject Filter */}
        <select
          value={selectedSubjectId}
          onChange={(e) => setSelectedSubjectId(e.target.value)}
          className="input-field text-sm font-medium py-2 max-w-xs"
        >
          <option value="">All Subjects</option>
          {subjects.map((s) => (
            <option key={s.subject_id} value={s.subject_id}>
              {s.name}
            </option>
          ))}
        </select>

        {/* Year Filter */}
        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(e.target.value)}
          className="input-field text-sm py-2 max-w-[130px]"
        >
          <option value="">All Years</option>
          {[2024, 2023, 2022, 2021, 2020, 2019, 2018].map((yr) => (
            <option key={yr} value={yr}>
              {yr}
            </option>
          ))}
        </select>

        {/* Marks Filter */}
        <select
          value={selectedMarks}
          onChange={(e) => setSelectedMarks(e.target.value)}
          className="input-field text-sm py-2 max-w-[130px]"
        >
          <option value="">All Marks</option>
          {[2, 5, 8, 10, 15, 20].map((m) => (
            <option key={m} value={m}>
              {m} Marks
            </option>
          ))}
        </select>
      </div>

      {/* Questions Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        {loading && pyqs.length === 0 ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-2" />
            <p className="text-sm text-slate-500 font-medium">Fetching PYQs...</p>
          </div>
        ) : filteredPyqs.length === 0 ? (
          <div className="p-12 text-center">
            <HelpCircle className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-base font-semibold text-slate-700">No questions found</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Add individual questions manually or import a batch via CSV file.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredPyqs.map((q) => (
              <div
                key={q.pyq_id}
                className="p-5 hover:bg-slate-50/80 transition-colors flex items-start justify-between gap-4"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="badge-primary inline-flex items-center gap-1">
                      <Calendar className="w-3 h-3" /> {q.exam_year}
                    </span>
                    <span className="badge-warning inline-flex items-center gap-1">
                      <Award className="w-3 h-3" /> {q.marks} Marks
                    </span>
                    {q.unit_name && (
                      <span className="badge-neutral text-xs">{q.unit_name}</span>
                    )}
                    {q.subject_name && (
                      <span className="text-xs text-slate-400 font-medium">
                        • {q.subject_name}
                      </span>
                    )}
                  </div>

                  <p className="text-sm font-medium text-slate-900 leading-relaxed">
                    {q.question}
                  </p>

                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    {q.has_embedding ? (
                      <span className="text-emerald-600 font-semibold flex items-center gap-1">
                        <Sparkles className="w-3.5 h-3.5" /> Vector Embedded (all-MiniLM-L6-v2)
                      </span>
                    ) : (
                      <span className="text-amber-500 font-medium">Pending embedding</span>
                    )}
                    {q.semester && <span>Semester: {q.semester}</span>}
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(q.pyq_id)}
                  className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors flex-shrink-0"
                  title="Delete question"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Manual Add Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-100 overflow-hidden animate-scale-up">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-900">Add Exam Question</h2>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleManualAdd} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Subject <span className="text-rose-500">*</span>
                </label>
                <select
                  required
                  value={formData.subject_id}
                  onChange={(e) => setFormData({ ...formData, subject_id: e.target.value })}
                  className="input-field"
                >
                  <option value="">Select a Subject</option>
                  {subjects.map((s) => (
                    <option key={s.subject_id} value={s.subject_id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Question Text <span className="text-rose-500">*</span>
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder="e.g. Explain ACID properties with a banking transaction scenario."
                  value={formData.question}
                  onChange={(e) => setFormData({ ...formData, question: e.target.value })}
                  className="input-field resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                    Exam Year <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    required
                    min={1990}
                    max={2030}
                    value={formData.exam_year}
                    onChange={(e) => setFormData({ ...formData, exam_year: parseInt(e.target.value) || 2024 })}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                    Marks Allocation <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    required
                    min={1}
                    max={100}
                    value={formData.marks}
                    onChange={(e) => setFormData({ ...formData, marks: parseInt(e.target.value) || 10 })}
                    className="input-field"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                    Unit / Module
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Unit 3: Normalization"
                    value={formData.unit_name}
                    onChange={(e) => setFormData({ ...formData, unit_name: e.target.value })}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                    Semester
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Semester 5"
                    value={formData.semester}
                    onChange={(e) => setFormData({ ...formData, semester: e.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setIsAddModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !formData.question.trim() || !formData.subject_id}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  Save Question
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CSV Import Modal */}
      {isCsvModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-100 overflow-hidden animate-scale-up">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                Import PYQs from CSV
              </h2>
              <button onClick={() => setIsCsvModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCsvImport} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Target Subject <span className="text-rose-500">*</span>
                </label>
                <select
                  required
                  value={csvSubjectId}
                  onChange={(e) => setCsvSubjectId(e.target.value)}
                  className="input-field"
                >
                  <option value="">Choose Subject</option>
                  {subjects.map((s) => (
                    <option key={s.subject_id} value={s.subject_id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Select CSV File <span className="text-rose-500">*</span>
                </label>
                <input
                  ref={csvInputRef}
                  type="file"
                  accept=".csv"
                  required
                  onChange={(e) => e.target.files?.[0] && setCsvFile(e.target.files[0])}
                  className="input-field file:mr-4 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                />
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-1">
                <p className="font-semibold text-slate-800">Expected CSV Headers:</p>
                <code className="block bg-white p-2 rounded border border-slate-200 font-mono text-indigo-700">
                  question,exam_year,marks,semester,unit_name
                </code>
                <p className="text-slate-400 text-[11px] mt-1">
                  * Questions are automatically vectorized with all-MiniLM-L6-v2 upon import.
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setIsCsvModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importing || !csvFile || !csvSubjectId}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {importing && <Loader2 className="w-4 h-4 animate-spin" />}
                  Import Questions
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
