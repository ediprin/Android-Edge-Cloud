from __future__ import annotations

import os
import time
import uuid
from typing import Tuple

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.datastructures import UploadFile as StarletteUploadFile

APP_TITLE = "Edge Node - Size Only Offloading"
APP_VERSION = "clean-v1"
CLOUD_BASE_URL = os.getenv("CLOUD_BASE_URL", "http://127.0.0.1:9000").rstrip("/")
IMAGE_SIZE_THRESHOLD_KB = float(os.getenv("IMAGE_SIZE_THRESHOLD_KB", "300"))
REQUEST_TIMEOUT = float(os.getenv("EDGE_FORWARD_TIMEOUT_SECONDS", "30"))

app = FastAPI(title=APP_TITLE)


def log(msg: str) -> None:
    print(f"[EDGE] {msg}", flush=True)


def measure_cloud_rtt_ms(timeout: float = 1.5) -> float:
    try:
        start = time.perf_counter()
        response = requests.get(f"{CLOUD_BASE_URL}/health", timeout=timeout)
        response.raise_for_status()
        return (time.perf_counter() - start) * 1000.0
    except Exception:
        return 1000.0


def parse_form_payload(form) -> Tuple[StarletteUploadFile, str, str]:
    image = form.get("image")
    client_name = str(form.get("client_name", "unknown-client"))
    mode = str(form.get("mode", "auto")).strip().lower() or "auto"

    if image is None or not isinstance(image, StarletteUploadFile):
        raise HTTPException(
            status_code=400,
            detail="Field multipart 'image' wajib ada dan harus berupa file upload.",
        )

    if mode not in {"auto", "edge", "cloud"}:
        raise HTTPException(status_code=400, detail="Field 'mode' harus auto, edge, atau cloud.")

    return image, client_name, mode


def forward_to_cloud(image_bytes: bytes, filename: str, mime_type: str, request_id: str):
    files = {"image": (filename, image_bytes, mime_type)}
    headers = {"X-Request-ID": request_id, "X-Forwarded-From": "edge"}
    response = requests.post(
        f"{CLOUD_BASE_URL}/process",
        files=files,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.content, response.headers, response.headers.get("Content-Type", mime_type)


@app.on_event("startup")
def startup_banner():
    log("=" * 60)
    log(f"{APP_TITLE} {APP_VERSION}")
    log(f"CLOUD_BASE_URL={CLOUD_BASE_URL}")
    log(f"IMAGE_SIZE_THRESHOLD_KB={IMAGE_SIZE_THRESHOLD_KB}")
    log("=" * 60)


@app.get("/")
def root():
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "role": "edge",
        "cloud_base_url": CLOUD_BASE_URL,
        "image_size_threshold_kb": IMAGE_SIZE_THRESHOLD_KB,
    }


@app.get("/health")
def health():
    return {"status": "ok", "role": "edge", "version": APP_VERSION}


@app.get("/ping-cloud")
def ping_cloud():
    return {"cloud_rtt_ms": measure_cloud_rtt_ms(), "cloud_base_url": CLOUD_BASE_URL}


@app.post("/process")
async def process(request: Request):
    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()

    form = await request.form()
    image, client_name, mode = parse_form_payload(form)
    image_bytes = await image.read()
    filename = image.filename or "uploaded_file"
    mime_type = image.content_type or "application/octet-stream"
    image_size_kb = len(image_bytes) / 1024.0
    cloud_rtt_ms = measure_cloud_rtt_ms()

    log(f"request_id={request_id} client={client_name} terima request")
    log(f"request_id={request_id} file={filename} mime={mime_type} size_kb={image_size_kb:.2f} mode={mode}")

    if mode == "edge":
        decision_target = "edge"
        reasons = ["mode dipaksa ke edge"]
    elif mode == "cloud":
        if cloud_rtt_ms >= 1000:
            raise HTTPException(status_code=502, detail="Mode cloud dipilih, tetapi cloud tidak dapat dijangkau.")
        decision_target = "cloud"
        reasons = ["mode dipaksa ke cloud"]
    
    # algoritma keputusan task offloading
    else:
        if image_size_kb >= IMAGE_SIZE_THRESHOLD_KB:
            if cloud_rtt_ms >= 1000:
                decision_target = "edge"
                reasons = [
                    f"gambar besar ({image_size_kb:.2f} KB), tetapi cloud tidak dapat dijangkau"
                ]
            else:
                decision_target = "cloud"
                reasons = [
                    f"gambar besar ({image_size_kb:.2f} KB) >= threshold {IMAGE_SIZE_THRESHOLD_KB:.2f} KB"
                ]
        else:
            decision_target = "edge"
            reasons = [
                f"gambar kecil ({image_size_kb:.2f} KB) < threshold {IMAGE_SIZE_THRESHOLD_KB:.2f} KB"
            ]

    log(f"request_id={request_id} keputusan={decision_target} alasan={' | '.join(reasons)}")

    if decision_target == "edge":
        log(f"request_id={request_id} DIPROSES DI EDGE (gambar dikembalikan apa adanya)")
        output_bytes = image_bytes
        processed_by = "edge"
        cloud_used = "no"
        cloud_total_ms = "-"
        response_mime = mime_type
    else:
        log(f"request_id={request_id} FORWARD KE CLOUD")
        try:
            output_bytes, cloud_headers, response_mime = forward_to_cloud(
                image_bytes=image_bytes,
                filename=filename,
                mime_type=mime_type,
                request_id=request_id,
            )
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Gagal meneruskan ke cloud: {exc}") from exc
        processed_by = cloud_headers.get("X-Processed-By", "cloud")
        cloud_used = "yes"
        cloud_total_ms = cloud_headers.get("X-Cloud-Total-Time-MS", "-")

    total_ms = (time.perf_counter() - start) * 1000.0
    log(f"request_id={request_id} selesai total={total_ms:.2f} ms processed_by={processed_by}")

    headers = {
        "X-Request-ID": request_id,
        "X-Decision-Target": decision_target,
        "X-Processed-By": processed_by,
        "X-Routed-Via": "edge",
        "X-Cloud-Used": cloud_used,
        "X-Image-Size-KB": f"{image_size_kb:.2f}",
        "X-Threshold-KB": f"{IMAGE_SIZE_THRESHOLD_KB:.2f}",
        "X-Reasons": " | ".join(reasons),
        "X-Total-Time-MS": f"{total_ms:.2f}",
        "X-Cloud-Total-Time-MS": str(cloud_total_ms),
    }
    return Response(content=output_bytes, media_type=response_mime, headers=headers)


@app.post("/debug-form")
async def debug_form(request: Request):
    form = await request.form()
    keys = list(form.keys())
    return JSONResponse({"keys": keys})
