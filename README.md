# AntiTrust - Secure Temporary Room + Google Meet

AntiTrust adalah private temporary chat berbasis Streamlit. Paket ini sudah diperkuat untuk sesi chat sementara, invite link, file/packet, dan video call Google Meet dengan kontrol akses yang lebih aman.

## Perubahan terbaru dalam paket ini

- **Google Meet terkontrol**: link GMeet bisa disimpan, disembunyikan dulu, lalu ditampilkan ketika sesi benar-benar dimulai.
- **Waktu sesi mengikuti countdown room/chat**: peserta memakai countdown room sebagai patokan sesi.
- **Lock Room**: pembuat bisa mengunci room agar peserta baru tidak bisa masuk.
- **Limit peserta aktif**: pembuat dapat mengatur maksimal peserta aktif per room.
- **PIN aksi pembuat terpisah**: password room dipakai untuk membuka enkripsi/chat, sedangkan PIN aksi pembuat dipakai untuk lock, pengaturan Google Meet, revoke, dan hapus chat.
- **One-click revoke dengan konfirmasi**: room, pesan, packet, dan invite link bisa direvoke/dihapus dari panel Aksi.
- **Participant panel**: daftar peserta aktif dan status terakhir aktif.
- **Pin pesan penting**: pesan penting dapat dipin di bagian atas room.
- **Template undangan siap copy**: invite link dilengkapi template pesan yang bisa disalin, termasuk catatan keamanan.
- **Audit ringan**: mencatat event seperti room dibuat, lock/unlock, update GMeet, update limit, dan pin/unpin tanpa menyimpan isi chat.
- **Ringkasan sesi**: summary lokal dari pesan yang masih tersedia di room dan bisa diunduh sebagai `.md`.
- **Validasi upload lebih ketat**: file dibatasi ukuran dan tipe; script/executable diblokir; dokumen dicek berdasarkan signature/struktur file.
- **Batas percobaan password/PIN**: setelah beberapa percobaan salah, sesi diberi jeda sementara.

## Cara menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

Gunakan `app.py` di folder utama paket ini.

## Alur penggunaan yang disarankan

1. Buat room dari halaman awal.
2. Isi **Password room / enkripsi** minimal 8 karakter.
3. Isi **PIN aksi pembuat** atau kosongkan agar aplikasi membuat PIN otomatis.
4. Simpan PIN aksi pembuat. PIN ini tidak ikut dibagikan di WhatsApp/template undangan.
5. Kirim invite link dan password room hanya ke peserta yang dipercaya.
6. Setelah semua peserta masuk, buka **Panel room → Aksi → Kontrol akses room → Lock room**.
7. Untuk video call, buka **Panel room → Video Call**, simpan link Google Meet, lalu klik **Mulai/Tampilkan** saat sesi dimulai.

## Secrets yang disarankan

Simpan di Streamlit Secrets atau environment variable, jangan commit ke GitHub.

```toml
CHAT_ADMIN_PASSWORD = "password-admin-yang-kuat"
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

## Catatan keamanan penting

- Jangan samakan **Password room** dan **PIN aksi pembuat** jika peserta tidak boleh punya akses revoke/settings.
- Google Meet sebaiknya dibuka di tab baru melalui tombol **Join Google Meet**. Banyak layanan video call membatasi embed/iframe demi keamanan.
- Aplikasi mengamankan akses room, penyimpanan link, pesan, dan packet. Keamanan meeting tetap mengikuti kebijakan Google Meet.
- Room lama tetap kompatibel. Jika room lama belum punya PIN aksi pembuat, password room masih dipakai untuk aksi sensitif demi kompatibilitas.

## Format undangan yang direkomendasikan

> Halo, sesi akan dilakukan melalui AntiTrust.  
> Link masuk room: `[invite-link]`  
> Password room: minta ke pembuat room secara terpisah.  
> Waktu sesi mengikuti countdown di room/chat.  
> Jika ada video call, tombol Google Meet tersedia di Panel room → Video Call setelah masuk.  
> Jangan teruskan link/password ke orang lain dan hapus pesan ini setelah berhasil masuk.
