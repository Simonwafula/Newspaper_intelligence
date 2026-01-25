import axios, { AxiosError } from 'axios';
import {
  Edition, Item, SearchResult, GlobalSearchResult, SavedSearch, SavedSearchCreate, ItemType, ItemSubtype,
  Category, CategoryWithStats, CategoryCreate, CategoryUpdate, ItemWithCategories, ItemCategoryCreate,
  ItemCategoryResponse, BatchClassificationRequest, BatchClassificationResponse, ClassificationStats,
  Favorite, FavoriteCreate, Collection, CollectionCreate, CollectionUpdate, CollectionItem, CollectionItemCreate,
  CollectionWithItems, TrendDashboardResponse, StoryGroup, User, UserRole
} from '../types';

// Use empty string for production (relative URLs) or localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8007' : '');

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

  // Archive edition (manual trigger)
  archiveEdition: async (id: number): Promise<Edition> => {
    const response = await api.post(`/api/editions/${id}/archive`, {});
    return response.data;
  },

  // Get processing status and logs
  getProcessingStatus: async (id: number): Promise<{
    edition: Edition;
    extraction_runs: Array<{
      id: number;
      version: string;
      success: boolean;
      status?: string;
      started_at: string;
      finished_at?: string;
      completed_at?: string;
      log_path?: string;
      stats?: Record<string, unknown>;
      error_message?: string;
    }>;
  }> => {
    const response = await api.get(`/api/editions/${id}/status`);
    return response.data;
  },

  // Delete edition
  deleteEdition: async (id: number): Promise<void> => {
    await api.delete(`/api/editions/${id}`);
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

  getStoryGroups: async (editionId: number, skip = 0, limit = 100): Promise<StoryGroup[]> => {
    const response = await api.get(
      `/api/items/edition/${editionId}/story-groups?skip=${skip}&limit=${limit}`
    );
    return response.data;
  },

  getStoryGroup: async (editionId: number, groupId: number): Promise<StoryGroup> => {
    const response = await api.get(`/api/items/edition/${editionId}/story-groups/${groupId}`);
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

export const categoriesApi = {
  // List all categories
  getCategories: async (skip = 0, limit = 100, activeOnly = true): Promise<Category[]> => {
    const response = await api.get(`/api/categories/?skip=${skip}&limit=${limit}&active_only=${activeOnly}`);
    return response.data;
  },

  // Get category by ID
  getCategory: async (id: number): Promise<CategoryWithStats> => {
    const response = await api.get(`/api/categories/${id}`);
    return response.data;
  },

  // Get category by slug
  getCategoryBySlug: async (slug: string): Promise<CategoryWithStats> => {
    const response = await api.get(`/api/categories/slug/${slug}`);
    return response.data;
  },

  // Create new category (admin only)
  createCategory: async (category: CategoryCreate): Promise<Category> => {
    const response = await api.post('/api/categories/', category);
    return response.data;
  },

  // Update category (admin only)
  updateCategory: async (id: number, category: CategoryUpdate): Promise<Category> => {
    const response = await api.put(`/api/categories/${id}`, category);
    return response.data;
  },

  // Delete category (admin only)
  deleteCategory: async (id: number): Promise<void> => {
    await api.delete(`/api/categories/${id}`);
  },

  // Get items in category
  getItemsInCategory: async (
    categoryId: number,
    skip = 0,
    limit = 50,
    minConfidence = 0
  ): Promise<ItemWithCategories[]> => {
    const response = await api.get(
      `/api/categories/${categoryId}/items?skip=${skip}&limit=${limit}&min_confidence=${minConfidence}`
    );
    return response.data;
  },

  // Add category to item (admin only)
  addItemCategory: async (
    itemId: number,
    classification: ItemCategoryCreate
  ): Promise<ItemCategoryResponse> => {
    const response = await api.post(`/api/categories/items/${itemId}/categories`, classification);
    return response.data;
  },

  // Remove category from item (admin only)
  removeItemCategory: async (itemId: number, categoryId: number): Promise<void> => {
    await api.delete(`/api/categories/items/${itemId}/categories/${categoryId}`);
  },

  // Batch classify items (admin only)
  batchClassifyItems: async (request: BatchClassificationRequest): Promise<BatchClassificationResponse> => {
    const response = await api.post('/api/categories/batch-classify', request);
    return response.data;
  },

  // Reclassify all items (admin only)
  reclassifyAllItems: async (confidenceThreshold = 30): Promise<ClassificationStats> => {
    const response = await api.post(`/api/categories/reclassify-all?confidence_threshold=${confidenceThreshold}`);
    return response.data;
  },

  // Get category suggestions for text
  getCategorySuggestions: async (
    text: string,
    limit = 5,
    confidenceThreshold = 30
  ): Promise<Category[]> => {
    const response = await api.post(
      `/api/categories/suggest?text=${encodeURIComponent(text)}&limit=${limit}&confidence_threshold=${confidenceThreshold}`
    );
    return response.data;
  },
};

export const favoritesApi = {
  // List all favorites
  getFavorites: async (skip = 0, limit = 50, includeItems = true): Promise<Favorite[]> => {
    const response = await api.get(`/api/favorites/?skip=${skip}&limit=${limit}&include_items=${includeItems}`);
    return response.data;
  },

  // Add to favorites
  addFavorite: async (favorite: FavoriteCreate): Promise<Favorite> => {
    const response = await api.post('/api/favorites/', favorite);
    return response.data;
  },

  // Remove favorite by ID
  removeFavorite: async (id: number): Promise<void> => {
    await api.delete(`/api/favorites/${id}`);
  },

  // Remove favorite by item ID
  removeFavoriteByItem: async (itemId: number): Promise<void> => {
    await api.delete(`/api/favorites/item/${itemId}`);
  },
};

export const collectionsApi = {
  // List all collections
  getCollections: async (): Promise<Collection[]> => {
    const response = await api.get('/api/collections/');
    return response.data;
  },

  // Create new collection
  createCollection: async (collection: CollectionCreate): Promise<Collection> => {
    const response = await api.post('/api/collections/', collection);
    return response.data;
  },

  // Get collection with items
  getCollection: async (id: number): Promise<CollectionWithItems> => {
    const response = await api.get(`/api/collections/${id}`);
    return response.data;
  },

  // Update collection
  updateCollection: async (id: number, collection: CollectionUpdate): Promise<Collection> => {
    const response = await api.put(`/api/collections/${id}`, collection);
    return response.data;
  },

  // Delete collection
  deleteCollection: async (id: number): Promise<void> => {
    await api.delete(`/api/collections/${id}`);
  },

  // Add item to collection
  addItemToCollection: async (collectionId: number, item: CollectionItemCreate): Promise<CollectionItem> => {
    const response = await api.post(`/api/collections/${collectionId}/items`, item);
    return response.data;
  },

  // Remove item from collection
  removeItemFromCollection: async (collectionId: number, itemId: number): Promise<void> => {
    await api.delete(`/api/collections/${collectionId}/items/${itemId}`);
  },
};

export const analyticsApi = {
  // Get trend data
  getTrends: async (days = 30): Promise<TrendDashboardResponse> => {
    const response = await api.get(`/api/analytics/trends?days=${days}`);
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

export const usersApi = {
  // List all users (admin only)
  getUsers: async (): Promise<User[]> => {
    const response = await api.get('/api/users/');
    return response.data;
  },

  // Create new user (admin only)
  createUser: async (user: Partial<User> & { password?: string }): Promise<User> => {
    const response = await api.post('/api/users/admin', user);
    return response.data;
  },

  // Delete/Deactivate user (admin only)
  deleteUser: async (userId: number): Promise<void> => {
    await api.delete(`/api/users/${userId}`);
  },

  // Update user role (admin only)
  updateUserRole: async (userId: number, role: UserRole): Promise<User> => {
    const response = await api.patch(`/api/users/${userId}/role?role=${role}`);
    return response.data;
  },
};
