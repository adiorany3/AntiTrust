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
from urllib.parse import urlencode, urlparse

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
ADMIN_ROOM_MAX_TTL_MINUTES = 10080  # 7 hari, khusus admin
ADMIN_ROOM_DEFAULT_TTL_MINUTES = 1440  # 24 jam
RESERVED_DISPLAY_NAMES = {"adioranye", "galuh adi insani"}
VIDEO_CALL_PROVIDER = "Google Meet"
DEFAULT_VIDEO_SESSION_NOTE = "Sesi video call mengikuti waktu chat/room aktif. Gunakan countdown room sebagai patokan."
DEFAULT_MAX_PARTICIPANTS = 8
ROOM_MAX_PARTICIPANTS = 20
AUDIT_LOG_LIMIT = 80
PASSWORD_FAIL_LIMIT = 5
PASSWORD_FAIL_BLOCK_SECONDS = 300


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
  color-scheme: dark;
  --app-bg:#020403;
  --app-bg-2:#050b07;
  --terminal:#00ff66;
  --terminal-2:#39ff14;
  --terminal-soft:rgba(0,255,102,.12);
  --terminal-dim:#69d98e;
  --terminal-muted:#7aa886;
  --terminal-cyan:#00e5ff;
  --terminal-amber:#facc15;
  --danger:#ff3b30;
  --danger-soft:rgba(255,59,48,.13);
  --panel:rgba(0,12,5,.88);
  --panel-2:rgba(1,20,9,.78);
  --panel-strong:rgba(0,28,12,.92);
  --line:rgba(0,255,102,.42);
  --line-soft:rgba(0,255,102,.20);
  --input-bg:rgba(0,15,6,.92);
  --text:#d9ffe4;
  --text-strong:#effff3;
  --muted:#8bd6a4;
  --shadow:0 0 36px rgba(0,255,102,.16), inset 0 0 28px rgba(0,255,102,.055);
  --inner:inset 0 1px 0 rgba(140,255,180,.14);
  --mono:'SFMono-Regular','Cascadia Code','Consolas','Liberation Mono','Menlo',monospace;
}

/* Streamlit chrome */
#MainMenu, header, footer {visibility:hidden;}
html,body,.stApp{
  background:#020403!important;
  color:var(--text)!important;
  font-family:var(--mono)!important;
}
.stApp{
  min-height:100vh;
  background:
    radial-gradient(circle at 12% 8%, rgba(0,255,102,.12), transparent 28%),
    radial-gradient(circle at 88% 0%, rgba(0,229,255,.08), transparent 30%),
    radial-gradient(circle at 50% 100%, rgba(0,255,102,.09), transparent 30%),
    linear-gradient(180deg,#020403 0%,#061108 100%)!important;
  overflow:hidden;
}
.stApp::before{
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  z-index:0;
  background:
    linear-gradient(rgba(0,255,102,.065) 1px, transparent 1px),
    linear-gradient(90deg,rgba(0,255,102,.035) 1px, transparent 1px),
    repeating-linear-gradient(0deg,rgba(0,0,0,.25) 0,rgba(0,0,0,.25) 1px,transparent 1px,transparent 4px);
  background-size:42px 42px,42px 42px,100% 4px;
  opacity:.72;
  animation:grid-drift 18s linear infinite;
}
.stApp::after{
  content:"01001010  root@antitrust:~$  encrypted_channel  0xA17F  ACCESS GRANTED  ";
  position:fixed;
  left:0;
  right:0;
  top:0;
  height:24px;
  pointer-events:none;
  z-index:1;
  color:rgba(0,255,102,.38);
  background:rgba(0,0,0,.72);
  border-bottom:1px solid rgba(0,255,102,.28);
  font-family:var(--mono);
  font-size:11px;
  letter-spacing:.08em;
  white-space:nowrap;
  overflow:hidden;
  text-shadow:0 0 9px rgba(0,255,102,.8);
  animation:terminal-marquee 12s linear infinite;
}
@keyframes grid-drift{to{background-position:0 42px,42px 0,0 4px;}}
@keyframes terminal-marquee{0%{text-indent:100%}100%{text-indent:-100%}}

.block-container{
  max-width:860px!important;
  padding:1.6rem .85rem 1.15rem!important;
  position:relative;
  z-index:2;
}
[data-testid="stVerticalBlock"]{gap:.45rem!important;}
[data-testid="stHorizontalBlock"]{gap:.45rem!important;}
[data-testid="column"]{padding-left:.18rem!important;padding-right:.18rem!important;}

html,body,.stApp,.stMarkdown,p,span,label,div,[data-testid="stWidgetLabel"],[data-testid="stMarkdownContainer"]{
  color:var(--text)!important;
  font-family:var(--mono)!important;
}
h1,h2,h3,h4,h5,h6{
  color:var(--text-strong)!important;
  font-family:var(--mono)!important;
  letter-spacing:-.02em;
  text-shadow:0 0 18px rgba(0,255,102,.28);
}
h1{font-size:1.45rem!important;margin:.05rem 0!important;}
a{color:var(--terminal-cyan)!important;text-decoration:none!important;text-shadow:0 0 10px rgba(0,229,255,.42);}
hr{border-color:var(--line-soft)!important;}

/* Sidebar */
[data-testid="stSidebar"]{
  background:
    linear-gradient(rgba(0,255,102,.045) 1px, transparent 1px),
    linear-gradient(180deg,rgba(0,13,6,.96),rgba(0,0,0,.94))!important;
  background-size:100% 5px,auto!important;
  border-right:1px solid var(--line)!important;
  box-shadow:10px 0 36px rgba(0,255,102,.08), inset -1px 0 0 rgba(0,255,102,.12)!important;
}
[data-testid="stSidebar"] *{
  color:var(--text)!important;
  font-family:var(--mono)!important;
}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{
  color:var(--terminal)!important;
}

/* Terminal panels */
.card,
.element-container:has(.stDataFrame),
[data-testid="stExpander"]{
  background:
    linear-gradient(rgba(0,255,102,.035) 1px, transparent 1px),
    linear-gradient(180deg,var(--panel),var(--panel-2))!important;
  background-size:100% 4px,auto!important;
  border:1px solid var(--line)!important;
  border-radius:12px!important;
  padding:10px 12px;
  box-shadow:var(--shadow)!important;
  color:var(--text)!important;
  backdrop-filter:none!important;
  -webkit-backdrop-filter:none!important;
}
.card::before{content:"";}
[data-testid="stExpander"] summary{
  padding:.45rem .72rem!important;
  color:var(--terminal)!important;
  font-family:var(--mono)!important;
  text-shadow:0 0 10px rgba(0,255,102,.45);
}
[data-testid="stExpander"] details{
  color:var(--text)!important;
}

/* Hero / landing */
.hero,.terminal-hero{
  position:relative;
  overflow:hidden;
  border:1px solid rgba(0,255,102,.55)!important;
  border-radius:14px!important;
  padding:14px 16px!important;
  margin:6px 0 10px!important;
  background:
    linear-gradient(rgba(0,255,102,.055) 1px, transparent 1px),
    radial-gradient(circle at 16% 0%, rgba(0,255,102,.18), transparent 34%),
    radial-gradient(circle at 88% 20%, rgba(0,229,255,.10), transparent 32%),
    rgba(0,0,0,.90)!important;
  background-size:100% 4px,auto,auto,auto!important;
  color:var(--text)!important;
  box-shadow:0 0 34px rgba(0,255,102,.18), inset 0 0 38px rgba(0,255,102,.06)!important;
  font-family:var(--mono)!important;
}
.hero::before,.terminal-hero::before{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  background:linear-gradient(90deg, transparent, rgba(0,255,102,.10), transparent);
  transform:translateX(-100%);
  animation:terminal-scan 3.2s linear infinite;
}
.hero::after,.terminal-hero::after{
  content:"[SECURE SHELL]";
  position:absolute;
  right:12px;
  top:10px;
  font-size:.65rem;
  color:rgba(0,255,102,.62);
  letter-spacing:.12em;
}
@keyframes terminal-scan{to{transform:translateX(100%);}}
.terminal-kicker{
  font-size:.72rem;
  font-weight:900;
  color:var(--terminal)!important;
  letter-spacing:.08em;
  text-transform:uppercase;
  margin-bottom:6px;
  text-shadow:0 0 12px rgba(0,255,102,.72);
}
.hero h1,.terminal-hero h1{
  font-size:1.55rem!important;
  margin:0!important;
  color:var(--text-strong)!important;
  text-shadow:0 0 20px rgba(0,255,102,.55)!important;
  font-family:var(--mono)!important;
}
.hero .muted,.terminal-hero .muted{
  display:block!important;
  color:var(--terminal-dim)!important;
  opacity:.96;
  font-family:var(--mono)!important;
  font-size:.82rem!important;
  margin-top:5px!important;
}
.terminal-cursor{
  display:inline-block;
  width:9px;
  height:1.05em;
  background:var(--terminal);
  margin-left:5px;
  vertical-align:-2px;
  animation:terminal-blink .85s steps(2,start) infinite;
  box-shadow:0 0 12px rgba(0,255,102,.95);
}
@keyframes terminal-blink{50%{opacity:0;}}

.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:4px 8px;
  border-radius:6px;
  background:rgba(0,255,102,.085)!important;
  border:1px solid rgba(0,255,102,.35)!important;
  color:var(--terminal)!important;
  font-size:.70rem;
  font-weight:900;
  margin-right:6px;
  box-shadow:0 0 18px rgba(0,255,102,.08), inset 0 0 12px rgba(0,255,102,.04);
  text-transform:uppercase;
  letter-spacing:.04em;
}
.admin-badge{
  display:inline-flex;
  align-items:center;
  margin-left:5px;
  padding:2px 7px;
  border-radius:6px;
  background:rgba(250,204,21,.16)!important;
  color:var(--terminal-amber)!important;
  border:1px solid rgba(250,204,21,.42);
  font-size:.66rem;
  font-weight:900;
  letter-spacing:.05em;
  text-transform:uppercase;
  box-shadow:0 0 18px rgba(250,204,21,.16);
}
.muted{
  color:var(--muted)!important;
  font-size:.82rem;
  line-height:1.42;
  margin:.15rem 0 0;
}
.terminal-card{
  border:1px solid rgba(0,255,102,.42)!important;
  border-radius:12px!important;
  padding:11px 14px 13px!important;
  background:
    linear-gradient(rgba(0,255,102,.035) 1px, transparent 1px),
    linear-gradient(180deg,rgba(0,0,0,.86),rgba(0,20,8,.82))!important;
  background-size:100% 4px,auto!important;
  box-shadow:0 0 30px rgba(0,255,102,.11), inset 0 1px 0 rgba(140,255,180,.10)!important;
  color:var(--text)!important;
  margin-top:-8px!important;
  font-family:var(--mono)!important;
}
.terminal-card h3,.terminal-card p,.terminal-card span,.terminal-card label{color:var(--text)!important;}
.terminal-note{
  font-family:var(--mono)!important;
  color:var(--terminal)!important;
  font-size:.78rem;
  margin:-3px 0 7px;
  opacity:.92;
  text-shadow:0 0 10px rgba(0,255,102,.5);
}
.danger-box{
  background:
    linear-gradient(rgba(255,59,48,.05) 1px, transparent 1px),
    linear-gradient(180deg,rgba(26,0,0,.88),rgba(8,0,0,.86))!important;
  border:1px solid rgba(255,59,48,.55)!important;
  border-radius:12px!important;
  padding:10px 12px;
  margin:7px 0;
  color:#ffd9d6!important;
  box-shadow:0 0 26px rgba(255,59,48,.14), inset 0 0 24px rgba(255,59,48,.055)!important;
}

