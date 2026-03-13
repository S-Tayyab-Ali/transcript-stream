import re
import os
from models import TranscriptChunk
from config import WORDS_PER_MINUTE, LAST_CHUNK_FALLBACK_DURATION, TRANSCRIPT_DIR


TIMESTAMP_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})\s+(.+)$")
SPEAKER_PATTERN = re.compile(r"^\[([^\]]+)\]\s+(.+)$")


def parse_transcript(filename: str) -> list[TranscriptChunk]:
    filepath = os.path.join(TRANSCRIPT_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Transcript file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    raw_chunks: list[dict] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = TIMESTAMP_PATTERN.match(line)
        if not match:
            continue

        minutes = int(match.group(1))
        seconds = int(match.group(2))
        start_time = minutes * 60 + seconds
        text = match.group(3)

        # Check for optional speaker label: [Speaker Name] text...
        speaker_name = "Speaker 1"
        speaker_match = SPEAKER_PATTERN.match(text)
        if speaker_match:
            speaker_name = speaker_match.group(1)
            text = speaker_match.group(2)

        raw_chunks.append({
            "start_time": float(start_time),
            "text": text,
            "speaker_name": speaker_name,
        })

    chunks: list[TranscriptChunk] = []
    for i, raw in enumerate(raw_chunks):
        chunk_id = f"chunk_{i + 1:03d}"

        if i + 1 < len(raw_chunks):
            end_time = raw_chunks[i + 1]["start_time"]
        else:
            # Estimate duration from word count
            word_count = len(raw["text"].split())
            estimated_duration = (word_count / WORDS_PER_MINUTE) * 60
            end_time = raw["start_time"] + max(estimated_duration, LAST_CHUNK_FALLBACK_DURATION)

        chunks.append(TranscriptChunk(
            chunk_id=chunk_id,
            text=raw["text"],
            speaker_name=raw["speaker_name"],
            start_time=raw["start_time"],
            end_time=end_time,
        ))

    return chunks


def list_transcripts() -> list[str]:
    if not os.path.exists(TRANSCRIPT_DIR):
        return []
    return [f for f in os.listdir(TRANSCRIPT_DIR) if f.endswith(".txt")]
