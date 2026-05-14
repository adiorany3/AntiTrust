# AntiTrust Secure Glass v9

Versi perbaikan AntiTrust dengan tampilan glass/iPhone-style, room sementara, invite link, enkripsi Fernet, validasi file lebih ketat, destroy room + revoke key, identitas terkunci, share invite via WhatsApp, dan auto-revoke otomatis saat waktu room habis.

## Fitur utama

- **Siapa pun bisa create room** dari halaman awal tanpa harus login admin.
- **Masa aktif room maksimal 60 menit**. Slider dibatasi 1-60 menit.
- **Room auto revoke saat waktu habis**: pesan, packet/file, status online, pengaturan room, dan semua invite link room otomatis dihancurkan/direvoke.
- **Countdown live** untuk sisa waktu room dan invite link.
- **Semua user di room bisa create invite link** untuk mengajak orang lain.
- **Share invite via WhatsApp**: setiap invite link dapat langsung dibagikan ke WhatsApp dengan pesan otomatis.
- **Invite link tidak bisa lebih lama dari sisa waktu room** dan tetap maksimal 60 menit.
- **Tidak ada fitur tinggalkan room**: user tidak bisa keluar-masuk untuk mengganti nama atau mengakali akses percakapan.
- **Hancurkan room + revoke key dengan countdown 3 detik**: setelah tombol ditekan, user masih bisa menekan Cancel sebelum room benar-benar dihancurkan dan invite link direvoke.
- **Panic destroy** untuk menghapus pesan/packet room aktif.
- **Nama pengguna terkunci** setelah pertama kali ditetapkan selama sesi berjalan.
- **Reserved name protection**: `adioranye` dan `Galuh Adi Insani` hanya bisa digunakan oleh admin.

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
- Nama pengguna yang sudah ditetapkan tidak bisa diedit dari UI room. Untuk memakai nama reserved, login admin terlebih dahulu.
