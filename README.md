# AntiTrust Terminal

Aplikasi chat private-room berbasis Streamlit dengan tema terminal hacker. Public channel/manual room entry dinonaktifkan; akses chat hanya lewat invite link admin.

## Fitur utama

- Admin dapat membuat share link untuk room tertentu.
- Link memakai token invite: user membuka `https://antitrust.streamlit.app/?invite=TOKEN` dan room otomatis terkunci.
- Public channel dihapus: tanpa invite link, halaman hanya menampilkan ASCII skull dan tidak membuka form room/chat.
- Pesan teks terenkripsi dengan Fernet.
- Image Packet, Voice Packet, dan Document Packet disimpan sebagai file terenkripsi di luar `chat_rooms.json` agar browser tidak lag saat file besar.
- Preview gambar kecil memakai thumbnail.
- Packet viewer membuka/dekripsi file asli hanya saat dipilih.
- Tombol Panic Destroy untuk menghapus semua pesan dan packet di room aktif.
- Auto destroy pesan jika room kosong selama 10 sampai 60 menit, default 30 menit.
- Perlindungan dasar terhadap file shell/script yang menyamar sebagai gambar atau dokumen.
- Suara ding singkat untuk pesan baru dari user lain setelah tombol `ENABLE DING` diklik di browser.

## Cara deploy di Streamlit Cloud

1. Upload seluruh isi folder ini ke repository GitHub.
2. Deploy lewat Streamlit Cloud dengan entry file:

```bash
app.py
```

3. Tambahkan Secrets di Streamlit Cloud:

```toml
CHAT_ADMIN_PASSWORD = "ganti-password-admin-yang-kuat"
PUBLIC_APP_URL = "https://antitrust.streamlit.app"
```

## Cara menjalankan lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

Untuk lokal, set environment variable:

```bash
export CHAT_ADMIN_PASSWORD="ganti-password-admin-yang-kuat"
export PUBLIC_APP_URL="http://localhost:8501"
streamlit run app.py
```

## Cara admin membuat link room

1. Buka app. Halaman utama tanpa invite hanya menampilkan ASCII skull karena public channel sudah dimatikan.
2. Masuk ke sidebar `admin_share_link`.
3. Isi `admin_password`.
4. Isi `target_room`, misalnya `black-room-01`.
5. Klik `CREATE ROOM SHARE LINK`.
6. Bagikan link yang muncul.

Contoh hasil:

```text
https://antitrust.streamlit.app/?invite=TOKEN_RAHASIA
```

## Catatan keamanan

- Jangan commit `fernet.key` dari server produksi jika ingin menjaga data lama tetap privat.
- File `private_links.json` menyimpan hash token, bukan token mentah.
- Token invite hanya dapat dipakai selama `fernet.key` masih sama dan data `private_links.json` belum dihapus.
- Jika app diredeploy dan file runtime reset, link invite lama dapat hilang kecuali storage dipertahankan.

## Perilaku public URL

Jika user membuka URL utama tanpa token:

```text
https://antitrust.streamlit.app/
```

Aplikasi hanya menampilkan gambar tengkorak ASCII dan status:

```text
public_channel=disabled | invite_required=true
```

Form chat hanya muncul jika URL memiliki token invite yang valid dari admin.
