# Installing this add-on for someone

- For an explicitly requested new native Windows installation, follow WINDOWS.md and windows/setup_windows.py instead of the existing-app Linux workflow below. Use a separate destination, pinned upstream/hash verification and a private Python environment. Preserve any existing destination or shortcut. Do not run the upstream Linux installer or change the uConsole to install Windows support.
- For the one-click Windows edition, use the named portable release ZIP and Extract All, then START BANDICUSS.cmd. Python/dependencies are bundled; only the pinned upstream weather app is downloaded on first launch. Preserve the entire extracted folder and its data. Do not overwrite a previous portable folder, move a running copy, bundle local user data, or confuse GitHub's automatic source ZIP with the portable release asset. Build with windows/portable/build.py into a new output folder using dependencies.json; retain third-party licenses and verify release hashes.

- Read README.md and inspect the actual existing Bandicuss application and working shortcut. Do not assume a source checkout is the launched copy.
- This is an add-on for an existing app. Do not reinstall Bandicuss, replace weather.py wholesale, change weather products, install global dependencies or alter launchers to add an intro.
- Close the app before installation. Run install.py --check with the appropriate --weather path. Use the installer only after compatibility passes; it creates a verified backup and receipt.
- If a check refuses modified files, an unsupported structure or a symlink, preserve the user's work and report the issue. Never reset, force overwrite or delete the receipt to bypass a guard.
- Run the included tests and verify normal station/weather controls, I settings, both previews and saved preference after reopening. Distinguish automated checks from the user's physical screen confirmation.
- No credentials, private settings, captures or upstream weather source belong in this public repository. No messaging or publishing elsewhere is needed for installation.
- Uninstall with the included command before an upstream update. Retain backups and the user's settings.
