"""
Gemini Multimodal Chat Bot
───────────────────────────
A production-grade chat interface powered by Google Gemini.
Supports text, image, and video conversations with persistent history.

Built with: Streamlit · google-genai · Pillow

Roles assigned (SOLID layered architecture):
  - Config Layer     → Environment, paths, model settings
  - Storage Layer    → Chat history persistence, file management
  - Gemini Layer     → API communication, multimodal content building
  - UI Layer         → Streamlit components, custom CSS, UX flows
  - App Layer        → Orchestrator binding everything together
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image as PILImage

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG LAYER
# ═══════════════════════════════════════════════════════════════════════════════

load_dotenv()

GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")

AVAILABLE_MODELS: List[str] = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro-exp-03-25",
]

DEFAULT_MODEL: str = "gemini-2.0-flash"

CHAT_HISTORY_DIR: Path = Path("chat_history")
UPLOAD_DIR: Path = Path("uploads")
MAX_VIDEO_SIZE_MB: int = 50
MAX_IMAGE_SIZE_MB: int = 10

ALLOWED_IMAGE_EXTENSIONS: set[str] = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}
ALLOWED_VIDEO_EXTENSIONS: set[str] = {"mp4", "mov", "mpeg", "mpg", "avi", "flv", "wmv", "webm"}

CHAT_HISTORY_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# STORAGE LAYER
# ═══════════════════════════════════════════════════════════════════════════════


def _chat_path(session_id: str) -> Path:
    return CHAT_HISTORY_DIR / f"{session_id}.json"


def _default_session_meta(title: str | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "title": title or "New Chat",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "model": DEFAULT_MODEL,
    }


def list_sessions() -> List[Dict[str, Any]]:
    """Return all saved chat sessions sorted by most-recently-updated first."""
    sessions: List[Dict[str, Any]] = []
    for fp in sorted(CHAT_HISTORY_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            sessions.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return sessions


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Load a single session by id, or None if missing/corrupt."""
    fp = _chat_path(session_id)
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_session(data: Dict[str, Any]) -> None:
    """Persist a chat session to disk."""
    data["updated_at"] = datetime.now().isoformat()
    _chat_path(data["id"]).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def delete_session(session_id: str) -> None:
    """Remove a chat session file."""
    fp = _chat_path(session_id)
    if fp.exists():
        fp.unlink()


def rename_session(session_id: str, new_title: str) -> None:
    """Update the title of an existing session."""
    data = load_session(session_id)
    if data is None:
        return
    data["title"] = new_title.strip() or "New Chat"
    save_session(data)


def cleanup_upload(filepath: Path) -> None:
    """Delete a previously uploaded file."""
    if filepath.exists():
        filepath.unlink()


# ═══════════════════════════════════════════════════════════════════════════════
# GEMINI LAYER
# ═══════════════════════════════════════════════════════════════════════════════


