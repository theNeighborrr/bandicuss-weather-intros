"""Portable first-run preparation and launch using only the bundled Python."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(path):
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError('Please extract to a regular folder, without symbolic links or junctions.')


def verify_files(root, files):
    for name, digest in files.items():
        parts = PurePosixPath(name)
        if parts.is_absolute() or '..' in parts.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid package file name.')
        path = root / name
        safe_path(path)
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise ValueError('A file is missing or changed: ' + name + '. Keep this folder and extract a fresh ZIP separately.')


def verify_bundle(root):
    safe_path(root)
    manifest = json.loads((root / 'bundle-manifest.json').read_text(encoding='utf-8'))
    verify_files(root, manifest['files'])
    return manifest


@contextmanager
def launch_lock(data):
    import msvcrt
    safe_path(data)
    data.mkdir(exist_ok=True)
    path = data / 'launch.lock'
    safe_path(path)
    with path.open('a+b') as stream:
        if not stream.tell():
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('Bandicuss is already running from this folder. Use its existing window.') from None
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Bandicuss-Windows-Portable/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_installation(root, fetch=download):
    data = root / 'data'
    safe_path(data)
    data.mkdir(exist_ok=True)
    installation = data / 'installation'
    safe_path(installation)
    pin = json.loads((root / 'support/upstream.json').read_text(encoding='utf-8'))
    if installation.exists():
        receipt_path = installation / 'windows-receipt.json'
        if not receipt_path.is_file():
            raise ValueError('Existing app has no receipt. Keep this folder and extract a fresh ZIP separately.')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt['upstream'] != pin['commit']:
            raise ValueError('Existing app uses another version. Keep it and extract the new ZIP separately.')
        verify_files(installation, receipt['files'])
        return installation, False
    print('First launch: preparing Bandicuss Weather. This needs an internet connection.', flush=True)
    payload = {}
    for name, digest in pin['files'].items():
        if Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('Invalid upstream manifest.')
        url = f"https://raw.githubusercontent.com/{pin['repository']}/{pin['commit']}/{name}"
        content = fetch(url)
        if sha(content) != digest:
            raise ValueError('The downloaded app did not match the reviewed version. Please try again later.')
        payload[name] = content
    patcher = load_module('portable_intro_installer', root / 'support/intro_install.py')
    original = payload['weather.py']
    payload['weather.py'] = patcher.patch(original)
    for name in ('bandicuss_ascii.py', 'bandicuss_intro_settings.py'):
        payload[name] = (root / 'support' / name).read_bytes()
    # Publish the whole prepared installation in one rename. Failed staging is
    # retained for diagnosis; the next attempt never overwrites it.
    stage = Path(tempfile.mkdtemp(prefix='.prepare-', dir=data))
    app = stage / 'app'
    app.mkdir()
    for name, content in payload.items():
        (app / name).write_bytes(content)
    original_folder = stage / 'original'
    original_folder.mkdir()
    (original_folder / 'weather.py').write_bytes(original)
    config = stage / 'config/bandicuss-weather'
    config.mkdir(parents=True)
    (config / 'intros.json').write_text('{"style":"pixel"}\n', encoding='utf-8')
    files = {p.relative_to(stage).as_posix(): sha(p.read_bytes())
             for folder in (app, original_folder) for p in folder.rglob('*') if p.is_file()}
    receipt = {'version': 'portable-1.0.0', 'upstream': pin['commit'], 'files': files}
    (stage / 'windows-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    verify_files(stage, files)
    if installation.exists():
        raise ValueError('An installation appeared during setup; keeping both folders for review.')
    stage.rename(installation)
    print('Ready. Starting weather...', flush=True)
    return installation, True


def terminal_command(root, terminal, station):
    return [terminal, '-w', 'new', '--size', '120,36', 'new-tab',
            '--title', 'Bandicuss Weather', '-d', str(root),
            str(root / 'runtime/python.exe'), '-B', '-X', 'utf8',
            str(root / 'support/start.py'), '--here', '--station', station]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--here', action='store_true', help='Use this console instead of opening Windows Terminal')
    parser.add_argument('--prepare-only', action='store_true', help='Verify and prepare without opening the dashboard')
    parser.add_argument('--check', action='store_true', help='Read-only package and installed-app verification')
    parser.add_argument('--station', default='KMEM')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This package is for Windows.')
    if not re.fullmatch('[A-Za-z0-9]{4}', args.station):
        parser.error('Use a four-character ICAO station.')
    root = Path(__file__).resolve().parent.parent
    try:
        manifest = verify_bundle(root)
        if args.check:
            installation = root / 'data/installation'
            if installation.exists():
                receipt = json.loads((installation / 'windows-receipt.json').read_text(encoding='utf-8'))
                verify_files(installation, receipt['files'])
            print(json.dumps({'bundle': manifest['version'], 'verified': True,
                              'prepared': installation.exists(), 'python': sys.executable}))
            return 0
        if not args.here and not args.prepare_only and not os.environ.get('WT_SESSION'):
            terminal = shutil.which('wt.exe')
            if terminal:
                try:
                    result = subprocess.run(terminal_command(root, terminal, args.station), timeout=15)
                    if result.returncode == 0:
                        return 0
                except (OSError, subprocess.TimeoutExpired):
                    pass  # Windows Console remains a usable fallback.
        with launch_lock(root / 'data'):
            installation, created = prepare_installation(root)
            if args.prepare_only:
                print(json.dumps({'prepared': True, 'created': created, 'python': sys.executable}))
                return 0
            host = load_module('portable_windows_host', root / 'support/run_windows.py')
            if sys.stdout.isatty():
                system = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/mode.com'
                subprocess.run([str(system), 'con:', 'cols=120', 'lines=36'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            weather = host.prepare(installation, args.station.upper())
            with host.terminal_mode():
                try:
                    weather.main()
                except (KeyboardInterrupt, EOFError):
                    print('\n Weather closed.')
                finally:
                    if sys.stdout.isatty():
                        sys.stdout.write(host.RESTORE)
                        sys.stdout.flush()
        return 0
    except (Exception, KeyboardInterrupt) as error:
        print('\nBandicuss could not start: ' + str(error), file=sys.stderr)
        print('Your existing app and settings have been kept. Check your connection, then try again.', file=sys.stderr)
        if not args.prepare_only and not args.check and sys.stdin.isatty():
            try:
                input('Press Enter to close...')
            except (KeyboardInterrupt, EOFError):
                pass
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
