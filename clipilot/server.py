#!/usr/bin/env python3
"""ClipPilot Local: local-only video clipping service for user-selected files."""
from __future__ import annotations
import os, secrets, subprocess, tempfile, json, re
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel

ROOT = Path.home() / ".clippilot"
INBOX = ROOT / "inbox"
OUT = ROOT / "clips"
TOKEN_FILE = ROOT / "token.txt"
ROOT.mkdir(exist_ok=True); INBOX.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
TOKEN = os.environ.get("CLIPPILOT_TOKEN")
if not TOKEN:
    if TOKEN_FILE.exists(): TOKEN = TOKEN_FILE.read_text().strip()
    else:
        TOKEN = secrets.token_urlsafe(24); TOKEN_FILE.write_text(TOKEN)
print(f"ClipPilot access token (enter in website): {TOKEN}")

app = FastAPI(title="ClipPilot Local")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def auth(token: Optional[str]):
    if not token or not secrets.compare_digest(token, TOKEN):
        raise HTTPException(401, "Token fehlt oder ist falsch. Token im Terminal ablesen.")

@app.get("/api/health")
def health(): return {"ok": True, "service": "ClipPilot Local", "version": "0.1"}

def safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "video")
    return name[:100] or "video"

def srt_time(seconds: float) -> str:
    ms = max(0, int(seconds * 1000)); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def score_window(segments, start, end):
    text = " ".join(x["text"] for x in segments if x["start"] < end and x["end"] > start).lower()
    count = sum(1 for x in segments if x["start"] < end and x["end"] > start)
    excitement = sum(text.count(w) for w in ["wow","wtf","oh my","nein","no way","krass","unglaublich","warte","bro","holy","actually","finally","suddenly","but","why","what","geil","verdammt","!","?"])
    density = min(20, count * 0.7)
    return density + excitement * 2.0 + min(len(text)/90, 8)

def choose_windows(segments, duration, count, total):
    if not segments: return []
    maxstart=max(0,total-duration)
    step=max(8,duration//3)
    candidates=[]
    start=0
    while start<=maxstart:
        candidates.append((score_window(segments,start,start+duration),start))
        start+=step
    if not candidates: candidates=[(score_window(segments,0,duration),0)]
    candidates.sort(reverse=True)
    picked=[]
    for score,start in candidates:
        if all(start+duration <= p or start >= p+duration for p in picked):
            picked.append(start)
            if len(picked)>=count: break
    if not picked:
        picked=[0]
    return [(s,min(total,s+duration)) for s in sorted(picked)]

def write_srt(segments, start, end, path):
    lines=[]; idx=1
    for seg in segments:
        a=max(start,seg["start"]); b=min(end,seg["end"])
        if b<=a: continue
        txt=seg["text"].strip()
        if not txt: continue
        lines += [str(idx),f"{srt_time(a-start)} --> {srt_time(b-start)}",txt,""]
        idx+=1
    Path(path).write_text("\n".join(lines), encoding="utf-8")

def ffmpeg_sub_path(path):
    return str(path).replace("\\","\\\\").replace(":","\\:").replace("'","\\'")

@app.post("/api/process")
async def process_video(video: UploadFile=File(...), count: int=Form(3), duration: int=Form(45), model: str=Form("base"), x_clippilot_token: Optional[str]=Header(None)):
    auth(x_clippilot_token)
    if not video.filename: raise HTTPException(400,"Videodatei fehlt.")
    count=max(1,min(10,count)); duration=max(15,min(90,duration))
    model = model if model in ("tiny","base","small") else "base"
    job=secrets.token_hex(5); jobdir=OUT/job; jobdir.mkdir(parents=True,exist_ok=True)
    src=INBOX/(job+"_"+safe_filename(video.filename))
    try:
        with src.open("wb") as f:
            while chunk:=await video.read(1024*1024): f.write(chunk)
        probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(src)],capture_output=True,text=True,check=True)
        total=float(json.loads(probe.stdout)["format"]["duration"])
        if total<5: raise HTTPException(400,"Video ist zu kurz.")
        wm=WhisperModel(model,device="cpu",compute_type="int8")
        transcribed,_=wm.transcribe(str(src),vad_filter=True)
        segments=[{"start":float(s.start),"end":float(s.end),"text":s.text.strip()} for s in transcribed]
        windows=choose_windows(segments,duration,count,total)
        if not windows: raise HTTPException(422,"Keine Sprache erkannt. Bitte ein Video mit klarer Sprache testen.")
        results=[]
        for i,(start,end) in enumerate(windows,1):
            clipname=f"clip_{i:02d}.mp4"; clip=jobdir/clipname; srt=jobdir/f"clip_{i:02d}.srt"
            write_srt(segments,start,end,srt)
            vf="crop='min(iw,ih*9/16)':ih,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
            if srt.stat().st_size:
                vf+=f",subtitles='{ffmpeg_sub_path(srt)}':force_style='FontSize=18,Outline=2,Shadow=1,Alignment=2,MarginV=140'"
            command=["ffmpeg","-y","-ss",str(start),"-i",str(src),"-t",str(end-start),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","24","-c:a","aac","-b:a","128k","-movflags","+faststart",str(clip)]
            subprocess.run(command,check=True,capture_output=True)
            results.append({"name":f"Highlight {i}","duration":round(end-start,1),"file":job+"/"+clipname})
        src.unlink(missing_ok=True)
        return {"job":job,"clips":results,"transcript_segments":len(segments),"processing":"local"}
    except HTTPException:
        src.unlink(missing_ok=True); raise
    except Exception as exc:
        src.unlink(missing_ok=True)
        raise HTTPException(500,f"Lokale Verarbeitung fehlgeschlagen: {exc}")

@app.get("/api/download/{file_path:path}")
def download(file_path: str):
    # Restrict downloads to generated files in output directory.
    p=(OUT/file_path).resolve()
    if not str(p).startswith(str(OUT.resolve())) or not p.is_file(): raise HTTPException(404,"Clip nicht gefunden.")
    return FileResponse(p,filename=p.name,media_type="video/mp4")
