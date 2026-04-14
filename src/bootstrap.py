"""First-run bootstrap — checks Ollama, downloads model, verifies FFmpeg."""

import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"
DEFAULT_MODEL = "llama3.2:3b"
OLLAMA_HOST = "http://localhost:11434"


def is_ollama_running(host: str = OLLAMA_HOST, timeout: int = 2) -> bool:
    try:
        req = urllib.request.Request(f"{host}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def has_model(model: str, host: str = OLLAMA_HOST) -> bool:
    try:
        req = urllib.request.Request(f"{host}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            import json
            data = json.loads(r.read().decode("utf-8"))
            names = [m.get("name", "") for m in data.get("models", [])]
            return any(model in n for n in names)
    except Exception:
        return False


def find_ollama_exe() -> Path | None:
    """Try common Ollama install locations on Windows."""
    candidates = [
        Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
        Path("C:/Program Files/Ollama/ollama.exe"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def start_ollama_server() -> bool:
    """Launch Ollama server in background."""
    exe = find_ollama_exe()
    if not exe:
        return False
    try:
        subprocess.Popen(
            [str(exe), "serve"],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for server to come up
        for _ in range(15):
            time.sleep(1)
            if is_ollama_running():
                return True
        return False
    except Exception as e:
        print(f"[bootstrap] Failed to start Ollama: {e}")
        return False


def pull_model(model: str, progress_callback=None) -> bool:
    """Pull an Ollama model with progress reporting."""
    import json

    payload = json.dumps({"name": model, "stream": True}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/pull",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            for line in response:
                try:
                    data = json.loads(line.decode("utf-8"))
                    status = data.get("status", "")
                    completed = data.get("completed", 0)
                    total = data.get("total", 0)
                    if progress_callback and total:
                        pct = int((completed / total) * 100)
                        progress_callback(status, pct)
                    elif progress_callback:
                        progress_callback(status, 0)
                    if "success" in status.lower():
                        return True
                except json.JSONDecodeError:
                    continue
        return True
    except Exception as e:
        print(f"[bootstrap] Pull failed: {e}")
        return False


def check_ffmpeg() -> bool:
    """Verify FFmpeg is available (bundled or system)."""
    import shutil
    import sys
    if shutil.which("ffmpeg"):
        return True
    # PyInstaller bundle
    if getattr(sys, "frozen", False):
        for base in (Path(getattr(sys, "_MEIPASS", "")),
                     Path(sys.executable).parent,
                     Path(sys.executable).parent / "_internal"):
            if base and (base / "ffmpeg.exe").exists():
                return True
    return False


def ensure_ready(
    model: str = DEFAULT_MODEL,
    progress_callback=None,
) -> tuple[bool, str]:
    """Full readiness check. Returns (ok, message)."""

    def _log(msg: str):
        if progress_callback:
            progress_callback(msg, 0)
        print(f"[bootstrap] {msg}")

    # 1. FFmpeg
    if not check_ffmpeg():
        return False, "FFmpeg not found. Install from https://ffmpeg.org"

    # 2. Ollama server
    if not is_ollama_running():
        _log("Starting Ollama server...")
        if not start_ollama_server():
            return False, (
                "Ollama not installed. Download from https://ollama.com\n"
                "After installing, restart VideoCat."
            )

    # 3. Model
    if not has_model(model):
        _log(f"Downloading {model} (~2GB, one-time)...")
        if not pull_model(model, progress_callback):
            return False, f"Failed to download model {model}"

    return True, "Ready"
