# Edge Node - Size Only Offloading

Keputusan offloading hanya berdasarkan ukuran file gambar.

## Install
```powershell
python -m pip install -r requirements_edge.txt
```

## Run
```powershell
$env:CLOUD_BASE_URL="http://127.0.0.1:9000"
$env:IMAGE_SIZE_THRESHOLD_KB="300"
python -u -m uvicorn edge_app:app --host 0.0.0.0 --port 8000 --log-level info
```

## Endpoint cek
- `GET /health`
- `GET /`
- `GET /ping-cloud`
- `POST /debug-form`

## Penting
- Endpoint menerima multipart dengan field file bernama `image`
- Field teks yang dipakai: `client_name`, `mode`
- `mode` boleh `auto`, `edge`, `cloud`
