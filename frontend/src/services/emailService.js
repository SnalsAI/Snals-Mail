import apiClient from './api';

export const emailService = {
  // Lista email
  getEmails: async (filters = {}) => {
    const params = new URLSearchParams(filters);
    const response = await apiClient.get(`/api/emails?${params}`);
    return response.data;
  },

  // Dettaglio email
  getEmail: async (id) => {
    const response = await apiClient.get(`/api/emails/${id}`);
    return response.data;
  },

  // Statistiche
  getStats: async () => {
    const response = await apiClient.get('/api/emails/stats');
    return response.data;
  },

  // Ricategorizza
  recategorize: async (id) => {
    const response = await apiClient.post(`/api/emails/${id}/recategorize`);
    return response.data;
  },
};
