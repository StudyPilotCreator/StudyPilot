#!/usr/bin/env python3
"""ClipPilot: create short vertical clips from a supported public YouTube URL."""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel

ROOT = Path.home() / ".clippilot"
INBOX = ROOT / "inbox"
OUT = ROOT / "clips"
TOKEN_FILE = ROOT / "token.txt"
ROOT.mkdir(parents=True, exist_ok=True)
INBOX.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

TOKEN = os.environ.get("CLIPPILOT_TOKEN")
if not TOKEN:
    if TOKEN_FILE.exists():
        TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip()
    else:
        TOKEN = secrets.token_urlsafe(24)
        TOKEN_FILE.write_text(TOKEN, encoding="utf-8")
        try:
            TOKEN_FILE.chmod(0o600)
        except OSError:
            pass

print("\nClipPilot Verbindungstoken:")
print(TOKEN)
print("Dieses Token nur in deine eigene ClipPilot-Seite eintragen.\n")

app = FastAPI(title="ClipPilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

ALLOWED_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
WHISPER_MODEL: Optional[WhisperModel] = None
WHISPER_MODEL_NAME: Optional[str] = None


def auth(token: Optional[str]) -> None:
    if not token or not secrets.compare_digest(token, TOKEN):
        raise HTTPException(401, "Verbindungstoken fehlt oder ist falsch. Bitte Token im Mac-Terminal prüfen.")


def validate_youtube_url(value: str) -> str:
    value = (value or "").strip()
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        raise HTTPException(400, "Der YouTube-Link ist ungültig.")

    if parsed.scheme != "https" or host not in ALLOWED_YOUTUBE_HOSTS:
        raise HTTPException(400, "Bitte einen normalen YouTube-Link einfügen (youtube.com oder youtu.be).")
    if parsed.username or parsed.password or (port not in (None, 443)):
        raise HTTPException(400, "Dieser Link wird aus Sicherheitsgründen nicht unterstützt.")
    if parsed.path.startswith("/redirect"):
        raise HTTPException(400, "Weiterleitungslinks werden nicht unterstützt. Bitte den direkten YouTube-Link kopieren.")
    return value


@app.get("/")
def home():
    return FileResponse(Path(__file__).parent / "index.html", media_type="text/html")


@app.get("/mobile")
def mobile_page():
    return FileResponse(Path(__file__).parent / "mobile.html", media_type="text/html")


@app.get("/api/health")
def health(x_clippilot_token: Optional[str] = Header(None)):
    auth(x_clippilot_token)
    try:
        import yt_dlp
        yt_dlp_version = yt_dlp.version.__version__
    except Exception:
        yt_dlp_version = "unavailable"
    ffmpeg_bin = shutil.which("ffmpeg")
    subtitles_available = False
    if ffmpeg_bin:
        try:
            filters = subprocess.run(
                [ffmpeg_bin, "-hide_banner", "-filters"],
                capture_output=True, text=True, timeout=15
            )
            subtitles_available = (
                filters.returncode == 0
                and re.search(r"\bsubtitles\b", filters.stdout) is not None
            )
        except Exception:
            subtitles_available = False
    return {
        "ok": True,
        "service": "ClipPilot",
        "version": "0.4",
        "link_only": True,
        "yt_dlp_version": yt_dlp_version,
        "deno_available": bool(shutil.which("deno")),
        "ffmpeg_path": ffmpeg_bin,
        "ffmpeg_subtitles_available": subtitles_available,
    }


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "video")
    return cleaned[:100] or "video"


def get_whisper(model_name: str) -> WhisperModel:
    global WHISPER_MODEL, WHISPER_MODEL_NAME
    if model_name not in ("tiny", "base", "small"):
        model_name = "base"
    if WHISPER_MODEL is None or WHISPER_MODEL_NAME != model_name:
        WHISPER_MODEL = WhisperModel(model_name, device="cpu", compute_type="int8")
        WHISPER_MODEL_NAME = model_name
    return WHISPER_MODEL