def get_client() -> genai.Client:
    """Return an authenticated Gemini client. Raises ValueError if no key."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in .env file.")
    return genai.Client(api_key=GEMINI_API_KEY)


def _upload_video(client: genai.Client, filepath: Path) -> types.File:
    """Upload a video file to Gemini and wait for processing to complete."""
    uploaded = client.files.upload(file=filepath)

    # Poll until the file is active or fails
    while uploaded.state.name == "PROCESSING":
        time.sleep(1.5)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name == "FAILED":
        raise RuntimeError(f"Video processing failed: {uploaded.name}")

    return uploaded


def _build_history(history: List[Dict[str, Any]]) -> List[types.Content]:
    """Convert our message history into google-genai Content list."""
    contents: List[types.Content] = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        parts = _parts_from_message(msg)
        if parts:
            contents.append(types.Content(role=role, parts=parts))
    return contents


def _parts_from_message(msg: Dict[str, Any]) -> List[types.Part]:
    """Build a list of Parts from one message dict."""
    parts: List[types.Part] = [types.Part(text=msg.get("text", ""))]
    for media in msg.get("media", []):
        fp = Path(media["path"])
        if not fp.exists():
            continue
        mime = media.get("mime_type", "image/png")
        data = fp.read_bytes()
        if media["type"] == "image":
            parts.append(types.Part(inline_data=types.Blob(mime_type=mime, data=data)))
        elif media["type"] == "video":
            # Videos cannot be inlined; reference by uploaded file uri
            parts.append(types.Part(file_data=types.FileData(file_uri=media["uri"])))
    return parts


def generate_response(
    model_name: str,
    history: List[Dict[str, Any]],
    user_text: str,
    new_media: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Send a message to Gemini and return the full (non-streaming) response text.
    Handles error cases and returns user-friendly messages.
    """
    client = get_client()

    current_parts: List[types.Part] = [types.Part(text=user_text)]

    # Append newly uploaded media to current message
    if new_media:
        for item in new_media:
            fp = Path(item["path"])
            if not fp.exists():
                continue
            raw = fp.read_bytes()
            if item["type"] == "image":
                current_parts.append(
                    types.Part(inline_data=types.Blob(mime_type=item["mime_type"], data=raw))
                )
            elif item["type"] == "video" and item.get("uri"):
                current_parts.append(
                    types.Part(file_data=types.FileData(file_uri=item["uri"]))
                )

    full_history = _build_history(history)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=full_history + [types.Content(role="user", parts=current_parts)],
        )
        return response.text if response and response.text else "_(No response from model)_"
    except Exception as exc:
        friendly = _friendly_error(exc)
        raise RuntimeError(friendly) from exc


def generate_response_stream(
    model_name: str,
    history: List[Dict[str, Any]],
    user_text: str,
    new_media: Optional[List[Dict[str, Any]]] = None,
):
    """
    Stream a response from Gemini, yielding text chunks.  Returns the full text
    at the end so the caller can save it to history.
    """
    client = get_client()

    current_parts: List[types.Part] = [types.Part(text=user_text)]

    if new_media:
        for item in new_media:
            fp = Path(item["path"])
            if not fp.exists():
                continue
            raw = fp.read_bytes()
            if item["type"] == "image":
                current_parts.append(
                    types.Part(inline_data=types.Blob(mime_type=item["mime_type"], data=raw))
                )
            elif item["type"] == "video" and item.get("uri"):
                current_parts.append(
                    types.Part(file_data=types.FileData(file_uri=item["uri"]))
                )

    full_history = _build_history(history)

    try:
        stream = client.models.generate_content_stream(
            model=model_name,
            contents=full_history + [types.Content(role="user", parts=current_parts)],
        )

        collected: List[str] = []
        for chunk in stream:
            if chunk.text:
                collected.append(chunk.text)
                yield chunk.text

        if not collected:
            yield "_(No response from model)_"

    except Exception as exc:
        friendly = _friendly_error(exc)
        yield f"⚠️ {friendly}"


def _friendly_error(exc: Exception) -> str:
    """Map common Gemini API exceptions to user-friendly messages."""
    msg = str(exc).lower()
    if "api key" in msg or "unauthorized" in msg or "permission" in msg:
        return (
            "**Invalid or missing API key.**\n\n"
            "Make sure your `.env` file contains a valid `GEMINI_API_KEY`."
        )
    if "quota" in msg or "rate limit" in msg or "429" in str(exc):
        return "**Rate limit hit.**\n\nPlease wait a moment before sending another message."
    if "safety" in msg or "blocked" in msg:
        return "**Content blocked by safety filters.**\n\nTry rephrasing your message."
    if "not found" in msg and "model" in msg:
        return "**Model not found.**\n\nThe selected model may have been deprecated. Try switching to another model."
    if "video" in msg and "too large" in msg:
        return "**Video too large.**\n\nPlease upload a video smaller than 50 MB."
    return f"**Something went wrong.**\n\n```\n{exc}\n```"


