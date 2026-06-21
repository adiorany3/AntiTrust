# AntiTrust - Password-Derived Fernet Room Key + Google Meet

AntiTrust adalah private temporary chat berbasis Streamlit. Room bersifat sementara, invite link dapat dibagikan, pesan terenkripsi, dan room dapat otomatis direvoke sesuai durasi.

## Perubahan terbaru dalam paket ini

- Menambahkan tab **Video Call** di **Panel room**.
- Koneksi video call dapat menggunakan **Google Meet**.
- Pembuat room dapat menyimpan link Google Meet, misalnya `https://meet.google.com/abc-defg-hij`.
- Peserta dapat langsung membuka tombol **Join Google Meet** dari room.
- Catatan sesi default: **Sesi video call mengikuti waktu chat/room aktif. Gunakan countdown room sebagai patokan.**
- Pembuat room dapat mengirim info Google Meet ke chat dengan format yang lebih rapi.
- Link Google Meet disimpan terenkripsi di `room_settings.json` menggunakan Fernet global.
- Room lama tetap kompatibel karena field baru bersifat opsional.

## Fitur keamanan utama

- Metadata invite/room tetap memakai Fernet global supaya kompatibel dengan link lama.
- Isi pesan teks, secret note, poll, checklist, location, thumbnail, dan packet file memakai key Fernet per-room.
- Key per-room diturunkan memakai PBKDF2-HMAC-SHA256 dengan 390.000 iterasi, salt acak per room, room key sebagai context, dan server-side pepper dari `FERNET_KEY` + `CHAT_ADMIN_PASSWORD`.
- Password asli tidak disimpan. Yang disimpan hanya `creator_password_hash` dan `room_fernet_salt`.
- Room lama tanpa `room_fernet_salt` tetap bisa dibuka memakai enkripsi global lama.

## Cara menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secrets yang disarankan

Simpan di Streamlit Secrets atau environment variable, jangan commit ke GitHub.

```toml
CHAT_ADMIN_PASSWORD = "password-kuat"
FERNET_KEY = "fernet-key-yang-digenerate"
PUBLIC_APP_URL = "https://nama-app.streamlit.app"
```

Generate Fernet key:

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

## Catatan pemakaian Google Meet

Setelah room dibuat dan dibuka, masuk ke **Panel room → Video Call**. Masukkan link Google Meet, lalu simpan. Peserta yang masuk room akan melihat tombol join selama room masih aktif.

Kalimat rekomendasi untuk peserta:

> Untuk koneksi video call bisa menggunakan Google Meet. Sesi akan mengikuti waktu chat/room aktif, jadi gunakan countdown room sebagai patokan. Mohon join melalui link Google Meet yang tersedia di panel room.
