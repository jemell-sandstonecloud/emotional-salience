import React, { useState, useEffect, useCallback } from 'react';
import { getUsers, getUserMemory, getUserRatings, getStats, getModels, getExport } from '../api';

function Tab({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium transition ${
        active ? 'text-sand-400 border-b-2 border-sand-400' : 'text-gray-500 hover:text-gray-300'
      }`}
    >
      {label}
    </button>
  );
}

function UsersPanel() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUsers().then((d) => { setUsers(d.participants); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500 text-sm p-4">Loading...</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-800">
            <th className="p-2">Email</th>
            <th className="p-2">Name</th>
            <th className="p-2">Panel</th>
            <th className="p-2">Sessions</th>
            <th className="p-2">Exchanges</th>
            <th className="p-2">Consent</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.user_id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
              <td className="p-2 text-gray-300">{u.email}</td>
              <td className="p-2">{u.display_name}</td>
              <td className="p-2">
                <span className={`px-2 py-0.5 rounded text-xs ${
                  u.sandstone_panel === 'A' ? 'bg-blue-900 text-blue-300' : 'bg-emerald-900 text-emerald-300'
                }`}>
                  {u.sandstone_panel}
                </span>
              </td>
              <td className="p-2">{u.session_count}</td>
              <td className="p-2">{u.total_exchanges}</td>
              <td className="p-2">{u.consent_given_at ? '✓' : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {users.length === 0 && <p className="text-gray-600 text-center py-4">No participants yet.</p>}
    </div>
  );
}

function MemoryPanel() {
  const [userId, setUserId] = useState('');
  const [nodes, setNodes] = useState([]);
  const [searched, setSearched] = useState(false);

  const search = async () => {
    if (!userId.trim()) return;
    try {
      const d = await getUserMemory(userId.trim());
      setNodes(d.nodes);
      setSearched(true);
    } catch {
      setNodes([]);
      setSearched(true);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex gap-2">
        <input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="Enter user_id"
          className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm"
        />
        <button onClick={search} className="px-4 py-2 bg-sand-600 text-white rounded-lg text-sm">
          Search
        </button>
      </div>

      {searched && nodes.length === 0 && <p className="text-gray-500 text-sm">No memory nodes found.</p>}

      {nodes.map((n) => (
        <div key={n.id} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
          <div className="flex justify-between items-start mb-2">
            <span className="font-medium text-sand-400 uppercase text-sm">{n.topic}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              n.corrected_salience > 0.6 ? 'bg-red-900/50 text-red-300' :
              n.corrected_salience >= 0.3 ? 'bg-yellow-900/50 text-yellow-300' :
              'bg-gray-700 text-gray-400'
            }`}>
              {n.corrected_salience > 0.6 ? 'HIGH' : n.corrected_salience >= 0.3 ? 'MED' : 'LOW'}
              {' '}{n.corrected_salience.toFixed(3)}
            </span>
          </div>
          <p className="text-xs text-gray-400 mb-2">{n.content_preview}</p>
          <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
            <span>Base: {n.base_score.toFixed(3)}</span>
            <span>TDS: {n.tds_score.toFixed(3)}</span>
            <span>Decay: {n.decay_rate.toFixed(4)}</span>
            <span>Processed: {n.processing_count}×</span>
            <span>Spike: {n.spike_coefficient.toFixed(3)}</span>
            <span>Created: {n.created_at?.slice(0, 10)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function StatsPanel() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  if (!stats) return <p className="text-gray-500 text-sm p-4">Loading...</p>;

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          ['Participants', stats.total_participants],
          ['Total Ratings', stats.total_ratings],
          ['Total Sessions', stats.total_sessions],
          ['Total Exchanges', stats.total_exchanges],
        ].map(([label, val]) => (
          <div key={label} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
            <p className="text-2xl font-bold text-sand-400">{val}</p>
            <p className="text-xs text-gray-500">{label}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
        <h4 className="text-sm font-medium mb-2">Preference Breakdown</h4>
        <div className="flex gap-4 text-sm">
          <span className="text-blue-400">A: {stats.preference_breakdown.A}</span>
          <span className="text-emerald-400">B: {stats.preference_breakdown.B}</span>
          <span className="text-gray-400">None: {stats.preference_breakdown.none}</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Sandstone preference rate: {(stats.sandstone_preference_rate * 100).toFixed(1)}%
        </p>
      </div>
    </div>
  );
}

function ExportPanel() {
  const [exporting, setExporting] = useState(false);

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const data = await getExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sandstone-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <p className="text-sm text-gray-400">
        Export all study data including ratings, participant info, and memory state snapshots.
      </p>
      <button
        onClick={() => handleExport('json')}
        disabled={exporting}
        className="px-4 py-2 bg-sand-600 hover:bg-sand-500 text-white rounded-lg text-sm transition disabled:opacity-50"
      >
        {exporting ? 'Exporting...' : 'Export JSON'}
      </button>
    </div>
  );
}

export default function Admin({ user }) {
  const [tab, setTab] = useState('users');

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex border-b border-gray-800 px-4">
        {['users', 'memory', 'stats', 'export'].map((t) => (
          <Tab key={t} label={t.charAt(0).toUpperCase() + t.slice(1)} active={tab === t} onClick={() => setTab(t)} />
        ))}
      </div>

      {tab === 'users' && <UsersPanel />}
      {tab === 'memory' && <MemoryPanel />}
      {tab === 'stats' && <StatsPanel />}
      {tab === 'export' && <ExportPanel />}
    </div>
  );
}