# ═══════════════════════════════════════════════════════════════════════════════
# UI LAYER
# ═══════════════════════════════════════════════════════════════════════════════

PAGE_CSS = """
<style>
    /* ── Global reset & typography ── */
    #root, .stApp {
        background: #0f1117;
    }
    .main > div {
        background: #0f1117;
    }
    .block-container {
        padding: 1.5rem 2rem 3rem;
    }

    /* ── Chat message containers ── */
    .chat-message {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1.75rem;
        animation: fadeIn 0.3s ease;
    }
    .chat-message.user {
        flex-direction: row-reverse;
    }

    .chat-avatar {
        width: 36px;
        height: 36px;
        flex-shrink: 0;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }
    .chat-avatar.ai {
        background: linear-gradient(135deg, #4285f4, #34a853);
        color: #fff;
    }
    .chat-avatar.user {
        background: linear-gradient(135deg, #fbbc05, #ea4335);
        color: #fff;
    }

    .chat-bubble {
        max-width: 75%;
        padding: 0.75rem 1.25rem;
        border-radius: 1.25rem;
        line-height: 1.6;
        font-size: 0.92rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    }
    .chat-bubble.ai {
        background: #1e2029;
        color: #e8eaed;
        border-bottom-left-radius: 0.25rem;
        border: 1px solid #2a2d37;
    }
    .chat-bubble.user {
        background: linear-gradient(135deg, #1a73e8, #1557b0);
        color: #fff;
        border-bottom-right-radius: 0.25rem;
    }

    .chat-bubble img {
        max-width: 100%;
        border-radius: 0.5rem;
        margin-top: 0.5rem;
    }
    .chat-bubble video {
        max-width: 100%;
        border-radius: 0.5rem;
        margin-top: 0.5rem;
    }

    /* ── Status / info indicators ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.78rem;
        font-weight: 500;
        background: #1e2029;
        color: #9aa0a6;
        border: 1px solid #2a2d37;
    }

    .media-preview {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-bottom: 0.5rem;
    }
    .media-preview-item {
        position: relative;
        width: 80px;
        height: 80px;
        border-radius: 0.5rem;
        overflow: hidden;
        border: 1px solid #2a2d37;
    }
    .media-preview-item img, .media-preview-item video {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    /* ── Animations ── */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* ── Sidebar tweaks ── */
    section[data-testid="stSidebar"] {
        background: #161822 !important;
        border-right: 1px solid #2a2d37;
    }
    section[data-testid="stSidebar"] .stButton button {
        background: #1e2029;
        border: 1px solid #2a2d37;
        color: #e8eaed;
        border-radius: 0.5rem;
        width: 100%;
        text-align: left;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: #2a2d37;
        border-color: #4285f4;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #2a2d37; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #3a3d47; }
</style>
"""


def render_custom_css() -> None:
    st.markdown(PAGE_CSS, unsafe_allow_html=True)


