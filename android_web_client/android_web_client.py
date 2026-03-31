from __future__ import annotations

import base64
import os
import time

import requests
from flask import Flask, request, render_template_string

APP_NAME = "Android Web Client - Size Only"
APP_VERSION = "clean-v1"
DEFAULT_EDGE_URL = os.getenv("DEFAULT_EDGE_URL", "http://192.168.1.10:8000")
REQUEST_TIMEOUT = int(os.getenv("EDGE_TIMEOUT_SECONDS", "60"))
BIND_HOST = os.getenv("ANDROID_WEB_BIND_HOST", "127.0.0.1")
BIND_PORT = int(os.getenv("ANDROID_WEB_BIND_PORT", "5000"))

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ app_name }}</title>
  <style>
    body { font-family: Arial, sans-serif; background:#f5f5f5; margin:0; padding:16px; color:#222; }
    .card { background:#fff; border-radius:12px; padding:16px; margin-bottom:16px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }
    h1,h2 { margin-top:0; }
    label { display:block; margin-top:12px; margin-bottom:6px; font-weight:700; }
    input[type=text], select, input[type=file] { width:100%; padding:10px; border:1px solid #ccc; border-radius:8px; box-sizing:border-box; background:#fff; }
    button { width:100%; margin-top:16px; padding:12px; border:none; border-radius:8px; background:#2563eb; color:#fff; font-weight:700; font-size:16px; }
    table { width:100%; border-collapse:collapse; }
    td { padding:8px; border-bottom:1px solid #eee; vertical-align:top; }
    .key { width:42%; font-weight:700; }
    .ok { color:#0a7a2f; font-weight:700; }
    .err { color:#b91c1c; font-weight:700; white-space:pre-wrap; }
    .muted { color:#666; font-size:14px; }
    .mono { font-family:monospace; word-break:break-word; }
    img { max-width:100%; border:1px solid #ddd; border-radius:10px; margin-top:8px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>{{ app_name }}</h1>
    <div class="muted">Versi {{ app_version }} • Browser Android → Flask lokal → Edge → Cloud bila ukuran gambar melewati threshold.</div>
  </div>

  <div class="card">
    <h2>Upload Gambar Asli</h2>
    <form method="post" action="/submit" enctype="multipart/form-data">
      <label>Edge URL</label>
      <input type="text" name="edge_url" value="{{ form_data.edge_url }}" required>

      <label>Nama Client</label>
      <input type="text" name="client_name" value="{{ form_data.client_name }}" required>

      <label>Mode</label>
      <select name="mode">
        <option value="auto" {% if form_data.mode == 'auto' %}selected{% endif %}>auto</option>
        <option value="edge" {% if form_data.mode == 'edge' %}selected{% endif %}>edge</option>
        <option value="cloud" {% if form_data.mode == 'cloud' %}selected{% endif %}>cloud</option>
      </select>

      <label>Pilih Gambar</label>
      <input type="file" name="image" accept="image/*" required>

      <button type="submit">Kirim Gambar Asli</button>
    </form>
  </div>

  {% if message %}
  <div class="card">
    <h2>Status</h2>
    <div class="{{ message_class }}">{{ message }}</div>
  </div>
  {% endif %}

  {% if result %}
  <div class="card">
    <h2>Informasi Offloading</h2>
    <table>
      <tr><td class="key">Request ID</td><td class="mono">{{ result.request_id }}</td></tr>
      <tr><td class="key">Mode diminta</td><td>{{ result.requested_mode }}</td></tr>
      <tr><td class="key">Keputusan edge</td><td><b>{{ result.decision_target }}</b></td></tr>
      <tr><td class="key">Diproses oleh</td><td><b>{{ result.processed_by }}</b></td></tr>
      <tr><td class="key">Dirutekan via</td><td>{{ result.routed_via }}</td></tr>
      <tr><td class="key">Pakai cloud?</td><td>{{ result.cloud_used }}</td></tr>
      <tr><td class="key">Ukuran gambar</td><td>{{ result.image_size_kb }}</td></tr>
      <tr><td class="key">Threshold</td><td>{{ result.threshold_kb }}</td></tr>
      <tr><td class="key">Alasan</td><td>{{ result.reasons }}</td></tr>
      <tr><td class="key">Waktu client</td><td>{{ result.client_elapsed_ms }}</td></tr>
      <tr><td class="key">Waktu edge total</td><td>{{ result.edge_total_ms }}</td></tr>
      <tr><td class="key">Waktu cloud</td><td>{{ result.cloud_total_ms }}</td></tr>
      <tr><td class="key">HTTP status</td><td>{{ result.http_status }}</td></tr>
      <tr><td class="key">Content-Type balasan</td><td>{{ result.mime_type }}</td></tr>
      <tr><td class="key">Edge URL</td><td class="mono">{{ result.edge_url }}</td></tr>
    </table>
  </div>

  <div class="card">
    <h2>Preview Gambar Balasan</h2>
    <img src="data:{{ result.mime_type }};base64,{{ result.output_image_b64 }}" alt="Gambar hasil">
  </div>
  {% endif %}
</body>
</html>
"""


def header_value(headers, key: str, default: str = "-") -> str:
    value = headers.get(key)
    return value if value not in (None, "") else default


def default_form_data() -> dict:
    return {"edge_url": DEFAULT_EDGE_URL, "client_name": "phone-1", "mode": "auto"}


@app.get("/")
def index():
    return render_template_string(
        HTML,
        app_name=APP_NAME,
        app_version=APP_VERSION,
        form_data=default_form_data(),
        message=None,
        message_class="ok",
        result=None,
    )


@app.get("/health")
def health():
    return {"status": "ok", "role": "android-web-client", "version": APP_VERSION}


@app.post("/submit")
def submit():
    edge_url = request.form.get("edge_url", DEFAULT_EDGE_URL).strip().rstrip("/")
    client_name = request.form.get("client_name", "phone-1").strip() or "phone-1"
    mode = request.form.get("mode", "auto").strip() or "auto"
    uploaded = request.files.get("image")

    form_data = {"edge_url": edge_url, "client_name": client_name, "mode": mode}

    if uploaded is None or uploaded.filename == "":
        return render_template_string(
            HTML,
            app_name=APP_NAME,
            app_version=APP_VERSION,
            form_data=form_data,
            message="Gambar belum dipilih.",
            message_class="err",
            result=None,
        )

    filename = uploaded.filename
    mime_type = uploaded.mimetype or "application/octet-stream"
    image_bytes = uploaded.read()

    files = {"image": (filename, image_bytes, mime_type)}
    data = {"client_name": client_name, "mode": mode}

    start = time.perf_counter()
    try:
        response = requests.post(f"{edge_url}/process", files=files, data=data, timeout=REQUEST_TIMEOUT)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        text_body = response.text if "text" in response.headers.get("Content-Type", "") else ""

        if response.status_code != 200:
            msg = f"Edge error HTTP {response.status_code}:\n{text_body or response.content[:300]!r}"
            print(f"[ANDROID-WEB] ERROR {msg}")
            return render_template_string(
                HTML,
                app_name=APP_NAME,
                app_version=APP_VERSION,
                form_data=form_data,
                message=msg,
                message_class="err",
                result=None,
            )

        output_b64 = base64.b64encode(response.content).decode("utf-8")
        result = {
            "request_id": header_value(response.headers, "X-Request-ID"),
            "requested_mode": mode,
            "decision_target": header_value(response.headers, "X-Decision-Target"),
            "processed_by": header_value(response.headers, "X-Processed-By"),
            "routed_via": header_value(response.headers, "X-Routed-Via"),
            "cloud_used": header_value(response.headers, "X-Cloud-Used"),
            "image_size_kb": f"{header_value(response.headers, 'X-Image-Size-KB')} KB",
            "threshold_kb": f"{header_value(response.headers, 'X-Threshold-KB')} KB",
            "reasons": header_value(response.headers, "X-Reasons"),
            "client_elapsed_ms": f"{elapsed_ms:.2f} ms",
            "edge_total_ms": f"{header_value(response.headers, 'X-Total-Time-MS')} ms",
            "cloud_total_ms": f"{header_value(response.headers, 'X-Cloud-Total-Time-MS')} ms",
            "http_status": str(response.status_code),
            "edge_url": edge_url,
            "mime_type": response.headers.get("Content-Type", mime_type),
            "output_image_b64": output_b64,
        }

        print(
            f"[ANDROID-WEB] request_id={result['request_id']} "
            f"decision={result['decision_target']} processed_by={result['processed_by']}"
        )

        return render_template_string(
            HTML,
            app_name=APP_NAME,
            app_version=APP_VERSION,
            form_data=form_data,
            message="Task berhasil diproses.",
            message_class="ok",
            result=result,
        )
    except requests.exceptions.RequestException as exc:
        msg = f"Gagal menghubungi edge: {exc}"
        print(f"[ANDROID-WEB] ERROR {msg}")
        return render_template_string(
            HTML,
            app_name=APP_NAME,
            app_version=APP_VERSION,
            form_data=form_data,
            message=msg,
            message_class="err",
            result=None,
        )


if __name__ == "__main__":
    print("=" * 60)
    print(f"[ANDROID-WEB] {APP_NAME} {APP_VERSION}")
    print(f"[ANDROID-WEB] buka browser di http://{BIND_HOST}:{BIND_PORT}")
    print("=" * 60)
    app.run(host=BIND_HOST, port=BIND_PORT, debug=False)
