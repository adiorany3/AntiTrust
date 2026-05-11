import base64
import hashlib
import hmac
import html
import io
import json
import math
import os
import shutil
import struct
import time
import uuid
import wave
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet

try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 24_000_000
except Exception:
    Image = None

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

# ==============================
# CONFIG
# ==============================
APP_TITLE = "AntiTrust Terminal"
APP_ICON = "🟢"
PUBLIC_APP_URL = "https://antitrust.streamlit.app"

FERNET_KEY_FILE = "fernet.key"
CHAT_FILE = "chat_rooms.json"
ONLINE_FILE = "online_status.json"
ROOM_SETTINGS_FILE = "room_settings.json"
PRIVATE_LINKS_FILE = "private_links.json"
PACKET_DIR = "secure_packets"
SKULL_IMAGE_FILE = "assets/skull.svg"

WIB = timezone(timedelta(hours=7))
ONLINE_ACTIVE_SECONDS = 20
DEFAULT_AUTO_DESTROY_MINUTES = 30
AUTO_DESTROY_CHOICES = ["Never", "10 menit", "20 menit", "30 menit", "40 menit", "50 menit", "60 menit"]
MAX_MEDIA_BYTES = 25 * 1024 * 1024
THUMBNAIL_MAX_SIZE = (220, 220)

ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
ALLOWED_AUDIO_TYPES = ["wav", "mp3", "ogg", "m4a", "aac", "flac", "webm"]
ALLOWED_DOCUMENT_TYPES = ["pdf", "docx", "xlsx", "pptx"]
DOCUMENT_MIME_BY_EXT = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

SHELL_SIGNATURES = [
    b"#!/bin/sh",
    b"#!/bin/bash",
    b"#!/usr/bin/env sh",
    b"#!/usr/bin/env bash",
    b"#!/usr/bin/env zsh",
    b"powershell",
    b"@echo off",
]
SHELL_KEYWORDS = [
    b"rm -rf",
    b"chmod +x",
    b"curl ",
    b"wget ",
    b"nc ",
    b"netcat",
    b"bash -i",
    b"/bin/bash",
    b"/bin/sh",
    b"subprocess",
    b"eval(",
    b"exec(",
]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
:root {
  --green: #00ff66;
  --green-soft: #8cffae;
  --line: rgba(0,255,102,.55);
  --danger: #ff335c;
  --cyan: #00ddff;
  --panel: #020b04;
  --panel2: #001604;
}
#MainMenu, footer, header { visibility: hidden; }
.stApp {
  background: #000;
  color: var(--green);
  font-family: 'Share Tech Mono', monospace;
}
.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(to bottom, rgba(0,255,102,.035) 0, rgba(0,255,102,.035) 1px, transparent 2px, transparent 5px);
  opacity: .42;
  z-index: 9999;
}
.stApp::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  box-shadow: inset 0 0 90px rgba(0,255,102,.13);
  z-index: 9998;
}
.block-container { max-width: 900px; padding: 1.2rem 1rem 2rem 1rem; }
h1, h2, h3, p, label, span, div, button, input, textarea {
  font-family: 'Share Tech Mono', monospace !important;
}
h1, h2, h3 {
  color: var(--green) !important;
  text-shadow: 0 0 8px rgba(0,255,102,.55);
  letter-spacing: 1px;
}
h1 { font-size: 1.55rem !important; border-bottom: 1px solid var(--line); padding-bottom: .45rem; }
h1::before { content: "root@antitrust:~$ "; color: var(--green-soft); }
.terminal-bar, .compact-panel {
  border: 1px solid var(--line);
  background: var(--panel);
  padding: 10px 12px;
  margin: 8px 0 14px 0;
  box-shadow: 0 0 18px rgba(0,255,102,.14);
}
.terminal-line { margin: 0; color: var(--green-soft); font-size: .9rem; }
.terminal-line::before { content: "> "; color: var(--green); }
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea, .stNumberInput input {
  background: #000 !important;
  color: var(--green) !important;
  border: 1px solid var(--line) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: rgba(140,255,174,.5) !important; }
