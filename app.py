from __future__ import annotations

import base64
import hashlib
import hmac
import html
import io
import json
import os
import secrets
import shutil
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet, InvalidToken

try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 16_000_000
except Exception:  # pragma: no cover
    Image = None

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    st_autorefresh = None

APP_TITLE = "AntiTrust"
APP_ICON = "🔐"
WIB = timezone(timedelta(hours=7))
DATA_DIR = Path(os.getenv("ANTITRUST_DATA_DIR", ".antitrust_data"))
PACKET_DIR = DATA_DIR / "packets"
CHAT_FILE = DATA_DIR / "chat_rooms.json"
ONLINE_FILE = DATA_DIR / "online_status.json"
ROOM_SETTINGS_FILE = DATA_DIR / "room_settings.json"
INVITE_FILE = DATA_DIR / "private_links.json"
LOCAL_KEY_FILE = DATA_DIR / "fernet.key"

MAX_TEXT_LENGTH = 2000
MAX_MEDIA_BYTES = 10 * 1024 * 1024
ONLINE_ACTIVE_SECONDS = 25
DEFAULT_DESTROY_MINUTES = 30
AUTO_DESTROY_CHOICES = ["Never", "10 menit", "20 menit", "30 menit", "60 menit"]
MESSAGE_RATE_LIMIT_SECONDS = 1.5
INVITE_DEFAULT_TTL_HOURS = 24

ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}
ALLOWED_AUDIO_TYPES = {"wav", "mp3", "ogg", "m4a", "aac", "flac", "webm"}
ALLOWED_DOCUMENT_TYPES = {"pdf", "docx", "xlsx", "pptx"}
DOCUMENT_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
RISKY_EXTENSIONS = {
    "sh", "bash", "zsh", "ps1", "bat", "cmd", "exe", "dll", "scr", "vbs", "js", "jar", "com", "msi"
}
SHELL_SIGNATURES = [
    b"#!/bin/sh", b"#!/bin/bash", b"#!/usr/bin/env sh", b"#!/usr/bin/env bash"
]
SHELL_KEYWORDS = [b"curl ", b"wget ", b"chmod ", b"rm -rf", b"powershell", b"Invoke-WebRequest"]

CSS = """
<style>
:root{
  color-scheme: light;
  --app-bg:#f7f8fb;
  --app-bg-2:#eef3ff;
  --surface:#ffffff;
  --surface-2:#f8fafc;
  --surface-soft:rgba(255,255,255,.94);
  --text:#172033;
  --text-strong:#0f172a;
  --muted:#4b5563;
  --line:#d9dee8;
  --input-bg:#ffffff;
  --primary:#2563eb;
  --primary-soft:#eff6ff;
  --danger:#dc2626;
  --danger-soft:#fff1f2;
}
@media (prefers-color-scheme: dark){
  :root{
    color-scheme: dark;
    --app-bg:#0b1020;
    --app-bg-2:#111827;
    --surface:#141b2d;
    --surface-2:#1f2937;
    --surface-soft:rgba(20,27,45,.96);
    --text:#f8fafc;
    --text-strong:#ffffff;
    --muted:#cbd5e1;
    --line:#334155;
    --input-bg:#0f172a;
    --primary:#60a5fa;
    --primary-soft:#172554;
    --danger:#fb7185;
    --danger-soft:#3f111b;
  }
}
#MainMenu, header, footer {visibility:hidden;}
.stApp{background:linear-gradient(180deg,var(--app-bg) 0%,var(--app-bg-2) 100%)!important;color:var(--text)!important;}
.block-container{max-width:920px;padding:1.4rem 1rem 2.4rem;}
html,body,.stApp,.stMarkdown,p,span,label,div,[data-testid="stWidgetLabel"],[data-testid="stMarkdownContainer"]{color:var(--text)!important;}
h1,h2,h3,h4,h5,h6{color:var(--text-strong)!important;letter-spacing:-.02em;}
h1{font-size:2rem!important;margin-bottom:.15rem!important;}
a{color:var(--primary)!important;}
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--line)!important;}
[data-testid="stSidebar"] *{color:var(--text)!important;}
.stButton button,.stFormSubmitButton button,.stDownloadButton button{border-radius:14px!important;border:1px solid var(--line)!important;background:var(--surface-2)!important;color:var(--text-strong)!important;box-shadow:0 4px 14px rgba(0,0,0,.10)!important;}
.stButton button:hover,.stFormSubmitButton button:hover,.stDownloadButton button:hover{border-color:var(--primary)!important;color:var(--text-strong)!important;}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]{background:var(--danger)!important;color:#ffffff!important;border-color:var(--danger)!important;}
.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox div[data-baseweb="select"]>div{border-radius:14px!important;border:1px solid var(--line)!important;background:var(--input-bg)!important;color:var(--text-strong)!important;}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:var(--muted)!important;opacity:1!important;}
.stSelectbox [data-baseweb="select"] span{color:var(--text-strong)!important;}
.stTabs [data-baseweb="tab"]{color:var(--muted)!important;}
.stTabs [aria-selected="true"]{color:var(--primary)!important;}
.stCaption,.stCaption *,.stInfo,.stAlert,.stToast{color:var(--text)!important;}
.card{background:var(--surface-soft);border:1px solid var(--line);border-radius:24px;padding:18px 20px;box-shadow:0 10px 30px rgba(0,0,0,.14);margin:14px 0;color:var(--text)!important;}
.hero{background:linear-gradient(135deg,var(--surface) 0%,var(--surface-2) 100%);border:1px solid var(--line);border-radius:28px;padding:24px;box-shadow:0 16px 40px rgba(37,99,235,.12);margin-bottom:18px;color:var(--text)!important;}
.badge{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;background:var(--primary-soft);color:var(--primary)!important;font-size:.82rem;font-weight:700;margin-right:8px;}
.muted{color:var(--muted)!important;font-size:.94rem;line-height:1.55;}
.danger-box{background:var(--danger-soft);border:1px solid var(--danger);border-radius:20px;padding:14px 16px;margin:12px 0;color:var(--text)!important;}
</style>
"""

