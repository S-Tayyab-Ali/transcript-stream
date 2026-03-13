"use client";

const STATUS_STYLES: Record<string, string> = {
  idle: "bg-gray-500",
  streaming: "bg-green-500 animate-pulse",
  paused: "bg-yellow-500",
  completed: "bg-blue-500",
};

export default function StatusBadge({ state }: { state: string }) {
  const style = STATUS_STYLES[state] || "bg-gray-500";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium text-white ${style}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-white" />
      {state.toUpperCase()}
    </span>
  );
}
