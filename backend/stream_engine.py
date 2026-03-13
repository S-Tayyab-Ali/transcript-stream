import asyncio
import time
import uuid
from models import StreamSession, TranscriptChunk, ClientInfo
from transcript_parser import parse_transcript
from config import DEFAULT_TARGET_DURATION, DEFAULT_SPEED_MULTIPLIER


# Global session store
sessions: dict[str, StreamSession] = {}
# Map transcript_id -> session_id for WebSocket auth lookup
transcript_to_session: dict[str, str] = {}
# Streaming tasks so we can cancel them
streaming_tasks: dict[str, asyncio.Task] = {}

# Will be set by main.py after sio is created
sio = None


def set_sio(sio_instance):
    global sio
    sio = sio_instance


def create_session(
    transcript_file: str,
    target_duration: float = DEFAULT_TARGET_DURATION,
    speed_multiplier: float = DEFAULT_SPEED_MULTIPLIER,
) -> StreamSession:
    chunks = parse_transcript(transcript_file)
    if not chunks:
        raise ValueError("Transcript file is empty or has no valid chunks")

    session_id = str(uuid.uuid4())
    short_id = uuid.uuid4().hex[:8]
    transcript_id = f"mock_{short_id}"

    session = StreamSession(
        session_id=session_id,
        transcript_id=transcript_id,
        transcript_file=transcript_file,
        chunks=chunks,
        speed_multiplier=speed_multiplier,
        target_duration=target_duration,
    )

    sessions[session_id] = session
    transcript_to_session[transcript_id] = session_id
    return session


def get_session(session_id: str) -> StreamSession | None:
    return sessions.get(session_id)


def get_session_by_transcript(transcript_id: str) -> StreamSession | None:
    session_id = transcript_to_session.get(transcript_id)
    if session_id:
        return sessions.get(session_id)
    return None


def get_all_sessions() -> list[StreamSession]:
    return list(sessions.values())


def _get_time_scale(session: StreamSession) -> float:
    if not session.chunks:
        return 1.0
    max_time = session.chunks[-1].end_time
    if max_time == 0:
        return 1.0
    return session.target_duration / max_time


def _chunk_emit_time(session: StreamSession, chunk: TranscriptChunk) -> float:
    """Calculate when a chunk should be emitted (in meeting-time seconds)."""
    time_scale = _get_time_scale(session)
    return chunk.start_time * time_scale


def _chunk_to_event(session: StreamSession, chunk: TranscriptChunk) -> dict:
    return {
        "transcript_id": session.transcript_id,
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "speaker_name": chunk.speaker_name,
        "start_time": chunk.start_time,
        "end_time": chunk.end_time,
    }


async def _emit_chunk(session: StreamSession, chunk: TranscriptChunk):
    """Emit a single chunk to all connected clients of this session."""
    event_data = _chunk_to_event(session, chunk)
    session.emitted_chunks.append({
        "chunk_id": chunk.chunk_id,
        "emitted_at": time.time(),
        "meeting_time": session.elapsed_meeting_time,
        **event_data,
    })

    # Emit to each connected client individually
    clients = list(session.connected_clients.values())
    print(f"[STREAM] Emitting {chunk.chunk_id} to {len(clients)} clients")
    for client in clients:
        try:
            await sio.emit("transcription.broadcast", event_data, to=client.client_id)
            client.chunks_received += 1
            print(f"[STREAM] Sent {chunk.chunk_id} to {client.client_id}")
        except Exception as e:
            print(f"[WS] Failed to emit to {client.client_id}: {e}")


async def _streaming_loop(session: StreamSession):
    """Main async loop that emits chunks at the right times."""
    time_scale = _get_time_scale(session)

    while session.current_chunk_index < len(session.chunks) and session.state == "streaming":
        chunk = session.chunks[session.current_chunk_index]
        target_meeting_time = chunk.start_time * time_scale

        # How long to wait (in real seconds) until this chunk should emit
        time_until_chunk = (target_meeting_time - session.elapsed_meeting_time) / session.speed_multiplier

        if time_until_chunk > 0:
            # Sleep in small increments so we can respond to pause/speed changes
            sleep_start = time.time()
            while time_until_chunk > 0 and session.state == "streaming":
                sleep_amount = min(time_until_chunk, 0.1)
                await asyncio.sleep(sleep_amount)
                real_elapsed = time.time() - sleep_start
                session.elapsed_meeting_time = session.elapsed_meeting_time + (real_elapsed * session.speed_multiplier) - (session.elapsed_meeting_time - (target_meeting_time - (time_until_chunk - real_elapsed) * session.speed_multiplier))
                # Recalculate
                time_until_chunk = (target_meeting_time - session.elapsed_meeting_time) / session.speed_multiplier
                sleep_start = time.time()

        if session.state != "streaming":
            break

        # Update elapsed time to this chunk's time
        session.elapsed_meeting_time = target_meeting_time

        await _emit_chunk(session, chunk)
        session.current_chunk_index += 1

    if session.current_chunk_index >= len(session.chunks) and session.state == "streaming":
        session.state = "completed"


