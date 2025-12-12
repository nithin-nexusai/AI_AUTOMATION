"use client";

import { useEffect, useState } from "react";
import { Search, MessageSquare } from "lucide-react";
import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { StatusBadge } from "@/components/status-badge";
import { ChatModal } from "@/components/chat-modal";
import { getConversations } from "@/lib/api";
import { formatPhone, formatDateTime } from "@/lib/utils";
import type { Conversation, PaginatedResponse } from "@/lib/types";

export default function ConversationsPage() {
  const [data, setData] = useState<PaginatedResponse<Conversation> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const result = await getConversations({
          page,
          search: search || undefined,
          status: statusFilter || undefined,
        });
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [page, search, statusFilter]);

  const columns = [
    {
      key: "phone",
      header: "Phone",
      render: (item: Conversation) => (
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-gray-400" />
          <span className="font-medium">{formatPhone(item.phone)}</span>
        </div>
      ),
    },
    {
      key: "channel",
      header: "Channel",
      render: (item: Conversation) => (
        <span className="capitalize text-gray-600">{item.channel}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (item: Conversation) => <StatusBadge status={item.status} />,
    },
    {
      key: "message_count",
      header: "Messages",
      render: (item: Conversation) => (
        <span className="text-gray-600">{item.message_count}</span>
      ),
    },
    {
      key: "started_at",
      header: "Started",
      render: (item: Conversation) => (
        <span className="text-gray-600">{formatDateTime(item.started_at)}</span>
      ),
    },
    {
      key: "last_message_at",
      header: "Last Activity",
      render: (item: Conversation) => (
        <span className="text-gray-600">
          {item.last_message_at ? formatDateTime(item.last_message_at) : "-"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Conversations</h1>
        <p className="text-gray-500">CRM view of all chat sessions</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by phone number..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="closed">Closed</option>
          <option value="escalated">Escalated</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-violet-600 border-t-transparent" />
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-600">
          {error}
        </div>
      ) : (
        <>
          <DataTable
            columns={columns}
            data={data?.items || []}
            onRowClick={(item) => setSelectedId(item.id)}
            emptyMessage="No conversations found"
          />
          {data && (
            <Pagination
              currentPage={data.page}
              totalPages={data.pages}
              onPageChange={setPage}
            />
          )}
        </>
      )}

      {/* Chat Modal */}
      {selectedId && (
        <ChatModal
          conversationId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
