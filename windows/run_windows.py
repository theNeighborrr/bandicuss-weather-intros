"""Native Windows host for the reviewed Bandicuss v4.1 application.

Replace platform operations in memory; retain upstream retrieval and rendering.
"""
import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import functools
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import webbrowser

RESTORE = '\x1b[0m\x1b[?25h\x1b[?1049l'


@contextmanager
def terminal_mode():
    """Enable ANSI on this output handle only; restore its previous mode."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = kernel.GetStdHandle(-11 & 0xffffffff)
    previous = wintypes.DWORD()
    changed = bool(kernel.GetConsoleMode(handle, ctypes.byref(previous)))
    if changed and not kernel.SetConsoleMode(handle, previous.value | 0x0004):
        raise OSError('This console cannot enable ANSI output; use Windows Terminal.')
    try:
        yield
    finally:
        if changed:
            kernel.SetConsoleMode(handle, previous.value)


def wait_key(seconds):
    import msvcrt
    deadline = time.monotonic() + seconds
    while True:
        if msvcrt.kbhit():
            # Consume the entire skip event, including arrow/function-key pairs.
            key = msvcrt.getwch()
            if key in ('\x00', '\xe0'):
                msvcrt.getwch()
            while msvcrt.kbhit():
                msvcrt.getwch()
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(.01, remaining))


def play_intro(renderer, duration=8.0):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return
    if 'NO_COLOR' in os.environ or os.environ.get('BANDICUSS_NO_ANIMATION'):
        return
    if os.environ.get('TERM') == 'dumb':
        return
    columns, rows = shutil.get_terminal_size()
    if columns < 79 or rows < 24:
        return
    duration = max(.5, min(15, float(duration)))
    try:
        sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[2J')
        sys.stdout.flush()
        started = time.monotonic()
        last_size = None
        while True:
            frame_started = time.monotonic()
            elapsed = frame_started - started
            if elapsed >= duration:
                break
            columns, rows = shutil.get_terminal_size()
            if columns < 79 or rows < 24:
                break
            if (columns, rows) != last_size:
                sys.stdout.write('\x1b[2J')
                last_size = (columns, rows)
            pixels, scene = renderer.frame_at(elapsed / duration * renderer.DURATION)
            sys.stdout.write(renderer.ansi_frame(pixels, scene, columns, rows))
            sys.stdout.flush()
            if wait_key(max(0, 1 / renderer.FPS - (time.monotonic() - frame_started))):
                break
    finally:
        sys.stdout.write(RESTORE)
        sys.stdout.flush()


def open_product(weather, url, product_name):
    weather.clear()
    weather.title(product_name)
    print('\n ' + url + '\n')
    try:
        opened = webbrowser.open(url, new=2)
    except (OSError, webbrowser.Error):
        opened = False
    print(' Opened in your browser.' if opened else
          ' Could not open a browser. Copy the address above into your browser.')


def verify(root):
    receipt = json.loads((root / 'windows-receipt.json').read_text(encoding='utf-8'))
    for name, digest in receipt['files'].items():
        path = root / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Installed file changed; preserve and review: ' + name)
    return receipt


def prepare(root, station):
    verify(root)
    # Keep Windows preferences separate from existing Linux/WSL preferences.
    os.environ['XDG_CONFIG_HOME'] = str(root / 'config')
    sys.path.insert(0, str(root / 'app'))
    for name in ('bandicuss_ascii', 'bandicuss_intro'):
        renderer = importlib.import_module(name)
        renderer.play_intro = functools.partial(play_intro, renderer)
    weather = importlib.import_module('weather')
    weather.clear = weather.console.clear
    weather.launch_browser = functools.partial(open_product, weather)
    weather.DEFAULT_STATION = station
    return weather


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--station', default='KDCA')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This launcher is for native Windows Python.')
    root = args.root.resolve()
    if args.check:
        print(json.dumps({'status': 'verified', 'upstream': verify(root)['upstream']}))
        return
    weather = prepare(root, args.station.upper())
    with terminal_mode():
        try:
            weather.main()
        except (KeyboardInterrupt, EOFError):
            print('\n Weather closed.')
        finally:
            if sys.stdout.isatty():
                sys.stdout.write(RESTORE)
                sys.stdout.flush()


if __name__ == '__main__':
    main()