CHAT_CSS = """
<style>
:root{
  color-scheme: light;
  --chat-bg:rgba(255,255,255,.90);
  --bubble:#f2f5fb;
  --bubble-text:#172033;
  --me:#2563eb;
  --me-text:#ffffff;
  --muted:#4b5563;
  --line:#d9dee8;
  --empty:#4b5563;
}
@media (prefers-color-scheme: dark){
  :root{
    color-scheme: dark;
    --chat-bg:rgba(15,23,42,.92);
    --bubble:#1f2937;
    --bubble-text:#f8fafc;
    --me:#2563eb;
    --me-text:#ffffff;
    --muted:#cbd5e1;
    --line:#334155;
    --empty:#cbd5e1;
  }
}
html,body{margin:0;background:transparent;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:var(--bubble-text);}
.chat{height:470px;overflow-y:auto;padding:14px;background:var(--chat-bg);border:1px solid var(--line);border-radius:24px;box-sizing:border-box;}
.row{display:flex;margin:0 0 10px 0;}
.row.me{justify-content:flex-end;}
.bubble{max-width:76%;padding:11px 13px;border-radius:18px;background:var(--bubble);color:var(--bubble-text);border:1px solid var(--line);overflow-wrap:anywhere;line-height:1.42;}
.bubble small{color:var(--muted);}
.row.me .bubble{background:var(--me);color:var(--me-text);border-color:var(--me);}
.row.me .bubble small{color:rgba(255,255,255,.86);}
.meta{font-size:11px;color:var(--muted);margin-top:6px;}
.row.me .meta{color:rgba(255,255,255,.78);}
.empty{height:100%;display:flex;align-items:center;justify-content:center;color:var(--empty);}
.packet{display:block;font-weight:700;margin-bottom:4px;color:inherit;}
.thumb{max-width:min(260px,100%);max-height:190px;border-radius:14px;border:1px solid var(--line);object-fit:contain;display:block;margin-top:8px;background:#fff;}
</style>
"""


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PACKET_DIR.mkdir(parents=True, exist_ok=True)


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_dirs()
    tmp = path.with_suffix(path.suffix + f".{secrets.token_hex(6)}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> dict[str, Any]:
    ensure_dirs()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        backup = path.with_suffix(path.suffix + f".broken-{int(time.time())}")
        try:
            shutil.copy2(path, backup)
        except Exception:
            pass
        return {}


def get_fernet_key() -> bytes:
    secret_key = get_secret("FERNET_KEY", "").strip()
    if secret_key:
        return secret_key.encode("utf-8")
    ensure_dirs()
    if not LOCAL_KEY_FILE.exists():
        LOCAL_KEY_FILE.write_bytes(Fernet.generate_key())
    return LOCAL_KEY_FILE.read_bytes().strip()


@st.cache_resource(show_spinner=False)
def get_fernet() -> Fernet:
    return Fernet(get_fernet_key())


def encrypt_text(text: str) -> str:
    return get_fernet().encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str) -> str:
    try:
        return get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return "[pesan tidak dapat didekripsi]"


