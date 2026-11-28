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
def resolve_homebrew_ffmpeg_tool(tool: str) -> Optional[str]:
    """Prefer Homebrew's keg-only ffmpeg-full; fall back to PATH."""
    brew = shutil.which("brew") or "/opt/homebrew/bin/brew"
    try:
        prefix = subprocess.run(
            [brew, "--prefix", "ffmpeg-full"],
            capture_output=True, text=True, timeout=10, check=True
        ).stdout.strip()
        candidate = Path(prefix) / "bin" / tool
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    except Exception:
        pass
    return shutil.which(tool)


FFMPEG_BIN = resolve_homebrew_ffmpeg_tool("ffmpeg")
FFPROBE_BIN = resolve_homebrew_ffmpeg_tool("ffprobe")

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
    ffmpeg_bin = FFMPEG_BIN
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
    """Rank a window and give extra weight to an engaging first few seconds."""
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
            "krass", "geisteskrank", "niemals", "ernsthaft", "unfassbar",
        ],
        "emotion": [
            "ich liebe", "ich hasse", "verdammt", "geil", "crazy",
            "wild", "brutal", "absurd", "unglaublich",
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

    # A short-form clip should open with a compelling line, not warm-up or silence.
    hook_end = min(end, start + 5.0)
    opening_segments = [
        s for s in selected if s["start"] < hook_end and s["end"] > start
    ]
    opening_text = " ".join(s["text"] for s in opening_segments).lower()
    opening_words = re.findall(r"\b[\w']+\b", opening_text)
    hook_phrases = [
        "wait", "look at this", "watch this", "no way", "oh my god",
        "you won't believe", "you will not believe", "here's why",
        "wusstest du", "du glaubst nicht", "schau dir", "warte bis",
        "das ist", "warum", "wie kann", "unglaublich", "niemals",
        "krass", "was passiert",
    ]
    hook_score = min(10.0, sum(opening_text.count(p) for p in hook_phrases) * 2.5)
    if len(opening_words) >= 8:
        hook_score += 3.0
    elif len(opening_words) <= 2:
        hook_score -= 3.0
    if "?" in opening_text or "!" in opening_text:
        hook_score += 2.0
    if opening_segments:
        opening_delay = max(0.0, opening_segments[0]["start"] - start)
        hook_score -= min(5.0, opening_delay * 2.5)

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
        + diversity + hook_score - fragmentation_penalty - sparse_penalty
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

    # Place candidates just before transcript sentence/phrase starts so the clip
    # does not begin in the middle of a spoken word.
    for segment in segments:
        for offset in (-0.4, 0.0, -2.0, -5.0, -9.0):
            candidate = max(0.0, min(max_start, float(segment["start"]) + offset))
            starts.add(round(candidate, 2))

    candidates = [(score_window(segments, start, start + duration), start) for start in starts]
    candidates.sort(key=lambda item: item[0], reverse=True)

    # Keep the strongest moments apart, but preserve their ranking in the output:
    # clip_01 is the best-rated candidate and therefore the strongest opening clip.
    picked = []
    min_gap = duration * 0.35
    for score, start in candidates:
        if score <= -50:
            continue
        separated = all(
            start + duration <= previous_start - min_gap
            or start >= previous_start + duration + min_gap
            for _previous_score, previous_start in picked
        )
        if separated:
            picked.append((score, start))
            if len(picked) >= count:
                break

    if not picked and candidates:
        picked = [candidates[0]]
    return [
        (start, min(total, start + duration))
        for _score, start in picked
    ]


def write_srt(segments, start: float, end: float, path: Path) -> None:
    """Write short, single-line captions from Whisper word-level timestamps."""
    words = []
    for segment in segments:
        for word in segment.get("words", []):
            token = str(word.get("word", "")).strip()
            if token:
                words.append({
                    "start": float(word["start"]),
                    "end": float(word["end"]),
                    "text": token,
                })

    # Compatibility fallback if a model/runtime did not return word timestamps.
    if not words:
        for segment in segments:
            raw_tokens = segment["text"].split()
            if not raw_tokens:
                continue
            seg_start = float(segment["start"])
            seg_end = float(segment["end"])
            span = max(0.05, seg_end - seg_start)
            for i, token in enumerate(raw_tokens):
                words.append({
                    "start": seg_start + span * i / len(raw_tokens),
                    "end": seg_start + span * (i + 1) / len(raw_tokens),
                    "text": token,
                })

    visible = []
    for word in words:
        a = max(start, word["start"])
        b = min(end, word["end"])
        if b <= a:
            continue
        visible.append({"start": a, "end": b, "text": word["text"]})

    lines = []
    index = 1
    current = []
    current_start = None
    current_end = None
    current_chars = 0
    max_chars = 30
    max_caption_seconds = 2.2

    def flush_caption():
        nonlocal index, current, current_start, current_end, current_chars
        if not current or current_start is None or current_end is None:
            return
        caption = " ".join(item["text"] for item in current).strip()
        if caption:
            lines.extend([
                str(index),
                f"{srt_time(max(0.0, current_start - start))} --> {srt_time(max(0.05, current_end - start))}",
                caption,
                "",
            ])
            index += 1
        current = []
        current_start = None
        current_end = None
        current_chars = 0

    for item in visible:
        token = item["text"]
        proposed_chars = current_chars + (1 if current else 0) + len(token)
        proposed_duration = item["end"] - (current_start if current_start is not None else item["start"])
        previous_ends_sentence = bool(current and re.search(r"[.!?][\"')\]]*$", current[-1]["text"]))

        if current and (
            proposed_chars > max_chars
            or proposed_duration > max_caption_seconds
            or previous_ends_sentence
        ):
            flush_caption()

        if not current:
            current_start = item["start"]
        current.append(item)
        current_end = item["end"]
        current_chars += (1 if current_chars else 0) + len(token)

    flush_caption()
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
                FFPROBE_BIN or "ffprobe", "-v", "error", "-show_entries", "format=duration",
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
        transcribed, _info = whisper.transcribe(
            str(source), vad_filter=True, word_timestamps=True
        )
        segments = []
        for item in transcribed:
            item_words = []
            for word in (getattr(item, "words", None) or []):
                if word.start is None or word.end is None:
                    continue
                item_words.append({
                    "start": float(word.start),
                    "end": float(word.end),
                    "word": word.word,
                })
            segments.append({
                "start": float(item.start),
                "end": float(item.end),
                "text": item.text.strip(),
                "words": item_words,
            })
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
                    "force_style='FontName=Arial,FontSize=30,Bold=1,"
                    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,"
                    "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,"
                    "MarginL=90,MarginR=90,MarginV=300,WrapStyle=2'"
                )

            command = [
                FFMPEG_BIN or "ffmpeg", "-y", "-ss", str(start), "-i", str(source),
                "-t", str(end - start), "-vf", video_filter,
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
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
            "socket_timeout": 60,
            # Googlevideo delivery hosts can have temporary DNS/network failures.
            # Retry more generously and prefer IPv4 on networks with unreliable IPv6 routing.
            "retries": 10,
            "fragment_retries": 10,
            "extractor_retries": 5,
            "force_ipv4": True,
            "sleep_interval_requests": 1,
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
        elif "failed to resolve" in lower_message or "name or service not known" in lower_message or "nodename nor servname" in lower_message:
            explanation = (
                "Dein Mac konnte den YouTube-Videoserver (googlevideo.com) gerade nicht per DNS finden. "
                "ClipPilot versucht Downloads jetzt öfter und bevorzugt IPv4. "
                "Wenn der Fehler bleibt: WLAN kurz trennen und verbinden, VPN/Proxy testweise ausschalten "
                "und denselben Link danach erneut versuchen."
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
