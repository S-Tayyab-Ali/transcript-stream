"use client";

import { setSpeed } from "@/lib/api";

const SPEEDS = [1, 2, 5, 10, 50];

interface SpeedControlProps {
  sessionId: string;
  currentSpeed: number;
  onSpeedChange: (speed: number) => void;
}

export default function SpeedControl({
  sessionId,
  currentSpeed,
  onSpeedChange,
}: SpeedControlProps) {
  const handleSpeed = async (speed: number) => {
    try {
      await setSpeed(sessionId, speed);
      onSpeedChange(speed);
    } catch (e) {
      console.error("Failed to set speed:", e);
    }
  };

  return (
    <div>
      <label className="block text-xs font-medium text-gray-400 mb-2">
        Speed
      </label>
      <div className="flex gap-1.5">
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => handleSpeed(s)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              currentSpeed === s
                ? "bg-indigo-600 text-white"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
}
