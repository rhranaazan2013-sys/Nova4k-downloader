
import os
import re
import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="4K Nova API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class AnalyzeRequest(BaseModel):
    url: HttpUrl

def validate_url(url: str):
    host = re.sub(r"^www\.", "", url.split("/")[2].split(":")[0].lower())
    allowed = (
        host == "youtube.com" or host.endswith(".youtube.com")
        or host == "youtu.be"
        or host == "tiktok.com" or host.endswith(".tiktok.com")
        or host == "instagram.com" or host.endswith(".instagram.com")
        or host == "facebook.com" or host.endswith(".facebook.com")
        or host == "fb.watch"
        or host == "x.com" or host.endswith(".x.com")
        or host == "twitter.com" or host.endswith(".twitter.com")
        or host == "reddit.com" or host.endswith(".reddit.com")
        or host == "redd.it"
        or host == "pinterest.com" or host.endswith(".pinterest.com")
        or host == "pin.it"
        or host == "vimeo.com" or host.endswith(".vimeo.com")
        or host == "dailymotion.com" or host.endswith(".dailymotion.com")
    )
    if not allowed:
        raise HTTPException(400, "This platform is not supported yet.")

@app.get("/")
def home():
    return {"service": "4K Nova API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    url = str(req.url)
    validate_url(url)

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "format": "best[height<=1080]/best",
        "socket_timeout": 15,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()

        for item in info.get("formats", []):
            height = item.get("height")
            if not height or height > 1080:
                continue
            if not item.get("url"):
                continue

            key = (height, item.get("ext", "unknown"))
            if key in seen:
                continue
            seen.add(key)

            formats.append({
                "height": height,
                "quality": f"{height}p",
                "format": item.get("ext", "unknown"),
                "has_audio": bool(item.get("acodec") not in (None, "none")),
            })

        formats.sort(key=lambda f: f["height"], reverse=True)

        return {
            "title": info.get("title", "Video"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "platform": info.get("extractor_key", "Unknown"),
            "formats": formats,
            "message": "Available formats detected. Download delivery must be configured separately."
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            502,
            "Could not analyze this video. The platform may block the server or require access."
)
          
