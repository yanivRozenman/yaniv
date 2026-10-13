"""macOS side: get generated files into Logic Pro.

Logic has no scripting API for tracks, regions or plugins, so there are exactly
three ways in, in descending order of reliability:

  1. drag-and-drop      - `reveal()` puts the file in front of you. Always works.
  2. UI scripting       - `import_midi()` drives File > Import > MIDI File via
                          System Events. Needs Accessibility permission for your
                          terminal, and can break when Logic changes its menus.
  3. Scripter           - JavaScript MIDI FX plugin. The only real programmatic
                          hook. See ../scripter/ for examples; you still paste
                          the code into the plugin window by hand.
"""
import shutil
import subprocess
from pathlib import Path

APP = "Logic Pro"


def _osascript(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "osascript failed")
    return r.stdout.strip()


def available():
    """True if we are on a Mac with Logic installed."""
    return shutil.which("osascript") is not None and Path(
        "/Applications/Logic Pro.app").exists()


def is_running():
    return _osascript(
        f'tell application "System Events" to (name of processes) contains "{APP}"'
    ) == "true"


def reveal(path):
    """Select the file in Finder, ready to drag onto a Logic track."""
    subprocess.run(["open", "-R", str(Path(path).resolve())], check=True)


def activate():
    _osascript(f'tell application "{APP}" to activate')


def import_midi(path, timeout_hint=1.0):
    """Drive File > Import > MIDI File... and type the path into the open dialog.

    Best-effort UI automation. Requires System Settings > Privacy & Security >
    Accessibility access for whatever is running this. Raises on failure so the
    caller can fall back to reveal().
    """
    p = str(Path(path).resolve())
    script = f'''
    tell application "{APP}" to activate
    delay 0.6
    tell application "System Events"
        tell process "{APP}"
            click menu item "MIDI File..." of menu 1 of menu item "Import" of menu 1 of menu bar item "File" of menu bar 1
            delay {timeout_hint}
            keystroke "g" using {{command down, shift down}}
            delay 0.4
            keystroke "{p}"
            delay 0.3
            keystroke return
            delay 0.5
            keystroke return
        end tell
    end tell
    '''
    _osascript(script)


def transport(action="play"):
    """Send space / return to Logic. action: play, stop, rewind."""
    key = {"play": "space", "stop": "space", "rewind": "return"}[action]
    code = {"space": 49, "return": 36}[key]
    _osascript(f'''
    tell application "{APP}" to activate
    delay 0.2
    tell application "System Events" to key code {code}
    ''')


def project_dir():
    """Logic's default project folder, where it is handy to drop generated files."""
    return Path.home() / "Music" / "Logic"


def deliver(path, into=None, and_reveal=True):
    """Copy a generated file next to your Logic projects and surface it."""
    dest_dir = Path(into) if into else project_dir() / "claude-loops"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(path).name
    shutil.copy2(path, dest)
    if and_reveal and available():
        reveal(dest)
    return dest
