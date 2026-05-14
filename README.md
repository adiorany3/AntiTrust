# AntiTrust Secure Improved

Versi perbaikan AntiTrust dengan tampilan lebih sederhana, room berbasis invite, enkripsi Fernet, validasi file lebih ketat, panic destroy, dan auto-destroy saat room tidak aktif.

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
- Invite link dibuat dari panel admin dan memiliki masa aktif.
- File upload dibatasi ukuran dan diverifikasi berdasarkan magic bytes/struktur file.
- Room dan packet disimpan memakai key hash, bukan nama room mentah.