def render_chat_message(role: str, content: str, media: Optional[List[Dict]] = None) -> None:
    """Render a single chat message bubble with avatar in the main thread."""
    avatar_icon = "🤖" if role == "assistant" else "👤"
    avatar_class = "ai" if role == "assistant" else "user"
    bubble_class = "ai" if role == "assistant" else "user"

    # Render media previews first
    media_html = ""
    if media:
        for m in media:
            fp = Path(m["path"])
            if not fp.exists():
                continue
            if m["type"] == "image":
                media_html += f'<img src="data:{m["mime_type"]};base64,{_img_to_b64(fp)}" />'
            elif m["type"] == "video":
                media_html += (
                    f'<video controls preload="metadata" style="max-width:100%;border-radius:8px;margin-top:6px;">'
                    f'<source src="data:{m["mime_type"]};base64,{_file_to_b64(fp)}" type="{m["mime_type"]}">'
                    f'</video>'
                )

    st.markdown(
        f"""
        <div class="chat-message {role}">
            <div class="chat-avatar {avatar_class}">{avatar_icon}</div>
            <div class="chat-bubble {bubble_class}">
                {content}
                {media_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _img_to_b64(path: Path) -> str:
    import base64
    return base64.b64encode(path.read_bytes()).decode()


def _file_to_b64(path: Path) -> str:
    import base64
    return base64.b64encode(path.read_bytes()).decode()


def render_sidebar() -> None:
    """Build the sidebar with chat listing, model picker, and new-chat button."""
    with st.sidebar:
        st.markdown("## 🤖 Gemini Chat")
        st.markdown("---")

        # New chat
        if st.button("➕ New Chat", use_container_width=True, key="new_chat_btn"):
            _reset_session()
            st.rerun()

        st.markdown("---")
        st.markdown("### 💬 Chat History")
        sessions = list_sessions()

        if not sessions:
            st.caption("No saved chats yet.")
        else:
            for session in sessions:
                sid = session["id"]
                title = session.get("title", "New Chat")
                if st.button(
                    f"  {title[:42]}",
                    use_container_width=True,
                    key=f"session_{sid}",
                ):
                    if sid != st.session_state.get("session_id", ""):
                        _load_existing_session(sid)
                        st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Settings")

        model_idx = (
            AVAILABLE_MODELS.index(st.session_state.get("model", DEFAULT_MODEL))
            if st.session_state.get("model") in AVAILABLE_MODELS
            else 0
        )
        chosen = st.selectbox(
            "Model",
            options=AVAILABLE_MODELS,
            index=model_idx,
            label_visibility="collapsed",
        )
        if chosen != st.session_state.get("model"):
            st.session_state["model"] = chosen
            # Update the session data model field
            session_data = st.session_state.get("session_data")
            if session_data:
                session_data["model"] = chosen
                save_session(session_data)

        # Danger zone
        with st.expander("🗑️ Danger Zone", expanded=False):
            if st.button("Delete current chat", use_container_width=True, type="secondary"):
                _delete_current_chat()
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _init_session_state() -> None:
    """Ensure all required session state keys exist."""
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "session_data" not in st.session_state:
        st.session_state["session_data"] = _default_session_meta(st.session_state["session_id"])
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "pending_media" not in st.session_state:
        st.session_state["pending_media"] = []
    if "model" not in st.session_state:
        st.session_state["model"] = DEFAULT_MODEL
    if "processing" not in st.session_state:
        st.session_state["processing"] = False


def _reset_session(title: str | None = None) -> None:
    """Start a fresh chat session."""
    st.session_state["session_id"] = str(uuid.uuid4())
    st.session_state["session_data"] = _default_session_meta(title or "New Chat")
    st.session_state["messages"] = []
    st.session_state["pending_media"] = []
    st.session_state["processing"] = False


def _load_existing_session(session_id: str) -> None:
    """Load a saved session into state."""
    data = load_session(session_id)
    if data is None:
        st.error("Could not load that chat session.")
        return
    st.session_state["session_id"] = data["id"]
    st.session_state["session_data"] = data
    st.session_state["messages"] = data.get("messages", [])
    st.session_state["model"] = data.get("model", DEFAULT_MODEL)
    st.session_state["pending_media"] = []
    st.session_state["processing"] = False


def _delete_current_chat() -> None:
    """Remove the current session and start fresh."""
    sid = st.session_state.get("session_id", "")
    if sid:
        delete_session(sid)
    _reset_session()


def _save_current_session() -> None:
    """Persist current in-memory messages to disk."""
    data = st.session_state.get("session_data", _default_session_meta())
    data["messages"] = st.session_state.get("messages", [])
    data["model"] = st.session_state.get("model", DEFAULT_MODEL)
    # Auto-title from first user message if still default
    if data["title"] == "New Chat" and data["messages"]:
        first_user = next(
            (m for m in data["messages"] if m["role"] == "user"), None
        )
        if first_user:
            text = first_user.get("text", "")
            data["title"] = (text[:48] + "…") if len(text) > 48 else text
    st.session_state["session_data"] = data
    save_session(data)


# ═══════════════════════════════════════════════════════════════════════════════
# MEDIA HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════


def handle_image_upload(uploaded_file) -> Optional[Dict[str, Any]]:
    """Validate and save an uploaded image. Returns media dict or None."""
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        st.error(f"Unsupported image format: `.{ext}`. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}")
        return None

    file_size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
    if file_size_mb > MAX_IMAGE_SIZE_MB:
        st.error(f"Image too large ({file_size_mb:.1f} MB). Max: {MAX_IMAGE_SIZE_MB} MB.")
        return None

    dest = UPLOAD_DIR / f"img_{uuid.uuid4().hex}_{uploaded_file.name}"
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return {
        "type": "image",
        "path": str(dest.resolve()),
        "mime_type": uploaded_file.type or f"image/{ext}",
        "file_name": uploaded_file.name,
    }


def handle_video_upload(uploaded_file) -> Optional[Dict[str, Any]]:
    """Validate and save an uploaded video, then upload to Gemini File API."""
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        st.error(f"Unsupported video format: `.{ext}`.")
        return None

    file_size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
    if file_size_mb > MAX_VIDEO_SIZE_MB:
        st.error(f"Video too large ({file_size_mb:.1f} MB). Max: {MAX_VIDEO_SIZE_MB} MB.")
        return None

    dest = UPLOAD_DIR / f"vid_{uuid.uuid4().hex}_{uploaded_file.name}"
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Upload to Gemini
    try:
        client = get_client()
        with st.spinner("⏳ Uploading and processing video…"):
            gemini_file = _upload_video(client, dest)
    except Exception as exc:
        cleanup_upload(dest)
        friendly = _friendly_error(exc)
        st.error(friendly)
        return None

    # Keep the local copy for preview; Gemini keeps its own copy
    return {
        "type": "video",
        "path": str(dest.resolve()),
        "mime_type": uploaded_file.type or f"video/{ext}",
        "file_name": uploaded_file.name,
        "uri": gemini_file.uri,
    }


def render_media_uploader() -> None:
    """Display the media upload section in the sidebar or main area."""
    with st.sidebar:
        st.markdown("### 📎 Attach Media")

        img_file = st.file_uploader(
            "Upload Image",
            type=list(ALLOWED_IMAGE_EXTENSIONS),
            key="img_uploader",
            label_visibility="collapsed",
        )
        if img_file is not None:
            media = handle_image_upload(img_file)
            if media:
                st.session_state.setdefault("pending_media", []).append(media)
                st.success(f"✅ Image added: {img_file.name}")
                st.rerun()

        vid_file = st.file_uploader(
            "Upload Video",
            type=list(ALLOWED_VIDEO_EXTENSIONS),
            key="vid_uploader",
            label_visibility="collapsed",
        )
        if vid_file is not None:
            media = handle_video_upload(vid_file)
            if media:
                st.session_state.setdefault("pending_media", []).append(media)
                st.success(f"✅ Video added: {vid_file.name}")
                st.rerun()

        # Show pending media
        pending = st.session_state.get("pending_media", [])
        if pending:
            st.markdown("**Pending attachments:**")
            for i, m in enumerate(pending):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption(f"{'🖼️' if m['type']=='image' else '🎬'} {m['file_name'][:30]}")
                with col2:
                    if st.button("✕", key=f"remove_media_{i}"):
                        cleanup_upload(Path(m["path"]))
                        pending.pop(i)
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# APP LAYER  —  ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

# ── Streamlit page config (must be first Streamlit call) ──
st.set_page_config(
    page_title="Gemini Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API key guard ──
if not GEMINI_API_KEY:
    st.error(
        "## ⚠️ API Key Not Found\n\n"
        "Create a `.env` file in the project root with:\n\n"
        "```\nGEMINI_API_KEY=\"your-api-key-here\"\n```"
    )
    st.stop()


def main() -> None:
    """Top-level application orchestrator."""

    _init_session_state()
    render_custom_css()
    render_sidebar()
    render_media_uploader()

    # ── Main chat area ──
    st.markdown(
        f"## 💬 {st.session_state['session_data'].get('title', 'Chat')}　"
        f'<span class="status-badge">{st.session_state["model"]}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Display messages ──
    messages = st.session_state.get("messages", [])
    for msg in messages:
        render_chat_message(
            role=msg["role"],
            content=msg.get("text", ""),
            media=msg.get("media"),
        )

    # ── Input area ──
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        prompt = st.chat_input("Type your message…", key="chat_input", disabled=st.session_state.get("processing", False))
    with col2:
        has_media = bool(st.session_state.get("pending_media", []))
        st.markdown(f"<div style='padding-top:0.4rem;text-align:center;'>📎{'✅' if has_media else '✕'}</div>", unsafe_allow_html=True)

    # ── Process message ──
    if prompt and not st.session_state.get("processing", False):
        _handle_send(prompt)

    # ── Show processing indicator ──
    if st.session_state.get("processing", False):
        st.markdown(
            "<div style='display:flex;gap:0.5rem;align-items:center;padding:0.5rem 0;'>"
            "<span class='status-badge'>⏳ Thinking…</span></div>",
            unsafe_allow_html=True,
        )

    # ── Footer ──
    st.markdown("---")
    st.caption(
        f"Session: `{st.session_state['session_id'][:8]}…`  ·  "
        f"{len(st.session_state.get('messages', [])) // 2} exchanges  ·  "
        "Powered by Google Gemini"
    )


def _handle_send(prompt: str) -> None:
    """Process user message: save to history, call Gemini, display response."""
    st.session_state["processing"] = True

    # Snapshot pending media & clear
    pending_media = list(st.session_state.get("pending_media", []))
    st.session_state["pending_media"] = []

    # ── Append user message ──
    user_msg: Dict[str, Any] = {"role": "user", "text": prompt, "media": pending_media}
    st.session_state.setdefault("messages", []).append(user_msg)
    _save_current_session()

    # Re-render so user sees their message immediately
    render_chat_message(role="user", content=prompt, media=pending_media)

    # ── Streaming assistant response ──
    history_before = list(st.session_state["messages"][:-1])  # everything except current user msg

    assistant_placeholder = st.empty()

    collected_text: List[str] = []
    model_name = st.session_state.get("model", DEFAULT_MODEL)

    try:
        stream = generate_response_stream(
            model_name=model_name,
            history=history_before,
            user_text=prompt,
            new_media=pending_media,
        )

        # Drain & render
        for chunk in stream:
            collected_text.append(chunk)
            full = "".join(collected_text)
            assistant_placeholder.markdown(
                f"""
                <div class="chat-message assistant">
                    <div class="chat-avatar ai">🤖</div>
                    <div class="chat-bubble ai">{full}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        final = "".join(collected_text).strip()
        if not final:
            final = "_(No response)_"

    except RuntimeError as exc:
        final = str(exc)
        # Render inline error
        assistant_placeholder.markdown(
            f"""
            <div class="chat-message assistant">
                <div class="chat-avatar ai">🤖</div>
                <div class="chat-bubble ai" style="border-color:#ea4335;">{final}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Append assistant message ──
    assistant_msg: Dict[str, Any] = {"role": "assistant", "text": final, "media": None}
    st.session_state["messages"].append(assistant_msg)
    _save_current_session()

    st.session_state["processing"] = False
    # Rerun to clear input and re-render full state
    st.rerun()


if __name__ == "__main__":
    main()
