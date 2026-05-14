# AntiTrust Secure Glass v5

Versi perbaikan AntiTrust dengan tampilan glass/iPhone-style, room sementara, invite link, enkripsi Fernet, validasi file lebih ketat, leave room, destroy room + revoke key, dan auto-revoke otomatis saat waktu room habis.

## Fitur utama

- **Siapa pun bisa create room** dari halaman awal tanpa harus login admin.
- **Masa aktif room maksimal 60 menit**. Slider dibatasi 1-60 menit.
- **Room auto revoke saat waktu habis**: pesan, packet/file, status online, pengaturan room, dan semua invite link room otomatis dihancurkan/direvoke.
- **Countdown live** untuk sisa waktu room dan invite link.
- **Semua user di room bisa create invite link** untuk mengajak orang lain.
- **Invite link tidak bisa lebih lama dari sisa waktu room** dan tetap maksimal 60 menit.
- **Tinggalkan room sekarang**: user keluar dari daftar online room aktif.
- **Hancurkan room + revoke key**: user bisa menghancurkan room manual dan mencabut semua invite link.
- **Panic destroy** untuk menghapus pesan/packet room aktif.

## Jalankan lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secrets yang disarankan

Buat file `.streamlit/secrets.toml` saat deploy di Streamlit Cloud:

```toml
CHAT_ADMIN_PASSWORD = "ganti-dengan-password-kuat"
FERNET_KEY = "isi-dengan-key-fernet"
PUBLIC_APP_URL = "https://nama-app.streamlit.app"
```

Generate Fernet key:

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

## Catatan keamanan

- Jangan commit `fernet.key`, `.antitrust_data/`, `.env`, atau secrets ke GitHub.
- Room dan invite link sekarang hanya berlaku maksimal 60 menit.
- Saat room expired, semua invite link untuk room tersebut ditandai revoked.
- File upload dibatasi ukuran dan diverifikasi berdasarkan magic bytes/struktur file.
- Room dan packet disimpan memakai key hash, bukan nama room mentah.
