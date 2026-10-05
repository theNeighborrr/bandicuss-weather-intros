#!/usr/bin/env python3
"""Guarded, reversible add-on installer for an existing Bandicuss Weather v4."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

VERSION = "1.0.0"
MODULES = ("bandicuss_ascii.py", "bandicuss_intro.py", "bandicuss_intro_settings.py")
MARKER = "BANDICUSS-INTROS"
HOOKS = {
    "startup_animation": (
        '    """Short animated Bandicuss Weather boot screen."""\n',
        '    # BANDICUSS-INTROS startup\n'
        '    try:\n'
        '        from bandicuss_intro_settings import play_selected\n'
        '    except ImportError:\n'
        '        pass  # Keep the original animation if the add-on is missing.\n'
        '    else:\n'
        '        play_selected()\n'
        '        return\n'
        '    # END BANDICUSS-INTROS startup\n',
        "after",
    ),
    "build_v4_controls": (
        '    controls.append("[Q]", style="bold bright_cyan")\n',
        '    # BANDICUSS-INTROS controls\n'
        '    controls.append("[I]", style="bold bright_cyan")\n'
        '    controls.append(" INTRO SETTINGS     ", style="white")\n'
        '    # END BANDICUSS-INTROS controls\n',
        "before",
    ),
    "weather_menu": (
        '        elif choice == "q":\n',
        '        # BANDICUSS-INTROS menu\n'
        '        elif choice == "i":\n'
        '            from bandicuss_intro_settings import settings_menu\n'
        '            settings_menu()\n'
        '        # END BANDICUSS-INTROS menu\n\n',
        "before",
    ),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Refusing symlink path: " + str(path))


def atomic(path, data, mode=0o644):
    safe_path(path)
    fd, name = tempfile.mkstemp(prefix=".intro-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def patch(data):
    text = data.decode("utf-8")
    if MARKER in text:
        raise ValueError("Existing intro hooks without a valid receipt; preserve and reconcile")
    newline = "\r\n" if "\r\n" in text else "\n"
    normal = text.replace("\r\n", "\n")
    tree = ast.parse(normal)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    lines = normal.splitlines(keepends=True)
    edits = []
    for name, (anchor, hook, placement) in HOOKS.items():
        node = funcs.get(name)
        if node is None:
            raise ValueError("Unsupported weather app: missing " + name)
        start = sum(len(s) for s in lines[:node.lineno - 1])
        end = sum(len(s) for s in lines[:node.end_lineno])
        section = normal[start:end]
        if section.count(anchor) != 1:
            raise ValueError("Unsupported " + name + "; expected v4 anchor not found exactly once")
        pos = start + section.index(anchor) + (len(anchor) if placement == "after" else 0)
        edits.append((pos, hook))
    for pos, hook in sorted(edits, reverse=True):
        normal = normal[:pos] + hook + normal[pos:]
    ast.parse(normal)
    return normal.replace("\n", newline).encode("utf-8")


def inspect(weather, package):
    safe_path(weather)
    if not weather.is_file():
        raise ValueError("Weather app not found: " + str(weather))
    state = weather.parent / ".bandicuss-intros"
    safe_path(state)
    receipt_path = state / "receipt.json"
    safe_path(receipt_path)
    for name in MODULES:
        safe_path(weather.parent / name)
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("version") != VERSION or receipt.get("weather") != str(weather):
            raise ValueError("Receipt belongs to a different version/path; preserve and reconcile")
        expected = receipt["installed"]
        if set(expected) != {weather.name, *MODULES}:
            raise ValueError("Invalid receipt file list")
        for name, digest in expected.items():
            path = weather.parent / name
            if not path.is_file() or sha(path.read_bytes()) != digest:
                raise ValueError("Installed file changed; refusing to overwrite: " + str(path))
        backup_name = receipt["backup"]
        if Path(backup_name).name != backup_name:
            raise ValueError("Invalid backup path")
        backup = state / backup_name
        safe_path(backup)
        if sha(backup.read_bytes()) != receipt["original_sha256"]:
            raise ValueError("Backup verification failed")
        return state, receipt
    for name in MODULES:
        if (weather.parent / name).exists():
            raise ValueError("Existing add-on file without receipt; preserve: " + name)
    patch(weather.read_bytes())
    for name in MODULES:
        ast.parse((package / name).read_text(encoding="utf-8"))
    return state, None


def install(weather, package, check=False, uninstall=False):
    weather = Path(os.path.abspath(weather.expanduser()))
    package = Path(package)
    if weather.name in MODULES:
        raise ValueError("Select the weather application, not an add-on module")
    state, receipt = inspect(weather, package)
    if check:
        return {"status": "installed" if receipt else "compatible", "version": VERSION, "weather": str(weather)}
    if uninstall:
        if not receipt:
            return {"status": "not installed"}
        # Validate every owned file before restoring anything. Keep backups/preferences.
        original = (state / receipt["backup"]).read_bytes()
        atomic(weather, original, receipt["mode"])
        for name in MODULES:
            (weather.parent / name).unlink()
        (state / "receipt.json").unlink()
        return {"status": "restored", "sha256": sha(original), "backup": str(state / receipt["backup"])}
    if receipt:
        if any(sha((package / name).read_bytes()) != receipt["installed"][name] for name in MODULES):
            raise ValueError("Package differs from installed add-on; uninstall the old package before updating")
        return {"status": "already installed", "version": VERSION}
    original = weather.read_bytes()
    patched = patch(original)
    mode = stat.S_IMODE(weather.stat().st_mode)
    payload = {name: (package / name).read_bytes() for name in MODULES}
    payload[weather.name] = patched
    state.mkdir(mode=0o700, exist_ok=True)
    backup = state / ("weather-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + ".py.bak")
    with backup.open("xb") as stream:
        stream.write(original)
    os.chmod(backup, 0o600)
    if backup.read_bytes() != original or weather.read_bytes() != original:
        raise ValueError("Backup/source changed; stopped before installation")
    receipt = {"version": VERSION, "weather": str(weather), "backup": backup.name,
               "original_sha256": sha(original), "mode": mode,
               "installed": {name: sha(data) for name, data in payload.items()}}
    written = []
    try:
        # Modules first; the app hook is the last application file changed.
        for name, data in payload.items():
            target = weather.parent / name
            if name == weather.name:
                if target.read_bytes() != original:
                    raise ValueError("Weather app changed during installation; preserve")
            elif target.exists():
                raise ValueError("Add-on collision during installation; preserve")
            atomic(target, data, mode if name == weather.name else 0o644)
            written.append(name)
        atomic(state / "receipt.json", (json.dumps(receipt, indent=2) + "\n").encode(), 0o600)
    except BaseException:
        for name in reversed(written):
            target = weather.parent / name
            if target.is_file() and sha(target.read_bytes()) == receipt["installed"][name]:
                if name == weather.name:
                    atomic(target, original, mode)
                else:
                    target.unlink()
        raise
    return {"status": "installed", "version": VERSION, "backup": str(backup), "weather_sha256": sha(patched)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weather", type=Path, default=Path.home() / ".local/share/bandicuss-weather/weather.py")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Read-only compatibility and drift check")
    action.add_argument("--uninstall", action="store_true", help="Restore verified original; keep backups/preferences")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.weather, Path(__file__).resolve().parent, args.check, args.uninstall), indent=2))
    except (OSError, ValueError, KeyError, SyntaxError) as exc:
        print("Stopped safely: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
