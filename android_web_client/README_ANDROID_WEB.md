# Android Web Client - Size Only

Paket ini dijalankan di Android melalui Pydroid.

## Install
```bash
pip install -r requirements_android.txt
```

## Run
```bash
python android_web_client.py
```

Buka browser Android ke:
```text
http://127.0.0.1:5000
```

## Isi form
- Edge URL: `http://IP_LAPTOP_EDGE:8000`
- Nama Client: bebas
- Mode: `auto`, `edge`, atau `cloud`
- Pilih gambar asli

## Catatan penting
- Jangan isi Edge URL dengan `/process`. Cukup base URL, misalnya `http://192.168.1.10:8000`
- Paket ini hanya mengirim gambar asli apa adanya
- Tidak ada grayscale, blur, atau kompresi di server
