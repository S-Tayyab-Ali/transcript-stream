"use client";

import { useEffect, useState } from "react";
import { getConnections, ConnectionEntry } from "@/lib/api";

function timeAgo(ts: number): string {
  const diff = Math.floor(Date.now() / 1000 - ts);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function ConnectionMonitor() {
  const [connections, setConnections] = useState<ConnectionEntry[]>([]);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await getConnections();
        setConnections(data);
      } catch {
        // ignore
      }
    };
    poll();
    const iv = setInterval(poll, 5000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">
        Connections ({connections.length})
      </h2>
      {connections.length === 0 ? (
        <p className="text-xs text-gray-500">No clients connected</p>
      ) : (
        <div className="space-y-2">
          {connections.map((c) => (
            <div
              key={c.client_id}
              className="text-xs bg-gray-900 rounded p-2"
            >
              <div className="font-mono text-gray-300">
                {c.client_id.substring(0, 12)}...
              </div>
              <div className="text-gray-500">
                connected {timeAgo(c.connected_at)} &middot; chunks:{" "}
                {c.chunks_received}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