def srt_time(seconds: float) -> str:
    ms = max(0, int(seconds * 1000))
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    secs = ms // 1000
    ms %= 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def score_window(segments, start: float, end: float) -> float:
    """Heuristic score: speech coverage, useful phrases, reactions and variety."""
    selected = [s for s in segments if s["start"] < end and s["end"] > start]
    if not selected:
        return -100.0

    text = " ".join(s["text"] for s in selected).lower()
    words = re.findall(r"\b[\w']+\b", text)
    word_count = len(words)
    speech_seconds = sum(
        max(0.0, min(end, s["end"]) - max(start, s["start"])) for s in selected
    )
    speech_ratio = min(1.0, speech_seconds / max(1.0, end - start))

    cues = {
        "reaction": [
            "wow", "wtf", "oh my god", "no way", "holy", "unglaublich",
            "krass", "geisteskrank", "niemals", "ernsthaft",
        ],
        "emotion": [
            "ich liebe", "ich hasse", "verdammt", "geil", "unfassbar",
            "crazy", "wild", "brutal", "absurd",
        ],
        "turning": [
            "aber dann", "plötzlich", "auf einmal", "doch dann",
            "am ende", "actually", "finally", "suddenly", "turns out",
        ],
        "reveal": [
            "das problem", "der grund", "die lösung", "geheimnis",
            "here's why", "deshalb", "darum", "because",
        ],
    }
    weights = {"reaction": 3.2, "emotion": 2.2, "turning": 2.5, "reveal": 2.0}
    cue_score = 0.0
    for category, phrases in cues.items():
        matches = sum(text.count(phrase) for phrase in phrases)
        cue_score += min(4, matches) * weights[category]

    punctuation = sum(s["text"].count("!") + 0.6 * s["text"].count("?") for s in selected)
    sentence_starts = sum(1 for s in selected if s["text"].strip())
    density = min(12.0, word_count / max(1.0, end - start) * 20.0)
    coverage = speech_ratio * 10.0
    length_quality = min(8.0, word_count / 7.0)
    punctuation_score = min(5.0, punctuation * 0.7)
    fragmentation_penalty = max(0, sentence_starts - word_count / 8.0) * 0.25
    sparse_penalty = 6.0 if word_count < 8 else (2.5 if word_count < 18 else 0.0)
    diversity = min(4.0, len(set(words)) / max(1, word_count) * 12.0)

    return (
        density + coverage + length_quality + cue_score + punctuation_score
        + diversity - fragmentation_penalty - sparse_penalty
    )


def choose_windows(segments, duration: int, count: int, total: float):
    if not segments:
        return []
    duration = max(15, min(90, int(duration)))
    count = max(1, min(10, int(count)))
    max_start = max(0.0, total - duration)

    step = max(5, min(12, duration // 5))
    starts = {0.0, float(max_start)}
    cursor = 0.0
    while cursor <= max_start:
        starts.add(round(cursor, 2))
        cursor += step
    for segment in segments:
        for offset in (0.0, -3.0, -7.0, -12.0):
            candidate = max(0.0, min(max_start, float(segment["start"]) + offset))
            starts.add(round(candidate, 2))

    candidates = [(score_window(segments, start, start + duration), start) for start in starts]
    candidates.sort(key=lambda item: item[0], reverse=True)

    picked = []
    min_gap = duration * 0.35
    for score, start in candidates:
        if score <= -50:
            continue
        separated = all(
            start + duration <= previous - min_gap
            or start >= previous + duration + min_gap
            for previous in picked
        )
        if separated:
            picked.append(start)
            if len(picked) >= count:
                break

    if not picked and candidates:
        picked = [candidates[0][1]]
    return [(start, min(total, start + duration)) for start in sorted(picked)]


def write_srt(segments, start: float, end: float, path: Path) -> None:
    lines = []
    index = 1
    for segment in segments:
        clip_start = max(start, segment["start"])
        clip_end = min(end, segment["end"])
        if clip_end <= clip_start:
            continue
        content = segment["text"].strip()
        if not content:
            continue
        lines.extend([
            str(index),
            f"{srt_time(clip_start - start)} --> {srt_time(clip_end - start)}",
            content,
            "",
        ])
        index += 1
    path.write_text("\n".join(lines), encoding="utf-8")


def ffmpeg_sub_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def process_source(source: Path, count: int, duration: int, model_name: str):
    count = max(1, min(10, int(count)))
    duration = max(15, min(90, int(duration)))
    job_id = secrets.token_hex(8)
    job_dir = OUT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "json", str(source),
            ],
            capture_output=True, text=True, check=True,
        )
        total = float(json.loads(probe.stdout)["format"]["duration"])
        if total < 5:
            raise HTTPException(400, "Das Video ist zu kurz.")
        if total > 4 * 60 * 60:
            raise HTTPException(413, "Das Video ist länger als vier Stunden. Bitte einen kürzeren Link verwenden.")

        whisper = get_whisper(model_name)
        transcribed, _info = whisper.transcribe(str(source), vad_filter=True)
        segments = [
            {"start": float(item.start), "end": float(item.end), "text": item.text.strip()}
            for item in transcribed
        ]
        windows = choose_windows(segments, duration, count, total)
        if not windows:
            raise HTTPException(
                422,
                "Es wurde keine klare Sprache erkannt. Bitte ein Video mit verständlicher Sprache testen.",
            )

        results = []
        for index, (start, end) in enumerate(windows, 1):
            clip_name = f"clip_{index:02d}.mp4"
            clip_path = job_dir / clip_name
            srt_path = job_dir / f"clip_{index:02d}.srt"
            write_srt(segments, start, end, srt_path)

            video_filter = (
                "crop='min(iw,ih*9/16)':ih,"
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920"
            )
            if srt_path.stat().st_size:
                video_filter += (
                    f",subtitles='{ffmpeg_sub_path(srt_path)}':"
                    "force_style='FontSize=42,Outline=3,Shadow=1,Alignment=2,MarginV=180'"
                )

            command = [
                "ffmpeg", "-y", "-ss", str(start), "-i", str(source),
                "-t", str(end - start), "-vf", video_filter,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                str(clip_path),
            ]
            encoded = subprocess.run(command, capture_output=True, text=True)
            if encoded.returncode != 0:
                details = (encoded.stderr or encoded.stdout or "Unbekannter FFmpeg-Fehler").strip()
                raise HTTPException(
                    500,
                    "FFmpeg konnte den Clip nicht exportieren. Technische Meldung: "
                    + details[-1800:]
                )
            results.append({
                "name": f"Highlight {index}",
                "duration": round(end - start, 1),
                "file": f"{job_id}/{clip_name}",
            })

        return {
            "job": job_id,
            "clips": results,
            "transcript_segments": len(segments),
            "processing": "local",
        }
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            500,
            "FFmpeg oder FFprobe wurde nicht gefunden. Bitte Update_ClipPilot.command ausführen "
            "und danach Start_ClipPilot.command erneut starten."
        ) from exc
    except Exception as exc:
        if "metadata_errors" in str(exc):
            raise HTTPException(
                500,
                "Die Audio-Bibliothek ist nicht kompatibel. Bitte ClipPilot mit Update_ClipPilot.command aktualisieren; "
                "dadurch wird PyAV auf eine kompatible Version unter 19 gesetzt."
            ) from exc
        raise HTTPException(500, f"Verarbeitung fehlgeschlagen: {exc}") from exc


