from dataclasses import dataclass, field
from pydantic import BaseModel
from typing import Optional
import time


@dataclass
class TranscriptChunk:
    chunk_id: str
    text: str
    speaker_name: str
    start_time: float
    end_time: float


@dataclass
class ClientInfo:
    client_id: str
    session_id: str
    transcript_id: str
    connected_at: float = field(default_factory=time.time)
    chunks_received: int = 0


@dataclass
class StreamSession:
    session_id: str
    transcript_id: str
    transcript_file: str
    chunks: list[TranscriptChunk] = field(default_factory=list)
    current_chunk_index: int = 0
    state: str = "idle"  # idle | streaming | paused | completed
    start_real_time: float = 0.0
    elapsed_meeting_time: float = 0.0
    pause_real_time: float = 0.0
    speed_multiplier: float = 1.0
    target_duration: float = 3000.0
    connected_clients: dict[str, ClientInfo] = field(default_factory=dict)
    emitted_chunks: list[dict] = field(default_factory=list)


# Pydantic models for API request/response

class CreateSessionRequest(BaseModel):
    transcript_file: str
    target_duration: float = 3000.0
    speed_multiplier: float = 1.0


class CreateSessionResponse(BaseModel):
    session_id: str
    transcript_id: str
    total_chunks: int
    target_duration: float
    state: str


class SessionSummary(BaseModel):
    session_id: str
    transcript_id: str
    transcript_file: str
    state: str
    elapsed_meeting_time: float
    total_chunks: int
    current_chunk: int
    connected_clients_count: int
    speed_multiplier: float
    target_duration: float


class SessionDetail(SessionSummary):
    connected_clients: list[dict]
    emitted_chunks: list[dict]


class SpeedRequest(BaseModel):
    speed: float


class SkipTimeRequest(BaseModel):
    seconds: float = 60.0


class ConnectionInfo(BaseModel):
    client_id: str
    session_id: str
    transcript_id: str
    connected_at: float
    chunks_received: int
