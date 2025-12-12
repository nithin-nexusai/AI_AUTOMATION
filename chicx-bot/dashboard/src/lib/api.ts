import type {
  OverviewData,
  Conversation,
  ConversationDetail,
  Call,
  CatalogGap,
  VoiceUsage,
  PaginatedResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY && { "X-API-Key": API_KEY }),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// Overview
export async function getOverview(): Promise<OverviewData> {
  return fetchApi<OverviewData>("/api/dashboard/overview");
}

// Conversations
export async function getConversations(params?: {
  status?: string;
  search?: string;
  page?: number;
  limit?: number;
}): Promise<PaginatedResponse<Conversation>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const query = searchParams.toString();
  return fetchApi<PaginatedResponse<Conversation>>(
    `/api/dashboard/conversations${query ? `?${query}` : ""}`
  );
}

export async function getConversationDetail(id: string): Promise<ConversationDetail> {
  return fetchApi<ConversationDetail>(`/api/dashboard/conversations/${id}`);
}

// Calls
export async function getCalls(params?: {
  status?: string;
  page?: number;
  limit?: number;
}): Promise<PaginatedResponse<Call>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const query = searchParams.toString();
  return fetchApi<PaginatedResponse<Call>>(
    `/api/dashboard/calls${query ? `?${query}` : ""}`
  );
}

export async function getCallAudio(id: string): Promise<{ audio_url: string; duration: number }> {
  return fetchApi(`/api/dashboard/calls/${id}/audio`);
}

// Voice Usage
export async function getVoiceUsage(params?: {
  year?: number;
  month?: number;
}): Promise<VoiceUsage> {
  const searchParams = new URLSearchParams();
  if (params?.year) searchParams.set("year", params.year.toString());
  if (params?.month) searchParams.set("month", params.month.toString());

  const query = searchParams.toString();
  return fetchApi<VoiceUsage>(
    `/api/dashboard/voice-usage${query ? `?${query}` : ""}`
  );
}

// Catalog Gaps
export async function getCatalogGaps(limit?: number): Promise<{ gaps: CatalogGap[]; total: number }> {
  const query = limit ? `?limit=${limit}` : "";
  return fetchApi(`/api/dashboard/catalog-gaps${query}`);
}
