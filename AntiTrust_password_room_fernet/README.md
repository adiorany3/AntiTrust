# AntiTrust - Password-Derived Fernet Room Key

Patch ini membuat room baru memakai Fernet key unik yang diturunkan dari Password pembuat room.

Perubahan utama:
- Metadata invite/room tetap memakai Fernet global supaya kompatibel dengan link lama.
- Isi pesan teks, secret note, poll, checklist, location, thumbnail, dan packet file memakai key Fernet per-room.
- Key per-room diturunkan memakai PBKDF2-HMAC-SHA256 dengan 390.000 iterasi, salt acak per room, room_key sebagai context, dan server-side pepper dari FERNET_KEY + CHAT_ADMIN_PASSWORD.
- Password asli tidak disimpan. Yang disimpan hanya creator_password_hash dan room_fernet_salt.
- Room lama tanpa room_fernet_salt tetap bisa dibuka memakai enkripsi global lama.

Catatan penting:
- Simpan FERNET_KEY dan CHAT_ADMIN_PASSWORD secara stabil. Jika diganti, room lama bisa gagal dibuka.
- Bagikan password room secara terpisah dari invite link.
- Minimal password room dinaikkan menjadi 8 karakter.
