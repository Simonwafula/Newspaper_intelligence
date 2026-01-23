export type EditionStatus = 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED';

export type ItemType = 'STORY' | 'AD' | 'CLASSIFIED';

export type ItemSubtype = 'TENDER' | 'JOB' | 'AUCTION' | 'NOTICE' | 'PROPERTY' | 'OTHER';

export interface Edition {
  id: number;
  newspaper_name: string;
  edition_date: string;
  file_hash: string;
  num_pages: number;
  status: EditionStatus;
  error_message?: string;
  created_at: string;
  processed_at?: string;
}

export interface Item {
  id: number;
  edition_id: number;
  page_id?: number;
  page_number: number;
  item_type: ItemType;
  subtype?: ItemSubtype;
  title?: string;
  text?: string;
  bbox_json?: Record<string, unknown>;
  extracted_entities_json?: Record<string, unknown>;
  created_at: string;
  categories?: ItemCategoryResponse[];
}

export interface Page {
  id: number;
  edition_id: number;
  page_number: number;
  image_path?: string;
  extracted_text?: string;
  created_at: string;
}

export interface SearchResult {
  item_id: number;
  title?: string;
  page_number: number;
  snippet: string;
  highlights: string[];
}

export interface GlobalSearchResult {
  item_id: number;
  title?: string;
  page_number: number;
  snippet: string;
  highlights: string[];
  edition_id: number;
  newspaper_name: string;
  edition_date: string;
  item_type: ItemType;
  subtype?: ItemSubtype;
}

export interface SavedSearch {
  id: number;
  name: string;
  description?: string;
  query: string;
  item_types?: ItemType[];
  date_from?: string;
  date_to?: string;
  match_count: number;
  last_run?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SavedSearchCreate {
  name: string;
  description?: string;
  query: string;
  item_types?: ItemType[];
  date_from?: string;
  date_to?: string;
}

// Category types
export interface Category {
  id: number;
  name: string;
  slug: string;
  description?: string;
  color: string;
  keywords?: string[];
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CategoryWithStats extends Category {
  item_count?: number;
  avg_confidence?: number;
  recent_items?: number;
}

export interface ItemCategory {
  id: number;
  item_id: number;
  category_id: number;
  confidence: number;
  source: 'auto' | 'manual';
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ItemCategoryResponse extends ItemCategory {
  category: Category;
}

export interface ItemWithCategories extends Item {
  categories: ItemCategoryResponse[];
}

export interface CategoryCreate {
  name: string;
  slug: string;
  description?: string;
  color: string;
  keywords?: string[];
  is_active?: boolean;
  sort_order?: number;
}

export interface CategoryUpdate {
  name?: string;
  slug?: string;
  description?: string;
  color?: string;
  keywords?: string[];
  is_active?: boolean;
  sort_order?: number;
}

export interface ItemCategoryCreate {
  category_id: number;
  confidence: number;
  notes?: string;
}

export interface BatchClassificationRequest {
  item_ids: number[];
  confidence_threshold?: number;
  clear_existing?: boolean;
}

export interface BatchClassificationResponse {
  total_items: number;
  items_classified: number;
  total_classifications: number;
  failed_items: number[];
  processing_time: number;
}

export interface ClassificationStats {
  total_items: number;
  items_classified: number;
  total_classifications: number;
  classification_rate: number;
  avg_categories_per_item: number;
}

// Auth types
export type UserRole = 'READER' | 'ADMIN';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_role: UserRole;
}