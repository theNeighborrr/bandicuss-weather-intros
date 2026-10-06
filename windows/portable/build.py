"""Build the portable ZIP from pinned official archives and original source."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent.parent
VERSION = 'windows-portable-v1.0.0'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dependency(entry, cache):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / entry['filename']
    if path.exists():
        data = path.read_bytes()
    else:
        with urllib.request.urlopen(entry['url'], timeout=60) as response:
            data = response.read()
        if sha(data) != entry['sha256']:
            raise ValueError('Download hash mismatch: ' + entry['filename'])
        path.write_bytes(data)
    if sha(data) != entry['sha256']:
        raise ValueError('Cached dependency changed: ' + str(path))
    return path


def extract(archive, target):
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            name = PurePosixPath(info.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in info.filename or ':' in info.filename:
                raise ValueError('Unsafe archive member')
            path = target / info.filename
            if info.is_dir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                if path.exists():
                    raise ValueError('Overlapping archive member: ' + str(path))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(source.read(info))


def build(output, cache):
    if output.exists():
        raise ValueError('Output already exists; preserve it and choose another directory.')
    output.mkdir(parents=True)
    root = output / 'Bandicuss Weather'
    root.mkdir()
    lock = json.loads((HERE / 'dependencies.json').read_text())
    extract(dependency(lock['python'], cache), root / 'runtime')
    for entry in lock['wheels']:
        extract(dependency(entry, cache), root / 'packages')
    (root / 'runtime/python314._pth').write_text(
        'python314.zip\n.\n../packages\n', encoding='utf-8', newline='\n')
    support = root / 'support'
    support.mkdir()
    mapping = {
        'start.py': HERE / 'start.py', 'run_windows.py': HERE.parent / 'run_windows.py',
        'intro_install.py': PACKAGE / 'install.py', 'upstream.json': HERE.parent / 'upstream.json',
        'bandicuss_ascii.py': PACKAGE / 'bandicuss_ascii.py',
        'bandicuss_intro_settings.py': PACKAGE / 'bandicuss_intro_settings.py',
    }
    for name, source in mapping.items():
        shutil.copyfile(source, support / name)
    for name in ('README.txt', 'THIRD-PARTY-NOTICES.txt'):
        shutil.copyfile(HERE / name, root / name)
    # Batch files use CRLF; all other source bytes are retained exactly.
    (root / 'START BANDICUSS.cmd').write_bytes((HERE / 'START BANDICUSS.cmd').read_text().replace('\n', '\r\n').encode('utf-8'))
    shutil.copyfile(PACKAGE / 'LICENSE', root / 'LICENSE-add-on.txt')
    files = {p.relative_to(root).as_posix(): sha(p.read_bytes())
             for p in sorted(root.rglob('*')) if p.is_file()}
    assert not (root / 'data').exists() and not any(n.endswith('/weather.py') for n in files)
    assert any(n.lower() == 'runtime/license.txt' for n in files)
    assert len([n for n in files if '.dist-info/' in n and 'license' in n.lower()]) >= 4
    manifest = {'version': VERSION, 'python': lock['python']['version'], 'architecture': 'x64',
                'dependencies': lock, 'files': files}
    (root / 'bundle-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    archive = output / 'Bandicuss-Weather-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo('Bandicuss Weather/' + path.relative_to(root).as_posix(), (2026, 10, 6, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                target.writestr(info, path.read_bytes())
    digest = sha(archive.read_bytes())
    (output / 'SHA256SUMS.txt').write_text(digest + '  ' + archive.name + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'version': VERSION, 'zip': str(archive), 'sha256': digest,
                      'bytes': archive.stat().st_size, 'files': len(files) + 1}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    build(args.output.absolute(), args.cache.absolute())
