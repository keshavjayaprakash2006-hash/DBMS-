import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, CartesianGrid
} from 'recharts';
import {
  BarChart3, PieChart as PieIcon, Award, Calendar,
  TrendingUp, FlameKindling, Loader2, AlertCircle, RefreshCw
} from 'lucide-react';
import { dashboardApi } from '../services/api';

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];

export default function Analytics() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await dashboardApi.analytics();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-20 bg-white rounded-2xl border border-slate-200">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-3" />
        <p className="text-sm text-slate-500 font-medium">Aggregating exam trends & heatmap analytics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-rose-50 rounded-2xl border border-rose-200 text-rose-800 text-center max-w-md mx-auto">
        <AlertCircle className="w-10 h-10 text-rose-600 mx-auto mb-2" />
        <h3 className="font-bold">Analytics Unavailable</h3>
        <p className="text-xs text-slate-600 mt-1 mb-4">{error}</p>
        <button onClick={fetchAnalytics} className="btn-primary text-xs">
          Try Again
        </button>
      </div>
    );
  }

  const pyqByYear = data?.pyq_by_year || [];
  const pyqBySubj = data?.pyq_by_subject || [];
  const marksDist = data?.marks_distribution || [];
  const topChunks = data?.top_matched_chunks || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-indigo-600" />
            Curriculum & PYQ Analytics
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Exam trends, weightage breakdowns, and highest-yield paragraphs across subjects.
          </p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Grid of Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PYQs by Exam Year */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-600" />
              PYQs by Exam Year
            </h3>
            <span className="text-xs text-slate-400">Total Years Analyzed</span>
          </div>

          <div className="h-64">
            {pyqByYear.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No year data available yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={pyqByYear} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', fontSize: '12px', border: '1px solid #e2e8f0' }}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} name="Questions" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Questions by Subject */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-purple-600" />
              Questions by Subject
            </h3>
            <span className="text-xs text-slate-400">Curriculum Volume</span>
          </div>

          <div className="h-64">
            {pyqBySubj.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No subject distribution data.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pyqBySubj}
                    dataKey="count"
                    nameKey="subject"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={false}
                  >
                    {pyqBySubj.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', fontSize: '12px', border: '1px solid #e2e8f0' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Marks Allocation Breakdown */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-500" />
              Marks Allocation Distribution
            </h3>
            <span className="text-xs text-slate-400">Question Weightage Patterns</span>
          </div>

          <div className="h-56">
            {marksDist.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No marks distribution available yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={marksDist} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="marks" tick={{ fontSize: 11 }} tickFormatter={(m) => `${m} Marks`} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', fontSize: '12px', border: '1px solid #e2e8f0' }}
                  />
                  <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Questions" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Top 10 High-Yield Paragraph Chunks Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FlameKindling className="w-5 h-5 text-rose-500" />
              Top 10 Highest-Yield Paragraph Chunks
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Paragraphs from your study notes with the highest frequency of recurring exam questions.
            </p>
          </div>
        </div>

        {topChunks.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No analysis runs completed yet to rank high-yield chunks.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Rank</th>
                  <th className="px-5 py-3.5">Importance</th>
                  <th className="px-5 py-3.5">Direct Hits</th>
                  <th className="px-5 py-3.5">Note Excerpt</th>
                  <th className="px-5 py-3.5">Document</th>
                  <th className="px-5 py-3.5">Subject</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {topChunks.map((chk: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-4 font-bold text-slate-400">
                      #{idx + 1}
                    </td>
                    <td className="px-5 py-4">
                      <span className="badge-danger font-bold">
                        {Math.round(chk.importance_score * 100)}%
                      </span>
                    </td>
                    <td className="px-5 py-4 font-semibold text-slate-900">
                      {chk.hit_count} PYQs
                    </td>
                    <td className="px-5 py-4 max-w-md">
                      <p className="line-clamp-2 text-xs text-slate-700 font-sans leading-relaxed">
                        {chk.excerpt}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-xs font-medium text-slate-600">
                      {chk.document}
                    </td>
                    <td className="px-5 py-4 text-xs font-semibold text-indigo-700">
                      {chk.subject}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