def encrypt_bytes(data: bytes) -> bytes:
    return get_fernet().encrypt(data)


def decrypt_bytes(data: bytes) -> bytes | None:
    try:
        return get_fernet().decrypt(data)
    except InvalidToken:
        return None


def now_epoch() -> int:
    return int(time.time())


def now_wib_label() -> str:
    return datetime.now(WIB).strftime("%d %b %Y, %H:%M")


def slug(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:32]


def hmac_digest(value: str) -> str:
    admin_secret = get_secret("CHAT_ADMIN_PASSWORD", "change-this-password")
    return hmac.new(admin_secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def room_key(room: str) -> str:
    return "room_" + hmac_digest(room)[:40]


def packet_room_dir(room: str) -> Path:
    return PACKET_DIR / room_key(room)


def safe_filename(filename: str) -> str:
    raw = Path(filename or "packet.bin").name
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in "._- ()")[:120]
    return cleaned or "packet.bin"


def ext_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def format_bytes(size: int | str | None) -> str:
    try:
        amount = float(size or 0)
    except Exception:
        amount = 0
    for unit in ["B", "KB", "MB", "GB"]:
        if amount < 1024 or unit == "GB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} {unit}"
        amount /= 1024
    return f"{amount:.1f} GB"


def is_text_like(data: bytes) -> bool:
    sample = data[:4096]
    if not sample:
        return False
    printable = sum(1 for byte in sample if byte in b"\t\n\r" or 32 <= byte <= 126)
    return printable / len(sample) > 0.86


def looks_like_script(data: bytes) -> bool:
    sample = data[:4096].lstrip().lower()
    if any(sample.startswith(sig.lower()) for sig in SHELL_SIGNATURES):
        return True
    if not is_text_like(data):
        return False
    hits = sum(1 for keyword in SHELL_KEYWORDS if keyword.lower() in sample)
    syntax = any(token in sample for token in [b"#!/", b"function ", b"; then", b"do\n", b"done\n"])
    return hits >= 2 or (hits >= 1 and syntax)


