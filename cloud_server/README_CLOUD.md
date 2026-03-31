# Cloud Server - Size Only Offloading

Cloud menerima gambar dari edge, menunggu sebentar untuk simulasi cloud, lalu mengembalikan gambar asli.

## Install
```powershell
python -m pip install -r requirements_cloud.txt
```

## Run
```powershell
$env:CLOUD_PROCESSING_DELAY_MS="300"
python -u -m uvicorn cloud_app:app --host 0.0.0.0 --port 9000 --log-level info
```

## Endpoint cek
- `GET /health`
- `GET /`

## Penting
- Endpoint `POST /process` menerima multipart dengan field file bernama `image`
