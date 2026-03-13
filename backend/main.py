import socketio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import time

from config import CORS_ORIGINS, TRANSCRIPT_DIR
from models import (
    CreateSessionRequest, CreateSessionResponse,
    SessionSummary, SessionDetail,
    SpeedRequest, SkipTimeRequest, ConnectionInfo,
)
import stream_engine
from transcript_parser import list_transcripts

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=CORS_ORIGINS,
)

# Pass sio to stream engine
stream_engine.set_sio(sio)

# Create FastAPI app
app = FastAPI(title="Mock Fireflies Realtime API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO as ASGI app
socket_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/ws/realtime")


# ─── Socket.IO Events ───


@sio.event
async def connect(sid, environ, auth):
    if not auth or "transcriptId" not in auth:
        await sio.emit("auth.failed", {"message": "Missing transcriptId"}, to=sid)
        await sio.disconnect(sid)
        return False

    transcript_id = auth["transcriptId"]
    token = auth.get("token", "")
    print(f"[WS] Client {sid} connecting with transcriptId={transcript_id}, token={token}")

    session = stream_engine.get_session_by_transcript(transcript_id)
    if not session:
        await sio.emit("auth.failed", {"message": "Invalid transcript ID"}, to=sid)
        await sio.disconnect(sid)
        return False

    # Join room for this transcript
    sio.enter_room(sid, transcript_id)

    # Track client
    stream_engine.add_client(session, sid)

    # Save transcript_id in session data for disconnect handling
    async with sio.session(sid) as sio_session:
        sio_session["transcript_id"] = transcript_id

    await sio.emit("auth.success", {"message": "Authenticated successfully"}, to=sid)
    await sio.emit("connection.established", {}, to=sid)

    print(f"[WS] Client {sid} authenticated and connected to session {session.session_id}")
    return True


@sio.event
async def disconnect(sid):
    print(f"[WS] Client {sid} disconnected")

    try:
        async with sio.session(sid) as sio_session:
            transcript_id = sio_session.get("transcript_id")
    except Exception:
        transcript_id = None

    if transcript_id:
        session = stream_engine.get_session_by_transcript(transcript_id)
        if session:
            stream_engine.remove_client(session, sid)


# ─── REST API Endpoints ───


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/sessions/create", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest):
    try:
        session = stream_engine.create_session(
            transcript_file=req.transcript_file,
            target_duration=req.target_duration,
            speed_multiplier=req.speed_multiplier,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreateSessionResponse(
        session_id=session.session_id,
        transcript_id=session.transcript_id,
        total_chunks=len(session.chunks),
        target_duration=session.target_duration,
        state=session.state,
    )


def _session_summary(s: stream_engine.StreamSession) -> dict:
    return {
        "session_id": s.session_id,
        "transcript_id": s.transcript_id,
        "transcript_file": s.transcript_file,
        "state": s.state,
        "elapsed_meeting_time": s.elapsed_meeting_time,
        "total_chunks": len(s.chunks),
        "current_chunk": s.current_chunk_index,
        "connected_clients_count": len(s.connected_clients),
        "speed_multiplier": s.speed_multiplier,
        "target_duration": s.target_duration,
    }


@app.get("/api/sessions")
async def list_sessions():
    return [_session_summary(s) for s in stream_engine.get_all_sessions()]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = stream_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    summary = _session_summary(session)
    summary["connected_clients"] = [
        {
            "client_id": c.client_id,
            "connected_at": c.connected_at,
            "chunks_received": c.chunks_received,
        }
        for c in session.connected_clients.values()
    ]
    summary["emitted_chunks"] = session.emitted_chunks[-50:]  # Last 50 for brevity
    return summary


@app.post("/api/sessions/{session_id}/start")
async def start_session(session_id: str):
    success = await stream_engine.start_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot start session (not in idle state or not found)")
    return {"status": "started"}


@app.post("/api/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    success = await stream_engine.pause_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause session (not streaming or not found)")
    return {"status": "paused"}


@app.post("/api/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    success = await stream_engine.resume_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume session (not paused or not found)")
    return {"status": "resumed"}


@app.post("/api/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    success = await stream_engine.reset_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Session not found")
    return {"status": "reset"}


@app.post("/api/sessions/{session_id}/skip-next")
async def skip_next(session_id: str):
    result = await stream_engine.skip_next(session_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot skip (session not found or no more chunks)")
    return {"status": "skipped", "chunk": result}


@app.post("/api/sessions/{session_id}/skip-time")
async def skip_time(session_id: str, req: SkipTimeRequest):
    result = await stream_engine.skip_time(session_id, req.seconds)
    if result is None:
        raise HTTPException(status_code=400, detail="Session not found")
    return {"status": "skipped", "chunks_emitted": len(result), "chunks": result}


@app.post("/api/sessions/{session_id}/speed")
async def set_speed(session_id: str, req: SpeedRequest):
    success = await stream_engine.set_speed(session_id, req.speed)
    if not success:
        raise HTTPException(status_code=400, detail="Session not found")
    return {"status": "speed_changed", "speed": req.speed}


@app.get("/api/transcripts")
async def get_transcripts():
    return {"transcripts": list_transcripts()}


@app.post("/api/transcripts/upload")
async def upload_transcript(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are accepted")

    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    filepath = os.path.join(TRANSCRIPT_DIR, file.filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return {"status": "uploaded", "filename": file.filename}


@app.get("/api/connections")
async def get_connections():
    connections = stream_engine.get_all_connections()
    return [
        {
            "client_id": c.client_id,
            "session_id": c.session_id,
            "transcript_id": c.transcript_id,
            "connected_at": c.connected_at,
            "chunks_received": c.chunks_received,
        }
        for c in connections
    ]


# The app is mounted via socket_app for proper Socket.IO handling
# Run with: uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