def detect_image_format(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def detect_document_format(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "pdf"
    if not data.startswith(b"PK"):
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zipped:
            names = set(zipped.namelist())
            lowered = {name.lower() for name in names}
            if "[content_types].xml" not in lowered:
                return None
            for name in names:
                normalized = name.replace("\\", "/")
                lower = normalized.lower()
                suffix = Path(lower).suffix.lstrip(".")
                if normalized.startswith("/") or "../" in normalized or suffix in RISKY_EXTENSIONS:
                    return None
            if any(name.startswith("word/") for name in lowered):
                return "docx"
            if any(name.startswith("xl/") for name in lowered):
                return "xlsx"
            if any(name.startswith("ppt/") for name in lowered):
                return "pptx"
    except zipfile.BadZipFile:
        return None
    return None


def validate_upload(uploaded_file: Any, media_type: str) -> tuple[bytes, str, str] | None:
    if uploaded_file is None:
        st.warning("Pilih file terlebih dahulu.")
        return None
    data = uploaded_file.getvalue()
    filename = safe_filename(getattr(uploaded_file, "name", "packet.bin"))
    extension = ext_of(filename)
    mime_type = getattr(uploaded_file, "type", "application/octet-stream") or "application/octet-stream"

    if not data:
        st.error("File kosong atau gagal dibaca.")
        return None
    if len(data) > MAX_MEDIA_BYTES:
        st.error(f"Ukuran file terlalu besar. Maksimal {format_bytes(MAX_MEDIA_BYTES)}.")
        return None
    if extension in RISKY_EXTENSIONS or looks_like_script(data):
        st.error("File diblokir karena terindikasi script/executable.")
        return None

    if media_type == "image":
        real_format = detect_image_format(data)
        if real_format is None or extension not in ALLOWED_IMAGE_TYPES:
            st.error("Image harus PNG, JPG/JPEG, atau WEBP asli.")
            return None
        if Image is not None:
            try:
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
            except Exception:
                st.error("Image rusak atau tidak valid.")
                return None
        return data, "image/jpeg" if real_format == "jpg" else f"image/{real_format}", filename

    if media_type == "audio":
        if extension not in ALLOWED_AUDIO_TYPES:
            st.error("Audio harus WAV, MP3, OGG, M4A, AAC, FLAC, atau WEBM.")
            return None
        if not (mime_type.startswith("audio/") or mime_type in {"video/webm", "application/octet-stream"}):
            st.error("Format audio tidak valid.")
            return None
        return data, mime_type, filename

    if media_type == "document":
        real_format = detect_document_format(data)
        if extension not in ALLOWED_DOCUMENT_TYPES or real_format != extension:
            st.error("Dokumen harus PDF, DOCX, XLSX, atau PPTX asli, bukan file yang menyamar.")
            return None
        return data, DOCUMENT_MIME[real_format], filename

    return None


def make_thumbnail(data: bytes) -> tuple[str, str]:
    if Image is None:
        return "", ""
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.thumbnail((320, 240))
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            buf = io.BytesIO()
            image.save(buf, format="JPEG", quality=72, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("ascii"), "image/jpeg"
    except Exception:
        return "", ""


def save_packet(room: str, message_id: str, data: bytes) -> str:
    directory = packet_room_dir(room)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{message_id}.bin"
    path.write_bytes(encrypt_bytes(data))
    return path.relative_to(DATA_DIR).as_posix()


def resolve_packet_path(relative_path: str) -> Path | None:
    if not relative_path:
        return None
    candidate = (DATA_DIR / relative_path).resolve()
    try:
        candidate.relative_to(DATA_DIR.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def read_packet(relative_path: str) -> bytes | None:
    path = resolve_packet_path(relative_path)
    if path is None:
        return None
    return decrypt_bytes(path.read_bytes())


def delete_room_packets(room: str) -> None:
    shutil.rmtree(packet_room_dir(room), ignore_errors=True)


def parse_destroy_choice(choice: str) -> int | None:
    return None if choice == "Never" else int(choice.split()[0])


def choice_from_minutes(minutes: int | None) -> str:
    return "Never" if minutes is None else f"{minutes} menit"


def get_room_config(room: str) -> dict[str, Any]:
    settings = load_json(ROOM_SETTINGS_FILE)
    key = room_key(room)
    config = settings.get(key, {}) if isinstance(settings.get(key), dict) else {}
    minutes = config.get("auto_destroy_minutes", DEFAULT_DESTROY_MINUTES)
    if minutes not in {None, 10, 20, 30, 60}:
        minutes = DEFAULT_DESTROY_MINUTES
    return {"auto_destroy_minutes": minutes, "last_active_at": int(config.get("last_active_at", now_epoch()))}


def save_room_config(room: str, config: dict[str, Any]) -> None:
    settings = load_json(ROOM_SETTINGS_FILE)
    settings[room_key(room)] = config
    atomic_write_json(ROOM_SETTINGS_FILE, settings)


def mark_room_active(room: str) -> None:
    config = get_room_config(room)
    config["last_active_at"] = now_epoch()
    save_room_config(room, config)


def update_online(room: str, username: str) -> list[str]:
    online = load_json(ONLINE_FILE)
    key = room_key(room)
    now = now_epoch()
    online.setdefault(key, {})
    online[key][username] = now
    active = {user: int(ts) for user, ts in online[key].items() if now - int(ts) <= ONLINE_ACTIVE_SECONDS}
    online[key] = active
    atomic_write_json(ONLINE_FILE, online)
    mark_room_active(room)
    return [user for user in active if user != username]


def purge_inactive_rooms() -> int:
    rooms = load_json(CHAT_FILE)
    online = load_json(ONLINE_FILE)
    settings = load_json(ROOM_SETTINGS_FILE)
    now = now_epoch()
    destroyed = 0
    changed = False

    for key, config in list(settings.items()):
        active = {u: int(ts) for u, ts in online.get(key, {}).items() if now - int(ts) <= ONLINE_ACTIVE_SECONDS}
        online[key] = active
        minutes = config.get("auto_destroy_minutes", DEFAULT_DESTROY_MINUTES)
        if active:
            config["last_active_at"] = now
            settings[key] = config
            changed = True
            continue
        if minutes is None:
            settings[key] = config
            continue
        last_active = int(config.get("last_active_at", now))
        if now - last_active >= int(minutes) * 60:
            rooms.pop(key, None)
            online.pop(key, None)
            settings.pop(key, None)
            # packet directory name uses the same room_key but original room is not stored; remove by key directly.
            shutil.rmtree(PACKET_DIR / key, ignore_errors=True)
            destroyed += 1
            changed = True

    if changed:
        atomic_write_json(CHAT_FILE, rooms)
        atomic_write_json(ONLINE_FILE, online)
        atomic_write_json(ROOM_SETTINGS_FILE, settings)
    return destroyed


def rate_limited(action: str) -> bool:
    key = f"rate::{action}"
    now = time.monotonic()
    last = float(st.session_state.get(key, 0))
    if now - last < MESSAGE_RATE_LIMIT_SECONDS:
        st.warning("Terlalu cepat. Coba kirim lagi sebentar.")
        return True
    st.session_state[key] = now
    return False


def append_text(room: str, username: str, text: str) -> None:
    clean = text.strip()[:MAX_TEXT_LENGTH]
    if not clean:
        return
    rooms = load_json(CHAT_FILE)
    key = room_key(room)
    rooms.setdefault(key, [])
    rooms[key].append({
        "id": secrets.token_urlsafe(18),
        "type": "text",
        "username": username,
        "text": encrypt_text(clean),
        "time": now_wib_label(),
        "created_at": now_epoch(),
    })
    atomic_write_json(CHAT_FILE, rooms)
    mark_room_active(room)


def append_media(room: str, username: str, media_type: str, data: bytes, mime_type: str, filename: str) -> None:
    rooms = load_json(CHAT_FILE)
    key = room_key(room)
    rooms.setdefault(key, [])
    message_id = secrets.token_urlsafe(18)
    packet_path = save_packet(room, message_id, data)
    message: dict[str, Any] = {
        "id": message_id,
        "type": media_type,
        "username": username,
        "packet_path": packet_path,
        "mime_type": mime_type,
        "filename": filename,
        "size_bytes": len(data),
        "time": now_wib_label(),
        "created_at": now_epoch(),
    }
    if media_type == "image":
        thumb, thumb_mime = make_thumbnail(data)
        if thumb:
            message["thumbnail"] = encrypt_text(thumb)
            message["thumbnail_mime"] = thumb_mime
    rooms[key].append(message)
    atomic_write_json(CHAT_FILE, rooms)
    mark_room_active(room)


def load_messages(room: str) -> list[dict[str, Any]]:
    rooms = load_json(CHAT_FILE)
    messages = rooms.get(room_key(room), [])
    return messages if isinstance(messages, list) else []


def panic_destroy(room: str) -> int:
    rooms = load_json(CHAT_FILE)
    key = room_key(room)
    count = len(rooms.get(key, [])) if isinstance(rooms.get(key), list) else 0
    rooms[key] = []
    atomic_write_json(CHAT_FILE, rooms)
    delete_room_packets(room)
    mark_room_active(room)
    return count


def token_hash(token: str) -> str:
    return hmac_digest(token)


def create_invite(room: str, ttl_hours: int = INVITE_DEFAULT_TTL_HOURS) -> str:
    token = secrets.token_urlsafe(32)
    invites = load_json(INVITE_FILE)
    invites[token_hash(token)] = {
        "room": encrypt_text(room),
        "created_at": now_epoch(),
        "expires_at": now_epoch() + max(1, ttl_hours) * 3600,
        "revoked": False,
    }
    atomic_write_json(INVITE_FILE, invites)
    return token


def resolve_invite(token: str | None) -> str | None:
    if not token:
        return None
    invites = load_json(INVITE_FILE)
    item = invites.get(token_hash(token))
    if not isinstance(item, dict) or item.get("revoked"):
        return None
    if int(item.get("expires_at", 0)) < now_epoch():
        return None
    room = decrypt_text(str(item.get("room", ""))).strip()
    return room or None


def public_base_url() -> str:
    configured = get_secret("PUBLIC_APP_URL", "").strip().rstrip("/")
    return configured or "http://localhost:8501"


def build_invite_url(token: str) -> str:
    return f"{public_base_url()}?{urlencode({'invite': token})}"


def get_query_param(name: str) -> str | None:
    try:
        value = st.query_params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value
    except Exception:
        params = st.experimental_get_query_params()
        values = params.get(name, [])
        return values[0] if values else None


def render_chat(messages: list[dict[str, Any]], username: str) -> str:
    if not messages:
        return CHAT_CSS + '<div class="chat"><div class="empty">Belum ada pesan. Mulai percakapan aman.</div></div>'
    rows = ""
    for msg in messages[-120:]:
        sender = html.escape(str(msg.get("username", "unknown")))
        is_me = sender == html.escape(username)
        time_label = html.escape(str(msg.get("time", "")))
        msg_type = str(msg.get("type", "text"))
        if msg_type == "text":
            content = html.escape(decrypt_text(str(msg.get("text", ""))))
        else:
            filename = html.escape(str(msg.get("filename", "packet")))
            size = html.escape(format_bytes(msg.get("size_bytes", 0)))
            label = {"image": "Image", "audio": "Voice", "document": "Document"}.get(msg_type, "Packet")
            content = f'<span class="packet">{label} Packet</span>{filename}<br><small>{size} · buka di Packet Viewer</small>'
            if msg_type == "image" and msg.get("thumbnail"):
                thumb = decrypt_text(str(msg.get("thumbnail", "")))
                mime = html.escape(str(msg.get("thumbnail_mime", "image/jpeg")))
                if thumb and not thumb.startswith("["):
                    content += f'<img class="thumb" src="data:{mime};base64,{html.escape(thumb, quote=True)}" />'
        cls = "row me" if is_me else "row"
        rows += f'<div class="{cls}"><div class="bubble">{content}<div class="meta">{sender}{" · kamu" if is_me else ""} · {time_label}</div></div></div>'
    return CHAT_CSS + f'<div class="chat">{rows}</div>'


def latest_foreign_signature(messages: list[dict[str, Any]], username: str) -> str:
    for msg in reversed(messages):
        if str(msg.get("username", "")) != username:
            return str(msg.get("id", ""))
    return ""


def render_sound_notice(signature: str, enabled: bool) -> None:
    if not enabled or not signature:
        return
    safe_sig = html.escape(signature, quote=True)
    components.html(
        f"""
        <button id="enable" style="border:1px solid var(--line,#d9dee8);border-radius:999px;padding:8px 12px;background:var(--surface,#fff);color:var(--text,#172033);cursor:pointer">Aktifkan suara notifikasi</button>
        <script>
        const key='antitrust-last-sound';
        const sig='{safe_sig}';
        function beep(){{
          const ctx=new(window.AudioContext||window.webkitAudioContext)();
          const osc=ctx.createOscillator(); const gain=ctx.createGain();
          osc.frequency.value=880; gain.gain.value=0.05;
          osc.connect(gain); gain.connect(ctx.destination); osc.start();
          setTimeout(()=>{{osc.stop();ctx.close();}},120);
        }}
        document.getElementById('enable').onclick=()=>{{localStorage.setItem('antitrust-sound','1');beep();}};
        if(localStorage.getItem('antitrust-sound')==='1' && localStorage.getItem(key)!==sig){{beep();localStorage.setItem(key,sig);}}
        </script>
        """,
        height=45,
    )


def render_packet_viewer(room: str, messages: list[dict[str, Any]]) -> None:
    packets = [msg for msg in messages if str(msg.get("type", "")) in {"image", "audio", "document"}]
    if not packets:
        return
    with st.container(border=True):
        st.subheader("Packet Viewer")
        packet_map = {str(msg.get("id")): msg for msg in packets}
        selected = st.selectbox(
            "Pilih file terenkripsi",
            options=list(reversed(list(packet_map.keys()))),
            format_func=lambda mid: f"{packet_map[mid].get('type','packet')} · {packet_map[mid].get('filename','packet')} · {format_bytes(packet_map[mid].get('size_bytes',0))}",
        )
        msg = packet_map[selected]
        if st.button("Buka packet", use_container_width=True):
            st.session_state[f"opened::{room}"] = selected
        if st.session_state.get(f"opened::{room}") != selected:
            st.caption("File asli baru didekripsi setelah tombol dibuka.")
            return
        data = read_packet(str(msg.get("packet_path", "")))
        if data is None:
            st.error("Packet tidak ditemukan atau gagal didekripsi.")
            return
        mime = str(msg.get("mime_type", "application/octet-stream"))
        filename = safe_filename(str(msg.get("filename", "packet.bin")))
        if msg.get("type") == "image":
            st.image(data, caption=filename, width=420)
        elif msg.get("type") == "audio":
            st.audio(data, format=mime)
        st.download_button("Download packet", data=data, file_name=filename, mime=mime, use_container_width=True)


def render_admin_panel() -> None:
    admin_password = get_secret("CHAT_ADMIN_PASSWORD", "")
    with st.container(border=True):
        st.subheader("Admin")
        if not admin_password:
            st.error("Set CHAT_ADMIN_PASSWORD di Streamlit Secrets atau environment variable dulu.")
            st.code('CHAT_ADMIN_PASSWORD = "password-yang-kuat"\nFERNET_KEY = "hasil-generate-fernet-key"\nPUBLIC_APP_URL = "https://nama-app.streamlit.app"')
            return
        if not st.session_state.get("admin_ok"):
            password = st.text_input("Password admin", type="password")
            if st.button("Login admin", use_container_width=True):
                if hmac.compare_digest(password, admin_password):
                    st.session_state["admin_ok"] = True
                    st.rerun()
                else:
                    st.error("Password salah.")
            return

        st.success("Admin aktif")
        room = st.text_input("Nama room tujuan", placeholder="kelas-private-01")
        ttl = st.number_input("Masa aktif invite link (jam)", min_value=1, max_value=168, value=24)
        if st.button("Buat invite link", use_container_width=True):
            if not room.strip():
                st.warning("Nama room tidak boleh kosong.")
            else:
                token = create_invite(room.strip(), int(ttl))
                st.session_state["last_invite"] = build_invite_url(token)
                st.success("Invite link berhasil dibuat.")
        if st.session_state.get("last_invite"):
            st.text_input("Invite link", value=st.session_state["last_invite"])
        if st.button("Logout admin", use_container_width=True):
            st.session_state.pop("admin_ok", None)
            st.rerun()


def render_landing() -> None:
    st.markdown('<div class="hero"><span class="badge">🔐 invite only</span><span class="badge">encrypted packets</span><h1>AntiTrust</h1><p class="muted">Private chat sederhana dengan room berbasis invite, enkripsi Fernet, validasi upload, dan auto-destroy saat room tidak aktif.</p></div>', unsafe_allow_html=True)
    st.info("Masuk memakai invite link. Admin dapat membuat invite link dari panel di bawah.")
    render_admin_panel()


def render_sidebar() -> tuple[bool, int, bool]:
    st.sidebar.title("AntiTrust")
    auto_refresh = st.sidebar.toggle("Auto refresh", value=True)
    interval = st.sidebar.selectbox("Interval", [3, 5, 10, 15], index=1)
    sound = st.sidebar.toggle("Suara pesan baru", value=True)
    st.sidebar.caption("Key dan password harus disimpan di Secrets/env, bukan di GitHub.")
    return auto_refresh, interval, sound


def render_room_settings(room: str) -> None:
    config = get_room_config(room)
    current = choice_from_minutes(config.get("auto_destroy_minutes"))
    with st.expander("Pengaturan room"):
        choice = st.selectbox("Auto-destroy jika room kosong", AUTO_DESTROY_CHOICES, index=AUTO_DESTROY_CHOICES.index(current) if current in AUTO_DESTROY_CHOICES else 3)
        if st.button("Simpan pengaturan", use_container_width=True):
            config["auto_destroy_minutes"] = parse_destroy_choice(choice)
            save_room_config(room, config)
            st.success("Pengaturan disimpan.")


def render_panic(room: str) -> None:
    st.markdown('<div class="danger-box"><b>Panic Destroy</b><br><span class="muted">Menghapus semua pesan dan packet di room aktif.</span></div>', unsafe_allow_html=True)
    confirm = st.checkbox("Saya paham tindakan ini menghapus pesan room aktif")
    if st.button("Panic destroy sekarang", type="primary", use_container_width=True, disabled=not confirm):
        count = panic_destroy(room)
        st.success(f"Berhasil menghapus {count} pesan/packet.")
        st.rerun()


def render_message_form(room: str, username: str) -> None:
    with st.container(border=True):
        st.subheader("Kirim pesan")
        with st.form("text-message", clear_on_submit=True):
            message = st.text_area("Pesan", placeholder="Tulis pesan terenkripsi...", height=90, max_chars=MAX_TEXT_LENGTH)
            submitted = st.form_submit_button("Kirim pesan", use_container_width=True)
            if submitted:
                if not rate_limited("text"):
                    append_text(room, username, message)
                    st.rerun()
        tab_img, tab_voice, tab_doc = st.tabs(["Image", "Voice", "Document"])
        with tab_img:
            image = st.file_uploader("Image", type=list(ALLOWED_IMAGE_TYPES))
            if st.button("Kirim image", use_container_width=True):
                if not rate_limited("image"):
                    payload = validate_upload(image, "image")
                    if payload:
                        append_media(room, username, "image", *payload)
                        st.rerun()
        with tab_voice:
            audio = st.file_uploader("Audio", type=list(ALLOWED_AUDIO_TYPES))
            recorded = st.audio_input("Rekam suara") if hasattr(st, "audio_input") else None
            if st.button("Kirim voice", use_container_width=True):
                if not rate_limited("audio"):
                    payload = validate_upload(recorded or audio, "audio")
                    if payload:
                        append_media(room, username, "audio", *payload)
                        st.rerun()
        with tab_doc:
            doc = st.file_uploader("Document", type=list(ALLOWED_DOCUMENT_TYPES))
            if st.button("Kirim document", use_container_width=True):
                if not rate_limited("document"):
                    payload = validate_upload(doc, "document")
                    if payload:
                        append_media(room, username, "document", *payload)
                        st.rerun()


def main() -> None:
    ensure_dirs()
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    destroyed = purge_inactive_rooms()
    auto_refresh, interval, sound = render_sidebar()
    if auto_refresh and st_autorefresh is not None:
        st_autorefresh(interval=interval * 1000, key="antitrust_refresh")
    if destroyed:
        st.toast(f"{destroyed} room tidak aktif sudah dibersihkan.")

    invite_token = get_query_param("invite")
    room = resolve_invite(invite_token)
    if not room:
        render_landing()
        return

    st.markdown('<div class="hero"><span class="badge">🔐 room aktif</span><span class="badge">private invite</span><h1>AntiTrust Room</h1><p class="muted">Pesan teks dan packet disimpan terenkripsi. File asli hanya didekripsi saat dibuka.</p></div>', unsafe_allow_html=True)
    username = st.text_input("Nama pengguna", placeholder="contoh: adiora")
    username = username.strip()[:40]
    if not username:
        st.info("Isi nama pengguna untuk masuk ke room.")
        return

    active_users = update_online(room, username)
    messages = load_messages(room)
    config = get_room_config(room)
    st.caption(f"User: {username} · Peers aktif: {len(active_users)} · Auto-destroy: {choice_from_minutes(config.get('auto_destroy_minutes'))}")
    render_room_settings(room)
    render_panic(room)
    render_sound_notice(latest_foreign_signature(messages, username), sound)
    components.html(render_chat(messages, username), height=500, scrolling=False)
    render_packet_viewer(room, messages)
    render_message_form(room, username)


if __name__ == "__main__":
    main()
