# Bandicuss Weather on Windows

## One-click edition — recommended for friends

1. Download **[Bandicuss-Weather-Windows-x64.zip](https://github.com/theNeighborrr/bandicuss-weather-intros/releases/download/windows-portable-v1.0.0/Bandicuss-Weather-Windows-x64.zip)** from [the portable release](https://github.com/theNeighborrr/bandicuss-weather-intros/releases/tag/windows-portable-v1.0.0).
2. Right-click the ZIP and choose **Extract All**.
3. Open the extracted folder and double-click **START BANDICUSS.cmd**.

No Python installation, command entry or administrator access is needed. Python 3.14.8 and the pinned display libraries are included. For Windows 10/11 Intel/AMD 64-bit PCs. The first launch automatically fetches and hash-checks the reviewed Bandicuss v4.1 app directly from its author; internet is required for that setup and live weather. Subsequent launches use the saved app. Windows Terminal is used when available, with Windows Console as fallback.

The default is Memphis (KMEM) with Pixel. **I** opens saved ASCII / Pixel / Off and preview settings. Keep the whole extracted folder together. Its app and preferences are in `data/installation`, independent of any installed copy. You can move the folder after closing Bandicuss; settings move with it. A shortcut to START BANDICUSS.cmd is optional. Future releases should be extracted into a new folder, preserving previous settings and files. The bundle and app refuse modified managed files instead of replacing them.

Use the named Windows ZIP above, not GitHub's automatic **Source code (zip)** or the older Linux intro ZIP. This release is a portable launcher/runtime, not a signed application installer. The included Python executable and DLL use the official Python Software Foundation signatures; the original launcher scripts are ordinary readable source. SHA256SUMS.txt is provided with the release. Third-party licenses remain included; the upstream weather app itself is fetched on first use rather than redistributed in the ZIP.

## Developer build

With Python available, from this source repository:

```powershell
py -3 windows/portable/build.py --output portable-build --cache portable-downloads
py -3 -B -m unittest discover -s windows/portable -p test_portable.py
```

The builder verifies pinned official Python/PyPI archive hashes, retains licenses, uses an explicit source allowlist and writes a deterministic release ZIP. It refuses an existing output directory. No app data, local installation or upstream source is copied into a release. The checked-in dependency manifest is updated only after review and validation.

## Existing Python-based installation

This optional Windows host runs the reviewed Bandicuss Weather v4.1 with ASCII / Pixel / Off, the I settings menu, live Horizon acquisition and weather products opened in your default browser. It is a separate installation; your uConsole and existing Linux copy are unaffected.

Requires Windows Terminal, native Windows Python 3.12+, and internet for installation and weather retrieval. The eight-second startup scenes need 79 columns by 24 rows. Horizon needs 97 by 23; use approximately 120 by 36 for both. Any key skips the startup intro. Ctrl+C exits. Resizing below the minimum skips animation while weather remains available.

## Install a new Windows copy

Download this repository or clone it. In PowerShell, from the extracted repository folder:

```powershell
py -3 windows/setup_windows.py --station KMEM
```

The installer downloads six upstream files from the pinned v4.1 commit `5a0fe47ad74b41e1627ab8a138cb3d105ffbac4a`, checks their SHA-256 hashes, applies the existing reversible intro hooks, and installs pinned Rich dependencies into a private Python environment. It never runs the upstream Linux installer or changes system Python packages. The public repository contains only original adapter/add-on code, not upstream weather source.

The destination is `%USERPROFILE%\Apps\BandicussWeather`. An existing destination, symlink or junction is refused. A failed setup leaves its folder for inspection; do not delete it automatically or bypass its guard. Use another explicitly chosen destination for a new test installation if needed.

Run it inside Windows Terminal:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Apps\BandicussWeather\Launch-Bandicuss.ps1"
```

The execution-policy option applies only to this launcher process; it does not change your saved PowerShell policy. To make a shortcut, use the provided `windows/create_shortcut.ps1` after installation. It refuses to replace an existing shortcut. You can then launch from the desktop.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File windows/create_shortcut.ps1
```

## Use and maintenance

The default installed style is Pixel. Press **I** in the main weather menu, then **1 / 2 / 3** for ASCII / Pixel / Off, **P** to preview and **B** to return. Preferences are separate under the installation's `config/bandicuss-weather/intros.json`. Startup Off still permits live Horizon; `BANDICUSS_NO_ANIMATION=1` disables both. No app starts automatically at login.

Each launch verifies the application and adapter against its installation receipt. Modified files are preserved and reported instead of replaced. Keep the receipt and `.bandicuss-intros` original backup. This Windows host adapts only keyboard input, screen clearing, initial station and browser opening in memory; upstream weather retrieval and renderers retain their code.

There is no automatic updater. Before an upgrade, close Bandicuss, compare the receipt and preserve any local changes and preferences. An upstream version needs a reviewed hash manifest and compatibility check. To remove the installation, close it and remove its desktop shortcut and its dedicated folder after retaining any preferences you want. It adds no services, machine-wide settings or global Python packages.

Windows bridge version 1.0.0; existing Linux intro installer version 1.1.0 is unchanged. Windows support does not imply Android/Termux support.
