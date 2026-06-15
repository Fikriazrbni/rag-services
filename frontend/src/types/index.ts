export interface Document {
  id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  pipeline_stage: string | null;
  chunk_count: number;
  skipped_pages: number[];
  error_type: string | null;
  error_message: string | null;
  processing_duration_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  source_references: SourceReference[] | null;
  created_at: string;
}

export interface SourceReference {
  chunk_id: string;
  document_name: string;
  page_number: number | null;
  excerpt: string;
  confidence_score: number;
}

export interface ProviderConfig {
  config_type: string;
  provider_name: string;
  model_identifier: string;
  endpoint_url: string | null;
  is_active: boolean;
}

export interface AnalyticsSummary {
  total_documents: number;
  total_chunks: number;
  total_queries: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta: { request_id: string; timestamp: string };
}

export interface PaginatedApiResponse<T> {
  success: boolean;
  data: T[];
  meta: { request_id: string; timestamp: string };
  pagination: PaginationMeta;
}
