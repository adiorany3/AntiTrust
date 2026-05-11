# ChatSecrets Hacker Terminal

Aplikasi chat multi-room berbasis Streamlit dengan tampilan terminal hacker, auto-refresh, enkripsi Fernet, dan suara pesan masuk.

## Perubahan Panic Room

Ketika tombol **PANIC ROOM // DESTROY NOW** ditekan:

1. Data pesan room dihapus dari `chat_rooms.json`.
2. Status online room dihapus dari `online_status.json`.
3. Nama room dimasukkan ke `destroyed_rooms.json`, sehingga room tidak otomatis dibuat ulang oleh user yang masih membuka halaman lama.
4. Input `room_name` pada sesi user yang menekan panic dikosongkan, sehingga user langsung keluar dari room.
5. User lain yang masih berada di room akan otomatis dikeluarkan pada auto-refresh berikutnya.

## Cara Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Catatan

File `fernet.key` tidak disertakan di ZIP ini. Aplikasi akan membuat key baru otomatis saat pertama kali dijalankan.
