export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokens?: number;
  model?: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface Document {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: string;
  created_at: string;
}

export interface SearchResult {
  content: string;
  score: number;
  document_id: number;
  document_name: string;
  metadata?: Record<string, any>;
}

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}
