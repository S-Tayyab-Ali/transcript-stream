"use client";

import { useEffect, useState } from "react";
import {
  getSessions,
  getTranscripts,
  createSession,
  SessionInfo,
} from "@/lib/api";
import StatusBadge from "./StatusBadge";

interface SessionListProps {
  selectedSessionId: string | null;
  onSelectSession: (session: SessionInfo) => void;
  onLog: (msg: string) => void;
}

export default function SessionList({
  selectedSessionId,
  onSelectSession,
  onLog,
}: SessionListProps) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [transcripts, setTranscripts] = useState<string[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [formFile, setFormFile] = useState("");
  const [formDuration, setFormDuration] = useState(50);
  const [formSpeed, setFormSpeed] = useState(1);

  const fetchSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchSessions();
    const iv = setInterval(fetchSessions, 3000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    getTranscripts()
      .then((d) => {
        setTranscripts(d.transcripts);
        if (d.transcripts.length > 0 && !formFile) {
          setFormFile(d.transcripts[0]);
        }
      })
      .catch(() => {});
  }, []);

  const handleCreate = async () => {
    try {
      const result = await createSession(
        formFile,
        formDuration * 60,
        formSpeed
      );
      onLog(
        `Session created: ${result.session_id.substring(0, 8)}... (${result.transcript_id})`
      );
      setShowCreate(false);
      await fetchSessions();
      // Auto-select the new session
      const newSessions = await getSessions();
      const created = newSessions.find(
        (s) => s.session_id === result.session_id
      );
      if (created) onSelectSession(created);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      onLog(`Create failed: ${msg}`);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300">Sessions</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded"
        >
          {showCreate ? "Cancel" : "+ New"}
        </button>
      </div>

      {showCreate && (
        <div className="mb-4 space-y-2 bg-gray-900 rounded p-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Transcript File
            </label>
            <select
              value={formFile}
              onChange={(e) => setFormFile(e.target.value)}
              className="w-full bg-gray-700 text-sm text-white rounded px-2 py-1.5"
            >
              {transcripts.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-xs text-gray-400 mb-1">
                Duration (min)
              </label>
              <input
                type="number"
                value={formDuration}
                onChange={(e) => setFormDuration(Number(e.target.value))}
                className="w-full bg-gray-700 text-sm text-white rounded px-2 py-1.5"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-gray-400 mb-1">
                Speed
              </label>
              <input
                type="number"
                value={formSpeed}
                onChange={(e) => setFormSpeed(Number(e.target.value))}
                step={0.5}
                min={0.1}
                className="w-full bg-gray-700 text-sm text-white rounded px-2 py-1.5"
              />
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={!formFile}
            className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-40 text-white text-sm py-1.5 rounded"
          >
            Create Session
          </button>
        </div>
      )}

      <div className="space-y-2">
        {sessions.length === 0 && (
          <p className="text-xs text-gray-500">
            No sessions yet. Create one to start.
          </p>
        )}
        {sessions.map((s) => (
          <button
            key={s.session_id}
            onClick={() => onSelectSession(s)}
            className={`w-full text-left rounded p-3 transition-colors ${
              selectedSessionId === s.session_id
                ? "bg-indigo-900/40 border border-indigo-600"
                : "bg-gray-900 hover:bg-gray-700 border border-transparent"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-xs text-gray-300">
                {s.transcript_id}
              </span>
              <StatusBadge state={s.state} />
            </div>
            <div className="text-xs text-gray-500">
              {s.transcript_file} &middot; {s.total_chunks} chunks &middot;{" "}
              {s.connected_clients_count} clients
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
