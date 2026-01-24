export type EditionStatus = 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED' | 'ARCHIVED' | 'CANCELLED';
export type EditionStage = 'QUEUED' | 'EXTRACT' | 'OCR' | 'LAYOUT' | 'INDEX' | 'DONE';
export type ArchiveStatus = 'NOT_SCHEDULED' | 'SCHEDULED' | 'ARCHIVING' | 'ARCHIVED' | 'ARCHIVE_FAILED';

export type ItemType = 'STORY' | 'AD' | 'CLASSIFIED';

export type ItemSubtype = 'TENDER' | 'JOB' | 'AUCTION' | 'NOTICE' | 'PROPERTY' | 'OTHER';

export interface Edition {
  id: number;
  newspaper_name: string;
  edition_date: string;
  file_hash: string;
  total_pages: number;
  processed_pages: number;
  status: EditionStatus;
  current_stage: EditionStage;
  archive_status: ArchiveStatus;
  archived_at?: string;
  storage_backend: 'local' | 'gdrive';
  storage_key?: string;
  cover_image_path?: string;
  last_error?: string;
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
  status: 'PENDING' | 'PROCESSING' | 'DONE' | 'FAILED';
  char_count: number;
  ocr_used: boolean;
  error_message?: string;
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

// Favorite types
export interface Favorite {
  id: number;
  user_id: number;
  item_id: number;
  notes?: string;
  created_at: string;
  item?: Item;
}

export interface FavoriteCreate {
  item_id: number;
  notes?: string;
}

// Collection types
export interface Collection {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  color: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface CollectionCreate {
  name: string;
  description?: string;
  color?: string;
  is_public?: boolean;
}

export interface CollectionUpdate {
  name?: string;
  description?: string;
  color?: string;
  is_public?: boolean;
}

export interface CollectionItem {
  id: number;
  collection_id: number;
  item_id: number;
  notes?: string;
  created_at: string;
  updated_at: string;
  item?: Item;
}

export interface CollectionItemCreate {
  item_id: number;
  notes?: string;
}

export interface CollectionWithItems extends Collection {
  items: CollectionItem[];
}

// Analytics types
export interface TopicTrend {
  category_name: string;
  date: string;
  count: number;
}

export interface VolumeTrend {
  date: string;
  count: number;
}

export interface TrendDashboardResponse {
  topic_trends: TopicTrend[];
  volume_trends: VolumeTrend[];
  top_categories: { name: string; count: number }[];
}

// Structured data types for enhanced classifieds
export interface JobStructuredData {
  job_title?: string;
  employer?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  salary_description?: string;
  experience_years?: number;
  experience_years_min?: number;
  experience_years_max?: number;
  sector?: string[];
  qualifications?: string[];
  education_requirements?: string[];
  application_deadline?: string;
  work_location?: string;
  work_mode?: string;
}

export interface TenderStructuredData {
  tender_reference?: string;
  issuer?: string;
  title?: string;
  category?: string[];
  estimated_value?: number;
  currency?: string;
  deadline?: string;
  eligibility?: string[];
  contact?: string[];
}

export interface ItemWithStructuredData extends Item {
  structured_data?: JobStructuredData | TenderStructuredData | Record<string, unknown>;
  contact_info_json?: {
    phone_numbers?: string[];
    email_addresses?: string[];
  };
  price_info_json?: {
    amount?: number;
    currency?: string;
    negotiable?: boolean;
  };
  date_info_json?: {
    dates_mentioned?: string[];
    deadlines?: string[];
  };
  location_info_json?: {
    addresses?: string[];
    cities?: string[];
  };
}
