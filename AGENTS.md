# Installing this add-on for someone

- Read README.md and inspect the actual existing Bandicuss application and working shortcut. Do not assume a source checkout is the launched copy.
- This is an add-on for an existing app. Do not reinstall Bandicuss, replace weather.py wholesale, change weather products, install global dependencies or alter launchers to add an intro.
- Close the app before installation. Run install.py --check with the appropriate --weather path. Use the installer only after compatibility passes; it creates a verified backup and receipt.
- If a check refuses modified files, an unsupported structure or a symlink, preserve the user's work and report the issue. Never reset, force overwrite or delete the receipt to bypass a guard.
- Run the included tests and verify normal station/weather controls, I settings, both previews and saved preference after reopening. Distinguish automated checks from the user's physical screen confirmation.
- No credentials, private settings, captures or upstream weather source belong in this public repository. No messaging or publishing elsewhere is needed for installation.
- Uninstall with the included command before an upstream update. Retain backups and the user's settings.
