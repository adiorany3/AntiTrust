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
    import qrcode
except Exception:  # pragma: no cover
    qrcode = None

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
AUTO_DESTROY_CHOICES = ["5 menit", "10 menit", "20 menit", "30 menit", "60 menit"]
MESSAGE_RATE_LIMIT_SECONDS = 1.5
INVITE_DEFAULT_TTL_MINUTES = 60
INVITE_MAX_TTL_MINUTES = 60
ROOM_DEFAULT_TTL_MINUTES = 60
MESSAGE_SELF_DESTRUCT_CHOICES = {
    "Sampai room berakhir": 0,
    "1 menit": 60,
    "5 menit": 300,
    "10 menit": 600,
}
REACTION_CHOICES = ["👍", "😂", "🔥", "✅", "👀"]

ROOM_MAX_TTL_MINUTES = 60
RESERVED_DISPLAY_NAMES = {"adioranye", "galuh adi insani"}

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
  --app-bg:#edf3ff;
  --app-bg-2:#f9fbff;
  --glass:rgba(255,255,255,.58);
  --glass-strong:rgba(255,255,255,.78);
  --glass-soft:rgba(255,255,255,.34);
  --text:#102033;
  --text-strong:#07111f;
  --muted:#506176;
  --line:rgba(255,255,255,.66);
  --line-strong:rgba(120,145,180,.34);
  --input-bg:rgba(255,255,255,.66);
  --primary:#1877f2;
  --primary-2:#7c3aed;
  --primary-soft:rgba(24,119,242,.12);
  --danger:#ff3b30;
  --danger-soft:rgba(255,59,48,.13);
  --shadow:0 22px 70px rgba(31,70,130,.18);
  --inner:inset 0 1px 0 rgba(255,255,255,.72);
}
@media (prefers-color-scheme: dark){
  :root{
    color-scheme: dark;
    --app-bg:#060914;
    --app-bg-2:#111827;
    --glass:rgba(18,25,43,.50);
    --glass-strong:rgba(23,31,52,.76);
    --glass-soft:rgba(255,255,255,.07);
    --text:#eef5ff;
    --text-strong:#ffffff;
    --muted:#bfcbdd;
    --line:rgba(255,255,255,.16);
    --line-strong:rgba(255,255,255,.20);
    --input-bg:rgba(15,23,42,.58);
    --primary:#66a6ff;
    --primary-2:#c084fc;
    --primary-soft:rgba(102,166,255,.16);
    --danger:#ff6b63;
    --danger-soft:rgba(255,107,99,.15);
    --shadow:0 24px 80px rgba(0,0,0,.42);
    --inner:inset 0 1px 0 rgba(255,255,255,.16);
  }
}
#MainMenu, header, footer {visibility:hidden;}
.stApp{
  background:
    radial-gradient(circle at 12% 8%, rgba(24,119,242,.26), transparent 34%),
    radial-gradient(circle at 86% 4%, rgba(192,132,252,.26), transparent 32%),
    radial-gradient(circle at 72% 92%, rgba(45,212,191,.20), transparent 30%),
    linear-gradient(180deg,var(--app-bg) 0%,var(--app-bg-2) 100%)!important;
  color:var(--text)!important;
}
.stApp::before{
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  background-image:linear-gradient(rgba(255,255,255,.055) 1px, transparent 1px),linear-gradient(90deg,rgba(255,255,255,.045) 1px, transparent 1px);
  background-size:42px 42px;
  mask-image:linear-gradient(to bottom, rgba(0,0,0,.7), transparent 72%);
}
.block-container{max-width:860px;padding:.75rem .85rem 1.4rem;}
[data-testid="stVerticalBlock"]{gap:.55rem!important;}
[data-testid="stHorizontalBlock"]{gap:.55rem!important;}
[data-testid="stExpander"]{border-radius:18px!important;background:linear-gradient(145deg,var(--glass),var(--glass-soft))!important;border:1px solid var(--line)!important;}
[data-testid="stExpander"] summary{padding:.55rem .8rem!important;}
.stSlider{padding-top:0!important;}
html,body,.stApp,.stMarkdown,p,span,label,div,[data-testid="stWidgetLabel"],[data-testid="stMarkdownContainer"]{color:var(--text)!important;}
h1,h2,h3,h4,h5,h6{color:var(--text-strong)!important;letter-spacing:-.035em;}
h1{font-size:1.55rem!important;margin:.05rem 0!important;}
a{color:var(--primary)!important;text-decoration:none!important;}
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,var(--glass-strong),var(--glass))!important;
  border-right:1px solid var(--line)!important;
  backdrop-filter:blur(28px) saturate(180%);
  -webkit-backdrop-filter:blur(28px) saturate(180%);
  box-shadow:var(--inner), 14px 0 55px rgba(0,0,0,.10)!important;
}
[data-testid="stSidebar"] *{color:var(--text)!important;}
.stButton button,.stFormSubmitButton button,.stDownloadButton button{
  border-radius:999px!important;
  border:1px solid var(--line)!important;
  background:linear-gradient(180deg,var(--glass-strong),var(--glass-soft))!important;
  color:var(--text-strong)!important;
  box-shadow:var(--inner),0 12px 30px rgba(0,0,0,.12)!important;
  backdrop-filter:blur(18px) saturate(170%);
  -webkit-backdrop-filter:blur(18px) saturate(170%);
  transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease!important;
}
.stButton button:hover,.stFormSubmitButton button:hover,.stDownloadButton button:hover{
  border-color:rgba(24,119,242,.55)!important;
  color:var(--text-strong)!important;
  transform:translateY(-1px);
  box-shadow:var(--inner),0 16px 36px rgba(24,119,242,.18)!important;
}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]{
  background:linear-gradient(135deg,var(--danger),#ff7a45)!important;
  color:#ffffff!important;
  border-color:rgba(255,255,255,.32)!important;
}
.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox div[data-baseweb="select"]>div{
  border-radius:18px!important;
  border:1px solid var(--line-strong)!important;
  background:var(--input-bg)!important;
  color:var(--text-strong)!important;
  box-shadow:var(--inner),0 10px 30px rgba(0,0,0,.08)!important;
  backdrop-filter:blur(18px) saturate(170%);
  -webkit-backdrop-filter:blur(18px) saturate(170%);
}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:var(--muted)!important;opacity:1!important;}
.stSelectbox [data-baseweb="select"] span{color:var(--text-strong)!important;}
.stTabs [data-baseweb="tab"]{color:var(--muted)!important;border-radius:999px!important;}
.stTabs [aria-selected="true"]{color:var(--primary)!important;background:var(--primary-soft)!important;}
.stCaption,.stCaption *,.stInfo,.stAlert,.stToast{color:var(--text)!important;}
.card,.element-container:has(.stDataFrame){
  background:linear-gradient(145deg,var(--glass-strong),var(--glass-soft));
  border:1px solid var(--line);
  border-radius:22px;
  padding:12px 14px;
  box-shadow:var(--shadow),var(--inner);
  margin:9px 0;
  color:var(--text)!important;
  backdrop-filter:blur(26px) saturate(180%);
  -webkit-backdrop-filter:blur(26px) saturate(180%);
}
.hero{
  position:relative;
  overflow:hidden;
  background:linear-gradient(135deg,var(--glass-strong),var(--glass-soft));
  border:1px solid var(--line);
  border-radius:24px;
  padding:14px 16px;
  box-shadow:var(--shadow),var(--inner);
  margin-bottom:10px;
  color:var(--text)!important;
  backdrop-filter:blur(30px) saturate(190%);
  -webkit-backdrop-filter:blur(30px) saturate(190%);
}
.hero::after{
  content:"";
  position:absolute;
  width:220px;
  height:220px;
  right:-80px;
  top:-90px;
  border-radius:999px;
  background:radial-gradient(circle,rgba(255,255,255,.62),rgba(102,166,255,.20) 45%,transparent 72%);
  filter:blur(4px);
  pointer-events:none;
}
.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:5px 9px;
  border-radius:999px;
  background:linear-gradient(135deg,rgba(255,255,255,.52),var(--primary-soft));
  border:1px solid var(--line);
  color:var(--primary)!important;
  font-size:.72rem;
  font-weight:800;
  margin-right:8px;
  box-shadow:var(--inner);
}

