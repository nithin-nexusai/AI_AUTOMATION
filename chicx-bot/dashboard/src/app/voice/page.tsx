"use client";

import { useEffect, useState } from "react";
import { Phone, Play, Clock } from "lucide-react";
import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { StatusBadge } from "@/components/status-badge";
import { AudioPlayer } from "@/components/audio-player";
import { getCalls, getVoiceUsage } from "@/lib/api";
import { formatPhone, formatDateTime } from "@/lib/utils";
import type { Call, PaginatedResponse, VoiceUsage } from "@/lib/types";

export default function VoicePage() {
  const [calls, setCalls] = useState<PaginatedResponse<Call> | null>(null);
  const [usage, setUsage] = useState<VoiceUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedCall, setSelectedCall] = useState<Call | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [callsData, usageData] = await Promise.all([
          getCalls({ page, status: statusFilter || undefined }),
          getVoiceUsage(),
        ]);
        setCalls(callsData);
        setUsage(usageData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [page, statusFilter]);

  const columns = [
    {
      key: "phone",
      header: "Phone",
      render: (item: Call) => (
        <div className="flex items-center gap-2">
          <Phone className="h-4 w-4 text-gray-400" />
          <span className="font-medium">{formatPhone(item.phone)}</span>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (item: Call) => <StatusBadge status={item.status} />,
    },
    {
      key: "duration",
      header: "Duration",
      render: (item: Call) => (
        <div className="flex items-center gap-1 text-gray-600">
          <Clock className="h-4 w-4" />
          {item.duration || "-"}
        </div>
      ),
    },
    {
      key: "language",
      header: "Language",
      render: (item: Call) => (
        <span className="text-gray-600 uppercase">{item.language || "-"}</span>
      ),
    },
    {
      key: "started_at",
      header: "Time",
      render: (item: Call) => (
        <span className="text-gray-600">{formatDateTime(item.started_at)}</span>
      ),
    },
    {
      key: "recording",
      header: "Recording",
      render: (item: Call) =>
        item.has_recording ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSelectedCall(item);
            }}
            className="flex items-center gap-1 rounded-full bg-violet-100 px-3 py-1 text-xs font-medium text-violet-700 hover:bg-violet-200"
          >
            <Play className="h-3 w-3" />
            Play
          </button>
        ) : (
          <span className="text-gray-400">-</span>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Voice</h1>
        <p className="text-gray-500">Call log and recordings</p>
      </div>

      {/* Usage Stats */}
      {usage && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">This Month</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">
              {usage.total_calls} calls
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Total Minutes</p>
            <p className="mt-1 text-2xl font-semibold text-violet-600">
              {usage.total_minutes} min
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Period</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">
              {usage.period.month_name} {usage.period.year}
            </p>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-4">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
        >
          <option value="">All Statuses</option>
          <option value="resolved">Resolved</option>
          <option value="escalated">Escalated</option>
          <option value="missed">Missed</option>
          <option value="failed">Failed</option>
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
            data={calls?.items || []}
            emptyMessage="No calls found"
          />
          {calls && (
            <Pagination
              currentPage={calls.page}
              totalPages={calls.pages}
              onPageChange={setPage}
            />
          )}
        </>
      )}

      {/* Audio Player Modal */}
      {selectedCall && (
        <AudioPlayer
          callId={selectedCall.id}
          phone={formatPhone(selectedCall.phone)}
          onClose={() => setSelectedCall(null)}
        />
      )}
    </div>
  );
}
