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


## Fitur interaktif tambahan

- Secret Note: pesan rahasia dibuka melalui panel Fitur.
- One-Time Message: pesan hilang setelah dibuka sekali.
- Poll Cepat: voting sederhana di dalam room.
- Location Pin: share link lokasi/manual maps tanpa live tracking.
- Checklist Bersama: daftar tugas kecil yang bisa dicentang bersama.
- Reaction Emoji: beri reaksi ke pesan.
- Pinned Message: pin pesan penting di atas room.
- Room Status: Waiting, Active, Closing soon, atau Revoked.
- Self-destruct Message: pesan tertentu bisa hilang otomatis setelah 1, 5, atau 10 menit.
- QR Invite: invite link bisa dibagikan lewat QR code.

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

## Update v13 - Compact Scroll
- Tampilan room dibuat lebih ringkas agar tidak terlalu banyak scroll naik-turun.
- Invite, fitur tambahan, file viewer, pengaturan, panic, dan destroy room dipindahkan ke satu **Panel room**.
- Tinggi chat, countdown, form, tab, tombol, dan input dipadatkan.
- Fitur v12 tetap dipertahankan.

## Update v14 - Expired Link Reset
- Jika sisa waktu invite link sudah `00:00`, link otomatis disembunyikan dari tampilan.
- Halaman dengan query invite yang sudah habis otomatis dibersihkan dan kembali ke halaman awal.
- QR Invite dan Share WhatsApp ikut hilang saat link expired.

## Update v15 - User Color Chat
- Setiap username mendapat warna chat otomatis yang berbeda dan konsisten.
- Bubble pesan user lain memakai aksen warna lembut agar mudah dibedakan.
- Bubble pesan milik sendiri memakai gradient berdasarkan warna username.
- Metadata chat diberi titik warna user agar percakapan lebih nyaman dibaca.
- Warna tetap aman untuk light mode dan dark mode.

## Update v16 - Unique Username Per Room
- Nama yang sama tidak bisa aktif bersamaan dalam satu room chat.
- Sistem mengecek username aktif sebelum user masuk ke percakapan.
- Jika nama sudah dipakai user lain di room yang sama, chat ditahan dan muncul notifikasi untuk memakai nama lain atau menunggu sesi lama tidak aktif.
- Format data online dibuat kompatibel dengan versi lama dan otomatis dibersihkan dari sesi yang sudah tidak aktif.

## Update v17 - Auto Scroll, Incoming Sound, Username Conflict Reset
- Chat box otomatis scroll ke pesan terbaru setiap render/refresh.
- Suara pesan masuk ditambahkan untuk pesan baru dari user lain.
- Browser perlu klik tombol **Aktifkan suara pesan masuk** satu kali agar audio diizinkan.
- Jika username yang dikunci ternyata sudah dipakai user lain dalam room yang sama, sistem otomatis refresh, mengosongkan username, lalu menampilkan kolom username agar bisa langsung diperbaiki.

## v17.3 stability hotfix
- Auto refresh chat sekarang default mati agar halaman tidak lompat/naik sendiri.
- Countdown invite/room berjalan client-side tanpa refresh Streamlit tiap detik.
- Auto-scroll hanya menggeser kotak chat ke pesan terbaru, bukan halaman browser utama.
- Tersedia tombol Refresh manual di sidebar.


## Update v17.4

- Auto refresh chat kembali aktif secara default.
- Komponen refresh dipindahkan ke area pesan agar tidak menarik tampilan ke bagian atas halaman.
- Pada layar HP, halaman otomatis diarahkan ke area message setelah refresh sehingga pengguna tidak perlu membuka setting sidebar.
- Scroll pesan tetap terjadi di dalam kotak chat, bukan menggulung seluruh browser.


## Update v17.5
- Interval auto-refresh default diubah menjadi 2 detik.
- Pilihan interval kini tersedia: 2, 5, 8, 10, 15, 30, dan 60 detik.
- Auto-refresh tetap aktif default dan tetap difokuskan ke area pesan.

## v17.6 Hotfix
- Memperbaiki error Streamlit slider menjelang room auto revoke.
- Panel invite sekarang otomatis ditutup saat sisa waktu room kurang dari 1 menit.
- State slider invite lama di-reset jika sudah di luar batas sisa waktu room.
- Jika room sudah habis, sesi dikembalikan ke halaman awal setelah revoke.
