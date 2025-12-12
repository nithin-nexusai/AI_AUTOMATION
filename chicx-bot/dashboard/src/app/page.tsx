"use client";

import { useEffect, useState } from "react";
import { MessageSquare, Package, Phone, PhoneMissed } from "lucide-react";
import { StatsCard } from "@/components/stats-card";
import { MessagesChart } from "@/components/messages-chart";
import { getOverview } from "@/lib/api";
import type { OverviewData } from "@/lib/types";

export default function OverviewPage() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const overview = await getOverview();
        setData(overview);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-violet-600 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-600">
        {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
        <p className="text-gray-500">Today&apos;s snapshot</p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Conversations Today"
          value={data.conversations_today}
          icon={MessageSquare}
        />
        <StatsCard
          title="Orders Tracked"
          value={data.orders_tracked}
          icon={Package}
        />
        <StatsCard
          title="Calls Received"
          value={data.calls_received}
          icon={Phone}
        />
        <StatsCard
          title="Calls Missed"
          value={data.calls_missed}
          icon={PhoneMissed}
        />
      </div>

      {/* Messages Chart */}
      <MessagesChart data={data.messages_by_hour} />
    </div>
  );
}
