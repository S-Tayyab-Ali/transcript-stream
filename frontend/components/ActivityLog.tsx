"use client";

import { useEffect, useRef } from "react";

interface ActivityLogProps {
  logs: string[];
}

export default function ActivityLog({ logs }: ActivityLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full flex flex-col">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">
        Activity Log
      </h2>
      <div className="flex-1 overflow-y-auto min-h-0 space-y-0.5">
        {logs.length === 0 && (
          <p className="text-xs text-gray-500">No activity yet</p>
        )}
        {logs.map((log, i) => (
          <div key={i} className="text-xs font-mono text-gray-400">
            {log}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