.stFileUploader, .stAudioInput {
  background: var(--panel);
  border: 1px dashed var(--line);
  border-radius: 0;
  padding: 8px;
}
.stButton button, .stFormSubmitButton button, .stDownloadButton button {
  background: #000 !important;
  color: var(--green) !important;
  border: 1px solid var(--green) !important;
  border-radius: 0 !important;
  text-transform: uppercase;
  letter-spacing: .8px;
  box-shadow: none !important;
}
.stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover {
  background: var(--green) !important;
  color: #000 !important;
}
button[kind="primary"] {
  border-color: var(--danger) !important;
  color: var(--danger) !important;
}
button[kind="primary"]:hover { background: var(--danger) !important; color: #000 !important; }
.stAlert {
  background: var(--panel) !important;
  color: var(--green-soft) !important;
  border: 1px solid var(--line) !important;
  border-radius: 0 !important;
}
[data-testid="stSidebar"] { background: #000; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] * { color: var(--green-soft) !important; }
hr { border: none; border-top: 1px dashed var(--line); margin: .9rem 0; }
.panic-panel { border: 1px solid var(--danger); background: rgba(255, 51, 92, .06); padding: 10px 12px; margin: 10px 0; }
.panic-title { color: var(--danger); letter-spacing: 1px; }
.panic-copy { color: #ff9db1; margin: 2px 0 0 0; font-size: .88rem; }
.cursor-blink { display: inline-block; width: 9px; height: 17px; background: var(--green); margin-left: 4px; animation: blink .85s infinite; }
.skull-lock-frame {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  border: 1px solid var(--line);
  padding: 22px 12px;
  margin-top: 18px;
  box-shadow: 0 0 20px rgba(0,255,102,.16);
}
.skull-lock-img {
  display: block;
  width: min(320px, 78vw);
  max-width: 100%;
  height: auto;
  filter: drop-shadow(0 0 10px rgba(0,255,102,.72));
}
.ascii-lock-note { color: rgba(140,255,174,.72); text-align: center; margin-top: 8px; font-size: .9rem; }
@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: var(--green); }
"""

CHAT_COMPONENT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
html, body { margin: 0; padding: 0; background: transparent; font-family: 'Share Tech Mono', monospace; }
.chat-box {
  height: 455px;
  overflow-y: auto;
  box-sizing: border-box;
  background: #000;
  border: 1px solid #00ff66;
  padding: 12px;
  box-shadow: inset 0 0 18px rgba(0,255,102,.12);
}
.chat-line { margin: 0 0 11px 0; }
.chat-bubble {
  border-left: 2px solid #00ff66;
  padding: 7px 9px;
  color: #00ff66;
  background: rgba(0,255,102,.045);
  overflow-wrap: anywhere;
}
.chat-bubble::before { content: "> "; color: #8cffae; }
.chat-bubble.me { border-left-color: #00ddff; color: #8ff3ff; background: rgba(0,221,255,.045); }
.chat-bubble.me::before { content: "$ "; color: #8ff3ff; }
.chat-meta { font-size: 11px; color: rgba(140,255,174,.65); margin-top: 4px; }
.media-label { display: block; color: rgba(140,255,174,.88); font-size: 11px; margin: 0 0 7px 0; letter-spacing: .6px; }
.media-note, .media-placeholder { display: block; color: rgba(140,255,174,.72); font-size: 11px; margin-top: 6px; }
.chat-image { display: block; max-width: min(260px, 100%); max-height: 220px; object-fit: contain; border: 1px solid rgba(0,255,102,.6); background: #000; }
.chat-doc { display: inline-block; border: 1px solid rgba(0,255,102,.7); padding: 7px 10px; color: #00ff66; text-decoration: none; background: rgba(0,255,102,.055); max-width: 100%; overflow-wrap: anywhere; }
.empty-line { color: rgba(140,255,174,.75); margin-top: 10px; }
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #00ff66; }
"""



# ==============================
# STORAGE + CRYPTO HELPERS
# ==============================
def load_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def get_fernet() -> Fernet:
    if not os.path.exists(FERNET_KEY_FILE):
        key = Fernet.generate_key()
        with open(FERNET_KEY_FILE, "wb") as file:
            file.write(key)
    else:
        with open(FERNET_KEY_FILE, "rb") as file:
            key = file.read().strip()
    return Fernet(key)


def encrypt_message(text: str) -> str:
    return get_fernet().encrypt(text.encode("utf-8", errors="ignore")).decode("ascii")


def decrypt_message(text: str) -> str:
    try:
        return get_fernet().decrypt(text.encode("ascii")).decode("utf-8", errors="replace")
    except Exception:
        return "[Pesan tidak dapat didekripsi]"


def encrypt_bytes(data: bytes) -> bytes:
    return get_fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return get_fernet().decrypt(token)


def safe_room_slug(room: str) -> str:
    return hashlib.sha256(room.encode("utf-8", errors="ignore")).hexdigest()[:32]


def packet_room_dir(room: str) -> Path:
    return Path(PACKET_DIR) / safe_room_slug(room)


def save_encrypted_packet(room: str, message_id: str, data: bytes) -> str:
    directory = packet_room_dir(room)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{message_id}.bin"
    path.write_bytes(encrypt_bytes(data))
    return str(path.as_posix())


def resolve_packet_path(packet_path: str) -> Path | None:
    if not packet_path:
        return None
    root = Path(PACKET_DIR).resolve()
    candidate = Path(packet_path)
    if candidate.is_absolute():
        return None
    target = candidate.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def read_encrypted_packet(packet_path: str) -> bytes | None:
    path = resolve_packet_path(packet_path)
    if path is None or not path.exists() or not path.is_file():
        return None
    try:
        return decrypt_bytes(path.read_bytes())
    except Exception:
        return None


def delete_room_packet_files(room: str) -> None:
    directory = packet_room_dir(room)
    if directory.exists():
        shutil.rmtree(directory, ignore_errors=True)


def format_bytes(size: int | str | None) -> str:
    try:
        value = int(size or 0)
    except (TypeError, ValueError):
        value = 0
    units = ["B", "KB", "MB", "GB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def wib_now() -> str:
    return datetime.now(WIB).strftime("%H:%M")


def epoch_now() -> int:
    return int(time.time())

# ==============================
# QUERY + ADMIN SHARE LINK
# ==============================
def get_query_param(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
    except Exception:
        try:
            params = st.experimental_get_query_params()
            value = params.get(name, [""])
        except Exception:
            value = ""
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8", errors="ignore")).hexdigest()


def valid_invite_token(token: str) -> bool:
    if not token or len(token) > 180:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return all(char in allowed for char in token)


def create_room_share_token(room: str) -> str:
    token = secrets_token()
    links = load_json(PRIVATE_LINKS_FILE)
    links[token_hash(token)] = {
        "room": encrypt_message(room),
        "created_at": str(epoch_now()),
        "active": True,
    }
    save_json(PRIVATE_LINKS_FILE, links)
    return token


def secrets_token() -> str:
    # Wrapper so the token generator is easy to harden later.
    import secrets
    return secrets.token_urlsafe(32)


def resolve_room_from_token(token: str) -> str | None:
    if not valid_invite_token(token):
        return None
    links = load_json(PRIVATE_LINKS_FILE)
    link_data = links.get(token_hash(token))
    if not isinstance(link_data, dict):
        return None
    if not link_data.get("active", True):
        return None
    encrypted_room = str(link_data.get("room", ""))
    room = decrypt_message(encrypted_room)
    if not room or room.startswith("[Pesan tidak dapat didekripsi]"):
        return None
    return room


def build_share_url(token: str, public_url: str = "") -> str:
    base_url = (public_url or get_secret("PUBLIC_APP_URL", PUBLIC_APP_URL)).strip().rstrip("/")
    return f"{base_url}/?{urlencode({'invite': token})}"


def render_admin_share_panel() -> None:
    admin_password = get_secret("CHAT_ADMIN_PASSWORD", "")
    public_url = get_secret("PUBLIC_APP_URL", PUBLIC_APP_URL)

    with st.sidebar.expander("admin_share_link", expanded=False):
        if not admin_password:
            st.error("CHAT_ADMIN_PASSWORD belum diset.")
            st.caption("Atur di Streamlit Secrets atau environment variable agar panel admin aktif.")
            st.code('CHAT_ADMIN_PASSWORD = "ganti-password-kuat"\nPUBLIC_APP_URL = "https://antitrust.streamlit.app"', language="toml")
            return

        password = st.text_input("admin_password:", type="password", key="admin_password_input")
        if not hmac.compare_digest(password, admin_password):
            st.caption("Masukkan password admin untuk membuat link room.")
            return

        target_room = st.text_input("target_room:", placeholder="black-room-01", key="admin_target_room_input")
        target_public_url = st.text_input(
            "public_app_url:",
            value=public_url,
            placeholder="https://antitrust.streamlit.app",
            key="admin_public_url_input",
        )

        if st.button("CREATE ROOM SHARE LINK", key="create_room_share_link", use_container_width=True):
            clean_room = target_room.strip()
            if not clean_room:
                st.error("target_room tidak boleh kosong.")
            else:
                token = create_room_share_token(clean_room)
                st.session_state["last_room_share_url"] = build_share_url(token, target_public_url)
                st.success("share_link=created")

        if st.session_state.get("last_room_share_url"):
            st.code(st.session_state["last_room_share_url"], language="text")
            st.caption("Bagikan link ini ke user. Room akan otomatis terkunci sesuai target_room.")

def get_skull_image_data_uri() -> str:
    skull_path = Path(SKULL_IMAGE_FILE)

    if skull_path.exists():
        svg_bytes = skull_path.read_bytes()
    else:
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="skull lock">\n  <rect width="512" height="512" fill="#000000"/>\n  <path d="M256 46C149 46 82 116 82 213c0 62 29 106 77 128v67c0 30 24 54 54 54h86c30 0 54-24 54-54v-67c48-22 77-66 77-128C430 116 363 46 256 46Z" fill="none" stroke="#00ff66" stroke-width="18" stroke-linejoin="round"/>\n  <path d="M178 238c0-29 20-52 46-52s46 23 46 52-20 52-46 52-46-23-46-52Zm108 0c0-29 20-52 46-52s46 23 46 52-20 52-46 52-46-23-46-52Z" fill="#00ff66" fill-opacity="0.88"/>\n  <path d="M256 289l-25 50h50l-25-50Z" fill="none" stroke="#00ff66" stroke-width="16" stroke-linejoin="round"/>\n  <path d="M183 371h146M202 407h108M226 371v72M256 371v72M286 371v72" fill="none" stroke="#00ff66" stroke-width="14" stroke-linecap="round"/>\n  <path d="M87 89l338 338M425 89L87 427" stroke="#00ff66" stroke-width="8" stroke-opacity="0.32"/>\n</svg>'

    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def render_locked_landing() -> None:
    skull_src = get_skull_image_data_uri()
    st.markdown(
        f"""
        <div class="skull-lock-frame">
          <img class="skull-lock-img" src="{skull_src}" alt="locked private channel skull" />
        </div>
        <p class="ascii-lock-note">public_channel=disabled | invite_required=true</p>
        """,
        unsafe_allow_html=True,
    )


# ==============================
# ROOM SETTINGS + AUTO DESTROY
# ==============================
def parse_destroy_choice(choice: str) -> int | None:
    if choice == "Never":
        return None
    return int(choice.split()[0])


def choice_from_minutes(minutes: int | None) -> str:
    if minutes is None:
        return "Never"
    return f"{minutes} menit"


def get_room_config(room: str) -> dict[str, Any]:
    settings = load_json(ROOM_SETTINGS_FILE)
    config = settings.get(room, {})
    mode = config.get("destroy_mode", "auto")
    minutes = config.get("auto_destroy_minutes", DEFAULT_AUTO_DESTROY_MINUTES)
    if mode == "never":
        minutes = None
    elif minutes not in {10, 20, 30, 40, 50, 60}:
        minutes = DEFAULT_AUTO_DESTROY_MINUTES
    return {
        "destroy_mode": "never" if minutes is None else "auto",
        "auto_destroy_minutes": minutes,
        "last_active_at": int(config.get("last_active_at", epoch_now())),
    }


def save_room_config(room: str, config: dict[str, Any]) -> None:
    settings = load_json(ROOM_SETTINGS_FILE)
    settings[room] = config
    save_json(ROOM_SETTINGS_FILE, settings)


def set_room_destroy_choice(room: str, choice: str) -> None:
    config = get_room_config(room)
    minutes = parse_destroy_choice(choice)
    config["destroy_mode"] = "never" if minutes is None else "auto"
    config["auto_destroy_minutes"] = minutes
    config.setdefault("last_active_at", epoch_now())
    save_room_config(room, config)


def mark_room_active(room: str) -> None:
    config = get_room_config(room)
    config["last_active_at"] = epoch_now()
    save_room_config(room, config)


def panic_clear_messages(room: str) -> int:
    rooms = load_json(CHAT_FILE)
    message_count = len(rooms.get(room, [])) if isinstance(rooms.get(room, []), list) else 0
    rooms[room] = []
    delete_room_packet_files(room)
    save_json(CHAT_FILE, rooms)
    mark_room_active(room)
    return message_count


def get_active_users_from_online(online: dict[str, Any], room: str, now: int) -> dict[str, int]:
    active: dict[str, int] = {}
    for user, last_seen in online.get(room, {}).items():
        try:
            last_seen_int = int(last_seen)
        except (TypeError, ValueError):
            continue
        if now - last_seen_int <= ONLINE_ACTIVE_SECONDS:
            active[str(user)] = last_seen_int
    return active


def purge_inactive_rooms() -> list[str]:
    now = epoch_now()
    rooms = load_json(CHAT_FILE)
    online = load_json(ONLINE_FILE)
    settings = load_json(ROOM_SETTINGS_FILE)
    all_rooms = set(rooms.keys()) | set(online.keys()) | set(settings.keys())
    destroyed: list[str] = []
    changed = False

    for room in list(all_rooms):
        config = get_room_config(room)
        minutes = config.get("auto_destroy_minutes")
        active_users = get_active_users_from_online(online, room, now)

        if online.get(room) != active_users:
            online[room] = active_users
            changed = True

        if active_users:
            config["last_active_at"] = now
            settings[room] = config
            changed = True
            continue

        if minutes is None:
            settings[room] = config
            continue

        last_active_at = int(config.get("last_active_at") or now)
        if now - last_active_at >= int(minutes) * 60:
            delete_room_packet_files(room)
            rooms.pop(room, None)
            online.pop(room, None)
            settings.pop(room, None)
            destroyed.append(room)
            changed = True
        else:
            settings[room] = config

    if changed:
        save_json(CHAT_FILE, rooms)
        save_json(ONLINE_FILE, online)
        save_json(ROOM_SETTINGS_FILE, settings)

    return destroyed

# ==============================
# CHAT HELPERS
# ==============================
def make_text_message(username: str, text: str) -> dict[str, str]:
    return {
        "id": str(uuid.uuid4()),
        "type": "text",
        "username": username,
        "text": encrypt_message(text),
        "time": wib_now(),
        "created_at": str(epoch_now()),
    }


def make_image_thumbnail(data: bytes) -> tuple[str, str]:
    if Image is None:
        return "", ""
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.thumbnail(THUMBNAIL_MAX_SIZE)
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=68, optimize=True)
            thumb_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
            return encrypt_message(thumb_b64), "image/jpeg"
    except Exception:
        return "", ""


def make_media_message(
    room: str,
    username: str,
    media_type: str,
    data: bytes,
    mime_type: str,
    filename: str,
) -> dict[str, str]:
    message_id = str(uuid.uuid4())
    packet_path = save_encrypted_packet(room, message_id, data)
    message: dict[str, str] = {
        "id": message_id,
        "type": media_type,
        "username": username,
        "storage": "external",
        "packet_path": packet_path,
        "mime_type": mime_type,
        "filename": filename,
        "size_bytes": str(len(data)),
        "time": wib_now(),
        "created_at": str(epoch_now()),
    }
    if media_type == "image":
        thumbnail_payload, thumbnail_mime = make_image_thumbnail(data)
        if thumbnail_payload:
            message["thumbnail_payload"] = thumbnail_payload
            message["thumbnail_mime"] = thumbnail_mime
    return message


def append_text_message(room: str, username: str, message_text: str) -> None:
    rooms = load_json(CHAT_FILE)
    rooms.setdefault(room, [])
    rooms[room].append(make_text_message(username, message_text))
    save_json(CHAT_FILE, rooms)
    mark_room_active(room)


def append_media_message(room: str, username: str, media_type: str, data: bytes, mime_type: str, filename: str) -> None:
    rooms = load_json(CHAT_FILE)
    rooms.setdefault(room, [])
    rooms[room].append(make_media_message(room, username, media_type, data, mime_type, filename))
    save_json(CHAT_FILE, rooms)
    mark_room_active(room)


def update_online_status(room: str, username: str) -> list[str]:
    online = load_json(ONLINE_FILE)
    now = epoch_now()
    online.setdefault(room, {})
    online[room][username] = now
    save_json(ONLINE_FILE, online)
    mark_room_active(room)
    active_users = get_active_users_from_online(online, room, now)
    return [user for user in active_users.keys() if user != username]

# ==============================
# FILE SECURITY
# ==============================
def get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def detect_image_format(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def is_probably_text_payload(data: bytes) -> bool:
    sample = data[:4096]
    if not sample:
        return False
    printable = sum(1 for byte in sample if byte in b"\t\n\r" or 32 <= byte <= 126)
    return printable / max(len(sample), 1) > 0.85


def looks_like_shell_payload(data: bytes) -> bool:
    sample = data[:4096].lstrip().lower()
    if any(sample.startswith(signature.lower()) for signature in SHELL_SIGNATURES):
        return True
    if not is_probably_text_payload(data):
        return False
    keyword_hits = sum(1 for keyword in SHELL_KEYWORDS if keyword.lower() in sample)
    shell_syntax_hits = sum(token in sample for token in [b"#!/", b"function ", b"; then", b"fi\n", b"for ", b"do\n", b"done\n"])
    return keyword_hits >= 2 or (keyword_hits >= 1 and shell_syntax_hits >= 1)


def security_destroy_for_disguised_image(room: str) -> None:
    deleted_count = panic_clear_messages(room)
    reset_media_packet("image_packet")
    st.error(
        "SECURITY ALERT: Image Packet terdeteksi sebagai file shell/script yang menyamar. "
        f"Payload diblokir dan {deleted_count} pesan di room ini langsung dihancurkan."
    )
    st.stop()


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
                lowered_name = normalized.lower()
                if normalized.startswith("/") or "../" in normalized:
                    return None
                if lowered_name.endswith((".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".exe", ".dll", ".scr", ".vbs")):
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


def validate_document_file(uploaded_file: Any) -> tuple[bytes, str, str] | None:
    if uploaded_file is None:
        st.error("Document Packet belum dipilih.")
        return None
    data = uploaded_file.getvalue()
    if not data:
        st.error("File dokumen kosong atau gagal dibaca.")
        return None
    if len(data) > MAX_MEDIA_BYTES:
        st.error(f"Ukuran dokumen terlalu besar. Maksimal {format_bytes(MAX_MEDIA_BYTES)} per dokumen.")
        return None
    filename = getattr(uploaded_file, "name", "document_packet") or "document_packet"
    extension = get_file_extension(filename)
    if extension not in ALLOWED_DOCUMENT_TYPES:
        st.error("Document Packet hanya menerima PDF, DOCX, XLSX, dan PPTX. File script/shell tidak diizinkan.")
        return None
    if looks_like_shell_payload(data):
        st.error("SECURITY BLOCK: Dokumen terindikasi shell/script. Payload diblokir dan tidak disimpan.")
        return None
    real_format = detect_document_format(data)
    if real_format is None:
        st.error("Document Packet tidak valid. File harus PDF atau Office Open XML asli, bukan file yang menyamar.")
        return None
    if real_format != extension:
        st.error(f"SECURITY BLOCK: Ekstensi .{extension} tidak cocok dengan format asli .{real_format}. Payload diblokir.")
        return None
    return data, DOCUMENT_MIME_BY_EXT[real_format], filename


def validate_media_file(uploaded_file: Any, expected_prefix: str, room: str | None = None) -> tuple[bytes, str, str] | None:
    if uploaded_file is None:
        st.error("File belum dipilih.")
        return None
    data = uploaded_file.getvalue()
    if not data:
        st.error("File kosong atau gagal dibaca.")
        return None
    if len(data) > MAX_MEDIA_BYTES:
        st.error(f"Ukuran file terlalu besar. Maksimal {format_bytes(MAX_MEDIA_BYTES)} per media.")
        return None

    mime_type = getattr(uploaded_file, "type", "") or "application/octet-stream"
    filename = getattr(uploaded_file, "name", "media_payload") or "media_payload"
    extension = get_file_extension(filename)

    if expected_prefix == "image":
        if looks_like_shell_payload(data) and room:
            security_destroy_for_disguised_image(room)
        real_image_format = detect_image_format(data)
        if real_image_format is None:
            st.error("File yang dikirim bukan gambar valid. Payload diblokir dan tidak disimpan.")
            return None
        if extension not in ALLOWED_IMAGE_TYPES:
            st.error("Ekstensi Image Packet harus PNG, JPG, JPEG, atau WEBP.")
            return None
        if Image is not None:
            try:
                with Image.open(io.BytesIO(data)) as image_check:
                    image_check.verify()
            except Exception:
                st.error("Image Packet rusak/tidak valid. Payload diblokir dan tidak disimpan.")
                return None
        mime_type = "image/jpeg" if real_image_format == "jpg" else f"image/{real_image_format}"

    if expected_prefix == "audio":
        if extension not in ALLOWED_AUDIO_TYPES:
            st.error("Voice Packet hanya menerima WAV, MP3, OGG, M4A, AAC, FLAC, atau WEBM.")
            return None
        if not (mime_type.startswith("audio/") or mime_type in {"video/webm", "application/octet-stream"}):
            st.error("File yang dikirim bukan audio valid.")
            return None

    return data, mime_type, filename

# ==============================
# RENDER CHAT + PACKETS
# ==============================
def render_media_payload(msg: dict[str, Any]) -> str:
    msg_type = str(msg.get("type", "text"))
    filename = html.escape(str(msg.get("filename", "media_payload")), quote=True)
    size_label = html.escape(format_bytes(msg.get("size_bytes", 0)))

    if msg_type == "image":
        thumbnail = decrypt_message(str(msg.get("thumbnail_payload", ""))) if msg.get("thumbnail_payload") else ""
        thumbnail_mime = html.escape(str(msg.get("thumbnail_mime", "image/jpeg")), quote=True)
        if thumbnail and not thumbnail.startswith("[Pesan tidak dapat didekripsi]"):
            safe_thumb = html.escape(thumbnail, quote=True)
            preview = f'<img class="chat-image" src="data:{thumbnail_mime};base64,{safe_thumb}" alt="image packet preview" />'
        else:
            preview = '<span class="media-placeholder">thumbnail=not_available</span>'
        return f'<span class="media-label">[IMAGE_PACKET] {filename}</span>{preview}<span class="media-note">size={size_label} | original=packet_viewer</span>'

    if msg_type == "audio":
        return f'<span class="media-label">[VOICE_PACKET] {filename}</span><span class="chat-doc">size={size_label} | playback=packet_viewer</span>'

    if msg_type == "document":
        return f'<span class="media-label">[DOCUMENT_PACKET] {filename}</span><span class="chat-doc">size={size_label} | download=packet_viewer</span>'

    return "[UNKNOWN_PACKET] Format pesan tidak dikenal."


def render_chat_box(messages: list[dict[str, Any]], username: str) -> str:
    if not messages:
        rows = '<p class="empty-line">[EMPTY] Belum ada pesan terenkripsi di room ini.</p>'
    else:
        rows = ""
        for msg in messages:
            msg_user = str(msg.get("username", "unknown"))
            msg_type = str(msg.get("type", "text"))
            is_me = msg_user == username
            css_class = "chat-bubble me" if is_me else "chat-bubble"
            safe_user = html.escape(msg_user)
            safe_time = html.escape(str(msg.get("time", "")))
            if msg_type == "text":
                content = html.escape(decrypt_message(str(msg.get("text", ""))))
            else:
                content = render_media_payload(msg)
            rows += f"""
            <div class="chat-line">
              <div class="{css_class}">{content}</div>
              <div class="chat-meta">{safe_user}{' / you' if is_me else ''} :: {safe_time}</div>
            </div>
            """
    return f"""
    <style>{CHAT_COMPONENT_CSS}</style>
    <div class="chat-box" id="chat-box">{rows}</div>
    <script>
      const box = document.getElementById('chat-box');
      if (box) box.scrollTop = box.scrollHeight;
    </script>
    """


def list_packet_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [msg for msg in messages if str(msg.get("type", "")) in {"image", "audio", "document"}]


def packet_label(msg: dict[str, Any]) -> str:
    msg_type = str(msg.get("type", "packet")).upper()
    filename = str(msg.get("filename", "packet"))
    user = str(msg.get("username", "unknown"))
    timestamp = str(msg.get("time", ""))
    size_label = format_bytes(msg.get("size_bytes", 0))
    return f"[{msg_type}] {filename} | {size_label} | {user} | {timestamp}"


def render_packet_viewer(room: str, messages: list[dict[str, Any]]) -> None:
    packets = list_packet_messages(messages)
    if not packets:
        return

    st.markdown("### ./packet_viewer")
    st.caption("Mode hemat performa: chat hanya memuat metadata + thumbnail kecil. File asli didekripsi saat packet dipilih.")

    indexed_packets = {str(msg.get("id", idx)): msg for idx, msg in enumerate(packets)}
    packet_ids = ["-- pilih packet --"] + list(reversed(list(indexed_packets.keys())))
    selected_id = st.selectbox(
        "open_packet:",
        options=packet_ids,
        format_func=lambda item: item if item == "-- pilih packet --" else packet_label(indexed_packets[item]),
        key=f"packet_viewer_select::{room}",
    )
    if selected_id == "-- pilih packet --":
        return

    selected_msg = indexed_packets[selected_id]
    if st.button("DECRYPT / OPEN SELECTED PACKET", key=f"open_packet_button::{room}"):
        st.session_state[f"opened_packet::{room}"] = selected_id

    opened_id = st.session_state.get(f"opened_packet::{room}")
    if opened_id != selected_id:
        st.info("packet_selected=true | klik DECRYPT / OPEN untuk memuat file asli")
        return

    data = read_encrypted_packet(str(selected_msg.get("packet_path", "")))
    if data is None:
        st.error("packet_error=missing_or_decrypt_failed")
        return

    msg_type = str(selected_msg.get("type", ""))
    mime_type = str(selected_msg.get("mime_type", "application/octet-stream"))
    filename = str(selected_msg.get("filename", "packet.bin"))

    if msg_type == "image":
        st.image(data, caption=f"IMAGE_PACKET :: {filename}", width=360)
    elif msg_type == "audio":
        st.audio(data, format=mime_type)
    elif msg_type == "document":
        st.info(f"DOCUMENT_PACKET siap di-download: {filename}")

    st.download_button(
        label=f"DOWNLOAD {msg_type.upper()} PACKET",
        data=data,
        file_name=filename,
        mime=mime_type,
        key=f"download_packet::{room}::{selected_id}",
    )

# ==============================
# SOUND NOTIFICATION
# ==============================
def latest_foreign_message_signature(messages: list[dict[str, Any]], username: str) -> str:
    for msg in reversed(messages):
        if str(msg.get("username", "")) != username:
            return str(msg.get("id") or f"{msg.get('created_at', '')}:{msg.get('time', '')}:{msg.get('username', '')}")
    return ""


@st.cache_data(show_spinner=False)
def hacker_beep_wav_bytes() -> bytes:
    sample_rate = 44100
    duration = 0.18
    total_samples = int(sample_rate * duration)
    samples: list[int] = []
    for i in range(total_samples):
        t = i / sample_rate
        envelope = min(1.0, t / 0.01) * max(0.0, 1.0 - (t / duration)) ** 2.6
        value = math.sin(2 * math.pi * 1568.0 * t) * 0.55 * envelope
        value += math.sin(2 * math.pi * 2093.0 * t) * 0.18 * envelope
        if t < 0.015:
            value += math.sin(2 * math.pi * 3136.0 * t) * 0.12 * (1.0 - t / 0.015)
        value = max(-1.0, min(1.0, value))
        samples.append(int(value * 32767))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return buffer.getvalue()


def hacker_beep_data_uri() -> str:
    return "data:audio/wav;base64," + base64.b64encode(hacker_beep_wav_bytes()).decode("ascii")


def render_sound_controller(trigger_id: str, enabled: bool) -> None:
    if not enabled:
        return
    trigger_safe = html.escape(trigger_id, quote=True)
    audio_uri = hacker_beep_data_uri()
    components.html(
        f"""
        <div style="font-family: monospace; color:#00ff66; background:#000; border:1px solid #00ff66; padding:6px; font-size:12px;">
          <button id="enable-sound" style="background:#000;color:#00ff66;border:1px solid #00ff66;font-family:monospace;">ENABLE DING</button>
          <span id="sound-state"> sound=browser_locked_until_enabled</span>
        </div>
        <script>
          const KEY = 'antitrust_sound_enabled';
          const trigger = "{trigger_safe}";
          const audioUri = "{audio_uri}";
          const btn = document.getElementById('enable-sound');
          const state = document.getElementById('sound-state');
          function setState(text) {{ if (state) state.textContent = ' ' + text; }}
          function ding() {{
            try {{
              const audio = new Audio(audioUri);
              audio.volume = 0.65;
              audio.play().then(() => setState('sound=armed')).catch(() => setState('sound=blocked_click_enable'));
            }} catch(e) {{ setState('sound=error'); }}
          }}
          if (btn) {{
            btn.onclick = () => {{ localStorage.setItem(KEY, '1'); ding(); }};
          }}
          const last = localStorage.getItem('antitrust_last_trigger') || '';
          if (localStorage.getItem(KEY) === '1') {{
            setState('sound=armed');
            if (trigger && trigger !== last) {{ ding(); }}
          }}
          if (trigger) localStorage.setItem('antitrust_last_trigger', trigger);
        </script>
        """,
        height=44,
    )

# ==============================
# UI HELPERS
# ==============================
def reset_media_packet(key_prefix: str) -> None:
    counter_key = f"{key_prefix}_counter"
    st.session_state[counter_key] = int(st.session_state.get(counter_key, 0)) + 1


def uploader_key(key_prefix: str) -> str:
    return f"{key_prefix}_{st.session_state.get(f'{key_prefix}_counter', 0)}"


def render_sidebar() -> tuple[bool, int, bool]:
    st.sidebar.title("./control")
    auto_refresh_enabled = st.sidebar.toggle("auto_refresh", value=True)
    refresh_seconds = st.sidebar.selectbox("refresh_interval:", options=[2, 3, 5, 10, 15], index=2)
    sound_enabled = st.sidebar.toggle("ding_on_new_message", value=True)
    st.sidebar.caption(f"public_url={get_secret('PUBLIC_APP_URL', PUBLIC_APP_URL)}")
    return auto_refresh_enabled, refresh_seconds, sound_enabled


def render_room_settings(room: str) -> None:
    config = get_room_config(room)
    current_choice = choice_from_minutes(config.get("auto_destroy_minutes"))
    try:
        current_index = AUTO_DESTROY_CHOICES.index(current_choice)
    except ValueError:
        current_index = AUTO_DESTROY_CHOICES.index("30 menit")

    with st.expander("room_destroy_settings", expanded=False):
        choice = st.selectbox(
            "auto_destroy_if_room_empty:",
            AUTO_DESTROY_CHOICES,
            index=current_index,
            help="Pesan room otomatis dihancurkan jika tidak ada user aktif selama durasi ini. Default 30 menit.",
        )
        if st.button("SAVE DESTROY SETTING", use_container_width=True):
            set_room_destroy_choice(room, choice)
            st.success(f"destroy_setting=saved | value={choice}")


def render_panic(room: str) -> None:
    st.markdown(
        """
        <div class="panic-panel">
          <div class="panic-title">PANIC BUTTON // DESTROY ROOM MESSAGES</div>
          <p class="panic-copy">Tekan tombol ini untuk menghancurkan semua pesan dan packet di room aktif.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("PANIC DESTROY NOW", type="primary", use_container_width=True):
        deleted_count = panic_clear_messages(room)
        st.success(f"room_destroyed=true | deleted_messages={deleted_count}")
        st.rerun()


def render_message_input(room: str, username: str) -> None:
    st.markdown("### ./send_packet")
    with st.form(key=f"text_form::{room}::{username}", clear_on_submit=True):
        message_text = st.text_area("message:", placeholder="ketik pesan terenkripsi...", height=82)
        send_text = st.form_submit_button("SEND TEXT PACKET", use_container_width=True)
        if send_text:
            clean_text = message_text.strip()
            if clean_text:
                append_text_message(room, username, clean_text)
                st.rerun()
            else:
                st.warning("message=empty")

    packet_tab, voice_tab, document_tab = st.tabs(["image_packet", "voice_packet", "document_packet"])

    with packet_tab:
        image_file = st.file_uploader(
            "image_packet:",
            type=ALLOWED_IMAGE_TYPES,
            key=uploader_key("image_packet"),
        )
        if st.button("SEND IMAGE PACKET", use_container_width=True, key=f"send_image::{room}"):
            payload = validate_media_file(image_file, "image", room)
            if payload:
                data, mime_type, filename = payload
                append_media_message(room, username, "image", data, mime_type, filename)
                reset_media_packet("image_packet")
                st.success("image_packet=sent | input=cleared")
                st.rerun()

    with voice_tab:
        voice_file = st.file_uploader(
            "voice_packet_file:",
            type=ALLOWED_AUDIO_TYPES,
            key=uploader_key("voice_packet"),
        )
        recorded_voice = None
        if hasattr(st, "audio_input"):
            recorded_voice = st.audio_input("record_voice:", key=uploader_key("record_voice_packet"))
        if st.button("SEND VOICE PACKET", use_container_width=True, key=f"send_voice::{room}"):
            candidate = recorded_voice or voice_file
            payload = validate_media_file(candidate, "audio", room)
            if payload:
                data, mime_type, filename = payload
                append_media_message(room, username, "audio", data, mime_type, filename)
                reset_media_packet("voice_packet")
                reset_media_packet("record_voice_packet")
                st.success("voice_packet=sent | input=cleared")
                st.rerun()

    with document_tab:
        doc_file = st.file_uploader(
            "document_packet:",
            type=ALLOWED_DOCUMENT_TYPES,
            key=uploader_key("document_packet"),
        )
        if st.button("SEND DOCUMENT PACKET", use_container_width=True, key=f"send_document::{room}"):
            payload = validate_document_file(doc_file)
            if payload:
                data, mime_type, filename = payload
                append_media_message(room, username, "document", data, mime_type, filename)
                reset_media_packet("document_packet")
                st.success("document_packet=sent | input=cleared")
                st.rerun()

# ==============================
# APP FLOW
# ==============================
def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

    destroyed_rooms = purge_inactive_rooms()

    st.title(APP_TITLE)
    st.markdown(
        """
        <div class="terminal-bar">
          <p class="terminal-line">encrypted private-room chat | public channel disabled | invite link locked-room mode</p>
          <p class="terminal-line">image/voice/document packets stored encrypted outside chat JSON</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if destroyed_rooms:
        st.warning("auto_destroy_completed=" + ",".join(destroyed_rooms))

    auto_refresh_enabled, refresh_seconds, sound_enabled = render_sidebar()
    render_admin_share_panel()

    if auto_refresh_enabled and st_autorefresh is not None:
        st_autorefresh(interval=refresh_seconds * 1000, key="antitrust_autorefresh")

    invite_token = get_query_param("invite")
    invite_room = resolve_room_from_token(invite_token) if invite_token else None

    if not invite_token:
        render_locked_landing()
        st.stop()

    if not invite_room:
        st.error("invite_link=invalid_or_revoked")
        render_locked_landing()
        st.stop()

    room = invite_room.strip()
    st.markdown(
        f'<div class="compact-panel"><p class="terminal-line">invite_link=active | room=locked | room={html.escape(room)}</p></div>',
        unsafe_allow_html=True,
    )
    username = st.text_input("user:", placeholder="zero_cool")
    username = username.strip() if isinstance(username, str) else ""

    if not username:
        st.info("Isi user untuk masuk ke terminal chat private.")
        return

    active_users = update_online_status(room, username)

    st.markdown("---")
    config = get_room_config(room)
    destroy_label = choice_from_minutes(config.get("auto_destroy_minutes"))
    st.caption(f"room={room} | user={username} | active_peers={len(active_users)} | auto_destroy={destroy_label}")

    render_room_settings(room)
    render_panic(room)

    rooms = load_json(CHAT_FILE)
    messages = rooms.get(room, []) if isinstance(rooms.get(room, []), list) else []

    trigger_id = latest_foreign_message_signature(messages, username)
    render_sound_controller(trigger_id, sound_enabled)

    components.html(render_chat_box(messages, username), height=480, scrolling=False)
    render_packet_viewer(room, messages)
    render_message_input(room, username)


if __name__ == "__main__":
    main()