@app.post("/api/process-link")
async def process_link(
    url: str = Form(...),
    count: int = Form(3),
    duration: int = Form(45),
    model: str = Form("base"),
    x_clippilot_token: Optional[str] = Header(None),
):
    auth(x_clippilot_token)
    youtube_url = validate_youtube_url(url)
    temporary_prefix = INBOX / secrets.token_hex(8)
    output_template = str(temporary_prefix) + ".%(ext)s"

    try:
        import yt_dlp

        options = {
            "format": "best[height<=720]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "max_filesize": 500 * 1024 * 1024,
            "socket_timeout": 30,
            "retries": 2,
            "fragment_retries": 2,
        }
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([youtube_url])

        candidates = [
            path for path in INBOX.glob(temporary_prefix.name + ".*")
            if path.is_file() and not path.name.endswith(".part")
        ]
        if not candidates:
            raise HTTPException(
                422,
                "YouTube konnte das Video nicht bereitstellen. Es kann privat, geschützt, zugangsbeschränkt oder nicht unterstützt sein.",
            )

        downloaded_video = max(
            candidates,
            key=lambda path: (path.suffix.lower() == ".mp4", path.stat().st_size),
        )
        return process_source(downloaded_video, count, duration, model)
    except HTTPException:
        raise
    except Exception as exc:
        message = str(exc)
        lower_message = message.lower()
        if "page needs to be reloaded" in lower_message or "javascript challenge" in lower_message:
            explanation = (
                "YouTube hat die aktuelle Player-/JavaScript-Prüfung abgewiesen. "
                "Bitte ClipPilot mit Update_ClipPilot.command aktualisieren und neu starten. "
                "Falls der Fehler bleibt, kann YouTube den Abruf dieses Videos oder der Verbindung vorübergehend blockieren."
            )
        elif "sign in to confirm" in lower_message or "age-restricted" in lower_message:
            explanation = (
                "YouTube verlangt eine Anmeldung oder Altersbestätigung. "
                "ClipPilot kann diese Zugangsbeschränkung nicht umgehen. Bitte einen anderen öffentlich erreichbaren Link testen."
            )
        else:
            explanation = (
                "Der YouTube-Link konnte nicht verarbeitet werden. Prüfe, ob das Video öffentlich erreichbar ist. "
                "Private, geschützte oder zugangsbeschränkte Videos werden nicht freigeschaltet."
            )
        raise HTTPException(
            422,
            f"{explanation} Technischer Hinweis: {message[:350]}",
        ) from exc
    finally:
        for item in INBOX.glob(temporary_prefix.name + ".*"):
            try:
                item.unlink(missing_ok=True)
            except OSError:
                pass


# Kept for compatibility with older local builds. The new interface only uses YouTube links.
@app.post("/api/process")
async def process_video(
    video: UploadFile = File(...),
    count: int = Form(3),
    duration: int = Form(45),
    model: str = Form("base"),
    x_clippilot_token: Optional[str] = Header(None),
):
    auth(x_clippilot_token)
    if not video.filename:
        raise HTTPException(400, "Videodatei fehlt.")
    source = INBOX / (secrets.token_hex(8) + "_" + safe_filename(video.filename))
    try:
        with source.open("wb") as target:
            while chunk := await video.read(1024 * 1024):
                target.write(chunk)
        return process_source(source, count, duration, model)
    finally:
        source.unlink(missing_ok=True)


@app.get("/api/download/{file_path:path}")
def download(file_path: str):
    target = (OUT / file_path).resolve()
    if not str(target).startswith(str(OUT.resolve()) + os.sep) or not target.is_file():
        raise HTTPException(404, "Clip nicht gefunden.")
    return FileResponse(target, filename=target.name, media_type="video/mp4")
