"use client";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

interface LiveClockProps {
  elapsed: number;
  total: number;
  currentChunk: number;
  totalChunks: number;
}

export default function LiveClock({
  elapsed,
  total,
  currentChunk,
  totalChunks,
}: LiveClockProps) {
  const progress = total > 0 ? (elapsed / total) * 100 : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-2xl font-mono text-white">
          {formatTime(elapsed)}{" "}
          <span className="text-gray-500">/ {formatTime(total)}</span>
        </span>
      </div>
      <div className="text-xs text-gray-400 mb-2">
        Chunk {currentChunk} / {totalChunks}
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div
          className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
    </div>
  );
}
