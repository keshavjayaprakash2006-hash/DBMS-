import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FileText, Upload, Trash2, RefreshCw, AlertCircle, CheckCircle,
  Clock, Loader2, Search, Filter, BookOpen, Layers, Eye, X,
  ChevronDown, FileUp, Sparkles
} from 'lucide-react';
import { documentsApi, subjectsApi } from '../services/api';
import type { Document, Subject, NoteChunk } from '../types';

export default function Notes() {
  const [searchParams] = useSearchParams();
  const initialSubjectId = searchParams.get('subject_id') || '';

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>(initialSubjectId);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Upload State
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Chunk Viewer State
  const [activeDocForChunks, setActiveDocForChunks] = useState<Document | null>(null);
  const [chunks, setChunks] = useState<NoteChunk[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);

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

  const fetchDocuments = async (subId?: string) => {
    try {
      setLoading(true);
      const docs = await documentsApi.list(subId || undefined);
      setDocuments(docs);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to load documents' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  useEffect(() => {
    fetchDocuments(selectedSubjectId);
  }, [selectedSubjectId]);

  const handleFileUpload = async (file: File) => {
    if (!selectedSubjectId) {
      setNotification({ type: 'error', message: 'Please select a subject first' });
      return;
    }
    const validExtensions = ['.pdf', '.docx', '.txt'];
    const hasValidExt = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    if (!hasValidExt) {
      setNotification({ type: 'error', message: 'Only PDF, DOCX, and TXT files are supported' });
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);
      await documentsApi.upload(selectedSubjectId, file, (progress) => {
        setUploadProgress(progress);
      });
      setNotification({
        type: 'success',
        message: `Uploaded '${file.name}'. Background chunking and vector embeddings underway!`,
      });
      fetchDocuments(selectedSubjectId);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Upload failed' });
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete '${filename}'? All note chunks will be removed.`)) return;
    try {
      await documentsApi.delete(docId);
      setNotification({ type: 'success', message: `Deleted '${filename}'` });
      if (activeDocForChunks?.document_id === docId) {
        setActiveDocForChunks(null);
        setChunks([]);
      }
      fetchDocuments(selectedSubjectId);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Delete failed' });
    }
  };

  const handleReprocess = async (docId: string) => {
    try {
      await documentsApi.reprocess(docId);
      setNotification({ type: 'success', message: 'Document scheduled for reprocessing' });
      fetchDocuments(selectedSubjectId);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Reprocess failed' });
    }
  };

  const handleViewChunks = async (doc: Document) => {
    setActiveDocForChunks(doc);
    try {
      setLoadingChunks(true);
      const chunkList = await documentsApi.getChunks(doc.document_id);
      setChunks(chunkList);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to load chunks' });
    } finally {
      setLoadingChunks(false);
    }
  };

  const filteredDocs = documents.filter(d =>
    d.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Notes & Study Documents</h1>
          <p className="text-sm text-slate-500 mt-1">
            Upload syllabi, lecture slides, and textbook chapters. The system extracts text and generates vector embeddings.
          </p>
        </div>

        {/* Subject Filter Dropdown */}
        <div className="flex items-center gap-3">
          <BookOpen className="w-4 h-4 text-slate-400" />
          <select
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="input-field text-sm font-semibold max-w-xs"
          >
            <option value="">All Subjects</option>
            {subjects.map((s) => (
              <option key={s.subject_id} value={s.subject_id}>
                {s.name} {s.course_code ? `(${s.course_code})` : ''}
              </option>
            ))}
          </select>
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

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-8 transition-all duration-200 text-center ${
          isDragging
            ? 'border-indigo-500 bg-indigo-50/60'
            : 'border-slate-300 hover:border-indigo-400 bg-slate-50/50 hover:bg-indigo-50/20'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center max-w-md mx-auto">
          <div className="w-14 h-14 bg-white shadow-sm border border-slate-200 rounded-2xl flex items-center justify-center text-indigo-600 mb-3">
            {uploading ? (
              <Loader2 className="w-7 h-7 animate-spin" />
            ) : (
              <FileUp className="w-7 h-7" />
            )}
          </div>
          <h3 className="text-base font-bold text-slate-800">
            {uploading ? `Processing Document (${uploadProgress}%)` : 'Upload Lecture Notes or Textbook'}
          </h3>
          <p className="text-xs text-slate-500 mt-1 mb-4">
            Drag and drop your file here, or click to browse. Supports PDF, DOCX, and TXT files up to 50MB.
          </p>

          <button
            type="button"
            disabled={uploading || !selectedSubjectId}
            onClick={() => fileInputRef.current?.click()}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Select File from Device
          </button>

          {!selectedSubjectId && (
            <p className="text-xs text-amber-600 mt-2 font-medium">
              * Please choose a subject from the top-right filter before uploading
            </p>
          )}
        </div>
      </div>

      {/* Filter and Document List */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search uploaded files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-10 text-sm py-2"
            />
          </div>
          <button
            onClick={() => fetchDocuments(selectedSubjectId)}
            className="p-2 text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 self-end sm:self-auto"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {loading && documents.length === 0 ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-2" />
            <p className="text-sm text-slate-500">Loading documents...</p>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-base font-semibold text-slate-700">No documents found</p>
            <p className="text-xs text-slate-400 mt-1">
              Upload course notes, textbook chapters, or unit summaries using the zone above.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Filename</th>
                  <th className="px-5 py-3.5">Type</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Chunks</th>
                  <th className="px-5 py-3.5">Embeddings</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDocs.map((doc) => (
                  <tr key={doc.document_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-4 font-medium text-slate-900">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-semibold">{doc.filename}</p>
                          <p className="text-xs text-slate-400">
                            {doc.extracted_text_length
                              ? `${doc.extracted_text_length.toLocaleString()} characters extracted`
                              : 'Pending extraction'}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="badge-neutral uppercase">{doc.file_type}</span>
                    </td>
                    <td className="px-5 py-4">
                      {doc.processing_status === 'completed' && (
                        <span className="badge-success inline-flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> Ready
                        </span>
                      )}
                      {doc.processing_status === 'processing' && (
                        <span className="badge-warning inline-flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin" /> Processing
                        </span>
                      )}
                      {doc.processing_status === 'pending' && (
                        <span className="badge-neutral inline-flex items-center gap-1">
                          <Clock className="w-3 h-3" /> Queued
                        </span>
                      )}
                      {doc.processing_status === 'failed' && (
                        <span className="badge-danger inline-flex items-center gap-1" title={doc.processing_error || ''}>
                          <AlertCircle className="w-3 h-3" /> Error
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 font-semibold text-slate-700">
                      {doc.chunk_count} chunks
                    </td>
                    <td className="px-5 py-4">
                      {doc.embeddings_generated ? (
                        <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                          <Sparkles className="w-3.5 h-3.5" /> 384-dim Vector
                        </span>
                      ) : (
                        <span className="text-xs font-medium text-slate-400">Not generated</span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleViewChunks(doc)}
                          className="p-1.5 rounded-lg text-indigo-600 hover:bg-indigo-50 transition-colors"
                          title="View chunks"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleReprocess(doc.document_id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                          title="Reprocess Document"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.document_id, doc.filename)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                          title="Delete Document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Chunk Drawer / Inspector Modal */}
      {activeDocForChunks && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex justify-end">
          <div className="bg-white w-full max-w-2xl h-full shadow-2xl flex flex-col animate-slide-left">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-indigo-600" />
                  Chunk Inspector
                </h3>
                <p className="text-xs text-slate-500 truncate max-w-md">
                  {activeDocForChunks.filename} ({chunks.length} chunks generated)
                </p>
              </div>
              <button
                onClick={() => setActiveDocForChunks(null)}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {loadingChunks ? (
                <div className="p-12 text-center">
                  <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-2" />
                  <p className="text-sm text-slate-500">Retrieving paragraph chunks from database...</p>
                </div>
              ) : chunks.length === 0 ? (
                <div className="p-12 text-center text-slate-400">
                  <p>No chunks generated for this document yet.</p>
                </div>
              ) : (
                chunks.map((chk) => (
                  <div
                    key={chk.chunk_id}
                    className="p-4 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 transition-colors shadow-sm"
                  >
                    <div className="flex items-center justify-between text-xs text-slate-500 mb-2 font-medium">
                      <span className="badge-primary">Position #{chk.position}</span>
                      <span>{chk.word_count} words</span>
                      {chk.has_embedding && (
                        <span className="text-emerald-600 font-semibold flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5" /> Vector Embedded
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-800 leading-relaxed font-sans bg-slate-50 p-3 rounded-lg border border-slate-100 whitespace-pre-wrap">
                      {chk.content}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
