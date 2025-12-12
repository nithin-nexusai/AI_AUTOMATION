"use client";

import { useEffect, useState } from "react";
import { X, MessageSquare } from "lucide-react";
import { getConversationDetail } from "@/lib/api";
import { formatTime, formatPhone, cn } from "@/lib/utils";
import type { ConversationDetail } from "@/lib/types";

interface ChatModalProps {
  conversationId: string;
  onClose: () => void;
}

export function ChatModal({ conversationId, onClose }: ChatModalProps) {
  const [data, setData] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const detail = await getConversationDetail(conversationId);
        setData(detail);
      } catch (err) {
        console.error("Failed to load conversation:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [conversationId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative max-h-[80vh] w-full max-w-lg overflow-hidden rounded-xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 bg-violet-600 px-4 py-3 text-white">
          <div className="flex items-center gap-3">
            <MessageSquare className="h-5 w-5" />
            <div>
              <p className="font-medium">
                {data ? formatPhone(data.phone) : "Loading..."}
              </p>
              <p className="text-xs text-violet-200">
                {data?.channel} &bull; {data?.status}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1 hover:bg-white/20"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="h-96 overflow-y-auto bg-gray-50 p-4">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-violet-600 border-t-transparent" />
            </div>
          ) : data?.messages.length === 0 ? (
            <div className="flex h-full items-center justify-center text-gray-500">
              No messages in this conversation
            </div>
          ) : (
            <div className="space-y-3">
              {data?.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    "flex",
                    msg.role === "user" ? "justify-start" : "justify-end"
                  )}
                >
                  <div
                    className={cn(
                      "max-w-[80%] rounded-2xl px-4 py-2",
                      msg.role === "user"
                        ? "rounded-bl-none bg-white shadow"
                        : "rounded-br-none bg-violet-600 text-white"
                    )}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    <p
                      className={cn(
                        "mt-1 text-xs",
                        msg.role === "user"
                          ? "text-gray-400"
                          : "text-violet-200"
                      )}
                    >
                      {formatTime(msg.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