/* Widgets */
.stButton button,.stFormSubmitButton button,.stDownloadButton button{
  border-radius:8px!important;
  border:1px solid rgba(0,255,102,.48)!important;
  background:
    linear-gradient(180deg,rgba(0,34,13,.92),rgba(0,10,4,.96))!important;
  color:var(--terminal)!important;
  box-shadow:0 0 18px rgba(0,255,102,.08), inset 0 0 16px rgba(0,255,102,.04)!important;
  font-family:var(--mono)!important;
  font-weight:900!important;
  letter-spacing:.02em!important;
  text-transform:uppercase!important;
  transition:transform .13s ease,border-color .13s ease,box-shadow .13s ease,background .13s ease!important;
}
.stButton button:hover,.stFormSubmitButton button:hover,.stDownloadButton button:hover{
  border-color:var(--terminal)!important;
  color:#07140b!important;
  background:linear-gradient(180deg,#00ff66,#39ff14)!important;
  transform:translateY(-1px);
  box-shadow:0 0 28px rgba(0,255,102,.32), inset 0 0 14px rgba(255,255,255,.18)!important;
}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]{
  background:linear-gradient(180deg,rgba(255,59,48,.90),rgba(80,0,0,.92))!important;
  color:#fff!important;
  border-color:rgba(255,99,90,.65)!important;
  box-shadow:0 0 24px rgba(255,59,48,.18)!important;
}
.stButton button[kind="primary"]:hover,.stFormSubmitButton button[kind="primary"]:hover{
  background:linear-gradient(180deg,#ff6b63,#ff3b30)!important;
  color:#fff!important;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"]>div,
.stDateInput input,
.stTimeInput input{
  border-radius:8px!important;
  border:1px solid rgba(0,255,102,.38)!important;
  background:var(--input-bg)!important;
  color:var(--terminal)!important;
  box-shadow:0 0 18px rgba(0,255,102,.06), inset 0 0 18px rgba(0,255,102,.04)!important;
  font-family:var(--mono)!important;
  caret-color:var(--terminal)!important;
}
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus{
  border-color:var(--terminal)!important;
  box-shadow:0 0 25px rgba(0,255,102,.20), inset 0 0 18px rgba(0,255,102,.05)!important;
}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{
  color:rgba(0,255,102,.50)!important;
  opacity:1!important;
}
.stSelectbox [data-baseweb="select"] span,
.stMultiSelect [data-baseweb="select"] span{
  color:var(--terminal)!important;
  font-family:var(--mono)!important;
}
[data-baseweb="popover"],[role="listbox"]{
  background:#020903!important;
  border:1px solid var(--line)!important;
  box-shadow:0 0 26px rgba(0,255,102,.16)!important;
}
[role="option"],[data-baseweb="menu"] *{
  color:var(--text)!important;
  background:#020903!important;
  font-family:var(--mono)!important;
}
[role="option"]:hover{
  background:rgba(0,255,102,.14)!important;
  color:var(--terminal)!important;
}
.stCheckbox label,.stRadio label,.stSlider label,.stFileUploader label{
  color:var(--terminal-dim)!important;
  font-family:var(--mono)!important;
}
.stCheckbox [data-testid="stWidgetLabel"],.stRadio [data-testid="stWidgetLabel"]{
  color:var(--terminal)!important;
}
.stSlider [data-baseweb="slider"] div{
  color:var(--terminal)!important;
}
[data-testid="stFileUploader"]{
  border:1px dashed rgba(0,255,102,.38)!important;
  border-radius:10px!important;
  background:rgba(0,12,5,.72)!important;
  box-shadow:inset 0 0 22px rgba(0,255,102,.04)!important;
}
[data-testid="stFileUploader"] *{
  color:var(--text)!important;
  font-family:var(--mono)!important;
}
.stTabs [data-baseweb="tab-list"]{
  gap:6px!important;
  border-bottom:1px solid var(--line-soft)!important;
}
.stTabs [data-baseweb="tab"]{
  color:var(--muted)!important;
  border-radius:8px!important;
  font-family:var(--mono)!important;
  font-weight:900!important;
}
.stTabs [aria-selected="true"]{
  color:var(--terminal)!important;
  background:rgba(0,255,102,.10)!important;
  border:1px solid rgba(0,255,102,.32)!important;
  box-shadow:0 0 18px rgba(0,255,102,.08)!important;
}
.stCaption,.stCaption *,.stInfo,.stAlert,.stToast{
  color:var(--text)!important;
  font-family:var(--mono)!important;
}
[data-testid="stAlert"]{
  background:rgba(0,20,8,.86)!important;
  border:1px solid rgba(0,255,102,.28)!important;
  border-radius:10px!important;
  box-shadow:0 0 20px rgba(0,255,102,.08)!important;
}

/* Dataframe / code / JSON */
pre,code,.stCodeBlock{
  background:#020903!important;
  color:var(--terminal)!important;
  border:1px solid rgba(0,255,102,.32)!important;
  border-radius:8px!important;
  font-family:var(--mono)!important;
  text-shadow:0 0 8px rgba(0,255,102,.28);
}
[data-testid="stDataFrame"]{
  background:#020903!important;
  color:var(--text)!important;
  border:1px solid rgba(0,255,102,.32)!important;
}

/* Online status */
.room-status-line{
  display:flex;
  align-items:center;
  gap:6px;
  flex-wrap:wrap;
  margin:4px 0 2px;
}
.online-strip{
  display:flex;
  gap:6px;
  overflow-x:auto;
  padding:5px 0 2px;
  margin:2px 0 4px;
  scrollbar-width:none;
  -webkit-overflow-scrolling:touch;
}
.online-strip::-webkit-scrollbar{display:none;}
.online-chip{
  flex:0 0 auto;
  display:inline-flex;
  align-items:center;
  gap:6px;
  max-width:210px;
  padding:5px 9px;
  border-radius:8px;
  border:1px solid rgba(0,255,102,.36);
  background:rgba(0,20,8,.82)!important;
  color:var(--text-strong)!important;
  font-size:.74rem;
  font-weight:900;
  white-space:nowrap;
  box-shadow:0 0 18px rgba(0,255,102,.08), inset 0 0 12px rgba(0,255,102,.04);
}
.online-dot{
  width:8px;
  height:8px;
  flex:0 0 auto;
  border-radius:999px;
  background:var(--terminal);
  box-shadow:0 0 0 3px rgba(0,255,102,.18),0 0 12px rgba(0,255,102,.82);
}
.online-me{
  border-color:rgba(0,229,255,.45);
  box-shadow:0 0 22px rgba(0,229,255,.14), inset 0 0 12px rgba(0,255,102,.04);
}
.online-label{
  color:var(--muted)!important;
  font-size:.74rem;
  font-weight:900;
}

/* Scrollbar */
*::-webkit-scrollbar{width:10px;height:10px;}
*::-webkit-scrollbar-track{background:#020403;}
*::-webkit-scrollbar-thumb{
  background:rgba(0,255,102,.30);
  border:2px solid #020403;
  border-radius:999px;
}
*::-webkit-scrollbar-thumb:hover{background:rgba(0,255,102,.52);}

/* Mobile */
iframe[title="st.iframe"]{display:block!important;}
@media (max-width:760px){
  .block-container{max-width:100%!important;padding:1.42rem .42rem .65rem!important;}
  .hero,.terminal-hero{padding:10px 10px!important;border-radius:12px!important;margin-bottom:5px!important;}
  .hero h1,.terminal-hero h1{font-size:1.10rem!important;}
  .hero::after,.terminal-hero::after{display:none;}
  .terminal-kicker{font-size:.60rem!important;}
  .hero .muted,.terminal-hero .muted{font-size:.72rem!important;}
  .badge{font-size:.58rem!important;padding:3px 6px!important;}
  .card,.danger-box,.terminal-card{border-radius:10px!important;padding:8px 9px!important;}
  .muted{font-size:.72rem!important;}
  .room-status-line{gap:4px;margin:2px 0;}
  .online-strip{margin:1px 0 2px;padding:4px 0 1px;}
  .online-chip{font-size:.68rem;padding:4px 7px;max-width:170px;}
  [data-testid="stExpander"] summary{padding:.36rem .56rem!important;font-size:.78rem!important;}
  .stTabs [data-baseweb="tab"]{height:31px!important;padding:.15rem .48rem!important;font-size:.74rem!important;}
  .stButton button,.stFormSubmitButton button,.stDownloadButton button{min-height:32px!important;padding:.22rem .55rem!important;font-size:.74rem!important;}
  .stTextInput input,.stTextArea textarea,.stNumberInput input{min-height:32px!important;font-size:16px!important;}
}
</style>
"""

UI_ENHANCEMENT_CSS = """
<style>
:root{
  color-scheme: dark;
  --ui-bg:#07110d;
  --ui-surface:rgba(13,25,20,.92);
  --ui-surface-2:rgba(20,35,29,.88);
  --ui-card:rgba(18,31,26,.88);
  --ui-card-hover:rgba(25,43,36,.95);
  --ui-border:rgba(126,231,166,.24);
  --ui-border-strong:rgba(126,231,166,.48);
  --ui-accent:#3ee98f;
  --ui-accent-2:#7dd3fc;
  --ui-warning:#facc15;
  --ui-danger:#fb7185;
  --ui-text:#ecfff4;
  --ui-muted:#a8d8bd;
  --ui-soft:#13241d;
  --ui-shadow:0 18px 55px rgba(0,0,0,.32);
  --ui-font:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
}

/* Modern readable shell: tetap gelap dan secure, tapi lebih nyaman dibaca di desktop & HP */
html,body,.stApp,.stMarkdown,p,span,label,div,[data-testid="stWidgetLabel"],[data-testid="stMarkdownContainer"]{
  font-family:var(--ui-font)!important;
  letter-spacing:0!important;
}
h1,h2,h3,h4,h5,h6{
  font-family:var(--ui-font)!important;
  letter-spacing:-.035em!important;
  text-shadow:none!important;
}
.stApp{
  background:
    radial-gradient(circle at top left, rgba(62,233,143,.16), transparent 32%),
    radial-gradient(circle at top right, rgba(125,211,252,.12), transparent 30%),
    linear-gradient(180deg,#07110d 0%,#08130f 48%,#040807 100%)!important;
  overflow:auto!important;
}
.stApp::before{
  opacity:.20!important;
  animation:none!important;
  background:
    linear-gradient(rgba(126,231,166,.10) 1px, transparent 1px),
    linear-gradient(90deg,rgba(126,231,166,.07) 1px, transparent 1px)!important;
  background-size:64px 64px!important;
}
.stApp::after{display:none!important;}
.block-container{
  max-width:1120px!important;
  padding:1.25rem 1rem 1.2rem!important;
}
[data-testid="stVerticalBlock"]{gap:.68rem!important;}
[data-testid="stHorizontalBlock"]{gap:.68rem!important;}

/* Sidebar lebih bersih */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,rgba(12,24,19,.98),rgba(5,10,8,.98))!important;
  border-right:1px solid var(--ui-border)!important;
  box-shadow:8px 0 28px rgba(0,0,0,.22)!important;
}
[data-testid="stSidebar"] *{font-family:var(--ui-font)!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:var(--ui-text)!important;}

/* Landing / hero */
.hero,.terminal-hero{
  border:1px solid var(--ui-border)!important;
  border-radius:24px!important;
  padding:22px 24px!important;
  margin:6px 0 14px!important;
  background:
    radial-gradient(circle at 8% 0%, rgba(62,233,143,.20), transparent 38%),
    radial-gradient(circle at 86% 16%, rgba(125,211,252,.15), transparent 35%),
    linear-gradient(135deg,rgba(20,38,31,.96),rgba(9,17,14,.94))!important;
  box-shadow:var(--ui-shadow)!important;
}
.hero::before,.terminal-hero::before,.hero::after,.terminal-hero::after{display:none!important;}
.terminal-kicker{
  font-family:var(--ui-font)!important;
  color:var(--ui-accent-2)!important;
  font-size:.76rem!important;
  letter-spacing:.06em!important;
  text-shadow:none!important;
}
.hero h1,.terminal-hero h1{
  font-size:clamp(1.7rem,4vw,3rem)!important;
  color:var(--ui-text)!important;
  text-shadow:none!important;
}
.hero .muted,.terminal-hero .muted,.muted{
  color:var(--ui-muted)!important;
  font-size:.92rem!important;
  line-height:1.55!important;
}
.terminal-cursor{
  width:7px!important;
  background:var(--ui-accent)!important;
  box-shadow:0 0 18px rgba(62,233,143,.55)!important;
}
.badge{
  background:rgba(62,233,143,.12)!important;
  border:1px solid rgba(62,233,143,.28)!important;
  color:var(--ui-accent)!important;
  border-radius:999px!important;
  text-transform:none!important;
  letter-spacing:0!important;
  padding:5px 10px!important;
}

/* Kartu, expander, dan kontainer */
.card,.terminal-card,.danger-box,[data-testid="stExpander"],div[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius:18px!important;
  border:1px solid var(--ui-border)!important;
  background:linear-gradient(180deg,var(--ui-surface),rgba(11,20,17,.92))!important;
  box-shadow:0 14px 42px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.04)!important;
}
.terminal-card{padding:18px!important;margin-top:0!important;}
.terminal-note{
  color:var(--ui-accent-2)!important;
  font-family:var(--ui-font)!important;
  text-shadow:none!important;
  font-size:.80rem!important;
}
.danger-box{
  background:linear-gradient(180deg,rgba(69,10,10,.78),rgba(27,6,6,.82))!important;
  border-color:rgba(251,113,133,.42)!important;
}
[data-testid="stExpander"] summary{
  color:var(--ui-text)!important;
  font-family:var(--ui-font)!important;
  text-shadow:none!important;
  font-weight:800!important;
}

/* Komponen khusus yang dipakai app */
.landing-grid{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
  margin:0 0 14px;
}
.feature-card,.status-card,.quick-action-card{
  border:1px solid var(--ui-border);
  border-radius:18px;
  padding:14px 15px;
  background:linear-gradient(180deg,var(--ui-card),rgba(9,17,14,.90));
  box-shadow:0 10px 30px rgba(0,0,0,.22);
}
.feature-card b,.status-card b,.quick-action-card b{
  color:var(--ui-text)!important;
  font-size:.98rem;
}
.feature-card span,.status-card span,.quick-action-card span{
  display:block;
  color:var(--ui-muted)!important;
  font-size:.84rem;
  line-height:1.45;
  margin-top:4px;
}
.room-dashboard{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px;
  margin:6px 0 8px;
}
.status-pill{
  display:inline-flex;
  align-items:center;
  gap:6px;
  border:1px solid var(--ui-border);
  background:rgba(62,233,143,.10);
  color:var(--ui-text)!important;
  border-radius:999px;
  padding:6px 10px;
  font-weight:800;
  font-size:.80rem;
  margin:2px 6px 2px 0;
}
.help-strip{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  align-items:center;
  border:1px solid var(--ui-border);
  background:rgba(125,211,252,.08);
  border-radius:16px;
  padding:10px 12px;
  margin:6px 0;
}
.help-strip span{color:var(--ui-muted)!important;font-size:.85rem;}
.panel-title{
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
  margin-bottom:6px;
}
.panel-title b{font-size:1.05rem;color:var(--ui-text)!important;}
.panel-title span{font-size:.82rem;color:var(--ui-muted)!important;}
.pinned-card{
  border:1px solid rgba(250,204,21,.34);
  background:linear-gradient(180deg,rgba(61,45,12,.78),rgba(24,19,9,.86));
  border-radius:16px;
  padding:11px 13px;
  box-shadow:0 10px 30px rgba(0,0,0,.22);
}
.participant-list{display:grid;gap:8px;margin-top:8px;}
.participant-item{
  display:flex;
  justify-content:space-between;
  gap:10px;
  align-items:center;
  border:1px solid var(--ui-border);
  background:rgba(255,255,255,.045);
  border-radius:14px;
  padding:9px 11px;
}
.participant-item b{color:var(--ui-text)!important;}
.participant-item span{color:var(--ui-muted)!important;font-size:.80rem;}

/* Tombol dan input */
.stButton button,.stFormSubmitButton button,.stDownloadButton button,.stLinkButton a{
  min-height:42px!important;
  border-radius:13px!important;
  border:1px solid rgba(62,233,143,.40)!important;
  background:linear-gradient(180deg,rgba(62,233,143,.18),rgba(24,47,37,.96))!important;
  color:var(--ui-text)!important;
  font-family:var(--ui-font)!important;
  font-weight:800!important;
  text-transform:none!important;
  letter-spacing:0!important;
  box-shadow:0 8px 24px rgba(0,0,0,.22)!important;
}
.stButton button:hover,.stFormSubmitButton button:hover,.stDownloadButton button:hover,.stLinkButton a:hover{
  border-color:rgba(62,233,143,.72)!important;
  background:linear-gradient(180deg,rgba(62,233,143,.30),rgba(30,65,49,.98))!important;
  color:#fff!important;
  transform:translateY(-1px);
}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]{
  background:linear-gradient(180deg,rgba(251,113,133,.92),rgba(136,19,55,.96))!important;
  border-color:rgba(251,113,133,.58)!important;
  color:#fff!important;
}
.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox div[data-baseweb="select"]>div,.stDateInput input,.stTimeInput input{
  min-height:42px!important;
  border-radius:13px!important;
  border:1px solid var(--ui-border)!important;
  background:rgba(4,11,8,.92)!important;
  color:var(--ui-text)!important;
  font-family:var(--ui-font)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03)!important;
}
.stTextArea textarea{line-height:1.45!important;}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:rgba(168,216,189,.68)!important;}
.stSlider [data-baseweb="slider"]{padding-top:.4rem!important;}

