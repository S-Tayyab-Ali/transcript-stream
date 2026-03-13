"use client";

import { useEffect, useRef, useState } from "react";
import { connectToStream, TranscriptEvent } from "@/lib/socket";

function formatTs(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

interface TranscriptViewerProps {
  transcriptId: string | null;
  onLog: (msg: string) => void;
}

export default function TranscriptViewer({
  transcriptId,
  onLog,
}: TranscriptViewerProps) {
  const [chunks, setChunks] = useState<Map<string, TranscriptEvent>>(
    new Map()
  );
  const [latestId, setLatestId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!transcriptId) return;

    // Reset chunks when transcript changes
    setChunks(new Map());
    setLatestId(null);

    const socket = connectToStream(transcriptId);

    socket.on("auth.success", () => {
      onLog("WebSocket authenticated");
    });

    socket.on("auth.failed", (data: { message: string }) => {
      onLog(`WebSocket auth failed: ${data.message}`);
    });

    socket.on("connection.established", () => {
      onLog("WebSocket connection established");
    });

    socket.on("transcription.broadcast", (event: TranscriptEvent) => {
      setChunks((prev) => {
        const next = new Map(prev);
        next.set(event.chunk_id, event);
        return next;
      });
      setLatestId(event.chunk_id);
      onLog(`${event.chunk_id} received`);
    });

    socket.on("disconnect", () => {
      onLog("WebSocket disconnected");
    });

    return () => {
      socket.disconnect();
    };
  }, [transcriptId, onLog]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chunks.size]);

  const sortedChunks = Array.from(chunks.values()).sort(
    (a, b) => a.start_time - b.start_time
  );

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full flex flex-col">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">
        Live Transcript
        {transcriptId && (
          <span className="ml-2 font-mono text-xs text-gray-500">
            {transcriptId}
          </span>
        )}
      </h2>
      <div className="flex-1 overflow-y-auto space-y-3 min-h-0">
        {sortedChunks.length === 0 && (
          <p className="text-xs text-gray-500">
            {transcriptId
              ? "Waiting for transcript chunks..."
              : "Select a session to view transcript"}
          </p>
        )}
        {sortedChunks.map((chunk) => (
          <div
            key={chunk.chunk_id}
            className={`transition-all duration-700 ${
              chunk.chunk_id === latestId
                ? "bg-indigo-900/30 border-l-2 border-indigo-500 pl-3"
                : "pl-3 border-l-2 border-gray-700"
            }`}
          >
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs font-mono text-indigo-400">
                [{formatTs(chunk.start_time)}]
              </span>
              <span className="text-xs font-medium text-gray-400">
                {chunk.speaker_name}
              </span>
            </div>
            <p className="text-sm text-gray-200 leading-relaxed">
              {chunk.text}
            </p>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
