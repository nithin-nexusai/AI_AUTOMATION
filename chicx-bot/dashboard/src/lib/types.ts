// API Response Types

export interface OverviewData {
  conversations_today: number;
  orders_tracked: number;
  calls_received: number;
  calls_missed: number;
  messages_by_hour: { hour: number; count: number }[];
}

export interface Conversation {
  id: string;
  phone: string;
  status: "active" | "closed" | "escalated";
  channel: "whatsapp" | "voice";
  message_count: number;
  started_at: string;
  last_message_at: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export interface ConversationDetail {
  id: string;
  phone: string;
  status: string;
  channel: string;
  started_at: string;
  messages: Message[];
}

export interface Call {
  id: string;
  phone: string;
  status: "resolved" | "escalated" | "missed" | "failed";
  duration: string | null;
  language: string | null;
  started_at: string;
  has_recording: boolean;
}

export interface CatalogGap {
  query: string;
  language: string | null;
  count: number;
  last_searched: string | null;
}

export interface VoiceUsage {
  period: {
    year: number;
    month: number;
    month_name: string;
  };
  total_calls: number;
  total_seconds: number;
  total_minutes: number;
  calls_by_status: Record<
    string,
    { count: number; duration_seconds: number; duration_minutes: number }
  >;
  daily_breakdown: {
    date: string;
    calls: number;
    duration_seconds: number;
    duration_minutes: number;
  }[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}
