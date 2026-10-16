import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './layouts/Layout';
import { Dashboard } from './pages/Dashboard';
import Subjects from './pages/Subjects';
import Notes from './pages/Notes';
import PYQLibrary from './pages/PYQLibrary';
import Heatmap from './pages/Heatmap';
import SemanticSearch from './pages/SemanticSearch';
import AIAssistant from './pages/AIAssistant';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="subjects" element={<Subjects />} />
          <Route path="notes" element={<Notes />} />
          <Route path="pyqs" element={<PYQLibrary />} />
          <Route path="heatmap" element={<Heatmap />} />
          <Route path="search" element={<SemanticSearch />} />
          <Route path="chat" element={<AIAssistant />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