async def _simple_streaming_loop(session: StreamSession):
    """Simplified streaming loop - uses wall clock tracking."""
    time_scale = _get_time_scale(session)
    loop_start = time.time()
    base_meeting_time = session.elapsed_meeting_time

    while session.current_chunk_index < len(session.chunks) and session.state == "streaming":
        chunk = session.chunks[session.current_chunk_index]
        target_meeting_time = chunk.start_time * time_scale

        while session.state == "streaming":
            now = time.time()
            real_elapsed = now - loop_start
            session.elapsed_meeting_time = base_meeting_time + (real_elapsed * session.speed_multiplier)

            if session.elapsed_meeting_time >= target_meeting_time:
                break

            # Sleep a small amount
            remaining = (target_meeting_time - session.elapsed_meeting_time) / session.speed_multiplier
            await asyncio.sleep(min(remaining, 0.1))

        if session.state != "streaming":
            break

        session.elapsed_meeting_time = target_meeting_time
        await _emit_chunk(session, chunk)
        session.current_chunk_index += 1

    if session.current_chunk_index >= len(session.chunks) and session.state == "streaming":
        session.state = "completed"


async def start_session(session_id: str) -> bool:
    session = get_session(session_id)
    if not session or session.state not in ("idle",):
        return False

    session.state = "streaming"
    session.start_real_time = time.time()
    session.elapsed_meeting_time = 0.0
    session.current_chunk_index = 0

    task = asyncio.create_task(_simple_streaming_loop(session))
    streaming_tasks[session_id] = task
    return True


async def pause_session(session_id: str) -> bool:
    session = get_session(session_id)
    if not session or session.state != "streaming":
        return False

    session.state = "paused"
    session.pause_real_time = time.time()

    # Cancel the streaming task
    task = streaming_tasks.pop(session_id, None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    return True


async def resume_session(session_id: str) -> bool:
    session = get_session(session_id)
    if not session or session.state != "paused":
        return False

    session.state = "streaming"

    task = asyncio.create_task(_simple_streaming_loop(session))
    streaming_tasks[session_id] = task
    return True


async def reset_session(session_id: str) -> bool:
    session = get_session(session_id)
    if not session:
        return False

    # Stop streaming if running
    if session.state == "streaming":
        session.state = "idle"
        task = streaming_tasks.pop(session_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    session.state = "idle"
    session.current_chunk_index = 0
    session.elapsed_meeting_time = 0.0
    session.start_real_time = 0.0
    session.emitted_chunks.clear()
    return True


async def skip_next(session_id: str) -> dict | None:
    session = get_session(session_id)
    if not session:
        return None
    if session.current_chunk_index >= len(session.chunks):
        return None

    chunk = session.chunks[session.current_chunk_index]
    time_scale = _get_time_scale(session)
    session.elapsed_meeting_time = chunk.start_time * time_scale

    was_streaming = session.state == "streaming"

    # Cancel current loop if streaming
    if was_streaming:
        session.state = "paused"
        task = streaming_tasks.pop(session_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    await _emit_chunk(session, chunk)
    session.current_chunk_index += 1

    if session.current_chunk_index >= len(session.chunks):
        session.state = "completed"
        return _chunk_to_event(session, chunk)

    # Restart streaming if it was running
    if was_streaming:
        session.state = "streaming"
        task = asyncio.create_task(_simple_streaming_loop(session))
        streaming_tasks[session_id] = task

    return _chunk_to_event(session, chunk)


async def skip_time(session_id: str, seconds: float) -> list[dict] | None:
    session = get_session(session_id)
    if not session:
        return None

    time_scale = _get_time_scale(session)
    target_time = session.elapsed_meeting_time + seconds

    was_streaming = session.state == "streaming"

    # Cancel current loop if streaming
    if was_streaming:
        session.state = "paused"
        task = streaming_tasks.pop(session_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # Emit all chunks that fall within the skipped window
    emitted = []
    while session.current_chunk_index < len(session.chunks):
        chunk = session.chunks[session.current_chunk_index]
        chunk_time = chunk.start_time * time_scale
        if chunk_time > target_time:
            break

        session.elapsed_meeting_time = chunk_time
        await _emit_chunk(session, chunk)
        emitted.append(_chunk_to_event(session, chunk))
        session.current_chunk_index += 1
        await asyncio.sleep(0.05)  # Small delay for client processing

    session.elapsed_meeting_time = target_time

    if session.current_chunk_index >= len(session.chunks):
        session.state = "completed"
    elif was_streaming:
        session.state = "streaming"
        task = asyncio.create_task(_simple_streaming_loop(session))
        streaming_tasks[session_id] = task

    return emitted


async def set_speed(session_id: str, speed: float) -> bool:
    session = get_session(session_id)
    if not session:
        return False

    was_streaming = session.state == "streaming"

    # If streaming, restart the loop with new speed
    if was_streaming:
        session.state = "paused"
        task = streaming_tasks.pop(session_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    session.speed_multiplier = speed

    if was_streaming:
        session.state = "streaming"
        task = asyncio.create_task(_simple_streaming_loop(session))
        streaming_tasks[session_id] = task

    return True


def add_client(session: StreamSession, client_id: str) -> ClientInfo:
    client = ClientInfo(
        client_id=client_id,
        session_id=session.session_id,
        transcript_id=session.transcript_id,
    )
    session.connected_clients[client_id] = client
    return client


def remove_client(session: StreamSession, client_id: str):
    session.connected_clients.pop(client_id, None)


def get_all_connections() -> list[ClientInfo]:
    connections = []
    for session in sessions.values():
        connections.extend(session.connected_clients.values())
    return connections
