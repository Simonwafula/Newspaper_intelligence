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