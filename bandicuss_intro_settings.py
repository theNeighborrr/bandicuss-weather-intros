"""Local preferences for the optional Bandicuss terminal intros (stdlib only)."""
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile

STYLES = {"ascii": "ASCII", "pixel": "Pixel", "off": "Off"}


def config_path():
    root = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    if not root.is_absolute():
        root = Path.home() / ".config"
    return root / "bandicuss-weather" / "intros.json"


def load_style():
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
        value = data.get("style") if isinstance(data, dict) else None
        return value if value in STYLES else "ascii"
    except (OSError, ValueError, TypeError):
        return "ascii"


def save_style(style):
    if style not in STYLES:
        raise ValueError("Unknown intro style")
    path = config_path()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise OSError("Preferences path is a symlink; leaving it unchanged")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".intros-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump({"style": style}, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def play_selected():
    style = load_style()
    if style == "off":
        return
    try:
        module = importlib.import_module(
            "bandicuss_ascii" if style == "ascii" else "bandicuss_intro"
        )
        module.play_intro()
    except Exception as exc:
        # An optional intro must never prevent access to the weather app.
        print("Intro skipped: " + str(exc), file=sys.stderr)


def settings_menu():
    message = ""
    while True:
        if sys.stdout.isatty():
            print("\x1b[2J\x1b[H", end="")
        print("\n BANDICUSS / INTRO SETTINGS\n")
        print(" Current: " + STYLES[load_style()])
        print("\n [1] ASCII — colored character art")
        print(" [2] Pixel — the original colorful landscape art")
        print(" [3] Off")
        print("\n [P] Preview current intro    [B] Back")
        print("\n Eight seconds. Any key skips. No internet needed.")
        if message:
            print("\n " + message)
        try:
            choice = input("\n SELECT OPTION: ").strip().lower()
        except EOFError:
            return
        if choice in ("b", "q"):
            return
        if choice == "p":
            play_selected()
            message = "Off selected; no animation." if load_style() == "off" else "Preview finished."
        elif choice in ("1", "2", "3"):
            style = {"1": "ascii", "2": "pixel", "3": "off"}[choice]
            try:
                save_style(style)
                message = "Saved: " + STYLES[style]
            except OSError as exc:
                message = "Could not save preference: " + str(exc)
        else:
            message = "Choose 1, 2, 3, P or B."
