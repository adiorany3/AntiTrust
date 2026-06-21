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


## Pembaruan desain responsif

- **Layout wide untuk desktop**: halaman utama memakai ruang layar lebih luas sehingga chat, panel kontrol, dan status room tidak terasa sempit.
- **Tampilan mobile lebih ramah HP**: tab bisa digeser horizontal, tombol lebih besar, input minimal 16px agar tidak memicu zoom di browser HP, dan kartu status disusun otomatis.
- **Landing page lebih jelas**: pengguna melihat alur 3 langkah: buat room, bagikan undangan, lalu jalankan sesi.
- **Pusat kontrol room terbuka otomatis**: invite, Google Meet, peserta, fitur, file, dan keamanan berada di satu area yang mudah ditemukan.
- **Dashboard status room**: sisa waktu, status lock, jumlah peserta, dan status Google Meet tampil sebagai kartu ringkas.
- **Chat bubble lebih modern**: pesan lebih mudah dibaca, bubble lebih rapi, dan gaya terminal/hacker dihilangkan agar nyaman untuk sesi panjang.
- **Label Bahasa Indonesia lebih natural**: tombol dan tab diganti menjadi teks yang mudah dipahami pengguna non-teknis.

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
6. Setelah semua peserta masuk, buka **Pusat kontrol room → Keamanan → Kontrol akses room → Lock room**.
7. Untuk video call, buka **Pusat kontrol room → Video**, simpan link Google Meet, lalu klik **Mulai/Tampilkan** saat sesi dimulai.

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
> Jika ada video call, tombol Google Meet tersedia di Pusat kontrol room → Video setelah masuk.  
> Jangan teruskan link/password ke orang lain dan hapus pesan ini setelah berhasil masuk.


## Update desain bersih

- Tampilan hacker/terminal sudah dihilangkan dan diganti menjadi desain profesional yang lebih terang, rapi, dan mudah dibaca.
- Dropdown/selectbox diperkuat dengan latar putih, teks gelap, kontras tinggi, dan area pilihan yang lebih besar agar nyaman di desktop maupun HP.
- Chat bubble, kartu status, tombol, tab, dan sidebar dibuat lebih sederhana sehingga pengguna baru lebih mudah memahami alur aplikasi.
- Layout tetap responsif: tab dapat digeser di layar kecil, tombol tetap besar, dan input memakai ukuran font aman untuk browser mobile.

### Pembaruan keterbacaan form

- Box ketik, textarea, dan dropdown sekarang memakai border 2px, fokus biru, latar putih, dan teks gelap agar mudah dibedakan dari background.
- Menu dropdown dibuat kontras tinggi dengan item lebih besar, cocok untuk desktop maupun browser HP.
- Area upload file diberi garis putus-putus yang lebih jelas sebagai drop zone.


## Perbaikan Admin Panel & Keterbacaan Form

Versi ini memperbaiki tampilan Admin Panel agar tidak tertumpuk, terutama di layar HP. Area admin sekarang memakai layout vertikal, label yang bisa membungkus baris, tombol lebih tinggi, dan ringkasan room dalam bentuk chip agar teks panjang tidak saling menimpa. Dropdown, input, checkbox, dan expander juga diberi jarak serta kontras yang lebih tegas.

- Perbaikan UI: teks ikon bawaan Streamlit disembunyikan dan diganti chevron CSS agar dropdown/expander tetap bersih.
