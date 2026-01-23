import axios, { AxiosError } from 'axios';
import { Edition, Item, SearchResult, GlobalSearchResult, SavedSearch, SavedSearchCreate, ItemType, ItemSubtype } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8007';

// Get JWT token from localStorage
const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token');
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add Authorization header
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear auth state and redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_role');

      // Only redirect if not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

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
    const response = await api.post(`/api/editions/${id}/reprocess`, {});
    return response.data;
  },

  // Process edition (trigger processing)
  processEdition: async (id: number): Promise<Edition> => {
    const response = await api.post(`/api/editions/${id}/process`, {});
    return response.data;
  },

  // Get processing status and logs
  getProcessingStatus: async (id: number): Promise<{
    edition: Edition;
    extraction_runs: Array<{
      id: number;
      version: string;
      success: boolean;
      started_at: string;
      finished_at?: string;
      log_path?: string;
      stats?: Record<string, unknown>;
    }>;
  }> => {
    const response = await api.get(`/api/processing/${id}/status`);
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

export const searchApi = {
  // Search within an edition
  searchEdition: async (
    editionId: number,
    query: string,
    filters?: {
      item_type?: ItemType;
      subtype?: ItemSubtype;
      page_number?: number;
      skip?: number;
      limit?: number;
    }
  ): Promise<SearchResult[]> => {
    const params = new URLSearchParams();
    params.append('q', query);
    if (filters?.item_type) params.append('item_type', filters.item_type);
    if (filters?.subtype) params.append('subtype', filters.subtype);
    if (filters?.page_number) params.append('page_number', filters.page_number.toString());
    if (filters?.skip) params.append('skip', filters.skip.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());

    const response = await api.get(`/api/search/edition/${editionId}/search?${params}`);
    return response.data;
  },

  // Search across all editions
  searchAll: async (
    query: string,
    filters?: {
      item_type?: ItemType;
      subtype?: ItemSubtype;
      newspaper_name?: string;
      date_from?: string;
      date_to?: string;
      skip?: number;
      limit?: number;
    }
  ): Promise<GlobalSearchResult[]> => {
    const params = new URLSearchParams();
    params.append('q', query);
    if (filters?.item_type) params.append('item_type', filters.item_type);
    if (filters?.subtype) params.append('subtype', filters.subtype);
    if (filters?.newspaper_name) params.append('newspaper_name', filters.newspaper_name);
    if (filters?.date_from) params.append('date_from', filters.date_from);
    if (filters?.date_to) params.append('date_to', filters.date_to);
    if (filters?.skip) params.append('skip', filters.skip.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());

    const response = await api.get(`/api/search/search?${params}`);
    return response.data;
  },
};

export const savedSearchesApi = {
  // Get all saved searches
  getSavedSearches: async (skip = 0, limit = 100, activeOnly = true): Promise<SavedSearch[]> => {
    const response = await api.get(`/api/saved-searches/?skip=${skip}&limit=${limit}&active_only=${activeOnly}`);
    return response.data;
  },

  // Get saved search by ID
  getSavedSearch: async (id: number): Promise<SavedSearch> => {
    const response = await api.get(`/api/saved-searches/${id}`);
    return response.data;
  },

  // Create saved search
  createSavedSearch: async (search: SavedSearchCreate): Promise<SavedSearch> => {
    const response = await api.post('/api/saved-searches', search);
    return response.data;
  },

  // Update saved search
  updateSavedSearch: async (id: number, search: SavedSearchCreate): Promise<SavedSearch> => {
    const response = await api.put(`/api/saved-searches/${id}`, search);
    return response.data;
  },

  // Delete saved search
  deleteSavedSearch: async (id: number): Promise<void> => {
    await api.delete(`/api/saved-searches/${id}`);
  },

  // Update search matches
  updateSearchMatches: async (id: number): Promise<SavedSearch> => {
    const response = await api.post(`/api/saved-searches/${id}/update-matches`, {});
    return response.data;
  },

  // Update all search matches
  updateAllSearchMatches: async (): Promise<{ message: string; updated: number; failed: number }> => {
    const response = await api.post('/api/saved-searches/update-all-matches', {});
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