"""Pure Python A.S.I.S. launcher - replaces npm run asis"""

from __future__ import annotations

import os
import sys
import subprocess
import time
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = os.name == "nt"
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe" if IS_WINDOWS else ROOT / ".venv" / "bin" / "python"
PYTHON_LAUNCHER = "py" if IS_WINDOWS else "python3"
OLLAMA_HOST = os.environ.get("ASIS_OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = int(os.environ.get("ASIS_OLLAMA_PORT", "11434"))
SERVE_BIND = os.environ.get("ASIS_OLLAMA_SERVE_BIND", "127.0.0.1:11434")
MODEL = "qwen3:14b"
SERVE_READY_TIMEOUT_MS = int(os.environ.get("ASIS_OLLAMA_SERVE_TIMEOUT_S", "120")) * 1000

def fail(message: str, code: int = 2) -> None:
    print(f"asis: ERROR: {message}", file=sys.stderr)
    sys.exit(code)

def run_foreground(cmd: list[str]) -> int:
    """Run a command with inherited stdio; return its exit code."""
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        fail(f"could not run {cmd[0]}: return code {result.returncode}")
    return result.returncode

def run_quiet(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command quietly; return (status, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return result.returncode, result.stdout, result.stderr

def command_exists(cmd: str) -> bool:
    if IS_WINDOWS:
        result = run_quiet("where", [cmd])
    else:
        result = run_quiet("sh", ["-c", f"command -v {cmd}"])
    return result[0] == 0

def ensure_venv() -> None:
    """Ensure .venv exists and has required packages."""
    if VENV_PYTHON.exists():
        status, _, _ = run_quiet([str(VENV_PYTHON), "-c", "import asis.cli.main; import textual"])
        if status == 0:
            return  # healthy venv
        print("asis: venv python or ""asis"" import is broken; reinstalling light deps...")
        code = run_foreground([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt", "-r", "requirements/development.txt", "-r", "requirements/tui.txt"])
        if code != 0:
            fail("pip install failed; run setup_venv.py manually and retry.")
        return

    if command_exists("uv"):
        print("asis: creating .venv via setup_venv.py (uv) ...")
        code = run_foreground([PYTHON_LAUNCHER, "setup_venv.py"])
        if code == 0 and VENV_PYTHON.exists():
            return
        print("asis: setup_venv.py failed; falling back to plain venv ...")
    else:
        print("asis: ""uv"" not found; falling back to plain venv ...")

    fallbacks = ["py -3.12", "py -3"] if IS_WINDOWS else [PYTHON_LAUNCHER]
    created = False
    for launcher in fallbacks:
        parts = launcher.split()
        code, _, _ = run_quiet([parts[0]] + parts[1:] + ["-m", "venv", ".venv"])
        if code == 0 and VENV_PYTHON.exists():
            created = True
            break

    if not created:
        msg = (
            "could not create .venv. Install uv (https://docs.astral.sh/uv/) or Python 3.12+ with the ""py"" launcher and retry."
            if IS_WINDOWS else "could not create .venv. Install uv (https://docs.astral.sh/uv/) or have Python 3.12+ available as ""python3"" and retry."
        )
        fail(msg)

    run_foreground([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"])
    deps = run_foreground([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt", "-r", "requirements/development.txt", "-r", "requirements/tui.txt"])
    if deps != 0:
        fail("pip install failed.")

def fetch_json(path: str):
    import urllib.request
    import json
    url = "http://{OLLAMA_HOST}:{OLLAMA_PORT}" + path
    request = urllib.request.Request(url)
    response = urllib.request.urlopen(request, timeout=5)
    body = response.read().decode("utf-8")
    import json
    return json.loads(body)

def ollama_up() -> bool:
    try:
        fetch_json("/api/tags")
        return True
    except Exception:
        return False

async def ensure_ollama() -> tuple[bool, int | None]:
    """Ensure an Ollama server is reachable. Returns (owned, serve_pid)."""
    if await ollama_up():
        return False, None
    print("asis: Ollama is down; starting ""ollama serve"" ...")
    env = {**os.environ, "OLLAMA_HOST": SERVE_BIND}
    proc = subprocess.Popen(["ollama", "serve"], detached=True, stdio="ignore", cwd=ROOT, env=env)
    await asyncio.sleep(0.5)
    if proc.poll() is not None:
        fail("could not spawn ""ollama"" (exited immediately). Install Ollama (https://ollama.com) and ensure it is on PATH, or start it with ""ollama serve"" and retry.")
    deadline = time.time() + SERVE_READY_TIMEOUT_MS / 1000
    while time.time() < deadline:
        await asyncio.sleep(1)
        if await ollama_up():
            print("asis: Ollama server is up (launcher-owned).")
            return True, proc.pid
    stop_serve_process(proc.pid)
    fail(" \"ollama serve\" did not become ready within " + str(SERVE_READY_TIMEOUT_MS / 1000) + "s. Start it manually with \"ollama serve\" to see why, then retry.")
    return False, None

async def check_model() -> None:
    tags = await fetch_json("/api/tags")
    names = {m['name'] for m in tags.get('models', [])}
    if not any(n.startswith(MODEL) for n in names):
        fail("model "" + MODEL + "" is not pulled. Run ""ollama pull "" + MODEL + "", then retry.")

async def main() -> None:
    import sys
    raw_args = sys.argv[1:]
    os.chdir(ROOT)
    ensure_venv()

    if "--test" in raw_args:
        sys.exit(run_foreground([str(VENV_PYTHON), "-m", "pytest", "-q"]))

    if raw_args and raw_args[0] == "voice" and not voice_deps_present():
        print("asis: voice extras are not installed; voice mode will use mock engines.")
        print("asis: for real audio run: uv pip install -r requirements/voice.txt")

    if "--check" in raw_args:
        sys.exit(run_foreground([str(VENV_PYTHON), "-m", "asis", "--identify"]))

    owned, serve_pid = await ensure_ollama()
    await check_model()

    child = subprocess.Popen([str(VENV_PYTHON), "-m", "asis"] + raw_args, stdio="inherit")

    def shutdown_owned() -> None:
        if owned:
            unload_model(MODEL)
            stop_serve_process(serve_pid)

    def signal_handler(sig, frame):
        shutdown_owned()
        sys.exit(1)

    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        child.wait()
    finally:
        shutdown_owned()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
