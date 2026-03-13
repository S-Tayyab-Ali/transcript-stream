"use client";

import {
  startSession,
  pauseSession,
  resumeSession,
  resetSession,
  skipNext,
  skipTime,
} from "@/lib/api";

interface SessionControlsProps {
  sessionId: string;
  state: string;
  onAction: () => void;
  onLog: (msg: string) => void;
}

export default function SessionControls({
  sessionId,
  state,
  onAction,
  onLog,
}: SessionControlsProps) {
  const act = async (
    label: string,
    fn: () => Promise<unknown>
  ) => {
    try {
      await fn();
      onLog(label);
      onAction();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      onLog(`${label} failed: ${msg}`);
    }
  };

  const btnBase =
    "px-4 py-2 rounded font-medium text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div className="flex flex-wrap gap-2">
      {state === "idle" && (
        <button
          className={`${btnBase} bg-green-600 hover:bg-green-700 text-white`}
          onClick={() => act("Stream started", () => startSession(sessionId))}
        >
          Start
        </button>
      )}

      {state === "streaming" && (
        <button
          className={`${btnBase} bg-yellow-600 hover:bg-yellow-700 text-white`}
          onClick={() => act("Stream paused", () => pauseSession(sessionId))}
        >
          Pause
        </button>
      )}

      {state === "paused" && (
        <button
          className={`${btnBase} bg-green-600 hover:bg-green-700 text-white`}
          onClick={() => act("Stream resumed", () => resumeSession(sessionId))}
        >
          Resume
        </button>
      )}

      <button
        className={`${btnBase} bg-red-600 hover:bg-red-700 text-white`}
        onClick={() => act("Session reset", () => resetSession(sessionId))}
      >
        Reset
      </button>

      <button
        className={`${btnBase} bg-indigo-600 hover:bg-indigo-700 text-white`}
        disabled={state === "completed"}
        onClick={() => act("Skipped to next chunk", () => skipNext(sessionId))}
      >
        Next Chunk
      </button>

      <button
        className={`${btnBase} bg-gray-600 hover:bg-gray-700 text-white`}
        disabled={state === "completed"}
        onClick={() =>
          act("Skipped +1 min", () => skipTime(sessionId, 60))
        }
      >
        +1 Min
      </button>
    </div>
  );
}
