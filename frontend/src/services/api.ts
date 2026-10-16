import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// Response error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const detail = error.response.data?.detail;
      const message = typeof detail === 'string' ? detail : 
                     Array.isArray(detail) ? detail.map((d: {msg: string}) => d.msg).join(', ') :
                     `HTTP ${error.response.status}`;
      return Promise.reject(new Error(message));
    } else if (error.request) {
      return Promise.reject(new Error('Cannot connect to server. Is the backend running?'));
    }
    return Promise.reject(error);
  }
);

// ── Subjects ────────────────────────────────────────────────────────────────

export const subjectsApi = {
  list: () => api.get('/api/subjects').then(r => r.data),
  get: (id: string) => api.get(`/api/subjects/${id}`).then(r => r.data),
  create: (data: { name: string; description?: string; course_code?: string }) =>
    api.post('/api/subjects', data).then(r => r.data),
  update: (id: string, data: { name?: string; description?: string; course_code?: string }) =>
    api.patch(`/api/subjects/${id}`, data).then(r => r.data),
  delete: (id: string) => api.delete(`/api/subjects/${id}`),
};

// ── Documents ────────────────────────────────────────────────────────────────

export const documentsApi = {
  list: (subjectId?: string) => {
    const params = subjectId ? { subject_id: subjectId } : {};
    return api.get('/api/documents', { params }).then(r => r.data);
  },
  upload: (subjectId: string, file: File, onProgress?: (pct: number) => void) => {
    const formData = new FormData();
    formData.append('subject_id', subjectId);
    formData.append('file', file);
    return api.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
      timeout: 120000,
    }).then(r => r.data);
  },
  get: (id: string) => api.get(`/api/documents/${id}`).then(r => r.data),
  delete: (id: string) => api.delete(`/api/documents/${id}`),
  reprocess: (id: string) => api.post(`/api/documents/${id}/reprocess`).then(r => r.data),
  getChunks: (id: string) => api.get(`/api/documents/${id}/chunks`).then(r => r.data),
};

// ── PYQs ─────────────────────────────────────────────────────────────────────

export const pyqsApi = {
  list: (params?: { subject_id?: string; exam_year?: number; marks?: number; skip?: number; limit?: number }) =>
    api.get('/api/pyqs', { params }).then(r => r.data),
  get: (id: string) => api.get(`/api/pyqs/${id}`).then(r => r.data),
  create: (data: {
    subject_id: string; exam_year: number; marks: number; question: string;
    semester?: string; course_code?: string; unit_name?: string;
  }) => api.post('/api/pyqs', data).then(r => r.data),
  update: (id: string, data: Partial<{ exam_year: number; marks: number; question: string; semester: string; unit_name: string }>) =>
    api.patch(`/api/pyqs/${id}`, data).then(r => r.data),
  delete: (id: string) => api.delete(`/api/pyqs/${id}`),
  importCSV: (subjectId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/api/pyqs/import-csv?subject_id=${subjectId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
};

// ── Analysis ──────────────────────────────────────────────────────────────────

export const analysisApi = {
  trigger: (subjectId: string) =>
    api.post(`/api/subjects/${subjectId}/analyze`).then(r => r.data),
  getRuns: (subjectId: string) =>
    api.get(`/api/subjects/${subjectId}/analysis`).then(r => r.data),
  get: (analysisId: string) =>
    api.get(`/api/analysis/${analysisId}`).then(r => r.data),
  getHeatmap: (analysisId: string) =>
    api.get(`/api/analysis/${analysisId}/heatmap`).then(r => r.data),
  getChunkPYQs: (chunkId: string) =>
    api.get(`/api/chunks/${chunkId}/pyqs`).then(r => r.data),
};

// ── Search ───────────────────────────────────────────────────────────────────

export const searchApi = {
  semantic: (query: string, subjectId?: string, topK: number = 10) =>
    api.post('/api/search/semantic', { query, subject_id: subjectId, top_k: topK }).then(r => r.data),
};

// ── Chat ─────────────────────────────────────────────────────────────────────

export const chatApi = {
  send: (question: string, sessionId?: string, subjectId?: string) =>
    api.post('/api/chat', { question, session_id: sessionId, subject_id: subjectId }, { timeout: 180000 }).then(r => r.data),
  getSessions: () => api.get('/api/chat/sessions').then(r => r.data),
  getSession: (id: string) => api.get(`/api/chat/sessions/${id}`).then(r => r.data),
  deleteSession: (id: string) => api.delete(`/api/chat/sessions/${id}`),
};

// ── Dashboard ────────────────────────────────────────────────────────────────

export const dashboardApi = {
  stats: () => api.get('/api/dashboard/stats').then(r => r.data),
  activity: () => api.get('/api/dashboard/activity').then(r => r.data),
  subjectsOverview: () => api.get('/api/dashboard/subjects-overview').then(r => r.data),
  analytics: () => api.get('/api/dashboard/analytics').then(r => r.data),
};

// ── Health ───────────────────────────────────────────────────────────────────

export const healthApi = {
  system: () => api.get('/api/health/system').then(r => r.data),
  database: () => api.get('/api/health/database').then(r => r.data),
  ollama: () => api.get('/api/health/ollama').then(r => r.data),
};
