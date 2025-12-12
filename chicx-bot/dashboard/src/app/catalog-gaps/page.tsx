"use client";

import { useEffect, useState } from "react";
import { Search, AlertCircle, TrendingUp } from "lucide-react";
import { getCatalogGaps } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { CatalogGap } from "@/lib/types";

export default function CatalogGapsPage() {
  const [gaps, setGaps] = useState<CatalogGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getCatalogGaps(100);
        setGaps(data.gaps);
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Catalog Gaps</h1>
        <p className="text-gray-500">
          Product searches that returned no results
        </p>
      </div>

      {/* Info Banner */}
      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <AlertCircle className="h-5 w-5 flex-shrink-0 text-amber-600" />
        <div>
          <p className="font-medium text-amber-800">
            These are searches that customers made but found no products
          </p>
          <p className="mt-1 text-sm text-amber-700">
            Consider adding products that match these searches to improve
            customer experience and capture missed sales.
          </p>
        </div>
      </div>

      {/* Gaps List */}
      {gaps.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
          <Search className="mx-auto h-12 w-12 text-gray-300" />
          <p className="mt-4 text-gray-500">No catalog gaps found</p>
          <p className="text-sm text-gray-400">
            All customer searches are returning results
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Search Query
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Language
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Count
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Last Searched
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {gaps.map((gap, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Search className="h-4 w-4 text-gray-400" />
                      <span className="font-medium text-gray-900">
                        {gap.query}
                      </span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <span className="uppercase text-gray-600">
                      {gap.language || "-"}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="flex items-center gap-2">
                      <TrendingUp
                        className={`h-4 w-4 ${
                          gap.count >= 10
                            ? "text-red-500"
                            : gap.count >= 5
                            ? "text-amber-500"
                            : "text-gray-400"
                        }`}
                      />
                      <span
                        className={`font-semibold ${
                          gap.count >= 10
                            ? "text-red-600"
                            : gap.count >= 5
                            ? "text-amber-600"
                            : "text-gray-600"
                        }`}
                      >
                        {gap.count}
                      </span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {gap.last_searched
                      ? formatDateTime(gap.last_searched)
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
