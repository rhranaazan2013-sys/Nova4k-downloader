
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="4K Nova API")

origins = [
    x.strip()
    for x in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if x.strip() and x.strip() != "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

TEMP_DIR = Path(tempfile.gettempdir()) / "4knova"
TEMP_DIR.mkdir(exist_ok=True)

class VideoRequest(BaseModel):
    url: HttpUrl
    height: int = 1080

def validate_url(url):
    parsed = urlparse(str(url))
    host = (parsed.hostname or "").lower()

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "Only HTTP/HTTPS links are allowed.")

    allowed = [
        "youtube.com", "youtu.be", "tiktok.com", "instagram.com",
        "facebook.com", "fb.watch", "x.com", "twitter.com",
        "reddit.com", "redd.it", "pinterest.com", "pin.it",
        "vimeo.com", "dailymotion.com"
    ]

    if not any(host == d or host.endswith("." + d) for d in allowed):
        raise HTTPException(400, "This platform is not supported.")

@app.get("/")
def home():
    return {"service": "4K Nova API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze")
def analyze(req: VideoRequest):
    url = str(req.url)
    validate_url(url)

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "socket_timeout": 15,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()

        for f in info.get("formats", []):
            h = f.get("height")
            ext = f.get("ext", "")
            if h and h <= 1080 and ext in ("mp4", "webm"):
                key = (h, ext)
                if key not in seen:
                    seen.add(key)
                    formats.append({
                        "height": h,
                        "quality": f"{h}p",
                        "format": ext
                    })

        formats.sort(key=lambda x: x["height"], reverse=True)

        return {
            "title": info.get("title", "Video"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "platform": info.get("extractor_key", "Unknown"),
            "formats": formats
        }

    except Exception:
        raise HTTPException(
            502,
            "Could not analyze this video. The platform may block access."
        )

@app.post("/download")
def download(req: VideoRequest):
    url = str(req.url)
    validate_url(url)

    height = max(144, min(req.height, 1080))
    output = str(TEMP_DIR / "%(id)s.%(ext)s")

    opts = {
        "format": f"best[height<={height}][ext=mp4]/best[height<={height}]",
        "outtmpl": output,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "socket_timeout": 20,
        "max_filesize": 500 * 1024 * 1024,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = Path(ydl.prepare_filename(info))

            if not filepath.exists():
                candidates = list(TEMP_DIR.glob(f"{info['id']}.*"))
                candidates = [
                    p for p in candidates
                    if p.suffix not in (".part", ".ytdl")
                ]
                if not candidates:
                    raise HTTPException(502, "Download file was not created.")
                filepath = candidates[0]

        return FileResponse(
            filepath,
            filename=filepath.name,
            media_type="application/octet-stream",
            background=None
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            502,
            "Download failed. This platform may block the server or restrict access."
        )
        
