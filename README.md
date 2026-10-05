# Bandicuss Weather Intros

Two animated terminal intros for an **existing Bandicuss Weather v4** installation, plus a saved **Intro settings** menu. No new Python dependencies, internet connection, sudo, or background service is needed for the intros.

- **ASCII** (default): colored character-art sunrise, storm, snow and aurora scenes.
- **Pixel**: the original colorful landscape design, using Unicode half-block pixels.
- **Off**: go straight to station selection.

Both automatically scale to fit and center within the terminal, preserving proportions and keeping captions at the current font size. They reflow when the window is resized. Both play for eight seconds. Any key skips. In the weather app's main menu, press **I** for Intro settings, **1 / 2 / 3** to save a choice, **P** to preview, and **B** to return. Preferences survive restarts.

## Give this to your AI

Copy this repository link: **https://github.com/theNeighborrr/bandicuss-weather-intros**

Suggested request:

> Install the ASCII and Pixel intros from this repository into my existing Bandicuss Weather app. Read its README and AGENTS.md. Find the application that my working shortcut actually launches, run the compatibility check, preserve my weather code and shortcuts, then use the included reversible installer. Do not reinstall Bandicuss or replace the whole application. Verify the I settings menu, saved choices, and normal weather controls. Stop and explain any incompatible version or local edits.

The public repository contains only the original add-on, installer and tests. It does **not** redistribute the upstream weather app, device configuration, credentials or private captures.

## Install

Close Bandicuss first. Download and extract [the v1.0.1 package](https://github.com/theNeighborrr/bandicuss-weather-intros/releases/tag/v1.0.1), or clone this repository, then open a terminal in its folder:

```sh
/usr/bin/python3 install.py --check
/usr/bin/python3 install.py
```

The default target is `~/.local/share/bandicuss-weather/weather.py`. If your launcher points elsewhere, use the **same explicit path** for each command:

```sh
/usr/bin/python3 install.py --weather /path/to/weather.py --check
/usr/bin/python3 install.py --weather /path/to/weather.py
```

Reopen your usual shortcut. Select your station, then press **I** in the main menu. The installer adds three narrow hooks and four adjacent Python modules. It leaves the original startup code in place as an import fallback. Weather retrieval and product controls retain their existing code.

Compatibility is checked against the v4 function/anchor structure, tested with upstream revision `395c38a32d4db477c1db9740c15e70cbd1d0679e`. Unrecognized versions, existing add-on conflicts, symlinks and modified installed files are refused. Do not bypass a refusal by resetting files or removing the receipt.

## Restore the original

From this package folder:

```sh
/usr/bin/python3 install.py --uninstall
```

Use `--weather` again if you selected a custom path. The installer checks every owned file and the backup before restoring the original weather file byte for byte. Backups remain in `.bandicuss-intros/` beside `weather.py`. Your intro preference is retained. If you have edited the app since installation, uninstall refuses to overwrite your work; reconcile those changes first.

To update from add-on 1.0.0, use this new installer with `--check`, then `--uninstall`, then run it without flags. It recognizes the verified 1.0.0 receipt, preserves your saved style and original backup, and refuses drift. Keep the app closed throughout.

An upstream update may overwrite the hooks. Uninstall this add-on **before** updating Bandicuss, then check compatibility again. There is no automatic update mechanism. Repeating the same installation is safe and reports `already installed`.

## Terminal and preferences

Linux/POSIX interactive terminal, Python 3.9+, truecolor support, and at least **79 columns × 24 rows**. Pixel also needs a font with `▀`. Smaller windows, redirected input/output, `NO_COLOR`, or `BANDICUSS_NO_ANIMATION=1` skip animation. The weather app still starts. To preview either renderer alone:

```sh
/usr/bin/python3 bandicuss_ascii.py
/usr/bin/python3 bandicuss_intro.py
```

Settings are saved to `~/.config/bandicuss-weather/intros.json`, honoring an absolute `XDG_CONFIG_HOME`. Missing or invalid preferences default to ASCII. Animation errors do not block weather; Ctrl+C remains an interrupt. Keyboard input mode, cursor and original screen are restored on completion, skip, interruption and resize.

Keep the working Python path in your shortcut. On the tested uConsole, `/usr/bin/python3` has Rich; another app's private Python on `PATH` does not. This package does not change launchers or install Rich.

## The first browser artwork

The [original colorful browser visualization](https://github.com/theNeighborrr/bandicuss-weather-intros/releases/download/v1.0.0/bandicuss-weather-intro.html) is also saved as a separate release download. It is the original file, with its sandboxed iframe and CSP preserved. Download it and open it in a browser. It is not required by the terminal app. Its wrapper may load public browser libraries; the terminal intros are self-contained.

## Checks and attribution

```sh
/usr/bin/python3 -B -m unittest -v test_intros.py
```

Fourteen tests cover installation, idempotence, rollback, failed-write recovery, conflicts, drift, newline preservation, settings, menu routing, the 1.0.0 upgrade path and proportional layouts without wrapping or scrolling. Additional checks on a uConsole CM4 exercised the actual v4 menu using stubbed weather data, exact backup restoration, and both renderers in pseudo-terminals (completion, space/arrow skip, Ctrl+C, shrinking and valid-size reflow). At the measured 158 × 40 terminal size, the artwork fills roughly 80–84% of the width and nearly all available height, including captions. The fixed-size 1.0.0 intro was user-confirmed working; its sizing issue was visible in device photos. These automated checks do not substitute for viewing the result on your own screen.

Bandicuss Weather and its identity belong to [the upstream project](https://github.com/bandicuss/bandicuss-weather). This is a separate add-on, not an official upstream release. The MIT license covers this repository's original add-on code and documentation, not the upstream weather app or third-party browser wrapper/libraries in the separate artwork download.