.admin-badge{
  display:inline-flex;
  align-items:center;
  margin-left:5px;
  padding:2px 7px;
  border-radius:999px;
  background:linear-gradient(135deg,#facc15,#fb923c);
  color:#111827!important;
  font-size:.68rem;
  font-weight:900;
  letter-spacing:.02em;
  text-transform:uppercase;
  box-shadow:0 8px 18px rgba(0,0,0,.14),var(--inner);
}

.muted{color:var(--muted)!important;font-size:.84rem;line-height:1.38;margin:.15rem 0 0;}
.danger-box{
  background:linear-gradient(135deg,var(--danger-soft),var(--glass-soft));
  border:1px solid rgba(255,107,99,.46);
  border-radius:18px;
  padding:10px 12px;
  margin:8px 0;
  color:var(--text)!important;
  box-shadow:var(--inner),0 16px 36px rgba(255,59,48,.10);
  backdrop-filter:blur(22px) saturate(180%);
  -webkit-backdrop-filter:blur(22px) saturate(180%);
}
hr{border-color:var(--line)!important;}
/* v13 compact layout: reduce vertical scroll */
.block-container{max-width:780px!important;padding:.45rem .65rem .8rem!important;}
[data-testid="stVerticalBlock"]{gap:.32rem!important;}
[data-testid="stHorizontalBlock"]{gap:.35rem!important;}
.hero{padding:9px 12px!important;margin-bottom:5px!important;border-radius:20px!important;}
.hero h1{font-size:1.18rem!important;line-height:1.1!important;display:inline-block;margin-left:4px!important;}
.hero .muted{display:inline;margin-left:6px!important;font-size:.76rem!important;}
.badge{padding:3px 7px!important;font-size:.66rem!important;margin-right:4px!important;}
.card{padding:8px 10px!important;margin:5px 0!important;border-radius:18px!important;}
.danger-box{padding:8px 10px!important;margin:5px 0!important;}
[data-testid="stExpander"] summary{padding:.38rem .65rem!important;font-size:.88rem!important;}
.stTabs [data-baseweb="tab"]{height:34px!important;padding:.2rem .65rem!important;font-size:.86rem!important;}
.stButton button,.stFormSubmitButton button,.stDownloadButton button{min-height:34px!important;padding:.28rem .7rem!important;}
.stTextInput input,.stTextArea textarea,.stNumberInput input{min-height:34px!important;}
[data-testid="stWidgetLabel"]{font-size:.82rem!important;}
.stMarkdown p{margin-bottom:.2rem!important;}
</style>
"""

CHAT_CSS = """
<style>
:root{
  color-scheme: light;
  --chat-bg:rgba(255,255,255,.46);
  --bubble:rgba(255,255,255,.64);
  --bubble-text:#102033;
  --me:linear-gradient(135deg,#1877f2,#7c3aed);
  --me-text:#ffffff;
  --muted:#506176;
  --line:rgba(255,255,255,.68);
  --line-strong:rgba(120,145,180,.34);
  --empty:#506176;
  --shadow:0 20px 55px rgba(31,70,130,.16);
  --inner:inset 0 1px 0 rgba(255,255,255,.70);
}
@media (prefers-color-scheme: dark){
  :root{
    color-scheme: dark;
    --chat-bg:rgba(15,23,42,.45);
    --bubble:rgba(23,31,52,.70);
    --bubble-text:#eef5ff;
    --me:linear-gradient(135deg,#2563eb,#9333ea);
    --me-text:#ffffff;
    --muted:#bfcbdd;
    --line:rgba(255,255,255,.15);
    --line-strong:rgba(255,255,255,.20);
    --empty:#bfcbdd;
    --shadow:0 20px 60px rgba(0,0,0,.36);
    --inner:inset 0 1px 0 rgba(255,255,255,.16);
  }
}
html,body{margin:0;background:transparent;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:var(--bubble-text);}
.chat{
  height:315px;
  overflow-y:auto;
  padding:11px;
  background:
    radial-gradient(circle at 8% 0%, rgba(24,119,242,.16), transparent 26%),
    radial-gradient(circle at 92% 10%, rgba(192,132,252,.18), transparent 28%),
    var(--chat-bg);
  border:1px solid var(--line);
  border-radius:22px;
  box-sizing:border-box;
  box-shadow:var(--shadow),var(--inner);
  backdrop-filter:blur(26px) saturate(180%);
  -webkit-backdrop-filter:blur(26px) saturate(180%);
}
.row{display:flex;margin:0 0 8px 0;}
.row.me{justify-content:flex-end;}
.bubble{
  max-width:76%;
  padding:9px 11px;
  border-radius:18px;
  background:var(--bubble);
  color:var(--bubble-text);
  border:1px solid var(--line-strong);
  overflow-wrap:anywhere;
  line-height:1.43;
  box-shadow:var(--inner),0 10px 28px rgba(0,0,0,.09);
  backdrop-filter:blur(18px) saturate(180%);
  -webkit-backdrop-filter:blur(18px) saturate(180%);
}
.bubble small{color:var(--muted);}
.row.me .bubble{background:var(--me);color:var(--me-text);border-color:rgba(255,255,255,.28);}
.row.me .bubble small{color:rgba(255,255,255,.86);}
.meta{font-size:10px;color:var(--muted);margin-top:4px;}
.row.me .meta{color:rgba(255,255,255,.80);}
.admin-badge{display:inline-flex;align-items:center;margin-left:5px;padding:1px 6px;border-radius:999px;background:linear-gradient(135deg,#facc15,#fb923c);color:#111827!important;font-size:9px;font-weight:900;letter-spacing:.02em;text-transform:uppercase;box-shadow:0 4px 12px rgba(0,0,0,.18);}
.row.me .admin-badge{background:rgba(255,255,255,.92);color:#111827!important;}
.empty{height:100%;display:flex;align-items:center;justify-content:center;color:var(--empty);text-align:center;}
.packet{display:block;font-weight:800;margin-bottom:4px;color:inherit;}
.thumb{max-width:min(220px,100%);max-height:150px;border-radius:18px;border:1px solid var(--line);object-fit:contain;display:block;margin-top:8px;background:rgba(255,255,255,.55);box-shadow:0 12px 30px rgba(0,0,0,.12);}

.pin,.secret,.poll,.checklist,.location{display:block;font-weight:800;margin-bottom:4px;color:inherit;}
.reactions{margin-top:6px;font-size:12px;opacity:.92;}
.expire{font-size:10px;opacity:.75;margin-top:3px;}
.pinned-card{border:1px solid var(--line);border-radius:16px;padding:8px 10px;margin:0 0 9px 0;background:rgba(250,204,21,.16);color:var(--bubble-text);}
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


def parse_destroy_choice(choice: str) -> int:
    minutes = int(choice.split()[0])
    return min(max(1, minutes), ROOM_MAX_TTL_MINUTES)


def choice_from_minutes(minutes: int | None) -> str:
    if minutes is None:
        return f"{DEFAULT_DESTROY_MINUTES} menit"
    return f"{int(minutes)} menit"


def clean_room_name(room: str) -> str:
    clean = " ".join(room.strip().split())[:80]
    return clean


def normalize_display_name(name: str) -> str:
    return " ".join(str(name or "").strip().split())


def canonical_display_name(name: str) -> str:
    return normalize_display_name(name).casefold()


def is_reserved_display_name(name: str) -> bool:
    return canonical_display_name(name) in RESERVED_DISPLAY_NAMES


def validate_display_name(name: str, *, is_admin: bool = False, field_label: str = "Nama pengguna") -> str | None:
    cleaned = normalize_display_name(name)[:40]
    if not cleaned:
        st.warning(f"{field_label} tidak boleh kosong.")
        return None
    if is_reserved_display_name(cleaned) and not is_admin:
        st.error("Nama adioranye dan Galuh Adi Insani hanya boleh digunakan setelah login admin.")
        return None
    return cleaned


def render_admin_login_box(*, success_username: str | None = None, context: str = "nama khusus") -> bool:
    """Render login admin inline. Return True after admin login succeeds."""
    admin_password = get_secret("CHAT_ADMIN_PASSWORD", "")
    st.warning(f"{context} membutuhkan login admin terlebih dahulu.")
    if not admin_password:
        st.error("CHAT_ADMIN_PASSWORD belum diset di Streamlit Secrets atau environment variable.")
        st.code('CHAT_ADMIN_PASSWORD = "password-yang-kuat"\nFERNET_KEY = "hasil-generate-fernet-key"')
        return False
    with st.form("reserved-name-admin-login"):
        password = st.text_input("Password admin", type="password")
        submitted = st.form_submit_button("Login admin untuk lanjut chat", use_container_width=True)
    if not submitted:
        return False
    if hmac.compare_digest(password, admin_password):
        st.session_state["admin_ok"] = True
        if success_username:
            st.session_state["username"] = success_username
            st.session_state.pop("pending_reserved_username", None)
        st.success("Login admin berhasil. Nama khusus sudah aktif.")
        st.rerun()
        return True
    st.error("Password admin salah.")
    return False


def username_with_badge_html(username: str) -> str:
    safe = html.escape(normalize_display_name(username))
    if is_reserved_display_name(username):
        return f'{safe} <span class="admin-badge">Admin</span>'
    return safe


def get_locked_username(is_admin: bool = False) -> str | None:
    locked = normalize_display_name(st.session_state.get("username", ""))[:40]
    if locked:
        if is_reserved_display_name(locked) and not st.session_state.get("admin_ok"):
            render_admin_login_box(success_username=locked, context=f"Nama {locked}")
            return None
        st.markdown(f'Nama pengguna terkunci: <b>{username_with_badge_html(locked)}</b>', unsafe_allow_html=True)
        return locked

    pending_reserved = normalize_display_name(st.session_state.get("pending_reserved_username", ""))[:40]
    if pending_reserved and is_reserved_display_name(pending_reserved) and not st.session_state.get("admin_ok"):
        render_admin_login_box(success_username=pending_reserved, context=f"Nama {pending_reserved}")
        if st.button("Gunakan nama lain", use_container_width=True):
            st.session_state.pop("pending_reserved_username", None)
            st.rerun()
        return None

    with st.form("lock-username-form"):
        raw_name = st.text_input("Nama pengguna", placeholder="contoh: Ng4D1miN", max_chars=40)
        submitted = st.form_submit_button("Tetapkan nama pengguna", use_container_width=True)
    if not submitted:
        st.info("Isi dan tetapkan nama pengguna untuk masuk ke room. Setelah ditetapkan, nama tidak bisa diubah selama sesi ini.")
        return None

    cleaned = normalize_display_name(raw_name)[:40]
    if not cleaned:
        st.warning("Nama pengguna tidak boleh kosong.")
        return None
    if is_reserved_display_name(cleaned) and not st.session_state.get("admin_ok"):
        st.session_state["pending_reserved_username"] = cleaned
        st.rerun()
        return None

    username = validate_display_name(cleaned, is_admin=bool(st.session_state.get("admin_ok")))
    if username is None:
        return None
    st.session_state["username"] = username
    st.success("Nama pengguna sudah ditetapkan dan dikunci.")
    st.rerun()
    return username


def clamp_minutes(value: int, maximum: int = ROOM_MAX_TTL_MINUTES) -> int:
    return min(max(1, int(value)), int(maximum))


def get_room_config(room: str) -> dict[str, Any]:
    settings = load_json(ROOM_SETTINGS_FILE)
    key = room_key(room)
    config = settings.get(key, {}) if isinstance(settings.get(key), dict) else {}
    created_at = int(config.get("created_at", now_epoch()))
    expires_at = int(config.get("expires_at", created_at + ROOM_DEFAULT_TTL_MINUTES * 60))
    minutes = config.get("auto_destroy_minutes", DEFAULT_DESTROY_MINUTES)
    if minutes not in {5, 10, 20, 30, 60}:
        minutes = DEFAULT_DESTROY_MINUTES
    return {
        "room_key": key,
        "room_cipher": config.get("room_cipher", encrypt_text(room)),
        "created_by": config.get("created_by", ""),
        "created_at": created_at,
        "expires_at": expires_at,
        "auto_destroy_minutes": int(minutes),
        "last_active_at": int(config.get("last_active_at", now_epoch())),
        "destroyed_at": int(config.get("destroyed_at", 0)),
        "pinned_message_id": str(config.get("pinned_message_id", "") or ""),
    }


def save_room_config(room: str, config: dict[str, Any]) -> None:
    settings = load_json(ROOM_SETTINGS_FILE)
    settings[room_key(room)] = config
    atomic_write_json(ROOM_SETTINGS_FILE, settings)


def ensure_room_config(room: str, lifetime_minutes: int = ROOM_DEFAULT_TTL_MINUTES, created_by: str = "") -> dict[str, Any]:
    room = clean_room_name(room)
    settings = load_json(ROOM_SETTINGS_FILE)
    key = room_key(room)
    existing = settings.get(key)
    now = now_epoch()
    if isinstance(existing, dict) and int(existing.get("expires_at", 0)) > now and not existing.get("destroyed_at"):
        config = get_room_config(room)
        if not config.get("room_cipher"):
            config["room_cipher"] = encrypt_text(room)
        settings[key] = config
        atomic_write_json(ROOM_SETTINGS_FILE, settings)
        return config
    lifetime_minutes = clamp_minutes(lifetime_minutes, ROOM_MAX_TTL_MINUTES)
    config = {
        "room_key": key,
        "room_cipher": encrypt_text(room),
        "created_by": encrypt_text(created_by.strip()[:80]) if created_by else "",
        "created_at": now,
        "expires_at": now + lifetime_minutes * 60,
        "auto_destroy_minutes": min(DEFAULT_DESTROY_MINUTES, lifetime_minutes),
        "last_active_at": now,
        "destroyed_at": 0,
    }
    settings[key] = config
    atomic_write_json(ROOM_SETTINGS_FILE, settings)
    return config


def room_seconds_left(room: str) -> int:
    config = get_room_config(room)
    return max(0, int(config.get("expires_at", 0)) - now_epoch())


def room_is_expired(room: str) -> bool:
    return room_seconds_left(room) <= 0


def mark_room_active(room: str) -> None:
    config = get_room_config(room)
    if int(config.get("expires_at", 0)) <= now_epoch():
        destroy_room_and_revoke(room)
        return
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


def revoke_room_invites_by_key(key: str) -> int:
    invites = load_json(INVITE_FILE)
    changed = False
    revoked = 0
    for item in invites.values():
        if not isinstance(item, dict) or item.get("revoked"):
            continue
        if item.get("room_key") == key:
            item["revoked"] = True
            item["revoked_at"] = now_epoch()
            revoked += 1
            changed = True
    if changed:
        atomic_write_json(INVITE_FILE, invites)
    return revoked


def purge_inactive_rooms() -> int:
    rooms = load_json(CHAT_FILE)
    online = load_json(ONLINE_FILE)
    settings = load_json(ROOM_SETTINGS_FILE)
    now = now_epoch()
    destroyed = 0
    changed = False

    for key, config in list(settings.items()):
        if not isinstance(config, dict):
            settings.pop(key, None)
            changed = True
            continue
        active = {u: int(ts) for u, ts in online.get(key, {}).items() if now - int(ts) <= ONLINE_ACTIVE_SECONDS}
        online[key] = active
        expires_at = int(config.get("expires_at", now + ROOM_DEFAULT_TTL_MINUTES * 60))
        minutes = int(config.get("auto_destroy_minutes", DEFAULT_DESTROY_MINUTES))
        should_destroy = expires_at <= now
        if not should_destroy and not active:
            last_active = int(config.get("last_active_at", now))
            should_destroy = now - last_active >= minutes * 60
        if should_destroy:
            rooms.pop(key, None)
            online.pop(key, None)
            settings.pop(key, None)
            shutil.rmtree(PACKET_DIR / key, ignore_errors=True)
            revoke_room_invites_by_key(key)
            destroyed += 1
            changed = True
            continue
        if active:
            config["last_active_at"] = now
            settings[key] = config
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


def append_text(room: str, username: str, text: str, ttl_seconds: int = 0) -> None:
    clean = text.strip()[:MAX_TEXT_LENGTH]
    if not clean:
        return
    rooms = load_json(CHAT_FILE)
    key = room_key(room)
    rooms.setdefault(key, [])
    now = now_epoch()
    message = {
        "id": secrets.token_urlsafe(18),
        "type": "text",
        "username": username,
        "text": encrypt_text(clean),
        "time": now_wib_label(),
        "created_at": now,
        "expires_at": now + int(ttl_seconds) if int(ttl_seconds or 0) > 0 else 0,
        "reactions": {},
    }
    rooms[key].append(message)
    atomic_write_json(CHAT_FILE, rooms)
    mark_room_active(room)


def append_special_message(room: str, username: str, msg_type: str, payload: dict[str, Any], ttl_seconds: int = 0) -> None:
    rooms = load_json(CHAT_FILE)
    key = room_key(room)
    rooms.setdefault(key, [])
    now = now_epoch()
    message: dict[str, Any] = {
        "id": secrets.token_urlsafe(18),
        "type": msg_type,
        "username": username,
        "time": now_wib_label(),
        "created_at": now,
        "expires_at": now + int(ttl_seconds) if int(ttl_seconds or 0) > 0 else 0,
        "reactions": {},
    }
    message.update(payload)
    rooms[key].append(message)
    atomic_write_json(CHAT_FILE, rooms)
    mark_room_active(room)


def message_summary(msg: dict[str, Any]) -> str:
    msg_type = str(msg.get("type", "text"))
    sender = normalize_display_name(str(msg.get("username", "unknown")))
    if msg_type == "text":
        body = decrypt_text(str(msg.get("text", "")))[:42]
    elif msg_type in {"secret_note", "one_time"}:
        body = decrypt_text(str(msg.get("text", "")))[:42]
    elif msg_type == "poll":
        body = decrypt_text(str(msg.get("question", "")))[:42]
    elif msg_type == "checklist":
        body = decrypt_text(str(msg.get("title", "Checklist")))[:42]
    elif msg_type == "location":
        body = decrypt_text(str(msg.get("label", "Location")))[:42]
    else:
        body = str(msg.get("filename", msg_type))[:42]
    return f"{sender} · {msg_type} · {body}"


def purge_expired_messages(room: str) -> int:
    rooms = load_json(CHAT_FILE)
    key = room_key(room)
    messages = rooms.get(key, [])
    if not isinstance(messages, list):
        return 0
    now = now_epoch()
    kept = []
    removed = 0
    removed_packet_paths = []
    for msg in messages:
        expires_at = int(msg.get("expires_at", 0) or 0)
        if expires_at and expires_at <= now:
            removed += 1
            if msg.get("packet_path"):
                removed_packet_paths.append(str(msg.get("packet_path")))
            continue
        kept.append(msg)
    if removed:
        rooms[key] = kept
        atomic_write_json(CHAT_FILE, rooms)
        for rel in removed_packet_paths:
            path = resolve_packet_path(rel)
            if path:
                try:
                    path.unlink()
                except Exception:
                    pass
    return removed


def remove_message(room: str, message_id: str) -> bool:
    rooms = load_json(CHAT_FILE)
    key = room_key(room)
    messages = rooms.get(key, [])
    if not isinstance(messages, list):
        return False
    new_messages = [m for m in messages if str(m.get("id")) != message_id]
    if len(new_messages) == len(messages):
        return False
    rooms[key] = new_messages
    atomic_write_json(CHAT_FILE, rooms)
    mark_room_active(room)
    return True


def update_message(room: str, message_id: str, updater) -> bool:
    rooms = load_json(CHAT_FILE)
    key = room_key(room)
    messages = rooms.get(key, [])
    if not isinstance(messages, list):
        return False
    changed = False
    for msg in messages:
        if str(msg.get("id")) == message_id:
            updater(msg)
            changed = True
            break
    if changed:
        rooms[key] = messages
        atomic_write_json(CHAT_FILE, rooms)
        mark_room_active(room)
    return changed


def add_reaction(room: str, message_id: str, username: str, emoji: str) -> bool:
    if emoji not in REACTION_CHOICES:
        return False
    def _update(msg: dict[str, Any]) -> None:
        reactions = msg.get("reactions") if isinstance(msg.get("reactions"), dict) else {}
        users = reactions.get(emoji) if isinstance(reactions.get(emoji), list) else []
        if username in users:
            users.remove(username)
        else:
            users.append(username)
        reactions[emoji] = users
        msg["reactions"] = reactions
    return update_message(room, message_id, _update)


def set_pinned_message(room: str, message_id: str | None) -> None:
    config = get_room_config(room)
    config["pinned_message_id"] = message_id or ""
    save_room_config(room, config)


def update_poll_vote(room: str, message_id: str, username: str, option: str) -> bool:
    def _update(msg: dict[str, Any]) -> None:
        votes = msg.get("votes") if isinstance(msg.get("votes"), dict) else {}
        votes[username] = option
        msg["votes"] = votes
    return update_message(room, message_id, _update)


def update_checklist_item(room: str, message_id: str, index: int, checked: bool) -> bool:
    def _update(msg: dict[str, Any]) -> None:
        state = msg.get("checked") if isinstance(msg.get("checked"), dict) else {}
        state[str(index)] = bool(checked)
        msg["checked"] = state
    return update_message(room, message_id, _update)


def room_status_label(room: str, active_count: int) -> str:
    left = room_seconds_left(room)
    if left <= 0:
        return "Revoked"
    if left <= 300:
        return "Closing soon"
    if active_count > 0:
        return "Active"
    return "Waiting"


def reaction_html(msg: dict[str, Any]) -> str:
    reactions = msg.get("reactions") if isinstance(msg.get("reactions"), dict) else {}
    parts = []
    for emoji in REACTION_CHOICES:
        users = reactions.get(emoji)
        if isinstance(users, list) and users:
            parts.append(f"{html.escape(emoji)} {len(set(users))}")
    return f'<div class="reactions">{" · ".join(parts)}</div>' if parts else ""


def expire_html(msg: dict[str, Any]) -> str:
    expires_at = int(msg.get("expires_at", 0) or 0)
    if not expires_at:
        return ""
    left = max(0, expires_at - now_epoch())
    return f'<div class="expire">self-destruct {format_countdown(left)}</div>'


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
    purge_expired_messages(room)
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



def revoke_room_invites(room: str) -> int:
    invites = load_json(INVITE_FILE)
    changed = False
    revoked = 0
    key = room_key(room)
    for item in invites.values():
        if not isinstance(item, dict) or item.get("revoked"):
            continue
        stored_room = decrypt_text(str(item.get("room", ""))).strip()
        if item.get("room_key") == key or stored_room == room:
            item["revoked"] = True
            item["revoked_at"] = now_epoch()
            revoked += 1
            changed = True
    if changed:
        atomic_write_json(INVITE_FILE, invites)
    return revoked


def destroy_room_and_revoke(room: str) -> tuple[int, int]:
    rooms = load_json(CHAT_FILE)
    online = load_json(ONLINE_FILE)
    settings = load_json(ROOM_SETTINGS_FILE)
    key = room_key(room)
    count = len(rooms.get(key, [])) if isinstance(rooms.get(key), list) else 0
    rooms.pop(key, None)
    online.pop(key, None)
    settings.pop(key, None)
    atomic_write_json(CHAT_FILE, rooms)
    atomic_write_json(ONLINE_FILE, online)
    atomic_write_json(ROOM_SETTINGS_FILE, settings)
    delete_room_packets(room)
    revoked = revoke_room_invites(room)
    return count, revoked


def token_hash(token: str) -> str:
    return hmac_digest(token)


def create_invite(room: str, ttl_minutes: int = INVITE_DEFAULT_TTL_MINUTES, created_by: str = "") -> str:
    room = clean_room_name(room)
    config = ensure_room_config(room, ROOM_DEFAULT_TTL_MINUTES, created_by)
    room_left_seconds = max(1, int(config.get("expires_at", now_epoch())) - now_epoch())
    max_ttl_minutes = max(1, min(INVITE_MAX_TTL_MINUTES, (room_left_seconds + 59) // 60))
    ttl_minutes = clamp_minutes(ttl_minutes, max_ttl_minutes)
    token = secrets.token_urlsafe(32)
    invites = load_json(INVITE_FILE)
    invites[token_hash(token)] = {
        "room": encrypt_text(room),
        "room_key": room_key(room),
        "created_by": encrypt_text(created_by.strip()[:80]) if created_by else "",
        "created_at": now_epoch(),
        "expires_at": min(now_epoch() + ttl_minutes * 60, int(config.get("expires_at", now_epoch() + ttl_minutes * 60))),
        "revoked": False,
    }
    atomic_write_json(INVITE_FILE, invites)
    return token


def create_room_with_invite(room: str, lifetime_minutes: int, created_by: str = "") -> str:
    room = clean_room_name(room)
    ensure_room_config(room, clamp_minutes(lifetime_minutes, ROOM_MAX_TTL_MINUTES), created_by)
    return create_invite(room, clamp_minutes(lifetime_minutes, INVITE_MAX_TTL_MINUTES), created_by)


def get_invite_item(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    invites = load_json(INVITE_FILE)
    item = invites.get(token_hash(token))
    return item if isinstance(item, dict) else None


def invite_seconds_left(token: str | None) -> int:
    item = get_invite_item(token)
    if not item or item.get("revoked"):
        return 0
    return max(0, int(item.get("expires_at", 0)) - now_epoch())


def clear_invite_display(*keys: str) -> None:
    """Remove expired invite UI state so links disappear immediately."""
    for key in keys:
        st.session_state.pop(key, None)


def force_landing_on_expired_invite() -> None:
    """Clear invite query/state and return to the landing page."""
    clear_invite_display(
        "room_invite_url", "room_invite_token",
        "public_invite_url", "public_invite_token", "public_room",
        "last_invite", "last_invite_token", "last_room",
    )
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()


def render_expiring_invite_link(
    *,
    url_key: str,
    token_key: str,
    room_key: str | None = None,
    input_key: str,
    label: str = "Sisa waktu link",
) -> bool:
    """Render invite link only while it is active. Returns True when visible."""
    invite_url = st.session_state.get(url_key)
    token = st.session_state.get(token_key)
    if not invite_url or not token:
        return False
    left = invite_seconds_left(token)
    if left <= 0:
        keys = [url_key, token_key]
        if room_key:
            keys.append(room_key)
        clear_invite_display(*keys)
        st.toast("Invite link sudah habis dan disembunyikan.")
        st.rerun()
    room_name = st.session_state.get(room_key) if room_key else None
    st.text_input("Invite link", value=invite_url, key=input_key)
    render_whatsapp_share(invite_url, room_name)
    with st.expander("QR Invite", expanded=False):
        render_qr_invite(invite_url)
    render_countdown(label, left)
    if st_autorefresh is not None:
        st_autorefresh(interval=1000, limit=max(1, min(left + 2, 3700)), key=f"{token_key}_expire_tick")
    return True


def format_countdown(seconds: int) -> str:
    seconds = max(0, int(seconds))
    minutes, sec = divmod(seconds, 60)
    return f"{minutes:02d}:{sec:02d}"


def render_countdown(label: str, seconds_left: int) -> None:
    safe_label = html.escape(label)
    components.html(
        f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;border:1px solid rgba(255,255,255,.22);border-radius:15px;padding:5px 8px;background:rgba(255,255,255,.10);backdrop-filter:blur(18px);color:inherit">
          <div style="font-size:10px;opacity:.72;margin-bottom:0">{safe_label}</div>
          <div id="countdown" style="font-size:16px;font-weight:800;letter-spacing:-.04em">{format_countdown(seconds_left)}</div>
        </div>
        <script>
          let left = {max(0, int(seconds_left))};
          const el = document.getElementById('countdown');
          function tick() {{
            const m = Math.floor(left / 60).toString().padStart(2, '0');
            const s = (left % 60).toString().padStart(2, '0');
            el.textContent = `${{m}}:${{s}}`;
            if (left > 0) left -= 1;
          }}
          tick(); setInterval(tick, 1000);
        </script>
        """,
        height=43,
    )


def resolve_invite(token: str | None) -> str | None:
    if not token:
        return None
    invites = load_json(INVITE_FILE)
    h = token_hash(token)
    item = invites.get(h)
    if not isinstance(item, dict) or item.get("revoked"):
        return None
    if int(item.get("expires_at", 0)) <= now_epoch():
        item["revoked"] = True
        item["revoked_at"] = now_epoch()
        invites[h] = item
        atomic_write_json(INVITE_FILE, invites)
        return None
    room = clean_room_name(decrypt_text(str(item.get("room", ""))).strip())
    if not room:
        return None
    if room_is_expired(room):
        destroy_room_and_revoke(room)
        return None
    return room


def public_base_url() -> str:
    configured = get_secret("PUBLIC_APP_URL", "").strip().rstrip("/")
    return configured or "http://localhost:8501"


def build_invite_url(token: str) -> str:
    return f"{public_base_url()}?{urlencode({'invite': token})}"


def build_whatsapp_share_url(invite_url: str, room: str | None = None) -> str:
    room_label = f" untuk room {room}" if room else ""
    text = (
        f"Masuk ke AntiTrust{room_label}: {invite_url}\n\n"
        "Catatan: link dan room bersifat sementara, maksimal aktif 60 menit."
    )
    return "https://wa.me/?" + urlencode({"text": text})


def render_whatsapp_share(invite_url: str, room: str | None = None) -> None:
    if not invite_url:
        return
    st.link_button("Share WhatsApp", build_whatsapp_share_url(invite_url, room), use_container_width=True)


def make_qr_png(data: str) -> bytes | None:
    if not data or qrcode is None:
        return None
    try:
        img = qrcode.make(data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def render_qr_invite(invite_url: str) -> None:
    png = make_qr_png(invite_url)
    if png is None:
        st.caption("QR invite membutuhkan package qrcode. Install requirements.txt versi terbaru.")
        return
    st.image(png, caption="QR Invite", width=180)
    st.download_button("Download QR", data=png, file_name="antitrust-invite-qr.png", mime="image/png", use_container_width=True)


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
    pinned = [m for m in messages if m.get("_pinned")]
    for msg in messages[-120:]:
        raw_sender = str(msg.get("username", "unknown"))
        sender = html.escape(raw_sender)
        sender_label = username_with_badge_html(raw_sender)
        is_me = sender == html.escape(username)
        time_label = html.escape(str(msg.get("time", "")))
        msg_type = str(msg.get("type", "text"))
        if msg_type == "text":
            content = html.escape(decrypt_text(str(msg.get("text", ""))))
        elif msg_type == "secret_note":
            content = '<span class="secret">🔒 Secret Note</span><small>Buka lewat panel Fitur.</small>'
        elif msg_type == "one_time":
            content = '<span class="secret">👁️ One-Time Message</span><small>Buka sekali lewat panel Fitur, lalu pesan terhapus.</small>'
        elif msg_type == "poll":
            question = html.escape(decrypt_text(str(msg.get("question", ""))))
            votes = msg.get("votes") if isinstance(msg.get("votes"), dict) else {}
            options = msg.get("options") if isinstance(msg.get("options"), list) else []
            counts = []
            for opt_token in options:
                opt = decrypt_text(str(opt_token))
                total = sum(1 for v in votes.values() if v == opt)
                counts.append(f"{html.escape(opt)}: {total}")
            content = f'<span class="poll">📊 Poll</span>{question}<br><small>{" · ".join(counts)}</small>'
        elif msg_type == "location":
            label = html.escape(decrypt_text(str(msg.get("label", "Lokasi"))))
            url = html.escape(decrypt_text(str(msg.get("url", ""))), quote=True)
            content = f'<span class="location">📍 Location Pin</span><a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
        elif msg_type == "checklist":
            title = html.escape(decrypt_text(str(msg.get("title", "Checklist"))))
            items = msg.get("items") if isinstance(msg.get("items"), list) else []
            checked = msg.get("checked") if isinstance(msg.get("checked"), dict) else {}
            done = sum(1 for i in range(len(items)) if checked.get(str(i)))
            content = f'<span class="checklist">☑️ Checklist</span>{title}<br><small>{done}/{len(items)} selesai · kelola lewat panel Fitur</small>'
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
        content += reaction_html(msg) + expire_html(msg)
        pin = ' 📌' if msg.get("_pinned") else ''
        cls = "row me" if is_me else "row"
        rows += f'<div class="{cls}"><div class="bubble">{content}<div class="meta">{sender_label}{" · kamu" if is_me else ""}{pin} · {time_label}</div></div></div>'
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
        st.markdown("**Packet Viewer**")
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
        ttl = st.slider("Masa aktif room & invite link", min_value=1, max_value=ROOM_MAX_TTL_MINUTES, value=ROOM_DEFAULT_TTL_MINUTES, help="Maksimal 1 jam. Saat waktu habis, room otomatis dihancurkan dan semua invite link direvoke.")
        if st.button("Buat room + invite link", use_container_width=True):
            room = clean_room_name(room)
            if not room:
                st.warning("Nama room tidak boleh kosong.")
            else:
                token = create_room_with_invite(room, int(ttl), "admin")
                st.session_state["last_invite"] = build_invite_url(token)
                st.session_state["last_invite_token"] = token
                st.session_state["last_room"] = room
                st.success("Room dan invite link berhasil dibuat.")
        if render_expiring_invite_link(
            url_key="last_invite",
            token_key="last_invite_token",
            room_key="last_room",
            input_key="admin_invite_box",
            label="Sisa waktu link",
        ):
            if st.session_state.get("last_room"):
                render_countdown("Sisa waktu room", room_seconds_left(st.session_state.get("last_room")))
        if st.button("Logout admin", use_container_width=True):
            st.session_state.pop("admin_ok", None)
            st.rerun()


def render_public_room_creator() -> None:
    with st.container(border=True):
        st.subheader("Buat room")
        st.caption("Maksimal 60 menit. Auto revoke saat waktu habis.")
        col_a, col_b = st.columns(2)
        with col_a:
            creator = st.text_input("Nama pembuat", placeholder="User", key="creator_name")
        with col_b:
            room = st.text_input("Nama room", placeholder="kelas-private-01", key="public_room_name")
        ttl = st.slider("Durasi room", min_value=1, max_value=ROOM_MAX_TTL_MINUTES, value=ROOM_DEFAULT_TTL_MINUTES, help="Maksimal 60 menit.", key="public_room_ttl")
        if st.button("Create room + link", use_container_width=True):
            room = clean_room_name(room)
            if not room:
                st.warning("Nama room tidak boleh kosong.")
                return
            creator_name = validate_display_name(creator or "public", is_admin=bool(st.session_state.get("admin_ok")), field_label="Nama pembuat")
            if creator_name is None:
                return
            token = create_room_with_invite(room, int(ttl), creator_name)
            st.session_state["public_invite_url"] = build_invite_url(token)
            st.session_state["public_invite_token"] = token
            st.session_state["public_room"] = room
            st.success("Room berhasil dibuat.")
        if st.session_state.get("public_invite_url"):
            left = invite_seconds_left(st.session_state.get("public_invite_token"))
            if left <= 0:
                clear_invite_display("public_invite_url", "public_invite_token", "public_room")
                st.toast("Invite link sudah habis dan halaman kembali ke awal.")
                st.rerun()
            col1, col2 = st.columns(2)
            with col1:
                render_expiring_invite_link(
                    url_key="public_invite_url",
                    token_key="public_invite_token",
                    room_key="public_room",
                    input_key="public_invite_box",
                    label="Sisa waktu link",
                )
            with col2:
                render_countdown("Sisa waktu room", room_seconds_left(st.session_state.get("public_room")))


def render_landing() -> None:
    st.markdown('<div class="hero"><span class="badge">🔐 secure</span><span class="badge">60 menit</span><span class="badge">auto revoke</span><h1>AntiTrust</h1><p class="muted">Room terenkripsi sementara. Share link, auto revoke.</p></div>', unsafe_allow_html=True)
    st.caption("Gunakanlah dengan bijak")
    render_public_room_creator()
    with st.expander("Admin panel", expanded=False):
        render_admin_panel()


def render_sidebar() -> tuple[bool, int, bool]:
    st.sidebar.title("🔐 AntiTrust")
    auto_refresh = st.sidebar.toggle("Auto refresh", value=True)
    interval = st.sidebar.selectbox("Interval", [3, 5, 10, 15], index=1)
    sound = st.sidebar.toggle("Suara pesan baru", value=True)
    st.sidebar.caption("Secrets/env only.")
    return auto_refresh, interval, sound


def render_room_invite_panel(room: str, username: str) -> None:
    with st.expander("Invite", expanded=False):
        room_left = room_seconds_left(room)
        max_link_minutes = max(1, min(INVITE_MAX_TTL_MINUTES, (room_left + 59) // 60))
        st.caption("Semua user bisa buat link. Maksimal mengikuti sisa waktu room.")
        ttl = st.slider("Masa aktif link", min_value=1, max_value=max_link_minutes, value=min(30, max_link_minutes), key="room_invite_ttl")
        if st.button("Create link", use_container_width=True):
            if room_is_expired(room):
                destroy_room_and_revoke(room)
                st.error("Room sudah kedaluwarsa dan direvoke.")
                st.rerun()
            token = create_invite(room, int(ttl), username)
            st.session_state["room_invite_url"] = build_invite_url(token)
            st.session_state["room_invite_token"] = token
            st.success("Invite link dibuat.")
        if st.session_state.get("room_invite_url"):
            render_expiring_invite_link(
                url_key="room_invite_url",
                token_key="room_invite_token",
                input_key="room_invite_url_box",
                label="Sisa waktu invite link",
            )


def clear_destroy_countdown() -> None:
    for key in ("destroy_pending_room", "destroy_countdown_until"):
        st.session_state.pop(key, None)


def render_room_actions(room: str, username: str) -> None:
    with st.expander("Aksi", expanded=False):
        st.caption("Keluar room dinonaktifkan agar identitas tidak bisa direset.")

        pending_room = st.session_state.get("destroy_pending_room")
        countdown_until = int(st.session_state.get("destroy_countdown_until", 0) or 0)

        if pending_room == room and countdown_until:
            remaining = max(0, countdown_until - now_epoch())
            if remaining > 0:
                st.warning(f"Room akan dihancurkan dalam {remaining} detik. Tekan cancel untuk membatalkan.")
                st.progress(max(0.0, min(1.0, (3 - remaining) / 3)))
                if st.button("Cancel destroy", use_container_width=True):
                    clear_destroy_countdown()
                    st.info("Destroy room dibatalkan.")
                    st.rerun()
                if st_autorefresh:
                    st_autorefresh(interval=1000, limit=4, key="destroy_room_countdown_tick")
                else:
                    components.html("<script>setTimeout(function(){window.parent.location.reload();},1000);</script>", height=0)
                return

            count, revoked = destroy_room_and_revoke(room)
            clear_destroy_countdown()
            st.session_state.pop("room_invite_url", None)
            st.session_state.pop("room_invite_token", None)
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.success(f"Room dihancurkan. {count} pesan/packet dihapus dan {revoked} invite link direvoke.")
            st.rerun()

        confirm = st.checkbox("Saya paham: room, pesan, packet, dan invite link akan dihancurkan", key="destroy_room_confirm")
        if st.button("Hancurkan room + revoke key", type="primary", use_container_width=True, disabled=not confirm):
            st.session_state["destroy_pending_room"] = room
            st.session_state["destroy_countdown_until"] = now_epoch() + 3
            st.rerun()


def render_room_settings(room: str) -> None:
    config = get_room_config(room)
    current = choice_from_minutes(config.get("auto_destroy_minutes"))
    with st.expander("Pengaturan"):
        st.caption("Opsional: percepat destroy jika room kosong.")
        choice = st.selectbox("Auto-destroy jika room kosong", AUTO_DESTROY_CHOICES, index=AUTO_DESTROY_CHOICES.index(current) if current in AUTO_DESTROY_CHOICES else 3)
        if st.button("Simpan pengaturan", use_container_width=True):
            config["auto_destroy_minutes"] = parse_destroy_choice(choice)
            save_room_config(room, config)
            st.success("Pengaturan disimpan.")


def render_panic(room: str) -> None:
    st.markdown('<div class="danger-box"><b>Panic Destroy</b> <span class="muted">hapus semua pesan/packet room aktif.</span></div>', unsafe_allow_html=True)
    confirm = st.checkbox("Saya paham tindakan ini menghapus pesan room aktif")
    if st.button("Panic destroy sekarang", type="primary", use_container_width=True, disabled=not confirm):
        count = panic_destroy(room)
        st.success(f"Berhasil menghapus {count} pesan/packet.")
        st.rerun()


def prepare_messages_for_render(room: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pinned_id = get_room_config(room).get("pinned_message_id", "")
    prepared = []
    for msg in messages:
        copy_msg = dict(msg)
        copy_msg["_pinned"] = bool(pinned_id and str(copy_msg.get("id")) == pinned_id)
        prepared.append(copy_msg)
    return prepared


def render_pinned_message(room: str, messages: list[dict[str, Any]]) -> None:
    pinned_id = get_room_config(room).get("pinned_message_id", "")
    if not pinned_id:
        return
    msg = next((m for m in messages if str(m.get("id")) == pinned_id), None)
    if not msg:
        set_pinned_message(room, "")
        return
    st.markdown(f'<div class="card"><b>📌 Pinned</b><br><span class="muted">{html.escape(message_summary(msg))}</span></div>', unsafe_allow_html=True)


def render_feature_panel(room: str, username: str, messages: list[dict[str, Any]]) -> None:
    with st.expander("Fitur", expanded=False):
        tab_secret, tab_poll, tab_check, tab_react, tab_pin = st.tabs(["Secret", "Poll", "Checklist", "React", "Pin"])
        with tab_secret:
            secret_messages = [m for m in messages if str(m.get("type")) in {"secret_note", "one_time"}]
            if not secret_messages:
                st.caption("Belum ada Secret Note atau One-Time Message.")
            else:
                msg_map = {str(m.get("id")): m for m in reversed(secret_messages)}
                selected = st.selectbox("Pilih pesan rahasia", list(msg_map.keys()), format_func=lambda mid: message_summary(msg_map[mid]), key="secret_select")
                if st.button("Buka pesan", use_container_width=True, key="open_secret_btn"):
                    msg = msg_map[selected]
                    st.session_state["opened_secret_text"] = decrypt_text(str(msg.get("text", "")))
                    st.session_state["opened_secret_type"] = str(msg.get("type"))
                    st.session_state["opened_secret_id"] = selected
                    if str(msg.get("type")) == "one_time":
                        remove_message(room, selected)
                if st.session_state.get("opened_secret_text"):
                    st.info(st.session_state.get("opened_secret_text"))
                    if st.session_state.get("opened_secret_type") == "one_time":
                        st.caption("One-Time Message sudah dihapus dari room setelah dibuka.")
        with tab_poll:
            polls = [m for m in messages if str(m.get("type")) == "poll"]
            if not polls:
                st.caption("Belum ada poll.")
            else:
                poll_map = {str(m.get("id")): m for m in reversed(polls)}
                selected_poll = st.selectbox("Pilih poll", list(poll_map.keys()), format_func=lambda mid: message_summary(poll_map[mid]), key="poll_select")
                msg = poll_map[selected_poll]
                question = decrypt_text(str(msg.get("question", "")))
                options = [decrypt_text(str(x)) for x in msg.get("options", []) if isinstance(x, str)]
                votes = msg.get("votes") if isinstance(msg.get("votes"), dict) else {}
                st.write(f"**{question}**")
                selected_option = st.radio("Vote", options, index=options.index(votes.get(username)) if votes.get(username) in options else 0, key="poll_vote_radio") if options else None
                if st.button("Simpan vote", use_container_width=True, key="save_vote_btn") and selected_option:
                    update_poll_vote(room, selected_poll, username, selected_option)
                    st.rerun()
                for option in options:
                    total = sum(1 for v in votes.values() if v == option)
                    st.caption(f"{option}: {total} vote")
        with tab_check:
            lists = [m for m in messages if str(m.get("type")) == "checklist"]
            if not lists:
                st.caption("Belum ada checklist.")
            else:
                list_map = {str(m.get("id")): m for m in reversed(lists)}
                selected_list = st.selectbox("Pilih checklist", list(list_map.keys()), format_func=lambda mid: message_summary(list_map[mid]), key="check_select")
                msg = list_map[selected_list]
                st.write(f"**{decrypt_text(str(msg.get('title', 'Checklist')))}**")
                items = [decrypt_text(str(x)) for x in msg.get("items", []) if isinstance(x, str)]
                state = msg.get("checked") if isinstance(msg.get("checked"), dict) else {}
                for i, item in enumerate(items):
                    checked = st.checkbox(item, value=bool(state.get(str(i))), key=f"check_{selected_list}_{i}")
                    if bool(state.get(str(i))) != checked:
                        update_checklist_item(room, selected_list, i, checked)
                        st.rerun()
        with tab_react:
            if not messages:
                st.caption("Belum ada pesan.")
            else:
                msg_map = {str(m.get("id")): m for m in reversed(messages)}
                selected_msg = st.selectbox("Pilih pesan", list(msg_map.keys()), format_func=lambda mid: message_summary(msg_map[mid]), key="react_select")
                emoji = st.radio("Reaction", REACTION_CHOICES, horizontal=True, key="react_emoji")
                if st.button("Toggle reaction", use_container_width=True, key="react_btn"):
                    add_reaction(room, selected_msg, username, emoji)
                    st.rerun()
        with tab_pin:
            if not messages:
                st.caption("Belum ada pesan.")
            else:
                msg_map = {str(m.get("id")): m for m in reversed(messages)}
                selected_pin = st.selectbox("Pilih pesan untuk pin", list(msg_map.keys()), format_func=lambda mid: message_summary(msg_map[mid]), key="pin_select")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Pin", use_container_width=True, key="pin_btn"):
                        set_pinned_message(room, selected_pin)
                        st.rerun()
                with col_b:
                    if st.button("Unpin", use_container_width=True, key="unpin_btn"):
                        set_pinned_message(room, "")
                        st.rerun()


def render_message_form(room: str, username: str) -> None:
    with st.container(border=True):
        st.markdown("**Kirim**")
        ttl_label = st.selectbox("Self-destruct pesan", list(MESSAGE_SELF_DESTRUCT_CHOICES.keys()), index=0, key="message_ttl")
        ttl_seconds = int(MESSAGE_SELF_DESTRUCT_CHOICES.get(ttl_label, 0))
        tab_text, tab_special, tab_img, tab_voice, tab_doc = st.tabs(["Text", "Secret", "Image", "Voice", "Doc"])
        with tab_text:
            with st.form("text-message", clear_on_submit=True):
                message = st.text_area("Pesan", placeholder="Tulis pesan terenkripsi...", height=52, max_chars=MAX_TEXT_LENGTH)
                submitted = st.form_submit_button("Kirim", use_container_width=True)
                if submitted:
                    if not rate_limited("text"):
                        append_text(room, username, message, ttl_seconds)
                        st.rerun()
        with tab_special:
            kind = st.selectbox("Jenis", ["Secret Note", "One-Time Message", "Poll Cepat", "Location Pin", "Checklist Bersama"], key="special_kind")
            if kind in {"Secret Note", "One-Time Message"}:
                with st.form("special-secret", clear_on_submit=True):
                    secret_text = st.text_area("Isi", height=58, max_chars=MAX_TEXT_LENGTH)
                    submitted = st.form_submit_button("Kirim secret", use_container_width=True)
                    if submitted and not rate_limited("secret"):
                        msg_type = "secret_note" if kind == "Secret Note" else "one_time"
                        append_special_message(room, username, msg_type, {"text": encrypt_text(secret_text.strip()[:MAX_TEXT_LENGTH])}, ttl_seconds)
                        st.rerun()
            elif kind == "Poll Cepat":
                with st.form("special-poll", clear_on_submit=True):
                    question = st.text_input("Pertanyaan", max_chars=160)
                    options_raw = st.text_area("Opsi, satu baris satu pilihan", height=66, placeholder="18.00\n19.00\n20.00")
                    submitted = st.form_submit_button("Buat poll", use_container_width=True)
                    if submitted and not rate_limited("poll"):
                        options = [line.strip()[:80] for line in options_raw.splitlines() if line.strip()][:6]
                        if not question.strip() or len(options) < 2:
                            st.warning("Poll butuh pertanyaan dan minimal 2 opsi.")
                        else:
                            append_special_message(room, username, "poll", {"question": encrypt_text(question.strip()[:160]), "options": [encrypt_text(o) for o in options], "votes": {}}, ttl_seconds)
                            st.rerun()
            elif kind == "Location Pin":
                with st.form("special-location", clear_on_submit=True):
                    label = st.text_input("Label lokasi", placeholder="Titik ketemu", max_chars=80)
                    url = st.text_input("Link Maps/manual", placeholder="https://maps.google.com/...", max_chars=500)
                    submitted = st.form_submit_button("Kirim lokasi", use_container_width=True)
                    if submitted and not rate_limited("location"):
                        if not url.startswith(("https://", "http://")):
                            st.warning("Masukkan link lokasi yang valid.")
                        else:
                            append_special_message(room, username, "location", {"label": encrypt_text((label or "Lokasi").strip()[:80]), "url": encrypt_text(url.strip()[:500])}, ttl_seconds)
                            st.rerun()
            else:
                with st.form("special-checklist", clear_on_submit=True):
                    title = st.text_input("Judul checklist", placeholder="Koordinasi cepat", max_chars=120)
                    items_raw = st.text_area("Item, satu baris satu tugas", height=72, placeholder="Sudah kirim file\nSudah dibaca\nSudah approve")
                    submitted = st.form_submit_button("Buat checklist", use_container_width=True)
                    if submitted and not rate_limited("checklist"):
                        items = [line.strip()[:120] for line in items_raw.splitlines() if line.strip()][:12]
                        if not items:
                            st.warning("Checklist minimal punya 1 item.")
                        else:
                            append_special_message(room, username, "checklist", {"title": encrypt_text((title or "Checklist").strip()[:120]), "items": [encrypt_text(i) for i in items], "checked": {}}, ttl_seconds)
                            st.rerun()
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


def render_compact_room_panel(room: str, username: str, messages: list[dict[str, Any]]) -> None:
    with st.expander("Panel room", expanded=False):
        tab_invite, tab_features, tab_files, tab_security = st.tabs(["Invite", "Fitur", "File", "Aksi"])
        with tab_invite:
            render_room_invite_panel(room, username)
        with tab_features:
            render_feature_panel(room, username, messages)
        with tab_files:
            render_packet_viewer(room, messages)
        with tab_security:
            render_room_actions(room, username)
            render_room_settings(room)
            render_panic(room)


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
        if invite_token:
            clear_invite_display("room_invite_url", "room_invite_token")
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.toast("Invite link tidak aktif atau sudah habis.")
            st.rerun()
        render_landing()
        return
    if room_is_expired(room):
        destroy_room_and_revoke(room)
        st.error("Room sudah melewati batas waktu 60 menit dan otomatis direvoke.")
        render_landing()
        return

    current_invite_left = invite_seconds_left(invite_token)
    if current_invite_left <= 0:
        st.toast("Invite link sudah habis. Kembali ke halaman awal.")
        force_landing_on_expired_invite()

    st.markdown('<div class="hero"><span class="badge">🔐 aktif</span><span class="badge">60 menit</span><span class="badge">auto revoke</span><h1>AntiTrust Room</h1></div>', unsafe_allow_html=True)
    col_timer1, col_timer2 = st.columns(2)
    with col_timer1:
        render_countdown("Sisa waktu room", room_seconds_left(room))
    with col_timer2:
        render_countdown("Sisa waktu invite link", current_invite_left)
    if st_autorefresh is not None:
        st_autorefresh(interval=1000, limit=max(1, min(current_invite_left + 2, 3700)), key="active_invite_expire_tick")
    username = get_locked_username(is_admin=bool(st.session_state.get("admin_ok")))
    if not username:
        return

    if room_is_expired(room):
        destroy_room_and_revoke(room)
        st.error("Room sudah kedaluwarsa dan otomatis direvoke.")
        st.rerun()
    active_users = update_online(room, username)
    messages = load_messages(room)
    config = get_room_config(room)
    status = room_status_label(room, len(active_users))
    st.markdown(f'<span class="muted">{username_with_badge_html(username)} · status: {html.escape(status)} · {len(active_users)} aktif · sisa {format_countdown(room_seconds_left(room))} · kosong: {choice_from_minutes(config.get("auto_destroy_minutes"))}</span>', unsafe_allow_html=True)
    render_sound_notice(latest_foreign_signature(messages, username), sound)
    render_pinned_message(room, messages)
    render_compact_room_panel(room, username, messages)
    render_messages = prepare_messages_for_render(room, messages)
    components.html(render_chat(render_messages, username), height=333, scrolling=False)
    render_message_form(room, username)


if __name__ == "__main__":
    main()
