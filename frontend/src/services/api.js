import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Auth API
export const authAPI = {
  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  register: (email, password, name) =>
    api.post('/auth/register', { email, password, name }),

  getCurrentUser: () =>
    api.get('/auth/me'),

  updateEmailConfig: (config) =>
    api.put('/auth/email-config', config)
};

// Email API
export const emailAPI = {
  getAll: (params) =>
    api.get('/emails', { params }),

  getById: (id) =>
    api.get(`/emails/${id}`),

  analyze: (id) =>
    api.post(`/emails/${id}/analyze`),

  updateStatus: (id, status, folder) =>
    api.patch(`/emails/${id}`, { status, folder }),

  delete: (id) =>
    api.delete(`/emails/${id}`),

  sync: (config) =>
    api.post('/emails/sync', config)
};

export default api;
