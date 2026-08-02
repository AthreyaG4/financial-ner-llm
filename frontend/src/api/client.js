const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) {
    let body = null;
    try { body = await res.json(); } catch (e) {}
    throw new ApiError(`API ${options.method || 'GET'} ${path} failed: ${res.status}`, res.status, body);
  }
  if (res.status === 204) return null;
  return res.json();
}
