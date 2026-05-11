# AntiTrust Terminal

Aplikasi chat private-room berbasis Streamlit dengan tema terminal hacker. Public channel/manual room entry dinonaktifkan; akses chat hanya lewat invite link admin.

## Fitur utama

- Public channel dihapus: URL utama tanpa invite menampilkan gambar tengkorak bergerak/glitch dan warning `public_channel=disabled | invite_required=true`.
- Admin panel memakai login password dan session.
- Admin panel tidak lagi tampil di sidebar; panel admin berada di tengah halaman, tepat di bawah gambar tengkorak, tanpa expander/collapse.
- Admin dapat logout dari panel admin.
- Admin dapat membuat share link untuk room tertentu.
- Link memakai token invite: user membuka `https://antitrust.streamlit.app/?invite=TOKEN` dan room otomatis terkunci.
- Link share dapat langsung ditampilkan sebagai QR code PNG.
- Admin dapat melihat room aktif, user yang sedang aktif, jumlah pesan, jumlah link invite, dan setting auto-destroy.
- Admin dapat menghapus room dari dashboard admin.
- Saat room dihapus, pesan, status online, setting room, file packet terenkripsi, dan invite link room tersebut dapat ikut dinonaktifkan.
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

## Cara admin membuat link dan QR room

1. Buka app di `https://antitrust.streamlit.app/`.
2. `admin_panel` tampil di tengah halaman, tepat di bawah gambar tengkorak, tanpa perlu membuka expander.
3. Isi `admin_password`.
4. Klik `LOGIN ADMIN`.
5. Isi `target_room`, misalnya `black-room-01`.
6. Klik `CREATE ROOM SHARE LINK`.
7. Salin link invite atau download QR PNG yang muncul.

Contoh hasil link:

```text
https://antitrust.streamlit.app/?invite=TOKEN_RAHASIA
```

## Cara admin melihat dan menghapus room aktif

1. Login ke `admin_panel`.
2. Bagian `active_rooms` menampilkan daftar room aktif secara default.
3. Matikan toggle `show_only_active_rooms` jika ingin melihat semua room yang diketahui sistem.
4. Pilih room pada `selected_room`.
5. Biarkan `revoke_invite_links_for_room` aktif jika link invite room tersebut juga ingin dinonaktifkan.
6. Ketik `DELETE` pada kolom konfirmasi.
7. Klik `DELETE SELECTED ROOM`.

## Logout admin

Setelah selesai, klik `LOG OUT ADMIN` di `admin_panel`. Session admin akan dibersihkan dan panel kembali ke mode login.

## Catatan keamanan

- Jangan commit `fernet.key` dari server produksi jika ingin menjaga data lama tetap privat.
- File `private_links.json` menyimpan data invite room terenkripsi. Jangan bagikan isi file ini.
- Token invite hanya dapat dipakai selama `fernet.key` masih sama dan data `private_links.json` belum dihapus.
- Jika room dihapus dengan opsi revoke aktif, semua invite link untuk room tersebut menjadi invalid.
- Jika app diredeploy dan file runtime reset, link invite lama dapat hilang kecuali storage dipertahankan.

## Perilaku public URL

Jika user membuka URL utama tanpa token:

```text
https://antitrust.streamlit.app/
```

Aplikasi hanya menampilkan gambar tengkorak dan status:

```text
public_channel=disabled | invite_required=true
```

Form chat hanya muncul jika URL memiliki token invite yang valid dari admin.
