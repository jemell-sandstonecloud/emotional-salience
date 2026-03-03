/**
 * Sandstone API client.
 * All calls go through the Vite proxy → Flask backend.
 */

const BASE = '/api';

let _token = null;

export function setToken(t) { _token = t; }
export function getToken() { return _token; }
export function clearToken() { _token = null; }

async function request(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...opts.headers };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

// Auth
export const signup = (email, password, display_name) =>
  request('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password, display_name }) });

export const login = (email, password) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });

export const consent = () =>
  request('/auth/consent', { method: 'POST' });

// Chat
export const chatSplit = (message, model_id, session_number) =>
  request('/chat/split', { method: 'POST', body: JSON.stringify({ message, model_id, session_number }) });

// Ratings
export const submitRating = (data) =>
  request('/ratings', { method: 'POST', body: JSON.stringify(data) });

export const getRatings = (userId) =>
  request(`/ratings/${userId}`);

// Sessions
export const newSession = () =>
  request('/session/new', { method: 'POST' });

// Admin
export const getUsers = () => request('/admin/users');
export const getUserMemory = (uid) => request(`/admin/user/${uid}/memory`);
export const getUserRatings = (uid) => request(`/admin/user/${uid}/ratings`);
export const getModels = () => request('/admin/models');
export const getStats = () => request('/admin/stats');
export const getExport = () => request('/admin/export');
