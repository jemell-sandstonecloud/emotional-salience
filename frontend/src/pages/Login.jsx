import React, { useState } from 'react';
import { signup, login, setToken } from '../api';

export default function Login({ onAuth }) {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      let data;
      if (isSignup) {
        data = await signup(email, password, displayName);
      } else {
        data = await login(email, password);
      }
      onAuth(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4">
      <div className="w-full max-w-sm">
        {/* Wordmark */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-widest text-sand-400">SANDSTONE</h1>
          <p className="text-gray-500 mt-1 text-sm">Conversation Study</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-xl p-6 border border-gray-800 space-y-4">
          <h2 className="text-lg font-medium text-center">
            {isSignup ? 'Create Account' : 'Sign In'}
          </h2>

          {isSignup && (
            <input
              type="text"
              placeholder="Display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-sand-500"
            />
          )}

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-sand-500"
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-sand-500"
          />

          {error && <p className="text-red-400 text-xs text-center">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-sand-600 hover:bg-sand-500 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            {loading ? '...' : isSignup ? 'Create Account' : 'Sign In'}
          </button>

          <p className="text-center text-xs text-gray-500">
            {isSignup ? 'Already have an account?' : 'Need an account?'}{' '}
            <button type="button" onClick={() => setIsSignup(!isSignup)} className="text-sand-400 hover:underline">
              {isSignup ? 'Sign in' : 'Sign up'}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