/* Tabs mudah dipahami dan bisa discroll di HP */
.stTabs [data-baseweb="tab-list"]{
  gap:8px!important;
  overflow-x:auto!important;
  padding:4px 0 8px!important;
  scrollbar-width:none;
  border-bottom:0!important;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar{display:none;}
.stTabs [data-baseweb="tab"]{
  flex:0 0 auto!important;
  min-height:38px!important;
  padding:.35rem .75rem!important;
  border:1px solid var(--ui-border)!important;
  border-radius:999px!important;
  background:rgba(255,255,255,.045)!important;
  color:var(--ui-muted)!important;
  font-family:var(--ui-font)!important;
  font-size:.88rem!important;
}
.stTabs [aria-selected="true"]{
  color:var(--ui-text)!important;
  background:rgba(62,233,143,.18)!important;
  border-color:rgba(62,233,143,.42)!important;
}

/* Online chips */
.online-strip{
  gap:8px!important;
  padding:8px 0 4px!important;
}
.online-chip{
  border-radius:999px!important;
  background:rgba(255,255,255,.055)!important;
  border-color:var(--ui-border)!important;
  font-family:var(--ui-font)!important;
}
.online-dot{background:var(--ui-accent)!important;box-shadow:0 0 0 3px rgba(62,233,143,.16)!important;}
.room-status-line{margin:6px 0 0!important;}

/* Chat iframe wrapper */
iframe[title="st.iframe"]{
  border-radius:18px!important;
  box-shadow:0 18px 48px rgba(0,0,0,.24)!important;
}

@media (min-width:1100px){
  .block-container{padding-left:2rem!important;padding-right:2rem!important;}
}
@media (max-width:760px){
  .block-container{padding:1rem .62rem .8rem!important;}
  .landing-grid{grid-template-columns:1fr!important;gap:8px!important;}
  .room-dashboard{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;}
  .hero,.terminal-hero{border-radius:18px!important;padding:17px 16px!important;}
  .terminal-hero h1,.hero h1{font-size:1.72rem!important;}
  .terminal-card{padding:14px!important;}
  .feature-card,.status-card,.quick-action-card{padding:12px!important;border-radius:15px!important;}
  .stTabs [data-baseweb="tab"]{font-size:.82rem!important;min-height:36px!important;padding:.30rem .62rem!important;}
  .stButton button,.stFormSubmitButton button,.stDownloadButton button,.stLinkButton a{min-height:40px!important;font-size:.88rem!important;}
  .stTextInput input,.stTextArea textarea,.stNumberInput input{font-size:16px!important;}
  .panel-title{align-items:flex-start;flex-direction:column;gap:2px;}
}
@media (max-width:420px){
  .room-dashboard{grid-template-columns:1fr!important;}
  .badge{font-size:.70rem!important;margin-bottom:4px;}
}
</style>
"""

CHAT_CSS = """
<style>
:root{
  color-scheme: dark;
  --chat-bg:rgba(0,8,4,.86);
  --bubble:rgba(0,22,9,.88);
  --bubble-text:#d9ffe4;
  --me:linear-gradient(180deg,rgba(0,255,102,.24),rgba(0,45,17,.96));
  --me-text:#effff3;
  --muted:#8bd6a4;
  --line:rgba(0,255,102,.40);
  --line-strong:rgba(0,255,102,.55);
  --empty:#69d98e;
  --shadow:0 0 28px rgba(0,255,102,.13), inset 0 0 26px rgba(0,255,102,.05);
  --mono:'SFMono-Regular','Cascadia Code','Consolas','Liberation Mono','Menlo',monospace;
  --terminal:#00ff66;
  --terminal-cyan:#00e5ff;
  --terminal-amber:#facc15;
}
html,body{
  margin:0;
  background:transparent;
  font-family:var(--mono);
  color:var(--bubble-text);
}
.chat{
  height:calc(100vh - 2px);
  min-height:315px;
  overflow-y:auto;
  padding:11px;
  background:
    linear-gradient(rgba(0,255,102,.055) 1px, transparent 1px),
    linear-gradient(90deg,rgba(0,255,102,.030) 1px, transparent 1px),
    repeating-linear-gradient(0deg,rgba(0,0,0,.24) 0,rgba(0,0,0,.24) 1px,transparent 1px,transparent 4px),
    radial-gradient(circle at 8% 0%, rgba(0,255,102,.12), transparent 26%),
    radial-gradient(circle at 92% 10%, rgba(0,229,255,.08), transparent 28%),
    var(--chat-bg);
  background-size:38px 38px,38px 38px,100% 4px,auto,auto,auto;
  border:1px solid var(--line);
  border-radius:12px;
  box-sizing:border-box;
  box-shadow:var(--shadow);
  backdrop-filter:none;
  -webkit-backdrop-filter:none;
  animation:chat-grid 18s linear infinite;
}
@keyframes chat-grid{to{background-position:0 38px,38px 0,0 4px,0 0,0 0,0 0;}}
.row{display:flex;margin:0 0 8px 0;}
.row.me{justify-content:flex-end;}
.row.system-row{justify-content:center;}
.row.system-row .bubble{
  max-width:92%;
  text-align:center;
  background:
    linear-gradient(rgba(255,59,48,.055) 1px, transparent 1px),
    linear-gradient(180deg,rgba(44,6,4,.94),rgba(10,0,0,.90));
  background-size:100% 4px,auto;
  border-color:rgba(255,59,48,.58);
  border-left-color:var(--terminal-amber);
  box-shadow:0 0 24px rgba(255,59,48,.18), inset 0 0 20px rgba(255,59,48,.055);
  color:#ffd9d6;
}
.row.system-row .bubble::before{content:"! ";color:var(--terminal-amber);}
.row.system-row .meta{justify-content:center;color:#ffc5c0;}
.system-dot{
  width:8px;
  height:8px;
  border-radius:999px;
  display:inline-block;
  background:var(--terminal-amber);
  box-shadow:0 0 0 2px rgba(250,204,21,.18),0 0 12px rgba(250,204,21,.82);
}
.system-info{
  display:block;
  font-weight:900;
  margin-bottom:5px;
  color:var(--terminal-amber)!important;
  letter-spacing:.04em;
  text-transform:uppercase;
}
.system-countdown-line{
  display:inline-block;
  margin-top:4px;
  padding:4px 8px;
  border-radius:8px;
  background:rgba(255,59,48,.18);
  border:1px solid rgba(255,59,48,.42);
  font-weight:900;
  color:#fff1ee;
}
.bubble{
  max-width:76%;
  padding:9px 11px;
  border-radius:8px;
  background:
    linear-gradient(rgba(0,255,102,.035) 1px, transparent 1px),
    var(--bubble);
  background-size:100% 4px,auto;
  color:var(--bubble-text);
  border:1px solid rgba(0,255,102,.32);
  border-left:4px solid var(--terminal);
  overflow-wrap:anywhere;
  line-height:1.43;
  box-shadow:0 0 18px rgba(0,255,102,.09), inset 0 0 18px rgba(0,255,102,.045);
  font-family:var(--mono);
  text-shadow:0 0 7px rgba(0,255,102,.14);
}
.bubble::before{
  content:"> ";
  color:var(--terminal);
  font-weight:900;
}
.bubble small{color:var(--muted);}
.row.me .bubble{
  background:
    linear-gradient(rgba(0,255,102,.055) 1px, transparent 1px),
    var(--me);
  background-size:100% 4px,auto;
  color:var(--me-text);
  border-color:rgba(0,255,102,.56);
  border-left-color:var(--terminal-cyan);
  box-shadow:0 0 22px rgba(0,229,255,.11), inset 0 0 18px rgba(0,255,102,.055);
}
.row.me .bubble::before{content:"$ ";color:var(--terminal-cyan);}
.row.me .bubble small{color:rgba(217,255,228,.86);}
.meta{
  font-size:10px;
  color:var(--muted);
  margin-top:5px;
  display:flex;
  align-items:center;
  gap:4px;
  flex-wrap:wrap;
  font-family:var(--mono);
  opacity:.96;
}
.user-dot{
  width:8px;
  height:8px;
  border-radius:999px;
  display:inline-block;
  background:var(--terminal);
  box-shadow:0 0 0 2px rgba(0,255,102,.16),0 0 12px rgba(0,255,102,.82);
}
.row.me .user-dot{
  background:var(--terminal-cyan);
  box-shadow:0 0 0 2px rgba(0,229,255,.16),0 0 12px rgba(0,229,255,.72);
}
.row.me .meta{color:rgba(217,255,228,.82);}
.admin-badge{
  display:inline-flex;
  align-items:center;
  margin-left:5px;
  padding:1px 6px;
  border-radius:6px;
  background:rgba(250,204,21,.16)!important;
  color:var(--terminal-amber)!important;
  border:1px solid rgba(250,204,21,.42);
  font-size:9px;
  font-weight:900;
  letter-spacing:.04em;
  text-transform:uppercase;
  box-shadow:0 0 14px rgba(250,204,21,.16);
}
.row.me .admin-badge{background:rgba(0,0,0,.52)!important;color:var(--terminal-amber)!important;}
.empty{
  height:100%;
  display:flex;
  align-items:center;
  justify-content:center;
  color:var(--empty);
  text-align:center;
  font-family:var(--mono);
  text-shadow:0 0 12px rgba(0,255,102,.28);
}
.empty::before{content:"root@antitrust:~# ";color:var(--terminal);font-weight:900;}
.packet,.pin,.secret,.poll,.checklist,.location,.ping{
  display:block;
  font-weight:900;
  margin-bottom:4px;
  color:var(--terminal)!important;
  letter-spacing:.02em;
}
.ping-card{font-weight:900;letter-spacing:.02em;color:var(--terminal-cyan)!important;}
.reactions{margin-top:7px;font-size:12px;opacity:.95;color:var(--terminal)!important;}
.expire{font-size:10px;opacity:.82;margin-top:4px;color:#ff9a9a!important;}
.pinned-card{
  border:1px solid rgba(250,204,21,.42);
  border-radius:8px;
  padding:8px 10px;
  margin:0 0 9px 0;
  background:rgba(250,204,21,.10);
  color:#fff8ce;
  box-shadow:0 0 18px rgba(250,204,21,.10);
  font-family:var(--mono);
}
.thumb{
  max-width:min(220px,100%);
  max-height:150px;
  border-radius:8px;
  border:1px solid var(--line);
  object-fit:contain;
  display:block;
  margin-top:8px;
  background:#020903;
  box-shadow:0 0 18px rgba(0,255,102,.12);
}
*::-webkit-scrollbar{width:10px;height:10px;}
*::-webkit-scrollbar-track{background:#020403;}
*::-webkit-scrollbar-thumb{
  background:rgba(0,255,102,.30);
  border:2px solid #020403;
  border-radius:999px;
}
*::-webkit-scrollbar-thumb:hover{background:rgba(0,255,102,.52);}
@media (max-width:760px){
  .chat{height:calc(100vh - 2px);min-height:360px;max-height:none;border-radius:10px;padding:8px;}
  .row{margin-bottom:7px;}
  .bubble{max-width:86%;padding:8px 9px;border-radius:8px;font-size:14px;line-height:1.36;}
  .meta{font-size:9px;gap:3px;}
  .thumb{max-height:130px;}
}
</style>
"""

CHAT_UI_CSS = """
<style>
:root{
  --chat-bg:rgba(9,17,14,.94);
  --chat-surface:rgba(18,31,26,.94);
  --chat-border:rgba(126,231,166,.26);
  --chat-accent:#3ee98f;
  --chat-blue:#7dd3fc;
  --chat-text:#ecfff4;
  --chat-muted:#a8d8bd;
  --chat-font:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
}
html,body,.chat,.bubble,.meta{font-family:var(--chat-font)!important;}
.chat{
  min-height:430px!important;
  border-radius:20px!important;
  border:1px solid var(--chat-border)!important;
  background:
    radial-gradient(circle at top left, rgba(62,233,143,.12), transparent 34%),
    linear-gradient(180deg,var(--chat-bg),rgba(4,8,7,.98))!important;
  background-size:auto!important;
  animation:none!important;
  box-shadow:0 18px 48px rgba(0,0,0,.28)!important;
  padding:14px!important;
}
.bubble{
  border-radius:18px!important;
  border:1px solid rgba(126,231,166,.20)!important;
  background:linear-gradient(180deg,rgba(255,255,255,.07),rgba(12,22,18,.94))!important;
  box-shadow:0 8px 26px rgba(0,0,0,.20)!important;
  color:var(--chat-text)!important;
  line-height:1.48!important;
}
.row.me .bubble{
  background:linear-gradient(180deg,rgba(62,233,143,.26),rgba(26,64,45,.96))!important;
  border-color:rgba(62,233,143,.40)!important;
}
.row.system-row .bubble{
  border-color:rgba(250,204,21,.36)!important;
  background:linear-gradient(180deg,rgba(74,54,13,.70),rgba(24,19,9,.92))!important;
  color:#fff7d6!important;
}
.meta{
  color:var(--chat-muted)!important;
  letter-spacing:0!important;
  text-transform:none!important;
  font-size:10px!important;
}
.user-dot,.online-dot{background:var(--chat-accent)!important;}
.secret,.poll,.checklist,.packet,.location,.ping,.system-info{
  border-radius:999px!important;
  padding:3px 8px!important;
  background:rgba(125,211,252,.12)!important;
  border:1px solid rgba(125,211,252,.26)!important;
  color:var(--chat-blue)!important;
  font-weight:800!important;
}
.empty{
  color:var(--chat-muted)!important;
  border:1px dashed rgba(126,231,166,.24);
  border-radius:16px;
  padding:20px;
  background:rgba(255,255,255,.04);
}
.pinned-card{
  border-radius:16px!important;
  background:linear-gradient(180deg,rgba(61,45,12,.78),rgba(24,19,9,.88))!important;
}
.thumb{border-radius:14px!important;border-color:rgba(126,231,166,.24)!important;}
@media (max-width:760px){
  .chat{min-height:380px!important;border-radius:16px!important;padding:10px!important;}
  .bubble{max-width:88%!important;border-radius:16px!important;font-size:14px!important;padding:10px 11px!important;}
  .meta{font-size:9.5px!important;}
}
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


# Metadata penting seperti invite link tetap memakai Fernet global agar link lama
# tidak rusak. Isi pesan dan packet room baru dienkripsi dengan Fernet unik
# yang diturunkan dari Password pembuat room.
ROOM_CRYPTO_VERSION = 2
ROOM_KDF_ITERATIONS = 390_000
ROOM_SALT_BYTES = 16


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


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(str(value or "").encode("ascii"))


def room_crypto_session_key(room: str) -> str:
    return "room_fernet_key::" + room_key(room)


def room_share_password_session_key(room: str) -> str:
    """Simpan password plaintext hanya di session browser agar bisa ikut dibagikan via WhatsApp.

    Password asli tidak pernah disimpan ke file JSON/server storage. Key ini hanya hidup
    selama sesi Streamlit user yang membuat atau berhasil unlock room.
    """
    return "room_share_password::" + room_key(room)


def room_crypto_salt(room: str) -> str:
    config = get_room_config(room)
    return str(config.get("room_fernet_salt", "") or "")


def room_encryption_enabled(room: str) -> bool:
    config = get_room_config(room)
    return bool(config.get("room_fernet_salt"))


def derive_room_fernet_key(room: str, password: str, salt_b64: str) -> bytes:
    """Turunkan Fernet key unik per room dari password pembuat room.

    Password asli tidak disimpan. Salt disimpan di room_settings.json, sedangkan
    CHAT_ADMIN_PASSWORD/FERNET_KEY dipakai sebagai server-side pepper supaya hasil
    KDF tidak hanya bergantung pada password user.
    """
    password = str(password or "")
    if not password:
        raise ValueError("Password pembuat room kosong.")
    salt = _b64decode(salt_b64)
    pepper = hashlib.sha256(get_fernet_key() + get_secret("CHAT_ADMIN_PASSWORD", "").encode("utf-8")).digest()
    material = password.encode("utf-8") + b"::" + pepper
    context_salt = salt + room_key(room).encode("utf-8")
    raw_key = hashlib.pbkdf2_hmac("sha256", material, context_salt, ROOM_KDF_ITERATIONS, dklen=32)
    return base64.urlsafe_b64encode(raw_key)


def remember_room_password(room: str, password: str) -> bool:
    clean_password = str(password or "")
    if room_password_block_seconds(room) > 0:
        return False
    if not verify_room_creator_password(room, clean_password):
        record_room_password_attempt(room, False)
        return False
    record_room_password_attempt(room, True)
    salt = room_crypto_salt(room)
    if salt:
        st.session_state[room_crypto_session_key(room)] = derive_room_fernet_key(room, clean_password, salt).decode("ascii")
    # Kompatibilitas: room lama yang belum punya PIN aksi pembuat tetap memakai password room untuk aksi sensitif.
    # Room baru memakai owner_action_hash, sehingga password room hanya membuka enkripsi dan tidak otomatis memberi hak revoke/settings.
    if not room_has_owner_pin(room):
        st.session_state[room_creator_session_key(room)] = True
    st.session_state[room_share_password_session_key(room)] = clean_password
    return True


def get_room_fernet(room: str) -> Fernet | None:
    if not room_encryption_enabled(room):
        return None
    key = str(st.session_state.get(room_crypto_session_key(room), "") or "")
    if not key:
        return None
    try:
        return Fernet(key.encode("ascii"))
    except Exception:
        return None


def encrypt_room_text(room: str, text: str) -> str:
    fernet = get_room_fernet(room)
    if fernet is None:
        # Legacy/fallback: room lama yang belum memakai password-derived key.
        return encrypt_text(text)
    return fernet.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_room_text(room: str, token: str) -> str:
    fernet = get_room_fernet(room)
    if fernet is not None:
        try:
            return fernet.decrypt(str(token).encode("utf-8")).decode("utf-8")
        except Exception:
            pass
    # Backward compatibility untuk pesan lama yang masih terenkripsi global.
    return decrypt_text(token)


def encrypt_room_bytes(room: str, data: bytes) -> bytes:
    fernet = get_room_fernet(room)
    if fernet is None:
        return encrypt_bytes(data)
    return fernet.encrypt(data)


def decrypt_room_bytes(room: str, data: bytes) -> bytes | None:
    fernet = get_room_fernet(room)
    if fernet is not None:
        try:
            return fernet.decrypt(data)
        except InvalidToken:
            pass
    return decrypt_bytes(data)


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
    path.write_bytes(encrypt_room_bytes(room, data))
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


def read_packet(room: str, relative_path: str) -> bytes | None:
    path = resolve_packet_path(relative_path)
    if path is None:
        return None
    return decrypt_room_bytes(room, path.read_bytes())


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




def generate_random_room_name(prefix: str = "room") -> str:
    """Create a random room name so users do not need to type one manually."""
    settings = load_json(ROOM_SETTINGS_FILE)
    for _ in range(20):
        candidate = clean_room_name(f"{prefix}-{secrets.token_hex(3)}-{secrets.token_hex(2)}")
        if room_key(candidate) not in settings:
            return candidate
    return clean_room_name(f"{prefix}-{secrets.token_urlsafe(8).replace('_', '').replace('-', '').lower()[:10]}")

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
    conflict_message = st.session_state.pop("username_conflict_message", "")
    if conflict_message:
        st.warning(conflict_message)

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
        raw_name = st.text_input("Nama pengguna", placeholder="contoh: NamaUnik", max_chars=40)
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
    try:
        max_participants = int(config.get("max_participants", DEFAULT_MAX_PARTICIPANTS) or DEFAULT_MAX_PARTICIPANTS)
    except Exception:
        max_participants = DEFAULT_MAX_PARTICIPANTS
    max_participants = min(max(1, max_participants), ROOM_MAX_PARTICIPANTS)
    locked_sessions = config.get("locked_session_ids", [])
    if not isinstance(locked_sessions, list):
        locked_sessions = []
    audit_log = config.get("audit_log", [])
    if not isinstance(audit_log, list):
        audit_log = []
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
        "creator_password_hash": str(config.get("creator_password_hash", "") or ""),
        "owner_action_hash": str(config.get("owner_action_hash", "") or ""),
        "room_fernet_salt": str(config.get("room_fernet_salt", "") or ""),
        "room_crypto_version": int(config.get("room_crypto_version", 1 if not config.get("room_fernet_salt") else ROOM_CRYPTO_VERSION)),
        "video_call_provider": str(config.get("video_call_provider", VIDEO_CALL_PROVIDER) or VIDEO_CALL_PROVIDER),
        "video_call_url_cipher": str(config.get("video_call_url_cipher", "") or ""),
        "video_session_note_cipher": str(config.get("video_session_note_cipher", "") or ""),
        "video_call_visible": bool(config.get("video_call_visible", False)),
        "is_locked": bool(config.get("is_locked", False)),
        "locked_at": int(config.get("locked_at", 0) or 0),
        "locked_by_cipher": str(config.get("locked_by_cipher", "") or ""),
        "locked_session_ids": [str(x) for x in locked_sessions if str(x)],
        "max_participants": max_participants,
        "audit_log": audit_log[-AUDIT_LOG_LIMIT:],
    }


def save_room_config(room: str, config: dict[str, Any]) -> None:
    settings = load_json(ROOM_SETTINGS_FILE)
    settings[room_key(room)] = config
    atomic_write_json(ROOM_SETTINGS_FILE, settings)

def owner_pin_digest(room: str, pin: str) -> str:
    """Hash PIN aksi pembuat tanpa menyimpan PIN asli."""
    clean_pin = str(pin or "")
    return hmac_digest(f"room-owner-pin::{room_key(room)}::{clean_pin}")


def generate_owner_pin() -> str:
    """PIN singkat untuk aksi pembuat; ditampilkan hanya ke pembuat saat room dibuat."""
    return secrets.token_urlsafe(7).replace("-", "").replace("_", "")[:10]


def room_has_owner_pin(room: str) -> bool:
    return bool(get_room_config(room).get("owner_action_hash"))


def verify_room_owner_pin(room: str, pin: str) -> bool:
    stored = str(get_room_config(room).get("owner_action_hash", "") or "")
    if not stored:
        return False
    return hmac.compare_digest(stored, owner_pin_digest(room, str(pin or "")))


def password_guard_key(room: str) -> str:
    return "room_password_guard::" + room_key(room)


def room_password_block_seconds(room: str) -> int:
    state = st.session_state.get(password_guard_key(room), {})
    if not isinstance(state, dict):
        return 0
    return max(0, int(state.get("blocked_until", 0) or 0) - now_epoch())


def record_room_password_attempt(room: str, success: bool) -> None:
    key = password_guard_key(room)
    if success:
        st.session_state.pop(key, None)
        return
    state = st.session_state.get(key, {})
    if not isinstance(state, dict):
        state = {}
    failures = int(state.get("failures", 0) or 0) + 1
    state["failures"] = failures
    state["last_failed_at"] = now_epoch()
    if failures >= PASSWORD_FAIL_LIMIT:
        state["blocked_until"] = now_epoch() + PASSWORD_FAIL_BLOCK_SECONDS
    st.session_state[key] = state


def remember_room_owner_pin(room: str, pin: str) -> bool:
    if room_password_block_seconds(room) > 0:
        return False
    if not verify_room_owner_pin(room, str(pin or "")):
        record_room_password_attempt(room, False)
        return False
    record_room_password_attempt(room, True)
    st.session_state[room_creator_session_key(room)] = True
    grant_current_session_room_access(room)
    append_audit_event(room, "owner_unlocked", "pembuat", "Akses aksi pembuat dibuka di sesi ini.")
    return True


def make_audit_event(event_type: str, actor: str = "", detail: str = "") -> dict[str, Any]:
    return {
        "at": now_epoch(),
        "time": now_wib_label(),
        "event": str(event_type or "event")[:64],
        "actor_cipher": encrypt_text(str(actor or "")[:80]) if actor else "",
        "detail_cipher": encrypt_text(str(detail or "")[:220]) if detail else "",
    }


def push_audit_event_to_config(config: dict[str, Any], event_type: str, actor: str = "", detail: str = "") -> None:
    audit_log = config.get("audit_log", [])
    if not isinstance(audit_log, list):
        audit_log = []
    audit_log.append(make_audit_event(event_type, actor, detail))
    config["audit_log"] = audit_log[-AUDIT_LOG_LIMIT:]


def append_audit_event(room: str, event_type: str, actor: str = "", detail: str = "") -> None:
    config = get_room_config(room)
    push_audit_event_to_config(config, event_type, actor, detail)
    save_room_config(room, config)


def get_room_audit_events(room: str) -> list[dict[str, Any]]:
    config = get_room_config(room)
    events = config.get("audit_log", []) if isinstance(config.get("audit_log"), list) else []
    decoded: list[dict[str, Any]] = []
    for event in events[-AUDIT_LOG_LIMIT:]:
        if not isinstance(event, dict):
            continue
        actor = decrypt_optional_config_text(str(event.get("actor_cipher", "") or ""), "")
        detail = decrypt_optional_config_text(str(event.get("detail_cipher", "") or ""), "")
        decoded.append({
            "time": str(event.get("time", "")),
            "event": str(event.get("event", "event")),
            "actor": actor,
            "detail": detail,
        })
    return decoded


def grant_current_session_room_access(room: str) -> None:
    config = get_room_config(room)
    sid = get_session_id()
    locked_sessions = [str(x) for x in config.get("locked_session_ids", []) if str(x)]
    if sid not in locked_sessions:
        locked_sessions.append(sid)
        config["locked_session_ids"] = locked_sessions[-ROOM_MAX_PARTICIPANTS:]
        save_room_config(room, config)


def current_session_has_room_access(room: str) -> bool:
    config = get_room_config(room)
    if not config.get("is_locked"):
        return True
    if room_creator_is_unlocked(room):
        return True
    sid = get_session_id()
    if sid in set(config.get("locked_session_ids", [])):
        return True
    online = load_json(ONLINE_FILE)
    active = normalize_online_entries(online.get(room_key(room), {}))
    return sid in active


def active_session_count(room: str) -> int:
    online = load_json(ONLINE_FILE)
    active = normalize_online_entries(online.get(room_key(room), {}))
    return len(active)


def room_join_block_reason(room: str) -> str:
    config = get_room_config(room)
    sid = get_session_id()
    online = load_json(ONLINE_FILE)
    active = normalize_online_entries(online.get(room_key(room), {}))
    if config.get("is_locked") and not current_session_has_room_access(room):
        return "Room sedang dikunci. Peserta baru tidak bisa masuk sampai pembuat membuka lock."
    max_participants = int(config.get("max_participants", DEFAULT_MAX_PARTICIPANTS) or DEFAULT_MAX_PARTICIPANTS)
    if sid not in active and len(active) >= max_participants and not room_creator_is_unlocked(room):
        return f"Room sudah mencapai batas maksimal {max_participants} peserta aktif."
    return ""


def set_room_lock(room: str, locked: bool, actor: str = "") -> None:
    config = get_room_config(room)
    active = normalize_online_entries(load_json(ONLINE_FILE).get(room_key(room), {}))
    session_ids = [str(sid) for sid in active.keys() if str(sid)]
    current_sid = get_session_id()
    if current_sid not in session_ids:
        session_ids.append(current_sid)
    config["is_locked"] = bool(locked)
    config["locked_at"] = now_epoch() if locked else 0
    config["locked_by_cipher"] = encrypt_text(str(actor or "pembuat")[:80]) if locked else ""
    config["locked_session_ids"] = session_ids if locked else []
    push_audit_event_to_config(
        config,
        "room_locked" if locked else "room_unlocked",
        actor or "pembuat",
        "Room dikunci untuk mencegah peserta baru masuk." if locked else "Room dibuka kembali untuk peserta baru.",
    )
    save_room_config(room, config)


def update_room_max_participants(room: str, max_participants: int, actor: str = "") -> None:
    config = get_room_config(room)
    value = min(max(1, int(max_participants)), ROOM_MAX_PARTICIPANTS)
    config["max_participants"] = value
    push_audit_event_to_config(config, "max_participants_updated", actor or "pembuat", f"Batas peserta diubah menjadi {value}.")
    save_room_config(room, config)


def creator_password_digest(room: str, password: str) -> str:
    """Hash password pembuat room tanpa menyimpan password asli."""
    clean_password = str(password or "")
    return hmac_digest(f"room-owner::{room_key(room)}::{clean_password}")


def room_has_creator_password(room: str) -> bool:
    config = get_room_config(room)
    return bool(config.get("creator_password_hash"))


def set_room_creator_password(room: str, password: str) -> None:
    clean_password = str(password or "").strip()
    if not clean_password:
        return
    config = get_room_config(room)
    config["creator_password_hash"] = creator_password_digest(room, clean_password)
    if not config.get("room_fernet_salt"):
        config["room_fernet_salt"] = _b64encode(secrets.token_bytes(ROOM_SALT_BYTES))
        config["room_crypto_version"] = ROOM_CRYPTO_VERSION
    save_room_config(room, config)
    st.session_state[room_crypto_session_key(room)] = derive_room_fernet_key(room, clean_password, str(config.get("room_fernet_salt", ""))).decode("ascii")
    st.session_state[room_share_password_session_key(room)] = clean_password


def verify_room_creator_password(room: str, password: str) -> bool:
    config = get_room_config(room)
    stored = str(config.get("creator_password_hash", "") or "")
    if not stored:
        return False
    return hmac.compare_digest(stored, creator_password_digest(room, str(password or "")))


def room_creator_session_key(room: str) -> str:
    return "creator_ok::" + room_key(room)


def room_creator_is_unlocked(room: str) -> bool:
    return bool(st.session_state.get("admin_ok")) or bool(st.session_state.get(room_creator_session_key(room)))


def render_room_creator_unlock(room: str, context_key: str = "default") -> bool:
    """Minta PIN aksi pembuat sebelum aksi sensitif seperti lock/revoke/hapus chat."""
    if room_creator_is_unlocked(room):
        return True
    if not room_has_creator_password(room):
        st.warning("Aksi ini hanya tersedia untuk admin karena room lama ini belum punya password pembuat.")
        return False

    safe_context = hashlib.sha1(str(context_key).encode("utf-8")).hexdigest()[:10]
    blocked = room_password_block_seconds(room)
    if blocked > 0:
        st.warning(f"Terlalu banyak percobaan salah. Coba lagi dalam {format_countdown(blocked)}.")
        return False

    if room_has_owner_pin(room):
        st.info("Masukkan PIN aksi pembuat untuk fitur sensitif seperti lock room, pengaturan GMeet, revoke, dan hapus chat.")
        owner_pin = st.text_input("PIN aksi pembuat", type="password", key=f"owner_pin_unlock::{safe_context}::{room_key(room)}")
        if st.button("Unlock aksi pembuat", use_container_width=True, key=f"creator_unlock_btn::{safe_context}::{room_key(room)}"):
            if remember_room_owner_pin(room, owner_pin):
                st.success("Akses pembuat aktif untuk sesi ini.")
                st.rerun()
            else:
                wait = room_password_block_seconds(room)
                st.error(f"PIN aksi pembuat salah.{f' Coba lagi dalam {format_countdown(wait)}.' if wait else ''}")
        return False

    st.info("Room lama ini belum punya PIN aksi pembuat terpisah. Masukkan password room untuk aksi sensitif.")
    password = st.text_input("Password pembuat room", type="password", key=f"creator_password_unlock::{safe_context}::{room_key(room)}")
    if st.button("Unlock aksi pembuat", use_container_width=True, key=f"creator_unlock_btn::{safe_context}::{room_key(room)}"):
        if remember_room_password(room, password):
            st.success("Akses pembuat aktif dan key Fernet room sudah dibuka.")
            st.rerun()
        else:
            wait = room_password_block_seconds(room)
            st.error(f"Password pembuat salah.{f' Coba lagi dalam {format_countdown(wait)}.' if wait else ''}")
    return False


def ensure_room_config(
    room: str,
    lifetime_minutes: int = ROOM_DEFAULT_TTL_MINUTES,
    created_by: str = "",
    creator_password: str = "",
    *,
    owner_action_pin: str = "",
    max_lifetime_minutes: int = ROOM_MAX_TTL_MINUTES,
    max_participants: int = DEFAULT_MAX_PARTICIPANTS,
) -> dict[str, Any]:
    room = clean_room_name(room)
    settings = load_json(ROOM_SETTINGS_FILE)
    key = room_key(room)
    existing = settings.get(key)
    now = now_epoch()
    clean_owner_pin = str(owner_action_pin or "").strip()
    if isinstance(existing, dict) and int(existing.get("expires_at", 0)) > now and not existing.get("destroyed_at"):
        config = get_room_config(room)
        if not config.get("room_cipher"):
            config["room_cipher"] = encrypt_text(room)
        if str(creator_password or "").strip() and not config.get("creator_password_hash"):
            config["creator_password_hash"] = creator_password_digest(room, creator_password)
        if clean_owner_pin and not config.get("owner_action_hash"):
            config["owner_action_hash"] = owner_pin_digest(room, clean_owner_pin)
        if str(creator_password or "").strip() and not config.get("room_fernet_salt"):
            config["room_fernet_salt"] = _b64encode(secrets.token_bytes(ROOM_SALT_BYTES))
            config["room_crypto_version"] = ROOM_CRYPTO_VERSION
        if str(creator_password or "").strip() and config.get("room_fernet_salt"):
            st.session_state[room_crypto_session_key(room)] = derive_room_fernet_key(room, creator_password, str(config.get("room_fernet_salt", ""))).decode("ascii")
            st.session_state[room_share_password_session_key(room)] = str(creator_password or "")
        if clean_owner_pin:
            st.session_state[room_creator_session_key(room)] = True
        settings[key] = config
        atomic_write_json(ROOM_SETTINGS_FILE, settings)
        return config
    lifetime_minutes = clamp_minutes(lifetime_minutes, max_lifetime_minutes)
    safe_max_participants = min(max(1, int(max_participants or DEFAULT_MAX_PARTICIPANTS)), ROOM_MAX_PARTICIPANTS)
    config = {
        "room_key": key,
        "room_cipher": encrypt_text(room),
        "created_by": encrypt_text(created_by.strip()[:80]) if created_by else "",
        "created_at": now,
        "expires_at": now + lifetime_minutes * 60,
        "auto_destroy_minutes": min(DEFAULT_DESTROY_MINUTES, lifetime_minutes),
        "last_active_at": now,
        "destroyed_at": 0,
        "creator_password_hash": creator_password_digest(room, creator_password) if str(creator_password or "").strip() else "",
        "owner_action_hash": owner_pin_digest(room, clean_owner_pin) if clean_owner_pin else "",
        "room_fernet_salt": _b64encode(secrets.token_bytes(ROOM_SALT_BYTES)) if str(creator_password or "").strip() else "",
        "room_crypto_version": ROOM_CRYPTO_VERSION if str(creator_password or "").strip() else 1,
        "video_call_provider": VIDEO_CALL_PROVIDER,
        "video_call_url_cipher": "",
        "video_session_note_cipher": encrypt_text(DEFAULT_VIDEO_SESSION_NOTE),
        "video_call_visible": False,
        "is_locked": False,
        "locked_at": 0,
        "locked_by_cipher": "",
        "locked_session_ids": [],
        "max_participants": safe_max_participants,
        "audit_log": [],
    }
    push_audit_event_to_config(config, "room_created", created_by or "anonymous", f"Room dibuat dengan durasi {lifetime_minutes} menit dan batas {safe_max_participants} peserta.")
    if str(creator_password or "").strip() and config.get("room_fernet_salt"):
        st.session_state[room_crypto_session_key(room)] = derive_room_fernet_key(room, creator_password, str(config.get("room_fernet_salt", ""))).decode("ascii")
        st.session_state[room_share_password_session_key(room)] = str(creator_password or "")
    if clean_owner_pin:
        st.session_state[room_creator_session_key(room)] = True
    settings[key] = config
    atomic_write_json(ROOM_SETTINGS_FILE, settings)
    return config


def sanitize_gmeet_url(raw_url: str) -> str:
    """Return a normalized Google Meet URL or an empty string when invalid."""
    value = str(raw_url or "").strip()
    if not value:
        return ""
    if value.startswith("meet.google.com/"):
        value = "https://" + value
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if parsed.scheme not in {"http", "https"} or host != "meet.google.com" or not parsed.path.strip("/"):
        return ""
    return value[:500]


def decrypt_optional_config_text(cipher_text: str, fallback: str = "") -> str:
    if not cipher_text:
        return fallback
    value = decrypt_text(cipher_text)
    if value.startswith("[") and "tidak dapat didekripsi" in value:
        return fallback
    return value


def get_room_video_call(room: str) -> dict[str, Any]:
    config = get_room_config(room)
    note = decrypt_optional_config_text(str(config.get("video_session_note_cipher", "") or ""), DEFAULT_VIDEO_SESSION_NOTE)
    return {
        "provider": str(config.get("video_call_provider", VIDEO_CALL_PROVIDER) or VIDEO_CALL_PROVIDER),
        "url": decrypt_optional_config_text(str(config.get("video_call_url_cipher", "") or ""), ""),
        "session_note": note or DEFAULT_VIDEO_SESSION_NOTE,
        "visible": bool(config.get("video_call_visible", False)),
    }


def save_room_video_call(room: str, url: str, session_note: str, visible: bool = True, actor: str = "") -> None:
    config = get_room_config(room)
    clean_url = sanitize_gmeet_url(url)
    clean_note = str(session_note or DEFAULT_VIDEO_SESSION_NOTE).strip()[:240] or DEFAULT_VIDEO_SESSION_NOTE
    config["video_call_provider"] = VIDEO_CALL_PROVIDER
    config["video_call_url_cipher"] = encrypt_text(clean_url) if clean_url else ""
    config["video_session_note_cipher"] = encrypt_text(clean_note)
    config["video_call_visible"] = bool(clean_url and visible)
    push_audit_event_to_config(
        config,
        "video_call_updated" if clean_url else "video_call_removed",
        actor or "pembuat",
        "Info Google Meet diperbarui." if clean_url else "Link Google Meet dihapus.",
    )
    save_room_config(room, config)


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


def get_session_id() -> str:
    session_id = st.session_state.get("client_session_id")
    if not session_id:
        session_id = secrets.token_hex(16)
        st.session_state["client_session_id"] = session_id
    return str(session_id)


def normalize_online_entries(raw_room: Any, now: int | None = None) -> dict[str, dict[str, Any]]:
    """Normalize old/new online data and keep only active sessions."""
    now = now_epoch() if now is None else int(now)
    active: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_room, dict):
        return active
    for key, value in raw_room.items():
        if isinstance(value, dict):
            username = normalize_display_name(value.get("username", ""))
            last_seen = int(value.get("last_seen", value.get("ts", 0)) or 0)
            session_id = str(value.get("session_id", key))
        else:
            # Backward compatibility for v15 data: {username: timestamp}
            username = normalize_display_name(key)
            last_seen = int(value or 0)
            session_id = "legacy::" + canonical_display_name(username)
        if username and now - last_seen <= ONLINE_ACTIVE_SECONDS:
            active[session_id] = {"username": username, "last_seen": last_seen, "session_id": session_id}
    return active


def username_taken_in_room(room: str, username: str) -> str | None:
    online = load_json(ONLINE_FILE)
    key = room_key(room)
    current_session = get_session_id()
    active = normalize_online_entries(online.get(key, {}))
    wanted = canonical_display_name(username)
    for session_id, entry in active.items():
        existing = normalize_display_name(entry.get("username", ""))
        if session_id != current_session and canonical_display_name(existing) == wanted:
            return existing
    return None


def update_online(room: str, username: str) -> list[str]:
    online = load_json(ONLINE_FILE)
    key = room_key(room)
    now = now_epoch()
    session_id = get_session_id()
    active = normalize_online_entries(online.get(key, {}), now)
    active[session_id] = {"username": username, "last_seen": now, "session_id": session_id}
    online[key] = active
    atomic_write_json(ONLINE_FILE, online)
    mark_room_active(room)
    return [entry["username"] for sid, entry in active.items() if sid != session_id]


def get_room_online_entries(room: str) -> list[dict[str, Any]]:
    """Return active online sessions for a room, including current user."""
    online = load_json(ONLINE_FILE)
    key = room_key(room)
    now = now_epoch()
    active = normalize_online_entries(online.get(key, {}), now)
    current_session = get_session_id()
    entries: list[dict[str, Any]] = []
    for sid, entry in active.items():
        name = normalize_display_name(entry.get("username", ""))
        if not name:
            continue
        last_seen = int(entry.get("last_seen", now) or now)
        entries.append({
            "username": name,
            "session_id": sid,
            "is_me": sid == current_session,
            "seconds_ago": max(0, now - last_seen),
        })
    entries.sort(key=lambda item: (not bool(item.get("is_me")), canonical_display_name(str(item.get("username", "")))))
    return entries


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
        active = normalize_online_entries(online.get(key, {}), now)
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
        "text": encrypt_room_text(room, clean),
        "crypto_version": ROOM_CRYPTO_VERSION if room_encryption_enabled(room) else 1,
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


def append_ping(room: str, username: str) -> None:
    """Send a lightweight attention ping into the room."""
    append_special_message(room, username, "ping", {})


def message_summary(msg: dict[str, Any], room: str = "") -> str:
    msg_type = str(msg.get("type", "text"))
    sender = normalize_display_name(str(msg.get("username", "unknown")))
    if msg_type == "text":
        body = decrypt_room_text(room, str(msg.get("text", "")))[:42]
    elif msg_type in {"secret_note", "one_time"}:
        body = decrypt_room_text(room, str(msg.get("text", "")))[:42]
    elif msg_type == "poll":
        body = decrypt_room_text(room, str(msg.get("question", "")))[:42]
    elif msg_type == "checklist":
        body = decrypt_room_text(room, str(msg.get("title", "Checklist")))[:42]
    elif msg_type == "location":
        body = decrypt_room_text(room, str(msg.get("label", "Location")))[:42]
    elif msg_type == "ping":
        body = "PING"
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
    config = get_room_config(room)
    left = room_seconds_left(room)
    if left <= 0:
        return "Revoked"
    if config.get("is_locked"):
        return "Locked"
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
            message["thumbnail"] = encrypt_room_text(room, thumb)
            message["crypto_version"] = ROOM_CRYPTO_VERSION if room_encryption_enabled(room) else 1
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


def create_invite(room: str, ttl_minutes: int = INVITE_DEFAULT_TTL_MINUTES, created_by: str = "", invite_max_ttl_minutes: int = INVITE_MAX_TTL_MINUTES) -> str:
    room = clean_room_name(room)
    config = ensure_room_config(room, ROOM_DEFAULT_TTL_MINUTES, created_by, max_lifetime_minutes=invite_max_ttl_minutes)
    room_left_seconds = max(1, int(config.get("expires_at", now_epoch())) - now_epoch())
    max_ttl_minutes = max(1, min(int(invite_max_ttl_minutes), (room_left_seconds + 59) // 60))
    ttl_minutes = clamp_minutes(ttl_minutes, max_ttl_minutes)
    token = secrets.token_urlsafe(32)
    invites = load_json(INVITE_FILE)
    invites[token_hash(token)] = {
        "room": encrypt_text(room),
        "room_key": room_key(room),
        "token_cipher": encrypt_text(token),
        "created_by": encrypt_text(created_by.strip()[:80]) if created_by else "",
        "created_at": now_epoch(),
        "expires_at": min(now_epoch() + ttl_minutes * 60, int(config.get("expires_at", now_epoch() + ttl_minutes * 60))),
        "revoked": False,
    }
    atomic_write_json(INVITE_FILE, invites)
    return token


def create_room_with_invite(
    room: str,
    lifetime_minutes: int,
    created_by: str = "",
    creator_password: str = "",
    *,
    owner_action_pin: str = "",
    max_lifetime_minutes: int = ROOM_MAX_TTL_MINUTES,
    max_invite_ttl_minutes: int = INVITE_MAX_TTL_MINUTES,
    max_participants: int = DEFAULT_MAX_PARTICIPANTS,
) -> str:
    room = clean_room_name(room)
    lifetime = clamp_minutes(lifetime_minutes, max_lifetime_minutes)
    ensure_room_config(
        room,
        lifetime,
        created_by,
        creator_password,
        owner_action_pin=owner_action_pin,
        max_lifetime_minutes=max_lifetime_minutes,
        max_participants=max_participants,
    )
    return create_invite(room, lifetime, created_by, max_invite_ttl_minutes)


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




def render_hide_link_redirect(seconds_left: int) -> None:
    """Reload landing after display-only countdown ends. This does not revoke invite/room."""
    left = max(0, int(seconds_left))
    if left <= 0:
        return
    components.html(
        f"""
        <script>
        (function(){{
          const delay = Math.max(1, {left}) * 1000 + 350;
          setTimeout(function(){{
            try {{
              const url = new URL(window.parent.location.href);
              url.search = '';
              url.hash = '';
              window.parent.location.replace(url.toString());
            }} catch(e) {{
              window.parent.location.reload();
            }}
          }}, delay);
        }})();
        </script>
        """,
        height=0,
    )


def render_click_to_copy_invite_link(invite_url: str, input_key: str, label: str = "Invite link") -> None:
    """Render invite link that copies itself when clicked."""
    safe_label = html.escape(label)
    safe_url = html.escape(str(invite_url or ""), quote=True)
    safe_id = "copy_invite_" + hashlib.sha1(f"{input_key}:{invite_url}:{time.time_ns()}".encode()).hexdigest()[:12]
    components.html(
        f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;width:100%;box-sizing:border-box;">
          <div style="font-size:12px;font-weight:700;margin-bottom:6px;opacity:.84;">{safe_label}</div>
          <div style="display:flex;gap:8px;align-items:center;width:100%;">
            <input id="{safe_id}_input" readonly value="{safe_url}" title="Klik untuk copy link" style="
              flex:1;
              min-width:0;
              cursor:pointer;
              border-radius:16px;
              border:1px solid rgba(120,145,180,.42);
              background:rgba(255,255,255,.54);
              color:inherit;
              padding:10px 12px;
              font-size:13px;
              outline:none;
              box-shadow:inset 0 1px 0 rgba(255,255,255,.65),0 8px 22px rgba(0,0,0,.08);
            "/>
            <button id="{safe_id}_btn" type="button" style="
              cursor:pointer;
              border-radius:999px;
              border:1px solid rgba(120,145,180,.42);
              background:rgba(255,255,255,.58);
              color:inherit;
              padding:10px 13px;
              font-weight:800;
              white-space:nowrap;
              box-shadow:inset 0 1px 0 rgba(255,255,255,.65),0 8px 22px rgba(0,0,0,.08);
            ">Copy</button>
          </div>
          <div id="{safe_id}_status" style="font-size:11px;margin-top:5px;opacity:.74;">Klik link atau tombol Copy untuk menyalin.</div>
        </div>
        <script>
        (function(){{
          const text = {json.dumps(str(invite_url or ""))};
          const input = document.getElementById('{safe_id}_input');
          const btn = document.getElementById('{safe_id}_btn');
          const status = document.getElementById('{safe_id}_status');
          function setStatus(message){{
            if (!status) return;
            status.textContent = message;
            setTimeout(() => {{ status.textContent = 'Klik link atau tombol Copy untuk menyalin.'; }}, 1800);
          }}
          async function copyLink(){{
            try {{
              if (navigator.clipboard && window.isSecureContext) {{
                await navigator.clipboard.writeText(text);
              }} else {{
                const temp = document.createElement('textarea');
                temp.value = text;
                temp.setAttribute('readonly', '');
                temp.style.position = 'fixed';
                temp.style.left = '-9999px';
                document.body.appendChild(temp);
                temp.select();
                document.execCommand('copy');
                document.body.removeChild(temp);
              }}
              if (input) input.select();
              setStatus('Link berhasil dicopy.');
            }} catch(e) {{
              if (input) input.select();
              setStatus('Gagal auto-copy. Link sudah diblok, tekan Ctrl/Cmd+C.');
            }}
          }}
          if (input) input.addEventListener('click', copyLink);
          if (btn) btn.addEventListener('click', copyLink);
        }})();
        </script>
        """,
        height=92,
    )

def render_copy_text_block(text: str, input_key: str, label: str = "Copy text") -> None:
    """Render a read-only textarea with a copy button for invitation templates or summaries."""
    safe_label = html.escape(label)
    safe_text = html.escape(str(text or ""), quote=True)
    safe_id = "copy_text_" + hashlib.sha1(f"{input_key}:{time.time_ns()}".encode()).hexdigest()[:12]
    components.html(
        f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;width:100%;box-sizing:border-box;">
          <div style="font-size:12px;font-weight:800;margin-bottom:6px;opacity:.86;">{safe_label}</div>
          <textarea id="{safe_id}_input" readonly style="
            width:100%;min-height:116px;box-sizing:border-box;resize:vertical;cursor:pointer;
            border-radius:14px;border:1px solid rgba(120,145,180,.42);
            background:rgba(255,255,255,.08);color:inherit;padding:10px 12px;
            font-size:13px;line-height:1.45;outline:none;">{safe_text}</textarea>
          <button id="{safe_id}_btn" type="button" style="
            margin-top:8px;cursor:pointer;border-radius:999px;border:1px solid rgba(120,145,180,.42);
            background:rgba(255,255,255,.14);color:inherit;padding:9px 13px;font-weight:800;">Copy template</button>
          <span id="{safe_id}_status" style="font-size:11px;margin-left:8px;opacity:.74;">Klik tombol untuk menyalin.</span>
        </div>
        <script>
        (function(){{
          const text = {json.dumps(str(text or ""))};
          const input = document.getElementById('{safe_id}_input');
          const btn = document.getElementById('{safe_id}_btn');
          const status = document.getElementById('{safe_id}_status');
          async function copyText(){{
            try {{
              if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
              else {{ input.select(); document.execCommand('copy'); }}
              if (input) input.select();
              if (status) status.textContent = 'Tersalin.';
            }} catch(e) {{
              if (input) input.select();
              if (status) status.textContent = 'Gagal auto-copy. Tekan Ctrl/Cmd+C.';
            }}
          }}
          if (btn) btn.addEventListener('click', copyText);
          if (input) input.addEventListener('click', () => input.select());
        }})();
        </script>
        """,
        height=190,
    )


def build_invite_template(invite_url: str, room: str | None = None, password: str | None = None) -> str:
    room_label = f" untuk room {room}" if room else ""
    password_line = f"Password room: {password}" if str(password or "").strip() else "Password room: minta ke pembuat room secara terpisah."
    return (
        f"Halo, sesi akan dilakukan melalui AntiTrust{room_label}.\n\n"
        f"Link masuk room:\n{invite_url}\n\n"
        f"{password_line}\n"
        "Waktu sesi mengikuti countdown di room/chat.\n"
        "Jika ada video call, tombol Google Meet tersedia di Panel room → Video Call setelah masuk.\n\n"
        "Catatan keamanan: jangan teruskan link/password ke orang lain dan hapus pesan ini setelah berhasil masuk."
    )


def render_invite_template(invite_url: str, room: str | None = None, password: str | None = None, input_key: str = "invite_template") -> None:
    with st.expander("Template undangan", expanded=False):
        render_copy_text_block(build_invite_template(invite_url, room, password), input_key=input_key, label="Template undangan siap kirim")


def render_temporary_invite_link(
    *,
    url_key: str,
    token_key: str,
    room_key: str | None = None,
    display_until_key: str,
    input_key: str,
    label: str = "Link hilang dari halaman dalam",
    password_key: str | None = None,
) -> bool:
    """Show invite link for 1 minute only in the UI; do not revoke token or room."""
    invite_url = st.session_state.get(url_key)
    token = st.session_state.get(token_key)
    if not invite_url or not token:
        return False

    display_until = int(st.session_state.get(display_until_key, 0) or 0)
    if display_until <= 0:
        display_until = now_epoch() + 60
        st.session_state[display_until_key] = display_until

    display_left = max(0, display_until - now_epoch())
    if display_left <= 0:
        keys = [url_key, token_key, display_until_key]
        if room_key:
            keys.append(room_key)
        if password_key:
            keys.append(password_key)
        if url_key == "public_invite_url":
            keys.append("public_owner_pin")
        clear_invite_display(*keys)
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.toast("Tampilan link sudah disembunyikan. Room/link tidak direvoke.")
        st.rerun()

    actual_left = invite_seconds_left(token)
    if actual_left <= 0:
        keys = [url_key, token_key, display_until_key]
        if room_key:
            keys.append(room_key)
        if password_key:
            keys.append(password_key)
        if url_key == "public_invite_url":
            keys.append("public_owner_pin")
        clear_invite_display(*keys)
        st.toast("Invite link sudah habis sesuai durasi aslinya.")
        st.rerun()

    room_name = st.session_state.get(room_key) if room_key else None
    share_password = st.session_state.get(password_key) if password_key else None
    render_click_to_copy_invite_link(invite_url, input_key)
    render_whatsapp_share(invite_url, room_name, share_password)
    render_invite_template(invite_url, room_name, share_password, input_key=f"template::{input_key}")
    with st.expander("QR Invite", expanded=False):
        render_qr_invite(invite_url)
    render_countdown(label, display_left)
    st.caption(f"Catatan: ini hanya menyembunyikan tampilan link setelah 1 menit. Invite asli masih aktif sampai {format_countdown(actual_left)} atau sampai room berakhir.")
    render_hide_link_redirect(display_left)
    return True

def force_landing_on_expired_invite() -> None:
    """Clear invite query/state and return to the landing page."""
    clear_invite_display(
        "room_invite_url", "room_invite_token",
        "public_invite_url", "public_invite_token", "public_room", "public_invite_display_until", "public_room_share_password",
        "last_invite", "last_invite_token", "last_room", "last_invite_display_until", "last_room_share_password",
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
    password: str | None = None,
    password_key: str | None = None,
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
        if password_key:
            keys.append(password_key)
        clear_invite_display(*keys)
        st.toast("Invite link sudah habis dan disembunyikan.")
        st.rerun()
    room_name = st.session_state.get(room_key) if room_key else None
    share_password = password if password is not None else (st.session_state.get(password_key) if password_key else None)
    render_click_to_copy_invite_link(invite_url, input_key)
    render_whatsapp_share(invite_url, room_name, share_password)
    render_invite_template(invite_url, room_name, share_password, input_key=f"template::{input_key}")
    with st.expander("QR Invite", expanded=False):
        render_qr_invite(invite_url)
    render_countdown(label, left)
    # Countdown berjalan di browser tanpa auto-refresh Streamlit, supaya halaman tidak lompat ke atas.
    return True


def format_countdown(seconds: int) -> str:
    seconds = max(0, int(seconds))
    minutes, sec = divmod(seconds, 60)
    return f"{minutes:02d}:{sec:02d}"


def format_room_time_left(seconds: int) -> str:
    """Format sisa waktu room agar durasi admin panjang tidak tampil sebagai ribuan menit."""
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, sec = divmod(rem, 60)
    if days:
        return f"{days} hari {hours:02d}:{minutes:02d}:{sec:02d}"
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def render_countdown(label: str, seconds_left: int) -> None:
    safe_label = html.escape(label)
    safe_id = "countdown_" + hashlib.sha1(f"{label}:{seconds_left}:{time.time_ns()}".encode()).hexdigest()[:12]
    warning_id = safe_id + "_warning"

    components.html(
        f"""
        <div style="
          font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          border:1px solid rgba(255,255,255,.22);
          border-radius:15px;
          padding:7px 9px;
          background:rgba(255,255,255,.10);
          backdrop-filter:blur(18px);
          color:inherit;
        ">
          <div style="font-size:10px;opacity:.72;margin-bottom:2px">{safe_label}</div>

          <div id="{safe_id}" style="
            font-size:16px;
            font-weight:800;
            letter-spacing:-.04em;
          ">{format_room_time_left(seconds_left)}</div>

          <div id="{warning_id}" style="
            display:none;
            margin-top:6px;
            padding:6px 8px;
            border-radius:10px;
            background:rgba(255,59,48,.18);
            border:1px solid rgba(255,59,48,.55);
            color:#ffd9d6;
            font-size:12px;
            font-weight:800;
          "></div>
        </div>

        <script>
          let left = {max(0, int(seconds_left))};
          const el = document.getElementById('{safe_id}');
          const warning = document.getElementById('{warning_id}');

          function fmt(total) {{
            total = Math.max(0, total);
            const d = Math.floor(total / 86400);
            const h = Math.floor((total % 86400) / 3600);
            const m = Math.floor((total % 3600) / 60);
            const s = total % 60;

            const hh = h.toString().padStart(2, '0');
            const mm = m.toString().padStart(2, '0');
            const ss = s.toString().padStart(2, '0');

            if (d > 0) return `${{d}} hari ${{hh}}:${{mm}}:${{ss}}`;
            if (h > 0) return `${{hh}}:${{mm}}:${{ss}}`;
            return `${{mm}}:${{ss}}`;
          }}

          function tick() {{
            if (!el) return;

            el.textContent = fmt(left);

            if (warning) {{
              if (left > 0 && left <= 30) {{
                warning.style.display = 'block';
                warning.textContent = `⚠️ Waktu hampir habis. Room akan berakhir dalam ${{left}} detik.`;
              }} else if (left <= 0) {{
                warning.style.display = 'block';
                warning.textContent = '⛔ Waktu habis. Room akan otomatis direvoke.';
              }} else {{
                warning.style.display = 'none';
              }}
            }}

            if (left > 0) left -= 1;
          }}

          tick();
          setInterval(tick, 1000);
        </script>
        """,
        height=76,
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


def build_whatsapp_share_url(invite_url: str, room: str | None = None, password: str | None = None) -> str:
    room_label = f" untuk room {room}" if room else ""
    password = str(password or "").strip()
    password_line = f"\nPassword room: {password}" if password else "\nPassword room: minta ke pembuat room."
    text = (
        f"Masuk ke AntiTrust{room_label}: {invite_url}"
        f"{password_line}\n\n"
        "Catatan: link, room, dan password bersifat sementara, ketikkan password diatas. Jangan teruskan ke orang yang tidak dipercaya. Hapus pesan ini setelah berhasil masuk room"
    )
    return "https://wa.me/?" + urlencode({"text": text})


def render_whatsapp_share(invite_url: str, room: str | None = None, password: str | None = None) -> None:
    if not invite_url:
        return
    st.link_button("Share WhatsApp", build_whatsapp_share_url(invite_url, room, password), use_container_width=True)


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


def user_hue(username: str) -> int:
    """Deterministic, readable accent color for each display name."""
    clean = normalize_display_name(username).casefold()
    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 360


def render_chat(messages: list[dict[str, Any]], username: str, room: str = "") -> str:
    if not messages:
        return CHAT_CSS + CHAT_UI_CSS + """
        <div id="antitrust-chat-box" class="chat"><div class="empty">Belum ada pesan. Mulai percakapan aman.</div><div id="antitrust-chat-bottom"></div></div>
        <script>
          // Scroll hanya di dalam kotak chat, bukan scroll halaman browser.
          const box = document.getElementById('antitrust-chat-box');
          if (box) requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; });
        </script>
        """
    rows = ""
    countdown_targets: list[dict[str, Any]] = []
    pinned = [m for m in messages if m.get("_pinned")]
    for msg in messages[-120:]:
        raw_sender = str(msg.get("username", "unknown"))
        sender = html.escape(raw_sender)
        sender_label = username_with_badge_html(raw_sender)
        msg_type = str(msg.get("type", "text"))
        is_system = msg_type in {"system_countdown", "system_info"}
        is_me = (sender == html.escape(username)) and not is_system
        hue = user_hue(raw_sender)
        bubble_style = f' style="--user-hue:{hue}"'
        time_label = html.escape(str(msg.get("time", "")))
        if msg_type == "text":
            content = html.escape(decrypt_room_text(room, str(msg.get("text", ""))))
        elif msg_type == "system_countdown":
            seconds_left = max(0, int(msg.get("seconds_left", 0) or 0))
            target_id = "system_countdown_" + hashlib.sha1(str(msg.get("id", secrets.token_hex(6))).encode("utf-8")).hexdigest()[:12]
            countdown_targets.append({"id": target_id, "left": seconds_left})
            if seconds_left > 0:
                content = (
                    '<span class="system-info">⚠️ Info System</span>'
                    'Waktu room hampir habis dan akan segera berakhir.<br>'
                    f'<span class="system-countdown-line">Waktu habis dalam <b id="{target_id}">{seconds_left} detik</b></span><br>'
                    '<small>Hitungan mundur otomatis dari sistem.</small>'
                )
            else:
                content = (
                    '<span class="system-info">⛔ Info System</span>'
                    '<span class="system-countdown-line">Waktu habis. Room akan otomatis direvoke.</span><br>'
                    '<small>Sistem sedang menutup akses room.</small>'
                )
        elif msg_type == "system_info":
            content = '<span class="system-info">ℹ️ Info System</span>' + html.escape(str(msg.get("text", "")))
        elif msg_type == "secret_note":
            content = '<span class="secret">🔒 Secret Note</span><small>Buka lewat panel Fitur diatas.</small>'
        elif msg_type == "one_time":
            content = '<span class="secret">👁️ One-Time Message</span><small>Buka sekali lewat panel Fitur diatas, lalu pesan terhapus.</small>'
        elif msg_type == "poll":
            question = html.escape(decrypt_room_text(room, str(msg.get("question", ""))))
            votes = msg.get("votes") if isinstance(msg.get("votes"), dict) else {}
            options = msg.get("options") if isinstance(msg.get("options"), list) else []
            counts = []
            for opt_token in options:
                opt = decrypt_room_text(room, str(opt_token))
                total = sum(1 for v in votes.values() if v == opt)
                counts.append(f"{html.escape(opt)}: {total}")
            content = f'<span class="poll">📊 Poll</span>{question}<br><small>{" · ".join(counts)}</small>'
        elif msg_type == "location":
            label = html.escape(decrypt_room_text(room, str(msg.get("label", "Lokasi"))))
            url = html.escape(decrypt_room_text(room, str(msg.get("url", ""))), quote=True)
            content = f'<span class="location">📍 Location Pin</span><a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
        elif msg_type == "checklist":
            title = html.escape(decrypt_room_text(room, str(msg.get("title", "Checklist"))))
            items = msg.get("items") if isinstance(msg.get("items"), list) else []
            checked = msg.get("checked") if isinstance(msg.get("checked"), dict) else {}
            done = sum(1 for i in range(len(items)) if checked.get(str(i)))
            content = f'<span class="checklist">☑️ Checklist</span>{title}<br><small>{done}/{len(items)} selesai · kelola lewat panel Fitur</small>'
        elif msg_type == "ping":
            content = '<span class="ping">📡 Ping</span><span class="ping-card">Butuh perhatian sekarang</span><br><small>Ping dikirim ke room.</small>'
        else:
            filename = html.escape(str(msg.get("filename", "packet")))
            size = html.escape(format_bytes(msg.get("size_bytes", 0)))
            label = {"image": "Image", "audio": "Voice", "document": "Document"}.get(msg_type, "Packet")
            content = f'<span class="packet">{label} Packet</span>{filename}<br><small>{size} · buka di Packet Viewer</small>'
            if msg_type == "image" and msg.get("thumbnail"):
                thumb = decrypt_room_text(room, str(msg.get("thumbnail", "")))
                mime = html.escape(str(msg.get("thumbnail_mime", "image/jpeg")))
                if thumb and not thumb.startswith("["):
                    content += f'<img class="thumb" src="data:{mime};base64,{html.escape(thumb, quote=True)}" />'
        if not is_system:
            content += reaction_html(msg) + expire_html(msg)
        pin = ' 📌' if msg.get("_pinned") else ''
        cls = "row system-row" if is_system else ("row me" if is_me else "row")
        dot = '<span class="system-dot" aria-hidden="true"></span>' if is_system else '<span class="user-dot" aria-hidden="true"></span>'
        me_label = '<span>kamu</span>' if is_me else ''
        pin_label = '<span>📌</span>' if pin else ''
        rows += f'<div class="{cls}"><div class="bubble"{bubble_style}>{content}<div class="meta">{dot}<span>{sender_label}</span>{me_label}{pin_label}<span>{time_label}</span></div></div></div>'

    countdown_payload = json.dumps(countdown_targets, ensure_ascii=False)
    return CHAT_CSS + CHAT_UI_CSS + f"""
    <div id="antitrust-chat-box" class="chat">{rows}<div id="antitrust-chat-bottom"></div></div>
    <script>
      const box = document.getElementById('antitrust-chat-box');
      function scrollLatest() {{
        // Jangan panggil scrollIntoView karena itu menggeser halaman utama Streamlit.
        if (box) box.scrollTop = box.scrollHeight;
      }}
      const systemCountdownTargets = {countdown_payload};
      systemCountdownTargets.forEach(function(target) {{
        let left = Math.max(0, parseInt(target.left || 0, 10));
        const node = document.getElementById(target.id);
        function tickSystemCountdown() {{
          if (!node) return;
          const line = node.closest('.system-countdown-line');
          if (left > 0) {{
            node.textContent = left + ' detik';
          }} else {{
            if (line) line.textContent = 'Waktu habis. Room akan otomatis direvoke.';
            else node.textContent = 'waktu habis';
          }}
          if (left > 0) left -= 1;
        }}
        tickSystemCountdown();
        setInterval(tickSystemCountdown, 1000);
      }});
      requestAnimationFrame(scrollLatest);
      setTimeout(scrollLatest, 80);
      setTimeout(scrollLatest, 240);
    </script>
    """


def latest_foreign_signature(messages: list[dict[str, Any]], username: str) -> str:
    for msg in reversed(messages):
        if str(msg.get("username", "")) != username:
            return str(msg.get("id", ""))
    return ""


def render_sound_notice(signature: str, enabled: bool) -> None:
    """Browser-side incoming-message sound.

    The first click enables audio for the browser tab. After that, every new
    foreign message signature plays a short iOS-like beep on refresh.
    """
    if not enabled:
        return
    safe_sig = html.escape(signature or "", quote=True)
    components.html(
        f"""
        <div id="sound-wrap" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:0">
          <button id="sound-toggle" style="width:100%;border:1px solid rgba(120,145,180,.28);border-radius:999px;padding:6px 10px;background:rgba(255,255,255,.14);color:inherit;cursor:pointer;font-size:12px;font-weight:800;backdrop-filter:blur(14px)">🔔 Aktifkan suara pesan masuk</button>
          <span id="sound-state" style="display:block;margin-top:3px;font-size:10px;opacity:.68;text-align:center"></span>
        </div>
        <script>
        (function(){{
          const sig = '{safe_sig}';
          const enabledKey = 'antitrust_sound_enabled_v2';
          const lastKey = 'antitrust_last_foreign_message_v2';
          const btn = document.getElementById('sound-toggle');
          const state = document.getElementById('sound-state');
          function storageGet(k){{ try{{return window.localStorage.getItem(k)}}catch(e){{return window.sessionStorage.getItem(k)}} }}
          function storageSet(k,v){{ try{{window.localStorage.setItem(k,v)}}catch(e){{window.sessionStorage.setItem(k,v)}} }}
          function beep(){{
            try{{
              const Ctx = window.AudioContext || window.webkitAudioContext;
              const ctx = new Ctx();
              const gain = ctx.createGain();
              gain.gain.setValueAtTime(0.0001, ctx.currentTime);
              gain.gain.exponentialRampToValueAtTime(0.075, ctx.currentTime + 0.018);
              gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.22);
              gain.connect(ctx.destination);
              [880, 1175].forEach((freq, i) => {{
                const osc = ctx.createOscillator();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, ctx.currentTime + i * 0.055);
                osc.connect(gain);
                osc.start(ctx.currentTime + i * 0.055);
                osc.stop(ctx.currentTime + 0.20 + i * 0.055);
              }});
              setTimeout(() => ctx.close(), 420);
            }}catch(e){{}}
          }}
          function refreshUI(){{
            const on = storageGet(enabledKey) === '1';
            btn.textContent = on ? '🔔 Suara pesan aktif' : '🔔 Aktifkan suara pesan masuk';
            if(state) state.textContent = on ? 'Notifikasi akan berbunyi saat ada pesan baru dari user lain.' : 'Klik sekali agar browser mengizinkan suara.';
          }}
          btn.addEventListener('click', () => {{
            storageSet(enabledKey, '1');
            if (sig) storageSet(lastKey, sig);
            beep();
            refreshUI();
          }});
          refreshUI();
          const on = storageGet(enabledKey) === '1';
          const last = storageGet(lastKey) || '';
          if (on && sig && last && last !== sig) {{
            beep();
            storageSet(lastKey, sig);
          }} else if (on && sig && !last) {{
            storageSet(lastKey, sig);
          }}
        }})();
        </script>
        """,
        height=52,
    )



def decode_room_name_from_config(config: dict[str, Any], fallback_key: str = "") -> str:
    """Ambil nama room dari config terenkripsi untuk panel admin."""
    room_cipher = str(config.get("room_cipher", "") or "")
    if room_cipher:
        room = clean_room_name(decrypt_text(room_cipher).strip())
        if room and not room.startswith("["):
            return room
    return fallback_key[:18] + "..." if fallback_key else "room-tidak-terbaca"


def destroy_room_by_settings_key(settings_key: str, room_name: str = "") -> tuple[int, int]:
    """Revoke room dari panel admin, tetap aman walau nama room gagal didekripsi."""
    room_name = clean_room_name(room_name)
    if room_name and room_key(room_name) == settings_key:
        return destroy_room_and_revoke(room_name)

    rooms = load_json(CHAT_FILE)
    online = load_json(ONLINE_FILE)
    settings = load_json(ROOM_SETTINGS_FILE)
    count = len(rooms.get(settings_key, [])) if isinstance(rooms.get(settings_key), list) else 0
    rooms.pop(settings_key, None)
    online.pop(settings_key, None)
    settings.pop(settings_key, None)
    atomic_write_json(CHAT_FILE, rooms)
    atomic_write_json(ONLINE_FILE, online)
    atomic_write_json(ROOM_SETTINGS_FILE, settings)
    shutil.rmtree(PACKET_DIR / settings_key, ignore_errors=True)
    revoked = revoke_room_invites_by_key(settings_key)
    return count, revoked


def get_active_invite_links_by_room_key(settings_key: str) -> list[dict[str, Any]]:
    """Ambil semua invite link aktif untuk satu room.

    Catatan: app versi lama hanya menyimpan hash token, jadi link lama yang
    belum punya token_cipher tidak bisa dibangun ulang. Link baru setelah update
    ini akan tampil lengkap di panel admin.
    """
    invites = load_json(INVITE_FILE)
    now = now_epoch()
    links: list[dict[str, Any]] = []
    for item in invites.values():
        if not isinstance(item, dict):
            continue
        if item.get("room_key") != settings_key or item.get("revoked"):
            continue
        expires_at = int(item.get("expires_at", 0) or 0)
        if expires_at <= now:
            continue
        token_cipher = str(item.get("token_cipher", "") or "")
        token = decrypt_text(token_cipher).strip() if token_cipher else ""
        if not token or token.startswith("["):
            links.append({
                "url": "",
                "seconds_left": max(0, expires_at - now),
                "created_at": int(item.get("created_at", 0) or 0),
                "legacy": True,
            })
            continue
        links.append({
            "url": build_invite_url(token),
            "seconds_left": max(0, expires_at - now),
            "created_at": int(item.get("created_at", 0) or 0),
            "legacy": False,
        })
    links.sort(key=lambda item: item.get("seconds_left", 0))
    return links


def get_active_room_rows() -> list[dict[str, Any]]:
    """Daftar semua room yang masih aktif untuk halaman admin."""
    settings = load_json(ROOM_SETTINGS_FILE)
    rooms = load_json(CHAT_FILE)
    online = load_json(ONLINE_FILE)
    now = now_epoch()
    rows: list[dict[str, Any]] = []

    for key, config in settings.items():
        if not isinstance(config, dict):
            continue
        expires_at = int(config.get("expires_at", 0) or 0)
        destroyed_at = int(config.get("destroyed_at", 0) or 0)
        if destroyed_at or expires_at <= now:
            continue
        room_name = decode_room_name_from_config(config, key)
        active_entries = normalize_online_entries(online.get(key, {}), now)
        online_users = []
        for entry in active_entries.values():
            name = normalize_display_name(entry.get("username", ""))
            if name:
                online_users.append(name)
        online_users = sorted(set(online_users), key=lambda value: value.casefold())
        messages = rooms.get(key, [])
        created_by = decrypt_text(str(config.get("created_by", ""))).strip() if config.get("created_by") else "anonymous"
        if not created_by or created_by.startswith("["):
            created_by = "anonymous"
        invite_links = get_active_invite_links_by_room_key(key)
        rows.append({
            "key": key,
            "room": room_name,
            "created_by": created_by,
            "messages": len(messages) if isinstance(messages, list) else 0,
            "online": len(active_entries),
            "online_users": online_users,
            "invite_links": invite_links,
            "invite_count": len(invite_links),
            "seconds_left": max(0, expires_at - now),
            "created_at": int(config.get("created_at", 0) or 0),
        })

    rows.sort(key=lambda item: (item["seconds_left"], item["room"].casefold()))
    return rows


def render_admin_active_rooms_panel() -> None:
    st.divider()
    st.subheader("Room aktif")
    rows = get_active_room_rows()
    if not rows:
        st.info("Belum ada room aktif.")
        return

    st.caption(f"Total room aktif: {len(rows)}. Admin bisa melihat invite link aktif, membuat link baru, dan revoke satu per satu atau semuanya.")
    for row in rows:
        room_label = row["room"]
        with st.container(border=True):
            col_info, col_action = st.columns([3, 1])
            with col_info:
                st.markdown(f"**{html.escape(room_label)}**")
                st.caption(
                    f"Sisa waktu {format_room_time_left(row['seconds_left'])} · "
                    f"Online {row['online']} · Pesan/packet {row['messages']} · "
                    f"Link aktif {row.get('invite_count', 0)} · Pembuat {row['created_by']}"
                )
                online_users = row.get("online_users", []) if isinstance(row.get("online_users"), list) else []
                if online_users:
                    safe_users = [html.escape(str(name)) for name in online_users]
                    st.markdown("**User online:** " + ", ".join(safe_users), unsafe_allow_html=True)
                else:
                    st.caption("User online: belum ada user aktif di room ini.")

                invite_links = row.get("invite_links", []) if isinstance(row.get("invite_links"), list) else []
                if invite_links:
                    with st.expander("Lihat invite link aktif", expanded=False):
                        for idx, link in enumerate(invite_links, start=1):
                            if link.get("url"):
                                render_click_to_copy_invite_link(
                                    str(link.get("url", "")),
                                    input_key=f"admin_active_invite::{row['key']}::{idx}",
                                    label=f"Invite link {idx} · sisa {format_countdown(int(link.get('seconds_left', 0)))}",
                                )
                            else:
                                st.caption(
                                    f"Invite link {idx} masih aktif, tetapi token asli tidak tersedia karena dibuat sebelum update ini. "
                                    f"Sisa {format_countdown(int(link.get('seconds_left', 0)))}."
                                )
                else:
                    st.caption("Belum ada invite link aktif yang bisa ditampilkan untuk room ini.")
            with col_action:
                if st.button("Buat link baru", use_container_width=True, key=f"admin_make_invite::{row['key']}"):
                    # Buat invite baru dengan sisa waktu mengikuti sisa room, maksimal 7 hari untuk admin.
                    minutes_left = max(1, (int(row.get("seconds_left", 0)) + 59) // 60)
                    token = create_invite(
                        room_label,
                        ttl_minutes=minutes_left,
                        created_by="admin",
                        invite_max_ttl_minutes=ADMIN_ROOM_MAX_TTL_MINUTES,
                    )
                    st.success("Invite link baru berhasil dibuat. Link akan muncul di daftar room ini.")
                    st.rerun()
                confirm_key = f"admin_confirm_revoke::{row['key']}"
                confirmed = st.checkbox("Konfirmasi", key=confirm_key)
                if st.button("Revoke", type="primary", use_container_width=True, disabled=not confirmed, key=f"admin_revoke_room::{row['key']}"):
                    count, revoked = destroy_room_by_settings_key(row["key"], room_label)
                    st.success(f"Room {room_label} direvoke. {count} pesan/packet dihapus, {revoked} invite link direvoke.")
                    st.rerun()

    confirm_all = st.checkbox("Saya paham: semua room aktif, chat, packet, dan invite link akan direvoke/dihapus", key="admin_confirm_revoke_all_rooms")
    if st.button("Revoke semua room aktif", type="primary", use_container_width=True, disabled=not confirm_all, key="admin_revoke_all_rooms"):
        total_rooms = 0
        total_messages = 0
        total_invites = 0
        for row in get_active_room_rows():
            count, revoked = destroy_room_by_settings_key(row["key"], row["room"])
            total_rooms += 1
            total_messages += count
            total_invites += revoked
        st.success(f"{total_rooms} room aktif direvoke. {total_messages} pesan/packet dihapus, {total_invites} invite link direvoke.")
        st.rerun()

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
        st.caption("Nama room dibuat otomatis dan acak. Room baru memakai Fernet key unik dari Password pembuat room. Simpan password ini karena dibutuhkan untuk membuka isi chat.")
        admin_duration_options = {
            "1 jam": 60,
            "3 jam": 180,
            "6 jam": 360,
            "12 jam": 720,
            "24 jam": 1440,
            "3 hari": 4320,
            "7 hari": 10080,
        }
        ttl_label = st.selectbox(
            "Masa aktif room & invite link",
            options=list(admin_duration_options.keys()),
            index=4,
            help="Khusus admin bisa membuat room lebih lama, maksimal 7 hari. Tampilan link tetap hanya muncul 1 menit setelah dibuat, tanpa revoke.",
        )
        ttl = admin_duration_options[ttl_label]
        admin_room_password = st.text_input(
            "Password pembuat room (min 8 karakter)",
            type="password",
            help="Password ini menurunkan Fernet key unik per room. Bagikan password secara terpisah dari invite link.",
            key="admin_creator_room_password",
        )
        if st.button("Buat room otomatis + invite link", use_container_width=True):
            if len(str(admin_room_password or "").strip()) < 8:
                st.warning("Password pembuat room minimal 8 karakter agar key Fernet lebih kuat.")
                return
            room = generate_random_room_name("admin")
            token = create_room_with_invite(
                room,
                int(ttl),
                "admin",
                admin_room_password,
                max_lifetime_minutes=ADMIN_ROOM_MAX_TTL_MINUTES,
                max_invite_ttl_minutes=ADMIN_ROOM_MAX_TTL_MINUTES,
            )
            st.session_state["last_invite"] = build_invite_url(token)
            st.session_state["last_invite_token"] = token
            st.session_state["last_room"] = room
            st.session_state["last_room_share_password"] = str(admin_room_password or "")
            st.session_state["last_invite_display_until"] = now_epoch() + 60
            st.success(f"Room otomatis `{room}` berhasil dibuat untuk {ttl_label}. Link hanya ditampilkan 1 menit, tanpa revoke.")
        if render_temporary_invite_link(
            url_key="last_invite",
            token_key="last_invite_token",
            room_key="last_room",
            display_until_key="last_invite_display_until",
            input_key="admin_invite_box",
            label="Link hilang dari halaman dalam",
            password_key="last_room_share_password",
        ):
            if st.session_state.get("last_room"):
                render_countdown("Sisa waktu room", room_seconds_left(st.session_state.get("last_room")))

        render_admin_active_rooms_panel()

        if st.button("Logout admin", use_container_width=True):
            st.session_state.pop("admin_ok", None)
            st.rerun()


def render_public_room_creator() -> None:
    st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
    st.markdown('<div class="terminal-note">Buat ruang aman sementara</div>', unsafe_allow_html=True)
    st.subheader("Buat Room Baru")
    st.caption("Isi password room, tentukan durasi, lalu bagikan link undangan. PIN aksi pembuat dipakai untuk kontrol sensitif seperti lock, Google Meet, dan revoke.")
    creator_password = st.text_input("Password room / enkripsi (min 8 karakter)", type="password", help="Bagikan ke peserta yang dipercaya agar mereka bisa membuka room. Jangan samakan dengan PIN aksi pembuat jika ingin kontrol lebih aman.", key="public_creator_room_password")
    owner_pin_input = st.text_input("PIN aksi pembuat (opsional, min 6 karakter)", type="password", help="Kosongkan untuk dibuat otomatis. PIN ini jangan dibagikan ke peserta biasa.", key="public_owner_pin_input")
    ttl = st.slider("Durasi room", min_value=1, max_value=ROOM_MAX_TTL_MINUTES, value=ROOM_DEFAULT_TTL_MINUTES, help="Maksimal 60 menit. Tampilan link hilang otomatis setelah 1 menit, tanpa revoke.", key="public_room_ttl")
    max_participants = st.slider("Maksimal peserta aktif", min_value=1, max_value=ROOM_MAX_PARTICIPANTS, value=DEFAULT_MAX_PARTICIPANTS, help="Peserta baru ditolak jika room sudah mencapai batas ini.", key="public_room_max_participants")
    if st.button("Buat room & link undangan", use_container_width=True):
        if len(str(creator_password or "").strip()) < 8:
            st.warning("Password room minimal 8 karakter agar key Fernet lebih kuat.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        clean_owner_pin = str(owner_pin_input or "").strip()
        if clean_owner_pin and len(clean_owner_pin) < 6:
            st.warning("PIN aksi pembuat minimal 6 karakter, atau kosongkan agar dibuat otomatis.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        owner_pin = clean_owner_pin or generate_owner_pin()
        room = generate_random_room_name("anon")
        token = create_room_with_invite(room, int(ttl), "anonymous", creator_password, owner_action_pin=owner_pin, max_participants=int(max_participants))
        st.session_state[room_creator_session_key(room)] = True
        st.session_state["public_invite_url"] = build_invite_url(token)
        st.session_state["public_invite_token"] = token
        st.session_state["public_room"] = room
        st.session_state["public_room_share_password"] = str(creator_password or "")
        st.session_state["public_owner_pin"] = owner_pin
        st.session_state["public_invite_display_until"] = now_epoch() + 60
        st.success(f"Room `{room}` berhasil dibuat. Salin link dan password sekarang; tampilan link akan disembunyikan dalam 1 menit.")
    if st.session_state.get("public_invite_url"):
        col1, col2 = st.columns(2)
        with col1:
            render_temporary_invite_link(
                url_key="public_invite_url",
                token_key="public_invite_token",
                room_key="public_room",
                display_until_key="public_invite_display_until",
                input_key="public_invite_box",
                label="Link hilang dari halaman dalam",
                password_key="public_room_share_password",
            )
            owner_pin = st.session_state.get("public_owner_pin")
            if owner_pin:
                st.warning("Simpan PIN aksi pembuat ini. PIN tidak ikut dikirim di template/WhatsApp dan akan disembunyikan bersama tampilan link.")
                st.code(str(owner_pin), language="text")
        with col2:
            render_countdown("Sisa waktu room", room_seconds_left(st.session_state.get("public_room")))
    st.markdown('</div>', unsafe_allow_html=True)


def render_landing() -> None:
    st.markdown(
        """<div class="terminal-hero">
            <div class="terminal-kicker">Private temporary room · chat · file · Google Meet</div>
            <h1>AntiTrust<span class="terminal-cursor"></span></h1>
            <p class="muted">Buat ruang diskusi sementara yang mudah dipakai di desktop maupun HP. Link undangan, password room, PIN pembuat, dan Google Meet dibuat lebih jelas agar sesi terasa aman dan rapi.</p>
        </div>
        <div class="landing-grid">
          <div class="feature-card"><b>1. Buat room</b><span>Room otomatis memakai nama acak, durasi terbatas, dan password enkripsi.</span></div>
          <div class="feature-card"><b>2. Bagikan undangan</b><span>Salin link, template pesan, atau QR. Link bisa disembunyikan dari halaman.</span></div>
          <div class="feature-card"><b>3. Jalankan sesi</b><span>Chat, file, pin pesan, ringkasan, peserta aktif, dan tombol Google Meet.</span></div>
        </div>""",
        unsafe_allow_html=True,
    )
    render_public_room_creator()
    with st.expander("Admin panel", expanded=False):
        render_admin_panel()


def render_sidebar() -> tuple[bool, int, bool]:
    st.sidebar.title("🔐 AntiTrust")
    st.sidebar.caption("Kontrol cepat sesi. Di HP, sidebar bisa dibuka dari ikon menu Streamlit.")
    # Auto refresh sengaja dibuat aktif secara default agar nyaman di HP.
    # Komponen refresh ditempatkan dekat area chat, bukan di awal halaman, supaya fokus tetap ke pesan.
    auto_refresh = True
    interval = st.sidebar.selectbox("Refresh chat setiap", [2, 5, 8, 10, 15, 30, 60], index=0, help="Semakin kecil, chat terasa lebih real-time tetapi halaman lebih sering refresh.")
    sound = st.sidebar.toggle("Bunyikan pesan masuk", value=True)
    if st.sidebar.button("Refresh sekarang", use_container_width=True):
        st.rerun()
    st.sidebar.divider()
    st.sidebar.caption("Tips: gunakan Pusat kontrol room untuk invite, Google Meet, peserta, file, dan aksi keamanan.")
    return auto_refresh, interval, sound


def render_message_focus_marker() -> None:
    st.markdown('<div id="antitrust-message-focus" class="message-focus-anchor"></div>', unsafe_allow_html=True)


def render_compose_focus_marker() -> None:
    st.markdown('<div id="antitrust-compose-focus" class="message-compose-anchor"></div>', unsafe_allow_html=True)


def render_mobile_message_focus() -> None:
    """Keep mobile users focused on the message section after auto refresh reruns."""
    components.html(
        """
        <script>
        (function(){
          try {
            const parentWindow = window.parent;
            const parentDoc = parentWindow && parentWindow.document;
            if (!parentDoc) return;
            const anchor = parentDoc.getElementById('antitrust-compose-focus') || parentDoc.getElementById('antitrust-message-focus');
            if (!anchor) return;
            const isMobile = parentWindow.innerWidth <= 760;
            if (!isMobile) return;
            setTimeout(function(){
              anchor.scrollIntoView({block: 'end', inline: 'nearest', behavior: 'auto'});
            }, 90);
          } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )


def render_room_invite_panel(room: str, username: str) -> None:
    with st.container(border=False):
        room_left = room_seconds_left(room)
        config = get_room_config(room)
        if config.get("is_locked") and not room_creator_is_unlocked(room):
            st.warning("Room sedang dikunci. Pembuatan invite baru ditutup untuk peserta biasa.")
            return

        # Saat room hampir habis/berakhir, jangan render slider.
        # Streamlit slider akan error bila state lama lebih besar dari max_value baru
        # atau max_value turun menjadi 0 menjelang auto revoke.
        if room_left <= 0 or room_is_expired(room):
            st.warning("Room sudah habis. Invite link otomatis dinonaktifkan.")
            for key in ("room_invite_url", "room_invite_token", "room_invite_url_box", "room_invite_ttl"):
                st.session_state.pop(key, None)
            destroy_room_and_revoke(room)
            st.session_state.pop("active_room", None)
            st.session_state.pop("active_invite_token", None)
            st.rerun()
            return

        max_link_minutes = min(INVITE_MAX_TTL_MINUTES, max(1, (room_left + 59) // 60))

        # Jika sisa waktu room mengecil, state slider lama dapat berada di luar range.
        # Reset sebelum widget dibuat agar tidak memicu StreamlitAPIException.
        current_ttl = st.session_state.get("room_invite_ttl", min(30, max_link_minutes))
        try:
            current_ttl = int(current_ttl)
        except Exception:
            current_ttl = min(30, max_link_minutes)
        if current_ttl < 1 or current_ttl > max_link_minutes:
            st.session_state["room_invite_ttl"] = min(30, max_link_minutes)

        if room_left < 60:
            st.info("Sisa waktu room kurang dari 1 menit. Pembuatan invite link baru ditutup.")
        else:
            st.caption("Semua user bisa buat link. Maksimal mengikuti sisa waktu room.")
            ttl = st.slider(
                "Masa aktif link",
                min_value=1,
                max_value=int(max_link_minutes),
                value=int(st.session_state.get("room_invite_ttl", min(30, max_link_minutes))),
                key="room_invite_ttl",
            )
            if st.button("Create link", use_container_width=True):
                if room_is_expired(room):
                    destroy_room_and_revoke(room)
                    st.error("Room sudah kedaluwarsa dan direvoke.")
                    st.session_state.pop("active_room", None)
                    st.session_state.pop("active_invite_token", None)
                    st.rerun()
                safe_ttl = max(1, min(int(ttl), int(max_link_minutes)))
                token = create_invite(room, safe_ttl, username)
                st.session_state["room_invite_url"] = build_invite_url(token)
                st.session_state["room_invite_token"] = token
                st.success("Invite link dibuat.")

        if st.session_state.get("room_invite_url"):
            render_expiring_invite_link(
                url_key="room_invite_url",
                token_key="room_invite_token",
                input_key="room_invite_url_box",
                label="Sisa waktu invite link",
                password=st.session_state.get(room_share_password_session_key(room)),
            )


def clear_destroy_countdown() -> None:
    for key in ("destroy_pending_room", "destroy_countdown_until"):
        st.session_state.pop(key, None)


def render_video_call_panel(room: str, username: str) -> None:
    data = get_room_video_call(room)
    current_url = str(data.get("url", "") or "")
    current_note = str(data.get("session_note", DEFAULT_VIDEO_SESSION_NOTE) or DEFAULT_VIDEO_SESSION_NOTE)
    current_visible = bool(data.get("visible", False))

    st.markdown("### 🎥 Google Meet")
    st.caption("Simpan link Google Meet di sini. Peserta hanya melihat tombol Join saat pembuat menampilkannya.")

    if current_url and current_visible and not room_is_expired(room):
        st.success("Link Google Meet aktif dan terlihat oleh peserta.")
        st.link_button("Buka Google Meet", current_url, use_container_width=True)
        st.caption(current_note)
    elif current_url:
        st.warning("Link Google Meet sudah disimpan, tetapi belum ditampilkan ke peserta. Pembuat bisa menekan Mulai/Tampilkan Video Call.")
        if room_creator_is_unlocked(room):
            st.link_button("Buka Google Meet sebagai pembuat", current_url, use_container_width=True)
    else:
        st.info("Belum ada link Google Meet. Pembuat room bisa menambahkan link agar peserta langsung join dari panel ini.")

    if not render_room_creator_unlock(room, "video_call_panel"):
        return

    with st.form(f"video_call_form::{room_key(room)}"):
        meet_url = st.text_input("Link Google Meet", value=current_url, placeholder="https://meet.google.com/abc-defg-hij")
        note = st.text_area("Catatan sesi", value=current_note, max_chars=240, height=76)
        visible = st.checkbox("Tampilkan tombol Join ke peserta", value=current_visible, help="Matikan jika link belum siap atau sesi belum dimulai.")
        save_clicked = st.form_submit_button("Simpan info video call", use_container_width=True)
    if save_clicked:
        clean_url = sanitize_gmeet_url(meet_url)
        if meet_url.strip() and not clean_url:
            st.warning("Masukkan link Google Meet yang valid, contoh: https://meet.google.com/abc-defg-hij")
            return
        save_room_video_call(room, clean_url, note, visible=visible, actor=username)
        st.success("Info Google Meet disimpan.")
        st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Mulai/Tampilkan", use_container_width=True, disabled=not bool(current_url), key=f"show_meet_info::{room_key(room)}"):
            save_room_video_call(room, current_url, current_note, visible=True, actor=username)
            st.rerun()
    with col2:
        if st.button("Kirim info ke chat", use_container_width=True, disabled=not bool(current_url), key=f"post_meet_info::{room_key(room)}"):
            text = (
                "Untuk koneksi video call bisa menggunakan Google Meet. "
                "Sesi mengikuti waktu chat/room aktif. "
                f"Link: {current_url}"
            )
            if not rate_limited("video_call_info"):
                append_text(room, username, text, 0)
                append_audit_event(room, "video_call_posted", username, "Info Google Meet dikirim ke chat.")
                st.rerun()
    with col3:
        if st.button("Hapus GMeet", use_container_width=True, disabled=not bool(current_url), key=f"clear_meet_info::{room_key(room)}"):
            save_room_video_call(room, "", DEFAULT_VIDEO_SESSION_NOTE, visible=False, actor=username)
            st.success("Link Google Meet dihapus dari room.")
            st.rerun()


def render_room_actions(room: str, username: str) -> None:
    with st.container(border=False):
        st.caption("Keluar room dinonaktifkan agar identitas tidak bisa direset.")

        if not render_room_creator_unlock(room, "revoke_room_actions"):
            return

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
            st.success(f"Room direvoke. {count} pesan/packet dihapus dan {revoked} invite link direvoke.")
            st.rerun()

        confirm = st.checkbox("Saya paham: room, pesan, packet, dan invite link akan direvoke/dihapus", key="destroy_room_confirm")
        if st.button("Revoke room + hapus chat", type="primary", use_container_width=True, disabled=not confirm):
            st.session_state["destroy_pending_room"] = room
            st.session_state["destroy_countdown_until"] = now_epoch() + 3
            st.rerun()


def render_room_settings(room: str) -> None:
    config = get_room_config(room)
    current = choice_from_minutes(config.get("auto_destroy_minutes"))
    with st.expander("Pengaturan"):
        st.caption("Opsional: percepat destroy jika room kosong.")
        if not render_room_creator_unlock(room, "room_settings"):
            return
        choice = st.selectbox("Auto-destroy jika room kosong", AUTO_DESTROY_CHOICES, index=AUTO_DESTROY_CHOICES.index(current) if current in AUTO_DESTROY_CHOICES else 3)
        if st.button("Simpan pengaturan", use_container_width=True):
            config["auto_destroy_minutes"] = parse_destroy_choice(choice)
            push_audit_event_to_config(config, "auto_destroy_updated", "pembuat", f"Auto-destroy diubah menjadi {choice}.")
            save_room_config(room, config)
            st.success("Pengaturan disimpan.")

def render_room_access_control(room: str, username: str) -> None:
    config = get_room_config(room)
    st.markdown("### 🛡️ Kontrol akses room")
    locked = bool(config.get("is_locked"))
    max_participants = int(config.get("max_participants", DEFAULT_MAX_PARTICIPANTS) or DEFAULT_MAX_PARTICIPANTS)
    active_count = active_session_count(room)
    st.caption(f"Status: {'terkunci' if locked else 'terbuka'} · peserta aktif {active_count}/{max_participants}")

    if not render_room_creator_unlock(room, "access_control"):
        return

    col1, col2 = st.columns(2)
    with col1:
        if locked:
            if st.button("Unlock room", use_container_width=True, key=f"unlock_room::{room_key(room)}"):
                set_room_lock(room, False, username)
                st.success("Room dibuka kembali untuk peserta baru.")
                st.rerun()
        else:
            if st.button("Lock room", use_container_width=True, key=f"lock_room::{room_key(room)}"):
                set_room_lock(room, True, username)
                st.success("Room dikunci. Peserta baru tidak bisa masuk.")
                st.rerun()
    with col2:
        new_limit = st.number_input("Maks peserta", min_value=1, max_value=ROOM_MAX_PARTICIPANTS, value=max_participants, step=1, key=f"max_participants::{room_key(room)}")
        if st.button("Simpan limit", use_container_width=True, key=f"save_max_participants::{room_key(room)}"):
            update_room_max_participants(room, int(new_limit), username)
            st.success("Limit peserta diperbarui.")
            st.rerun()


def render_participant_panel(room: str, current_username: str) -> None:
    entries = get_room_online_entries(room)
    config = get_room_config(room)
    st.markdown("### 👥 Peserta aktif")
    st.caption(f"{len(entries)}/{config.get('max_participants', DEFAULT_MAX_PARTICIPANTS)} peserta aktif · status online diperbarui otomatis")
    if not entries:
        st.info("Belum ada peserta aktif.")
        return
    rows = []
    for entry in entries:
        name = normalize_display_name(entry.get("username", "")) or "unknown"
        is_me = bool(entry.get("is_me")) or canonical_display_name(name) == canonical_display_name(current_username)
        me = " · kamu" if is_me else ""
        seconds = int(entry.get('seconds_ago', 0))
        rows.append(
            '<div class="participant-item">'
            f'<b>{username_with_badge_html(name)}{html.escape(me)}</b>'
            f'<span>aktif {seconds} detik lalu</span>'
            '</div>'
        )
    st.markdown('<div class="participant-list">' + ''.join(rows) + '</div>', unsafe_allow_html=True)


def render_audit_log(room: str) -> None:
    events = list(reversed(get_room_audit_events(room)[-20:]))
    with st.expander("Audit ringan", expanded=False):
        st.caption("Log ini mencatat event keamanan tanpa menyimpan isi pesan chat.")
        if not events:
            st.caption("Belum ada event audit.")
            return
        for event in events:
            actor = f" · {event.get('actor')}" if event.get("actor") else ""
            detail = f" — {event.get('detail')}" if event.get("detail") else ""
            st.caption(f"{event.get('time','')} · {event.get('event','event')}{actor}{detail}")


def build_session_summary(room: str, messages: list[dict[str, Any]], username: str = "") -> str:
    config = get_room_config(room)
    video = get_room_video_call(room)
    counts: dict[str, int] = {}
    for msg in messages:
        msg_type = str(msg.get("type", "text"))
        counts[msg_type] = counts.get(msg_type, 0) + 1
    lines = [
        f"# Ringkasan sesi AntiTrust",
        "",
        f"Room dibuat: {datetime.fromtimestamp(int(config.get('created_at', now_epoch())), WIB).strftime('%Y-%m-%d %H:%M:%S WIB')}",
        f"Sisa waktu saat ringkasan dibuat: {format_room_time_left(room_seconds_left(room))}",
        f"Dibuat oleh: {username or 'user'}",
        f"Status lock: {'terkunci' if config.get('is_locked') else 'terbuka'}",
        f"Batas peserta: {config.get('max_participants', DEFAULT_MAX_PARTICIPANTS)}",
        f"Google Meet: {'aktif/terlihat' if video.get('url') and video.get('visible') else ('tersimpan tapi tersembunyi' if video.get('url') else 'belum diset')}",
        "",
        "## Statistik pesan",
    ]
    if counts:
        for key, value in sorted(counts.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- Belum ada pesan.")

    pinned_id = str(config.get("pinned_message_id", "") or "")
    if pinned_id:
        pinned = next((m for m in messages if str(m.get("id")) == pinned_id), None)
        if pinned:
            lines += ["", "## Pesan pin", f"- {message_summary(pinned, room)}"]

    checklists = [m for m in messages if str(m.get("type")) == "checklist"]
    if checklists:
        lines += ["", "## Checklist"]
        for msg in checklists[-5:]:
            title = decrypt_room_text(room, str(msg.get("title", "Checklist")))
            items = msg.get("items") if isinstance(msg.get("items"), list) else []
            checked = msg.get("checked") if isinstance(msg.get("checked"), dict) else {}
            done = sum(1 for i in range(len(items)) if checked.get(str(i)))
            lines.append(f"- {title}: {done}/{len(items)} selesai")

    polls = [m for m in messages if str(m.get("type")) == "poll"]
    if polls:
        lines += ["", "## Poll"]
        for msg in polls[-5:]:
            question = decrypt_room_text(room, str(msg.get("question", "Poll")))
            votes = msg.get("votes") if isinstance(msg.get("votes"), dict) else {}
            options = [decrypt_room_text(room, str(x)) for x in msg.get("options", []) if isinstance(x, str)]
            result = ", ".join(f"{opt}: {sum(1 for v in votes.values() if v == opt)}" for opt in options)
            lines.append(f"- {question}: {result}")

    recent_texts = [m for m in messages if str(m.get("type")) == "text"][-8:]
    if recent_texts:
        lines += ["", "## Pesan teks terbaru"]
        for msg in recent_texts:
            sender = normalize_display_name(msg.get("username", "unknown")) or "unknown"
            text = decrypt_room_text(room, str(msg.get("text", ""))).replace("\n", " ")[:240]
            lines.append(f"- {msg.get('time','')} · {sender}: {text}")

    lines += ["", "Catatan: ringkasan ini dibuat lokal dari pesan yang masih tersedia di room. Pesan one-time yang sudah dibuka/hapus tidak bisa diringkas."]
    return "\n".join(lines)


def render_session_summary(room: str, username: str, messages: list[dict[str, Any]]) -> None:
    st.markdown("**Ringkasan sesi**")
    summary = build_session_summary(room, messages, username)
    st.text_area("Preview ringkasan", value=summary, height=220, key=f"summary_preview::{room_key(room)}")
    st.download_button(
        "Download summary .md",
        data=summary.encode("utf-8"),
        file_name=f"antitrust_summary_{slug(room)}_{datetime.now(WIB).strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )


def render_panic(room: str) -> None:
    st.markdown('<div class="danger-box"><b>Hapus Chat</b> <span class="muted">hapus semua pesan/packet room aktif tanpa revoke room.</span></div>', unsafe_allow_html=True)
    if not render_room_creator_unlock(room, "panic_delete_chat"):
        return
    confirm = st.checkbox("Saya paham tindakan ini menghapus pesan room aktif", key="panic_delete_confirm")
    if st.button("Hapus chat sekarang", type="primary", use_container_width=True, disabled=not confirm):
        count = panic_destroy(room)
        st.success(f"Berhasil menghapus {count} pesan/packet.")
        st.rerun()


def prepare_messages_for_render(room: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    config = get_room_config(room)
    pinned_id = config.get("pinned_message_id", "")
    prepared = []
    for msg in messages:
        copy_msg = dict(msg)
        copy_msg["_pinned"] = bool(pinned_id and str(copy_msg.get("id")) == pinned_id)
        prepared.append(copy_msg)

    # Tambahkan pesan virtual dari sistem saat sisa waktu room tinggal 30 detik.
    # Pesan ini tidak ditulis ke chat_rooms.json, jadi tidak menumpuk tiap detik.
    left = room_seconds_left(room)
    if 0 <= left <= 30:
        prepared.append({
            "id": f"system-room-countdown-{config.get('room_key', room_key(room))}-{config.get('expires_at', 0)}",
            "type": "system_countdown",
            "username": "System",
            "time": now_wib_label(),
            "seconds_left": int(left),
            "created_at": now_epoch(),
            "expires_at": int(config.get("expires_at", 0) or 0),
        })
    return prepared


def render_pinned_message(room: str, messages: list[dict[str, Any]]) -> None:
    pinned_id = get_room_config(room).get("pinned_message_id", "")
    if not pinned_id:
        return
    msg = next((m for m in messages if str(m.get("id")) == pinned_id), None)
    if not msg:
        set_pinned_message(room, "")
        return
    st.markdown(f'<div class="pinned-card"><b>📌 Pesan penting</b><br><span class="muted">{html.escape(message_summary(msg, room))}</span></div>', unsafe_allow_html=True)


def render_feature_panel(room: str, username: str, messages: list[dict[str, Any]]) -> None:
    with st.container(border=False):
        tab_secret, tab_poll, tab_check, tab_react, tab_pin, tab_summary = st.tabs(["🔒 Secret", "📊 Poll", "☑️ Checklist", "😊 React", "📌 Pin", "📝 Summary"])
        with tab_secret:
            secret_messages = [m for m in messages if str(m.get("type")) in {"secret_note", "one_time"}]
            if not secret_messages:
                st.caption("Belum ada Secret Note atau One-Time Message.")
            else:
                msg_map = {str(m.get("id")): m for m in reversed(secret_messages)}
                selected = st.selectbox("Pilih pesan rahasia", list(msg_map.keys()), format_func=lambda mid: message_summary(msg_map[mid], room), key="secret_select")
                if st.button("Buka pesan", use_container_width=True, key="open_secret_btn"):
                    msg = msg_map[selected]
                    st.session_state["opened_secret_text"] = decrypt_room_text(room, str(msg.get("text", "")))
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
                selected_poll = st.selectbox("Pilih poll", list(poll_map.keys()), format_func=lambda mid: message_summary(poll_map[mid], room), key="poll_select")
                msg = poll_map[selected_poll]
                question = decrypt_room_text(room, str(msg.get("question", "")))
                options = [decrypt_room_text(room, str(x)) for x in msg.get("options", []) if isinstance(x, str)]
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
                selected_list = st.selectbox("Pilih checklist", list(list_map.keys()), format_func=lambda mid: message_summary(list_map[mid], room), key="check_select")
                msg = list_map[selected_list]
                st.write(f"**{decrypt_room_text(room, str(msg.get('title', 'Checklist')))}**")
                items = [decrypt_room_text(room, str(x)) for x in msg.get("items", []) if isinstance(x, str)]
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
                selected_msg = st.selectbox("Pilih pesan", list(msg_map.keys()), format_func=lambda mid: message_summary(msg_map[mid], room), key="react_select")
                emoji = st.radio("Reaction", REACTION_CHOICES, horizontal=True, key="react_emoji")
                if st.button("Toggle reaction", use_container_width=True, key="react_btn"):
                    add_reaction(room, selected_msg, username, emoji)
                    st.rerun()
        with tab_pin:
            if not messages:
                st.caption("Belum ada pesan.")
            else:
                msg_map = {str(m.get("id")): m for m in reversed(messages)}
                selected_pin = st.selectbox("Pilih pesan untuk pin", list(msg_map.keys()), format_func=lambda mid: message_summary(msg_map[mid], room), key="pin_select")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Pin", use_container_width=True, key="pin_btn"):
                        set_pinned_message(room, selected_pin)
                        append_audit_event(room, "message_pinned", username, "Pesan penting dipin.")
                        st.rerun()
                with col_b:
                    if st.button("Unpin", use_container_width=True, key="unpin_btn"):
                        set_pinned_message(room, "")
                        append_audit_event(room, "message_unpinned", username, "Pin pesan dilepas.")
                        st.rerun()
        with tab_summary:
            render_session_summary(room, username, messages)


def render_message_form(room: str, username: str) -> None:
    with st.container(border=True):
        st.markdown("### 💬 Kirim pesan")
        tab_text, tab_ping, tab_special, tab_self, tab_img, tab_voice, tab_doc = st.tabs(["💬 Teks", "📡 Ping", "🔒 Secret", "⏳ Hilang", "🖼️ Gambar", "🎙️ Voice", "📎 Dokumen"])
        with tab_text:
            with st.form("text-message", clear_on_submit=True):
                message = st.text_input(
                    "Pesan",
                    placeholder="Tulis pesan lalu tekan Enter...",
                    max_chars=MAX_TEXT_LENGTH,
                    key="text_message_enter_input",
                )
                submitted = st.form_submit_button("Kirim", use_container_width=True)
                if submitted:
                    clean_message = (message or "").strip()
                    if clean_message and not rate_limited("text"):
                        append_text(room, username, clean_message, 0)
                        st.rerun()
        with tab_self:
            with st.form("self-destruct-message", clear_on_submit=True):
                sd_message = st.text_input(
                    "Pesan self-destruct",
                    placeholder="Tulis pesan sementara lalu tekan Enter...",
                    max_chars=MAX_TEXT_LENGTH,
                    key="self_destruct_message_input",
                )
                ttl_label = st.selectbox(
                    "Hilang setelah",
                    list(MESSAGE_SELF_DESTRUCT_CHOICES.keys())[1:],
                    index=0,
                    key="self_destruct_ttl",
                )
                ttl_seconds = int(MESSAGE_SELF_DESTRUCT_CHOICES.get(ttl_label, 60))
                submitted = st.form_submit_button("Kirim self-destruct", use_container_width=True)
                if submitted:
                    clean_message = (sd_message or "").strip()
                    if clean_message and not rate_limited("self_destruct"):
                        append_text(room, username, clean_message, ttl_seconds)
                        st.rerun()
        with tab_ping:
            st.caption("Kirim ping cepat untuk menarik perhatian user lain di room.")
            if st.button("📡 Ping room", use_container_width=True, key="send_ping_btn"):
                if not rate_limited("ping"):
                    append_ping(room, username)
                    st.toast("Ping terkirim.", icon="📡")
                    st.rerun()
        with tab_special:
            kind = st.selectbox("Jenis", ["Secret Note", "One-Time Message", "Poll Cepat", "Location Pin", "Checklist Bersama"], key="special_kind")
            if kind in {"Secret Note", "One-Time Message"}:
                with st.form("special-secret", clear_on_submit=True):
                    secret_text = st.text_area("Isi", height=58, max_chars=MAX_TEXT_LENGTH)
                    submitted = st.form_submit_button("Kirim secret", use_container_width=True)
                    if submitted and not rate_limited("secret"):
                        msg_type = "secret_note" if kind == "Secret Note" else "one_time"
                        append_special_message(room, username, msg_type, {"text": encrypt_room_text(room, secret_text.strip()[:MAX_TEXT_LENGTH]), "crypto_version": ROOM_CRYPTO_VERSION if room_encryption_enabled(room) else 1}, 0)
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
                            append_special_message(room, username, "poll", {"question": encrypt_room_text(room, question.strip()[:160]), "options": [encrypt_room_text(room, o) for o in options], "votes": {}, "crypto_version": ROOM_CRYPTO_VERSION if room_encryption_enabled(room) else 1}, 0)
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
                            append_special_message(room, username, "location", {"label": encrypt_room_text(room, (label or "Lokasi").strip()[:80]), "url": encrypt_room_text(room, url.strip()[:500]), "crypto_version": ROOM_CRYPTO_VERSION if room_encryption_enabled(room) else 1}, 0)
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
                            append_special_message(room, username, "checklist", {"title": encrypt_room_text(room, (title or "Checklist").strip()[:120]), "items": [encrypt_room_text(room, i) for i in items], "checked": {}, "crypto_version": ROOM_CRYPTO_VERSION if room_encryption_enabled(room) else 1}, 0)
                            st.rerun()
        with tab_img:
            image_reset = int(st.session_state.get("image_upload_reset", 0))
            image = st.file_uploader("Image", type=list(ALLOWED_IMAGE_TYPES), key=f"image_upload::{image_reset}")
            if st.button("Kirim image", use_container_width=True, key=f"send_image::{image_reset}"):
                if not rate_limited("image"):
                    payload = validate_upload(image, "image")
                    if payload:
                        append_media(room, username, "image", *payload)
                        st.session_state["image_upload_reset"] = image_reset + 1
                        st.rerun()
        with tab_voice:
            audio_reset = int(st.session_state.get("audio_upload_reset", 0))
            audio = st.file_uploader("Audio", type=list(ALLOWED_AUDIO_TYPES), key=f"audio_upload::{audio_reset}")
            recorded = st.audio_input("Rekam suara", key=f"audio_record::{audio_reset}") if hasattr(st, "audio_input") else None
            if st.button("Kirim voice", use_container_width=True, key=f"send_voice::{audio_reset}"):
                if not rate_limited("audio"):
                    payload = validate_upload(recorded or audio, "audio")
                    if payload:
                        append_media(room, username, "audio", *payload)
                        st.session_state["audio_upload_reset"] = audio_reset + 1
                        st.rerun()
        with tab_doc:
            doc_reset = int(st.session_state.get("document_upload_reset", 0))
            doc = st.file_uploader("Document", type=list(ALLOWED_DOCUMENT_TYPES), key=f"document_upload::{doc_reset}")
            if st.button("Kirim document", use_container_width=True, key=f"send_document::{doc_reset}"):
                if not rate_limited("document"):
                    payload = validate_upload(doc, "document")
                    if payload:
                        append_media(room, username, "document", *payload)
                        st.session_state["document_upload_reset"] = doc_reset + 1
                        st.rerun()



def render_packet_viewer(room: str, messages: list[dict[str, Any]]) -> None:
    packets = [msg for msg in messages if str(msg.get("type", "")) in {"image", "audio", "document"}]
    if not packets:
        st.caption("Belum ada file/packet di room ini.")
        return

    st.markdown("**Packet Viewer**")
    packet_map = {str(msg.get("id")): msg for msg in packets}
    selected = st.selectbox(
        "Pilih file",
        options=list(reversed(list(packet_map.keys()))),
        format_func=lambda mid: f"{packet_map[mid].get('type','packet')} · {packet_map[mid].get('filename','packet')} · {format_bytes(packet_map[mid].get('size_bytes',0))}",
        key=f"packet_select::{room}",
    )
    msg = packet_map[selected]

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Buka", use_container_width=True, key=f"open_packet::{room}::{selected}"):
            st.session_state[f"opened::{room}"] = selected
    with c2:
        if st.button("Tutup", use_container_width=True, key=f"close_packet::{room}::{selected}"):
            if st.session_state.get(f"opened::{room}") == selected:
                del st.session_state[f"opened::{room}"]
            st.rerun()

    if st.session_state.get(f"opened::{room}") != selected:
        st.caption("File asli baru didekripsi setelah tombol Buka ditekan.")
        return

    data = read_packet(room, str(msg.get("packet_path", "")))
    if data is None:
        st.error("Packet tidak ditemukan atau gagal didekripsi.")
        return

    mime = str(msg.get("mime_type", "application/octet-stream"))
    filename = safe_filename(str(msg.get("filename", "packet.bin")))
    if msg.get("type") == "image":
        st.image(data, caption=filename, use_container_width=True)
    elif msg.get("type") == "audio":
        st.audio(data, format=mime)
    else:
        st.caption(filename)

    st.download_button(
        "Download",
        data=data,
        file_name=filename,
        mime=mime,
        use_container_width=True,
        key=f"download_packet::{room}::{selected}",
    )

def render_online_users(entries: list[dict[str, Any]], current_username: str) -> None:
    """Render compact horizontal online-user chips for desktop and mobile."""
    if not entries:
        st.markdown('<div class="online-label">Tidak ada user online.</div>', unsafe_allow_html=True)
        return
    chips = []
    seen: set[str] = set()
    for entry in entries[:24]:
        name = normalize_display_name(entry.get("username", ""))
        if not name:
            continue
        ident = str(entry.get("session_id", "")) or canonical_display_name(name)
        if ident in seen:
            continue
        seen.add(ident)
        hue = user_hue(name)
        is_me = bool(entry.get("is_me")) or canonical_display_name(name) == canonical_display_name(current_username)
        cls = "online-chip online-me" if is_me else "online-chip"
        me = " · kamu" if is_me else ""
        safe_name = username_with_badge_html(name)
        chips.append(
            f'<span class="{cls}" style="--user-hue:{hue}">'
            f'<span class="online-dot"></span><span>{safe_name}{html.escape(me)}</span></span>'
        )
    label = f'<span class="online-label">Online {len(chips)}</span>'
    st.markdown(f'<div class="online-strip">{label}{"".join(chips)}</div>', unsafe_allow_html=True)


def render_room_dashboard(room: str, active_count: int, username: str) -> None:
    config = get_room_config(room)
    video_call = get_room_video_call(room)
    locked = bool(config.get("is_locked"))
    max_participants = int(config.get("max_participants", DEFAULT_MAX_PARTICIPANTS) or DEFAULT_MAX_PARTICIPANTS)
    video_status = "Siap" if video_call.get("url") and video_call.get("visible") else ("Tersimpan" if video_call.get("url") else "Belum diset")
    lock_icon = "🔒" if locked else "🔓"
    lock_text = "Terkunci" if locked else "Terbuka"
    cards = [
        ("⏱️ Sisa room", format_room_time_left(room_seconds_left(room))),
        (f"{lock_icon} Akses", lock_text),
        ("👥 Peserta", f"{active_count}/{max_participants} aktif"),
        ("🎥 Google Meet", video_status),
    ]
    html_cards = ''.join(
        f'<div class="status-card"><b>{html.escape(title)}</b><span>{html.escape(value)}</span></div>'
        for title, value in cards
    )
    st.markdown(f'<div class="room-dashboard">{html_cards}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="help-strip"><span>Masuk sebagai <b>{username_with_badge_html(username)}</b>.</span>'
        '<span>Gunakan Pusat kontrol room untuk undangan, video, peserta, file, dan keamanan.</span></div>',
        unsafe_allow_html=True,
    )


def render_compact_room_panel(room: str, username: str, messages: list[dict[str, Any]]) -> None:
    with st.expander("Pusat kontrol room", expanded=True):
        st.markdown('<div class="panel-title"><b>Kelola sesi</b><span>Invite, video call, peserta, file, dan keamanan.</span></div>', unsafe_allow_html=True)
        tab_invite, tab_video, tab_participants, tab_features, tab_files, tab_security = st.tabs(["🔗 Undangan", "🎥 Video", "👥 Peserta", "✨ Fitur", "📎 File", "🛡️ Keamanan"])
        with tab_invite:
            render_room_invite_panel(room, username)
        with tab_video:
            render_video_call_panel(room, username)
        with tab_participants:
            render_participant_panel(room, username)
        with tab_features:
            render_feature_panel(room, username, messages)
        with tab_files:
            render_packet_viewer(room, messages)
        with tab_security:
            render_room_access_control(room, username)
            render_audit_log(room)
            render_room_actions(room, username)
            render_room_settings(room)
            render_panic(room)


def render_room_password_unlock(room: str) -> bool:
    """Wajibkan password room untuk membuka Fernet key room.

    Room lama tanpa room_fernet_salt tetap bisa dipakai tanpa langkah ini.
    """
    if not room_encryption_enabled(room):
        return True
    if get_room_fernet(room) is not None:
        st.caption("🔑 Key Fernet room aktif di sesi ini.")
        return True

    st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
    st.markdown('<div class="terminal-note">$ unlock_room_key --password-derived-fernet</div>', unsafe_allow_html=True)
    st.subheader("Unlock enkripsi room")
    st.caption("Masukkan password room yang diberikan pembuat. Password ini membuka isi room, bukan otomatis membuka aksi pembuat pada room baru.")
    blocked = room_password_block_seconds(room)
    if blocked > 0:
        st.warning(f"Terlalu banyak percobaan salah. Coba lagi dalam {format_countdown(blocked)}.")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    with st.form(f"room_crypto_unlock::{room_key(room)}"):
        password = st.text_input("Password room", type="password")
        submitted = st.form_submit_button("Unlock room", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    if not submitted:
        return False
    if remember_room_password(room, password):
        st.success("Room berhasil dibuka. Key Fernet unik aktif untuk sesi ini.")
        st.rerun()
        return True
    wait = room_password_block_seconds(room)
    st.error(f"Password room salah atau key tidak cocok.{f' Coba lagi dalam {format_countdown(wait)}.' if wait else ''}")
    return False

def render_room_join_gate(room: str) -> bool:
    reason = room_join_block_reason(room)
    if not reason:
        return True
    st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
    st.warning(reason)
    st.caption("Peserta yang sudah berada di room tetap bisa melanjutkan selama sesi browsernya aktif. Pembuat dapat membuka lock atau menaikkan limit dari perangkat yang sudah memiliki akses.")
    if room_has_owner_pin(room):
        render_room_creator_unlock(room, "join_gate")
    st.markdown('</div>', unsafe_allow_html=True)
    return False


def render_invite_expiry_redirect(seconds_left: int) -> None:
    """Client-only redirect when invite reaches zero without causing periodic Streamlit refresh."""
    left = max(0, int(seconds_left))
    if left <= 0:
        return
    components.html(
        f"""
        <script>
        (function(){{
          const delay = Math.max(1, {left}) * 1000 + 350;
          setTimeout(function(){{
            try {{
              const url = new URL(window.parent.location.href);
              if (url.searchParams.has('invite')) {{
                url.searchParams.delete('invite');
                window.parent.location.href = url.origin + url.pathname + (url.search ? url.search : '');
              }}
            }} catch(e) {{}}
          }}, delay);
        }})();
        </script>
        """,
        height=0,
    )


def main() -> None:
    ensure_dirs()
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
    st.markdown(CSS + UI_ENHANCEMENT_CSS, unsafe_allow_html=True)
    destroyed = purge_inactive_rooms()
    auto_refresh, interval, sound = render_sidebar()
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
    render_invite_expiry_redirect(current_invite_left)
    if not render_room_password_unlock(room):
        return
    if not render_room_join_gate(room):
        return
    # Jangan auto-refresh tiap detik; countdown berjalan di browser agar halaman tidak naik sendiri.
    username = get_locked_username(is_admin=bool(st.session_state.get("admin_ok")))
    if not username:
        return

    taken_by = username_taken_in_room(room, username)
    if taken_by:
        st.session_state.pop("username", None)
        st.session_state["username_conflict_message"] = (
            f"Nama '{taken_by}' sedang digunakan di room ini. Silakan isi username lain untuk lanjut chat."
        )
        st.rerun()

    if room_is_expired(room):
        destroy_room_and_revoke(room)
        st.error("Room sudah kedaluwarsa dan otomatis direvoke.")
        st.rerun()
    active_users = update_online(room, username)
    online_entries = get_room_online_entries(room)
    messages = load_messages(room)
    config = get_room_config(room)
    status = room_status_label(room, len(active_users))
    st.markdown(
        f'<div class="room-status-line"><span class="status-pill">{username_with_badge_html(username)}</span>'
        f'<span class="status-pill">{html.escape(status)}</span>'
        f'<span class="status-pill">Auto-destroy kosong: {choice_from_minutes(config.get("auto_destroy_minutes"))}</span></div>',
        unsafe_allow_html=True,
    )
    render_room_dashboard(room, len(active_users), username)
    render_online_users(online_entries, username)
    video_call = get_room_video_call(room)
    if video_call.get("url") and video_call.get("visible") and not room_is_expired(room):
        with st.container(border=True):
            st.markdown("**Video call:** Google Meet")
            st.caption(video_call.get("session_note", DEFAULT_VIDEO_SESSION_NOTE))
            st.link_button("Join Google Meet", video_call["url"], use_container_width=True)
    render_sound_notice(latest_foreign_signature(messages, username), sound)
    render_pinned_message(room, messages)
    render_compact_room_panel(room, username, messages)
    render_messages = prepare_messages_for_render(room, messages)
    render_message_focus_marker()
    # Height iframe dibuat pas dengan chat panel agar tidak ada ruang kosong besar
    # antara panel pesan dan form kirim.
    components.html(render_chat(render_messages, username, room), height=520, scrolling=False)
    render_message_form(room, username)
    render_compose_focus_marker()
    render_mobile_message_focus()
    if auto_refresh and st_autorefresh is not None:
        st_autorefresh(interval=interval * 1000, key="antitrust_message_refresh")


if __name__ == "__main__":
    main()
