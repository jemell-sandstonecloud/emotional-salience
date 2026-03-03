import React, { useState, useCallback } from 'react';
import { setToken, clearToken } from './api';
import Login from './pages/Login';
import Consent from './pages/Consent';
import Chat from './pages/Chat';
import Admin from './pages/Admin';

/**
 * App — single-page router using state (no react-router needed for MVP).
 * Screens: login → consent → chat | admin
 */
export default function App() {
  const [user, setUser] = useState(null);       // { user_id, email, token, sandstone_panel, ... }
  const [consented, setConsented] = useState(false);
  const [screen, setScreen] = useState('login'); // login | consent | chat | admin

  const handleAuth = useCallback((userData) => {
    setToken(userData.token);
    setUser(userData);
    if (userData.session_count > 0) {
      // Returning user — skip consent
      setConsented(true);
      setScreen('chat');
    } else {
      setScreen('consent');
    }
  }, []);

  const handleConsent = useCallback(() => {
    setConsented(true);
    setScreen('chat');
  }, []);

  const handleLogout = useCallback(() => {
    clearToken();
    setUser(null);
    setConsented(false);
    setScreen('login');
  }, []);

  const handleAdmin = useCallback(() => setScreen('admin'), []);
  const handleChat = useCallback(() => setScreen('chat'), []);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Top bar */}
      {user && (
        <header className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800 text-sm">
          <span className="font-semibold tracking-wide text-sand-400">SANDSTONE</span>
          <div className="flex items-center gap-4">
            {screen === 'admin' && (
              <button onClick={handleChat} className="text-gray-400 hover:text-white transition">← Chat</button>
            )}
            {screen === 'chat' && (
              <button onClick={handleAdmin} className="text-gray-400 hover:text-white transition">Admin</button>
            )}
            <span className="text-gray-500">{user.email}</span>
            <button onClick={handleLogout} className="text-gray-500 hover:text-red-400 transition">Sign out</button>
          </div>
        </header>
      )}

      {/* Screens */}
      {screen === 'login' && <Login onAuth={handleAuth} />}
      {screen === 'consent' && <Consent onConsent={handleConsent} />}
      {screen === 'chat' && user && <Chat user={user} />}
      {screen === 'admin' && user && <Admin user={user} />}
    </div>
  );
}
