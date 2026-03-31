from __future__ import annotations

import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from starlette.datastructures import UploadFile as StarletteUploadFile

APP_TITLE = "Cloud Server - Size Only Offloading"
APP_VERSION = "clean-v1"
CLOUD_PROCESSING_DELAY_MS = int(os.getenv("CLOUD_PROCESSING_DELAY_MS", "300"))

app = FastAPI(title=APP_TITLE)


def log(msg: str) -> None:
    print(f"[CLOUD] {msg}", flush=True)


@app.on_event("startup")
def startup_banner():
    log("=" * 60)
    log(f"{APP_TITLE} {APP_VERSION}")
    log(f"CLOUD_PROCESSING_DELAY_MS={CLOUD_PROCESSING_DELAY_MS}")
    log("=" * 60)


@app.get("/")
def root():
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "role": "cloud",
        "cloud_processing_delay_ms": CLOUD_PROCESSING_DELAY_MS,
    }


@app.get("/health")
def health():
    return {"status": "ok", "role": "cloud", "version": APP_VERSION}


@app.post("/process")
async def process(request: Request):
    form = await request.form()
    image = form.get("image")
    if image is None or not isinstance(image, StarletteUploadFile):
        raise HTTPException(status_code=400, detail="Field multipart 'image' wajib ada dan harus berupa file upload.")

    request_id = request.headers.get("X-Request-ID", "-")
    source = request.headers.get("X-Forwarded-From", "unknown")
    image_bytes = await image.read()
    mime_type = image.content_type or "application/octet-stream"
    filename = image.filename or "uploaded_file"

    log(f"request_id={request_id} terima task dari {source}")
    log(f"request_id={request_id} file={filename} mime={mime_type} size_kb={len(image_bytes)/1024:.2f}")

    start = time.perf_counter()
    time.sleep(CLOUD_PROCESSING_DELAY_MS / 1000.0)
    total_ms = (time.perf_counter() - start) * 1000.0

    log(f"request_id={request_id} SELESAI DI CLOUD dalam {total_ms:.2f} ms")

    headers = {
        "X-Request-ID": request_id,
        "X-Processed-By": "cloud",
        "X-Routed-Via": "edge",
        "X-Cloud-Total-Time-MS": f"{total_ms:.2f}",
    }
    return Response(content=image_bytes, media_type=mime_type, headers=headers)
