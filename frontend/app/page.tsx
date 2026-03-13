"use client";

import { useCallback, useEffect, useState } from "react";
import { getSession, SessionInfo } from "@/lib/api";
import SessionList from "@/components/SessionList";
import SessionControls from "@/components/SessionControls";
import SpeedControl from "@/components/SpeedControl";
import LiveClock from "@/components/LiveClock";
import TranscriptViewer from "@/components/TranscriptViewer";
import ConnectionMonitor from "@/components/ConnectionMonitor";
import ActivityLog from "@/components/ActivityLog";
import StatusBadge from "@/components/StatusBadge";

function timestamp(): string {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

export default function Dashboard() {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = useCallback((msg: string) => {
    setLogs((prev) => [...prev.slice(-200), `${timestamp()} - ${msg}`]);
  }, []);

  // Poll session state
  useEffect(() => {
    if (!session) return;
    const poll = async () => {
      try {
        const data = await getSession(session.session_id);
        setSession(data);
      } catch {
        // ignore
      }
    };
    const iv = setInterval(poll, 1000);
    return () => clearInterval(iv);
  }, [session?.session_id]);

  const handleSelectSession = (s: SessionInfo) => {
    setSession(s);
    addLog(`Selected session ${s.transcript_id}`);
  };

  const handleAction = async () => {
    if (!session) return;
    try {
      const data = await getSession(session.session_id);
      setSession(data);
    } catch {
      // ignore
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-700">
        <h1 className="text-lg font-bold tracking-tight">
          MOCK FIREFLIES API
        </h1>
        {session && <StatusBadge state={session.state} />}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ height: "calc(100vh - 100px)" }}>
        {/* Left Column */}
        <div className="flex flex-col gap-4">
          {/* Session List */}
          <SessionList
            selectedSessionId={session?.session_id ?? null}
            onSelectSession={handleSelectSession}
            onLog={addLog}
          />

          {/* Controls */}
          {session && (
            <div className="bg-gray-800 rounded-lg p-4 space-y-4">
              <h2 className="text-sm font-semibold text-gray-300">Controls</h2>
              <SessionControls
                sessionId={session.session_id}
                state={session.state}
                onAction={handleAction}
                onLog={addLog}
              />
              <SpeedControl
                sessionId={session.session_id}
                currentSpeed={session.speed_multiplier}
                onSpeedChange={(speed) => {
                  setSession((prev) =>
                    prev ? { ...prev, speed_multiplier: speed } : null
                  );
                  addLog(`Speed changed to ${speed}x`);
                }}
              />
              <LiveClock
                elapsed={session.elapsed_meeting_time}
                total={session.target_duration}
                currentChunk={session.current_chunk}
                totalChunks={session.total_chunks}
              />

              {/* Transcript ID for copying */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Transcript ID (for client connection)
                </label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-gray-900 text-xs text-indigo-300 px-3 py-2 rounded font-mono">
                    {session.transcript_id}
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(session.transcript_id);
                      addLog("Transcript ID copied to clipboard");
                    }}
                    className="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-2 rounded text-gray-300"
                  >
                    Copy
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Transcript Viewer */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex-1 min-h-0">
            <TranscriptViewer
              transcriptId={session?.transcript_id ?? null}
              onLog={addLog}
            />
          </div>

          {/* Bottom Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-48">
            <ConnectionMonitor />
            <ActivityLog logs={logs} />
          </div>
        </div>
      </div>
    </div>
  );
}
