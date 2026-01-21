import axios from 'axios';
import { Edition, Item } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const editionsApi = {
  // Get all editions
  getEditions: async (skip = 0, limit = 50): Promise<Edition[]> => {
    const response = await api.get(`/api/editions/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  // Get edition by ID
  getEdition: async (id: number): Promise<Edition> => {
    const response = await api.get(`/api/editions/${id}`);
    return response.data;
  },

  // Upload new edition
  uploadEdition: async (file: File, newspaperName: string, editionDate: string): Promise<Edition> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('newspaper_name', newspaperName);
    formData.append('edition_date', editionDate);

    const response = await api.post('/api/editions/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Reprocess edition
  reprocessEdition: async (id: number): Promise<Edition> => {
    const response = await api.post(`/api/editions/${id}/reprocess`);
    return response.data;
  },

  // Process edition (trigger processing)
  processEdition: async (id: number): Promise<Edition> => {
    const response = await api.post(`/api/editions/${id}/process`);
    return response.data;
  },
};

export const itemsApi = {
  // Get items for edition
  getEditionItems: async (
    editionId: number,
    filters?: {
      item_type?: string;
      subtype?: string;
      page_number?: number;
      skip?: number;
      limit?: number;
    }
  ): Promise<Item[]> => {
    const params = new URLSearchParams();
    if (filters?.item_type) params.append('item_type', filters.item_type);
    if (filters?.subtype) params.append('subtype', filters.subtype);
    if (filters?.page_number) params.append('page_number', filters.page_number.toString());
    if (filters?.skip) params.append('skip', filters.skip.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());

    const response = await api.get(`/api/items/edition/${editionId}/items?${params}`);
    return response.data;
  },

  // Get single item
  getItem: async (id: number): Promise<Item> => {
    const response = await api.get(`/api/items/item/${id}`);
    return response.data;
  },
};

export const healthApi = {
  // Health check
  checkHealth: async (): Promise<{ status: string }> => {
    const response = await api.get('/api/healthz');
    return response.data;
  },
};