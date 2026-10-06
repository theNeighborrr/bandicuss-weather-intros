"""Install a separate, pinned Windows copy; never overwrite an existing folder."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import venv

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
VERSION = '1.0.0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_path(path):
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError('Refusing a symlink or junction destination')


def upstream_payload(source=None):
    pin = json.loads((HERE / 'upstream.json').read_text())
    result = {}
    for name, digest in pin['files'].items():
        if source:
            data = (source / name).read_bytes()
        else:
            url = f"https://raw.githubusercontent.com/{pin['repository']}/{pin['commit']}/{name}"
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Upstream verification failed: ' + name)
        result[name] = data
    return pin, result


def install(root, station, source=None):
    check_path(root)
    if root.exists():
        raise ValueError('Destination already exists; preserve it and inspect its receipt before updating: ' + str(root))
    if not re.fullmatch('[A-Z0-9]{4}', station):
        raise ValueError('Use a four-character ICAO station')
    pin, payload = upstream_payload(source)
    root.mkdir(parents=True, exist_ok=False)
    # Leave a failed installation intact for diagnosis; never recursively delete it.
    (root / 'INSTALLING.txt').write_text('Installation incomplete. Preserve this folder if setup fails.\n')
    app = root / 'app'
    app.mkdir()
    for name, data in payload.items():
        (app / name).write_bytes(data)
    spec = importlib.util.spec_from_file_location('intro_installer', PACKAGE / 'install.py')
    addon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(addon)
    addon.install(app / 'weather.py', PACKAGE)
    support = root / 'support'
    support.mkdir()
    for name in ('run_windows.py', 'upstream.json'):
        shutil.copyfile(HERE / name, support / name)
    shutil.copyfile(PACKAGE / 'LICENSE', support / 'LICENSE-add-on')
    shutil.copyfile(PACKAGE / 'WINDOWS.md', root / 'README-Windows.md')
    venv.EnvBuilder(with_pip=True).create(root / '.venv')
    python = root / '.venv/Scripts/python.exe'
    subprocess.run([str(python), '-m', 'pip', '--disable-pip-version-check', 'install',
                    '--only-binary=:all:', 'rich==15.0.0', 'markdown-it-py==4.0.0',
                    'mdurl==0.1.2', 'pygments==2.19.2'], check=True)
    subprocess.run([str(python), '-B', '-c', 'import rich; import msvcrt'], check=True)
    launcher = "$ErrorActionPreference = 'Stop'\n" \
        "& (Join-Path $PSScriptRoot '.venv/Scripts/python.exe') -B -X utf8 " \
        "(Join-Path $PSScriptRoot 'support/run_windows.py') --station " + station + "\n" \
        "if ($LASTEXITCODE -ne 0) { Read-Host 'Bandicuss stopped. Press Enter to close' }\n"
    (root / 'Launch-Bandicuss.ps1').write_text(launcher, encoding='utf-8')
    config = root / 'config/bandicuss-weather'
    config.mkdir(parents=True)
    (config / 'intros.json').write_text('{"style": "pixel"}\n', encoding='utf-8')
    files = {p.relative_to(root).as_posix(): sha(p) for folder in (app, support)
             for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for name in ('Launch-Bandicuss.ps1', 'README-Windows.md'):
        files[name] = sha(root / name)
    receipt = {'version': VERSION, 'upstream': pin['commit'], 'station': station,
               'files': files, 'python': str(python),
               'packages': json.loads(subprocess.check_output(
                   [str(python), '-m', 'pip', 'list', '--format=json'], encoding='utf-8'))}
    (root / 'windows-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    subprocess.run([str(python), '-B', str(support / 'run_windows.py'), '--check'], check=True)
    (root / 'INSTALLING.txt').unlink()
    return {'status': 'installed', 'root': str(root), 'upstream': pin['commit'], 'files': len(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path,
                        default=Path.home() / 'Apps/BandicussWeather')
    parser.add_argument('--station', default='KDCA')
    parser.add_argument('--source', type=Path, help='Optional locally available, hash-verified upstream snapshot')
    args = parser.parse_args()
    if os.name != 'nt' or sys.version_info < (3, 12):
        parser.error('Use native Windows Python 3.12 or newer')
    print(json.dumps(install(args.destination.absolute(), args.station.upper(), args.source), indent=2))


if __name__ == '__main__':
    main()
