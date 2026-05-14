# AntiTrust — Compact Glass Edition

Private temporary chat berbasis Streamlit dengan tampilan ringkas, glass-style, invite link, enkripsi Fernet, dan auto-revoke room maksimal 60 menit.

## Fitur utama

- Semua orang bisa membuat room sementara.
- Durasi room maksimal 60 menit.
- Room otomatis dihancurkan saat waktu habis.
- Invite link ikut direvoke saat room habis atau dihancurkan.
- Invite link bisa dibagikan langsung via WhatsApp.
- Nama pengguna terkunci setelah pertama kali ditetapkan.
- Jika user memakai nama `adioranye` atau `Galuh Adi Insani`, sistem menampilkan form login admin terlebih dahulu. Chat baru terbuka setelah login berhasil.
- Tombol keluar room dihapus agar identitas tidak bisa direset.
- Destroy room memakai countdown 3 detik dan bisa dibatalkan.
- Nama khusus admin tampil dengan badge `Admin` di header room dan metadata chat.
- Tampilan compact agar lebih ringan, sederhana, dan tidak terlalu banyak teks.

## Setup

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
