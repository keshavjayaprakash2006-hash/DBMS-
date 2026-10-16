import { Outlet, NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, BookOpen, FileText, HelpCircle,
  FlameKindling, Search, MessageSquare, BarChart3,
  Settings, Cpu, ChevronRight, GraduationCap
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/subjects', label: 'Subjects', icon: BookOpen },
  { path: '/notes', label: 'Notes', icon: FileText },
  { path: '/pyqs', label: 'PYQ Library', icon: HelpCircle },
  { path: '/heatmap', label: 'Study Heatmap', icon: FlameKindling },
  { path: '/search', label: 'Semantic Search', icon: Search },
  { path: '/chat', label: 'AI Assistant', icon: MessageSquare },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Layout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col">
        {/* Brand */}
        <div className="px-6 py-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center shadow-sm">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 leading-tight">PYQ Analyzer</h1>
              <p className="text-xs text-slate-500">Study Heatmap Platform</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                clsx(
                  'nav-item w-full',
                  isActive ? 'nav-item-active' : 'nav-item-inactive'
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1">{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-slate-100">
          <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-lg">
            <Cpu className="w-4 h-4 text-slate-400" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-600 truncate">Local Processing</p>
              <p className="text-xs text-slate-400">Offline-first • Private</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
