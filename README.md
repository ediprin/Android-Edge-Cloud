# Rancang Bangun Prototype Task Offloading pada Sistem Edge-Cloud Menggunakan Ukuran Gambar sebagai Dasar Keputusan

Prototype ini mendemonstrasikan mekanisme **task offloading** sederhana pada arsitektur **edge-cloud** dengan **ukuran gambar** sebagai dasar keputusan.

Sistem terdiri dari 3 peran utama:

- **Android Client**: antarmuka web lokal untuk memilih dan mengunggah gambar
- **Edge Node**: menerima gambar, membaca ukuran file, lalu memutuskan apakah gambar tetap ditangani di edge atau diteruskan ke cloud
- **Cloud Server**: menerima gambar dari edge jika ukuran file melewati threshold

Pada proyek ini, gambar **tidak diproses ulang** dan **tidak diubah**. File dikirim dan dikembalikan **apa adanya**. Fokus proyek ini adalah menunjukkan **mekanisme offloading**, bukan image processing.

---

## Tujuan Proyek

Tujuan dari proyek ini adalah:

- membangun prototype sistem edge-cloud sederhana
- menunjukkan alur offloading dari client ke edge lalu ke cloud
- menggunakan **ukuran gambar** sebagai parameter keputusan yang mudah diamati
- menyediakan antarmuka sederhana di Android tanpa membuat aplikasi native penuh

---

## Arsitektur Sistem

Alur sistem:

`Browser Android -> Web Server Lokal Android -> Edge -> Cloud (jika perlu) -> Edge -> Android`

Penjelasan singkat:

- User membuka UI lokal di Android
- User memilih gambar dan menekan tombol kirim
- Android mengirim gambar ke edge
- Edge membaca ukuran gambar
- Jika ukuran file **lebih kecil dari threshold**, gambar tetap di edge
- Jika ukuran file **lebih besar atau sama dengan threshold**, gambar diteruskan ke cloud
- Hasil dikembalikan ke Android

---

## Dasar Keputusan Offloading

Keputusan hanya berdasarkan **ukuran file gambar**:

- `ukuran gambar < threshold` -> **diproses di edge**
- `ukuran gambar >= threshold` -> **di-offload ke cloud**

Threshold diset di **edge** melalui environment variable:

```bash
IMAGE_SIZE_THRESHOLD_KB
```
