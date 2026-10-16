import { useEffect, useState } from 'react';
import { dashboardApi } from '../services/api';
import {
  BookOpen, FileText, HelpCircle, Brain,
  FlameKindling, PlusCircle, Upload, BarChart3,
  Search, MessageSquare, ChevronRight, AlertCircle,
  CheckCircle, Clock, TrendingUp, Activity
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { DashboardStats } from '../types';

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

interface Activity {
  type: string;
  description: string;
  timestamp: string;
  subject_name?: string;
  status?: string;
}

function StatCard({
  label, value, icon: Icon, color, subtitle
}: { label: string; value: number | string; icon: React.ElementType; color: string; subtitle?: string }) {
  return (
    <div className="stat-card animate-fade-in">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-3xl font-bold text-slate-900">{value}</p>
      {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
}

function QuickAction({ label, icon: Icon, color, onClick }: {
  label: string; icon: React.ElementType; color: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 w-full px-4 py-3 rounded-lg ${color} text-sm font-medium transition-all duration-150 hover:shadow-sm`}
    >
      <Icon className="w-4 h-4" />
      {label}
      <ChevronRight className="w-4 h-4 ml-auto" />
    </button>
  );
}

function activityIcon(type: string) {
  switch (type) {
    case 'document_uploaded': return <Upload className="w-4 h-4 text-blue-500" />;
    case 'pyq_added': return <HelpCircle className="w-4 h-4 text-purple-500" />;
    case 'analysis_completed': return <CheckCircle className="w-4 h-4 text-green-500" />;
    default: return <Activity className="w-4 h-4 text-slate-400" />;
  }
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (mins > 0) return `${mins}m ago`;
  return 'just now';
}

export function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [subjects, setSubjects] = useState<SubjectOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [s, a, so] = await Promise.all([
          dashboardApi.stats(),
          dashboardApi.activity(),
          dashboardApi.subjectsOverview(),
        ]);
        setStats(s);
        setActivities(a.activities || []);
        setSubjects(so.subjects || []);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="spinner w-8 h-8" />
      </div>
    );
  }

  const isEmpty = stats && stats.total_subjects === 0;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-1">Welcome to your Semantic PYQ Analyzer</p>
      </div>

      {error && (
        <div className="alert-error mb-6">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {isEmpty ? (
        /* Onboarding */
        <div className="card p-8 text-center max-w-2xl mx-auto">
          <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Brain className="w-8 h-8 text-blue-600" />
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Get Started</h2>
          <p className="text-slate-500 mb-6 text-sm">
            Set up your study workspace in 4 steps to unlock semantic analysis and the study heatmap.
          </p>
          <div className="grid grid-cols-2 gap-3 mb-6 text-left">
            {[
              { n: '1', t: 'Create a Subject', d: 'Add your course or subject', icon: BookOpen },
              { n: '2', t: 'Upload Notes', d: 'Upload PDF, DOCX, or TXT files', icon: Upload },
              { n: '3', t: 'Add PYQs', d: 'Import past exam questions', icon: HelpCircle },
              { n: '4', t: 'Run Analysis', d: 'Generate semantic heatmap', icon: FlameKindling },
            ].map(({ n, t, d, icon: Icon }) => (
              <div key={n} className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl">
                <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-blue-700">{n}</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-800">{t}</p>
                  <p className="text-xs text-slate-500">{d}</p>
                </div>
              </div>
            ))}
          </div>
          <button
            className="btn-primary"
            onClick={() => navigate('/subjects')}
          >
            <PlusCircle className="w-4 h-4" />
            Create Your First Subject
          </button>
        </div>
      ) : (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard
              label="Subjects"
              value={stats!.total_subjects}
              icon={BookOpen}
              color="bg-blue-50 text-blue-600"
              subtitle="Active courses"
            />
            <StatCard
              label="Documents"
              value={stats!.total_documents}
              icon={FileText}
              color="bg-violet-50 text-violet-600"
              subtitle="Uploaded files"
            />
            <StatCard
              label="Note Chunks"
              value={stats!.total_chunks.toLocaleString()}
              icon={Brain}
              color="bg-emerald-50 text-emerald-600"
              subtitle={`${stats!.chunks_with_embeddings} embedded`}
            />
            <StatCard
              label="PYQs"
              value={stats!.total_pyqs}
              icon={HelpCircle}
              color="bg-amber-50 text-amber-600"
              subtitle={`${stats!.pyqs_with_embeddings} embedded`}
            />
          </div>

          <div className="grid grid-cols-3 gap-4 mb-8">
            <StatCard
              label="Analyzed Subjects"
              value={stats!.analyzed_subjects}
              icon={TrendingUp}
              color="bg-rose-50 text-rose-600"
            />
            <StatCard
              label="Matched Chunks"
              value={stats!.matched_chunks}
              icon={FlameKindling}
              color="bg-orange-50 text-orange-600"
              subtitle="Linked to PYQs"
            />
            <StatCard
              label="Ready to Analyze"
              value={subjects.filter(s => s.ready_for_analysis).length}
              icon={CheckCircle}
              color="bg-green-50 text-green-600"
              subtitle="Subjects"
            />
          </div>

          <div className="grid grid-cols-3 gap-6">
            {/* Quick Actions */}
            <div className="card">
              <div className="card-header">
                <h3 className="font-semibold text-slate-800">Quick Actions</h3>
              </div>
              <div className="card-body space-y-2">
                <QuickAction label="Add Subject" icon={PlusCircle} color="bg-blue-50 text-blue-700 hover:bg-blue-100" onClick={() => navigate('/subjects')} />
                <QuickAction label="Upload Notes" icon={Upload} color="bg-violet-50 text-violet-700 hover:bg-violet-100" onClick={() => navigate('/notes')} />
                <QuickAction label="Add PYQs" icon={HelpCircle} color="bg-amber-50 text-amber-700 hover:bg-amber-100" onClick={() => navigate('/pyqs')} />
                <QuickAction label="View Heatmap" icon={FlameKindling} color="bg-orange-50 text-orange-700 hover:bg-orange-100" onClick={() => navigate('/heatmap')} />
                <QuickAction label="Semantic Search" icon={Search} color="bg-emerald-50 text-emerald-700 hover:bg-emerald-100" onClick={() => navigate('/search')} />
                <QuickAction label="AI Assistant" icon={MessageSquare} color="bg-rose-50 text-rose-700 hover:bg-rose-100" onClick={() => navigate('/chat')} />
              </div>
            </div>

            {/* Recent Activity */}
            <div className="card col-span-2">
              <div className="card-header flex items-center justify-between">
                <h3 className="font-semibold text-slate-800">Recent Activity</h3>
                <Clock className="w-4 h-4 text-slate-400" />
              </div>
              <div className="divide-y divide-slate-100">
                {activities.length === 0 ? (
                  <div className="p-6 text-center text-sm text-slate-400">
                    No recent activity. Start by uploading notes or adding PYQs.
                  </div>
                ) : (
                  activities.slice(0, 8).map((act, i) => (
                    <div key={i} className="px-6 py-3 flex items-start gap-3 hover:bg-slate-50">
                      <div className="mt-0.5">{activityIcon(act.type)}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-700 truncate">{act.description}</p>
                        {act.subject_name && (
                          <p className="text-xs text-slate-400">{act.subject_name}</p>
                        )}
                      </div>
                      <span className="text-xs text-slate-400 flex-shrink-0">{timeAgo(act.timestamp)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Subject Overview */}
          {subjects.length > 0 && (
            <div className="card mt-6">
              <div className="card-header flex items-center justify-between">
                <h3 className="font-semibold text-slate-800">Subject Overview</h3>
                <button onClick={() => navigate('/subjects')} className="text-xs text-blue-600 hover:underline">
                  View all →
                </button>
              </div>
              <div className="overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      <th>Subject</th>
                      <th>Docs</th>
                      <th>Chunks</th>
                      <th>PYQs</th>
                      <th>Analysis</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subjects.map(s => (
                      <tr key={s.subject_id}>
                        <td>
                          <p className="font-medium text-slate-800">{s.name}</p>
                          {s.course_code && <p className="text-xs text-slate-400">{s.course_code}</p>}
                        </td>
                        <td>{s.doc_count}</td>
                        <td>
                          <span>{s.embedded_chunks}/{s.chunk_count}</span>
                          {s.chunk_count > 0 && s.embedded_chunks < s.chunk_count && (
                            <span className="badge-warning ml-2">Processing</span>
                          )}
                        </td>
                        <td>{s.pyq_count}</td>
                        <td>
                          {s.has_analysis ? (
                            <span className="badge-success">Analyzed</span>
                          ) : s.ready_for_analysis ? (
                            <span className="badge-warning">Ready</span>
                          ) : (
                            <span className="badge-neutral">Not ready</span>
                          )}
                        </td>
                        <td>
                          {s.has_analysis && s.latest_analysis_id ? (
                            <button
                              onClick={() => navigate(`/heatmap?analysis=${s.latest_analysis_id}`)}
                              className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                            >
                              <FlameKindling className="w-3 h-3" /> Heatmap
                            </button>
                          ) : s.ready_for_analysis ? (
                            <button
                              onClick={() => navigate(`/subjects`)}
                              className="text-xs text-amber-600 hover:underline"
                            >
                              Run Analysis
                            </button>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
