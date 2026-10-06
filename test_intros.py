"""Run with python3 -m unittest -v test_intros.py; no weather/network required."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import re
from unittest.mock import patch as mock

import install
import bandicuss_intro_settings as settings

# Minimal original test fixture, not a copy of upstream Bandicuss.
FIXTURE = '''def startup_animation():
    """Short animated Bandicuss Weather boot screen."""
    print("original")

def build_v4_controls():
    controls = Text()
    controls.append("[Q]", style="bold bright_cyan")
    return controls

def weather_menu(station):
    while True:
        choice = input("option")
        if choice == "r":
            refresh(station)
        elif choice == "q":
            return station
'''


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.weather = self.folder / "weather.py"
        self.original = FIXTURE.encode()
        self.weather.write_bytes(self.original)
        self.package = Path(__file__).resolve().parent

    def apply(self, **kwargs):
        return install.install(self.weather, self.package, **kwargs)

    def test_roundtrip_and_idempotence(self):
        self.assertEqual(self.apply(check=True)["status"], "compatible")
        self.assertEqual(list(self.folder.iterdir()), [self.weather])
        result = self.apply()
        self.assertEqual(Path(result["backup"]).read_bytes(), self.original)
        self.assertEqual(self.apply()["status"], "already installed")
        self.assertEqual(self.apply(check=True)["status"], "installed")
        self.assertEqual(self.apply(uninstall=True)["status"], "restored")
        self.assertEqual(self.weather.read_bytes(), self.original)
        self.assertTrue(Path(result["backup"]).exists())
        self.assertFalse(any((self.folder / name).exists() for name in install.MODULES))

    def test_unsupported_is_readonly(self):
        self.weather.write_bytes(b'print("different app")\n')
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(list(self.folder.iterdir()), [self.weather])

    def test_app_drift_preserved(self):
        self.apply()
        changed = self.weather.read_bytes() + b"\n# user work\n"
        self.weather.write_bytes(changed)
        for action in ({}, {"check": True}, {"uninstall": True}):
            with self.assertRaises(ValueError):
                self.apply(**action)
            self.assertEqual(self.weather.read_bytes(), changed)

    def test_module_collision_preserved(self):
        path = self.folder / install.MODULES[0]
        path.write_bytes(b"existing work")
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(path.read_bytes(), b"existing work")
        self.assertEqual(self.weather.read_bytes(), self.original)

    def test_modified_module_blocks_uninstall(self):
        self.apply()
        (self.folder / install.MODULES[0]).write_bytes(b"modified")
        with self.assertRaises(ValueError):
            self.apply(uninstall=True)
        self.assertIn(install.MARKER.encode(), self.weather.read_bytes())

    def test_failed_write_rolls_back(self):
        real = install.atomic
        def failing(path, data, mode=0o644):
            if path.name == "receipt.json":
                raise OSError("simulated disk error")
            return real(path, data, mode)
        with mock.object(install, "atomic", side_effect=failing):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(self.weather.read_bytes(), self.original)
        self.assertFalse(any((self.folder / name).exists() for name in install.MODULES))

    def test_crlf_preserved(self):
        self.original = self.original.replace(b"\n", b"\r\n")
        self.weather.write_bytes(self.original)
        self.apply()
        self.assertNotIn(b"\n", self.weather.read_bytes().replace(b"\r\n", b""))
        self.apply(uninstall=True)
        self.assertEqual(self.weather.read_bytes(), self.original)

    def test_upgrade_preserves_verified_v1_backup(self):
        legacy_modules = tuple(n for n in install.MODULES if n != "bandicuss_intro_layout.py")
        with mock.object(install, "VERSION", "1.0.0"), mock.object(install, "MODULES", legacy_modules):
            first = self.apply()
        self.assertEqual(self.apply(check=True)["version"], "1.0.0")
        with self.assertRaisesRegex(ValueError, "Older add-on"):
            self.apply()
        self.apply(uninstall=True)
        self.assertEqual(self.weather.read_bytes(), self.original)
        self.assertEqual(self.apply()["version"], install.VERSION)
        self.assertEqual(Path(first["backup"]).read_bytes(), self.original)

    def test_v41_keeps_native_pixel_and_layout_on_install_and_restore(self):
        self.original = self.original.replace(
            b'Short animated Bandicuss Weather boot screen.',
            b'Play the optional Pixel intro before station selection.')
        self.weather.write_bytes(self.original)
        native = {"bandicuss_intro.py": b'def play_intro(): pass\n',
                  "bandicuss_intro_layout.py": b'# upstream layout\n'}
        for name, data in native.items():
            (self.folder / name).write_bytes(data)
        self.assertEqual(self.apply(check=True)["profile"], "v4.1")
        self.apply()
        self.assertEqual(self.apply()["status"], "already installed")
        receipt = json.loads((self.folder / '.bandicuss-intros/receipt.json').read_text())
        self.assertEqual(set(receipt['installed']), {'weather.py', 'bandicuss_ascii.py', 'bandicuss_intro_settings.py'})
        self.apply(uninstall=True)
        self.assertEqual(self.weather.read_bytes(), self.original)
        for name, data in native.items():
            self.assertEqual((self.folder / name).read_bytes(), data)

    def test_v41_missing_native_module_refuses_without_writes(self):
        self.weather.write_bytes(self.original.replace(
            b'Short animated Bandicuss Weather boot screen.',
            b'Play the optional Pixel intro before station selection.'))
        with self.assertRaisesRegex(ValueError, "Incomplete v4.1"):
            self.apply()
        self.assertEqual(list(self.folder.iterdir()), [self.weather])

    def test_hooks_keep_weather_routing(self):
        self.apply()
        scope = {"refresh": lambda station: calls.append(station)}
        calls = []
        exec(compile(self.weather.read_bytes(), "fixture", "exec"), scope)
        with mock("builtins.input", side_effect=["i", "r", "q"]), mock.object(settings, "settings_menu") as menu:
            self.assertEqual(scope["weather_menu"]("KMEM"), "KMEM")
            menu.assert_called_once_with()
            self.assertEqual(calls, ["KMEM"])
        with mock.object(settings, "play_selected") as intro:
            scope["startup_animation"]()
            intro.assert_called_once_with()


class SettingsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.env = mock.dict(os.environ, {"XDG_CONFIG_HOME": temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_saved_choices_and_invalid_config(self):
        self.assertEqual(settings.load_style(), "ascii")
        for style in ("pixel", "off", "ascii"):
            settings.save_style(style)
            self.assertEqual(settings.load_style(), style)
        for data in ('{"style": []}', 'null', '{bad', '{"style":"unknown"}'):
            settings.config_path().write_text(data)
            self.assertEqual(settings.load_style(), "ascii")

    def test_selection_routing_and_off(self):
        with mock.object(settings.importlib, "import_module") as module:
            settings.save_style("off")
            settings.play_selected()
            module.assert_not_called()
            for style, name in (("ascii", "bandicuss_ascii"), ("pixel", "bandicuss_intro")):
                settings.save_style(style)
                settings.play_selected()
                module.assert_called_with(name)
            self.assertEqual(module.return_value.play_intro.call_count, 2)

    def test_menu_saves_and_previews(self):
        with mock("builtins.input", side_effect=["2", "p", "b"]), mock.object(settings, "play_selected") as preview, redirect_stdout(io.StringIO()):
            settings.settings_menu()
            preview.assert_called_once_with()
        self.assertEqual(settings.load_style(), "pixel")


class LayoutTests(unittest.TestCase):
    def test_proportional_centered_fit(self):
        from bandicuss_intro_layout import fit_canvas
        for columns, rows in [(79, 24), (80, 24), (98, 30), (132, 35), (158, 40), (200, 60)]:
            for height, captions, pixel in [(22, 2, False), (40, 4, True)]:
                left, top, width, target_height = fit_canvas(columns, rows, 78, height, captions, pixel)
                used_rows = target_height // (2 if pixel else 1) + captions
                self.assertGreaterEqual(left, 0)
                self.assertGreaterEqual(top, 0)
                self.assertLess(left + width, columns)
                self.assertLessEqual(top + used_rows, rows)
                self.assertLessEqual(abs(left - (columns - left - width)), 1)
                self.assertLessEqual(abs(top - (rows - top - used_rows)), 1)
                self.assertLess(abs(width / 78 - target_height / height), .06)
                if columns == 158:
                    self.assertGreater(width, 120)
                    self.assertGreaterEqual(used_rows, 37)

    def test_frames_do_not_wrap_or_scroll(self):
        import bandicuss_ascii
        import bandicuss_intro
        escape = re.compile(r'\x1b\[([0-9;]*)([A-Za-z])')
        for module in (bandicuss_ascii, bandicuss_intro):
            for columns, rows in [(79, 24), (98, 30), (158, 40), (200, 60)]:
                for t in (0, 2, 4, 6):
                    data, scene = module.frame_at(t)
                    frame = module.ansi_frame(data, scene, columns, rows)
                    x = y = 0
                    i = 0
                    while i < len(frame):
                        match = escape.match(frame, i)
                        if match:
                            if match[2] == 'H':
                                y, x = (int(v) - 1 for v in match[1].split(';'))
                            i = match.end()
                            continue
                        self.assertGreaterEqual(x, 0)
                        self.assertLess(x, columns - 1)
                        self.assertGreaterEqual(y, 0)
                        self.assertLess(y, rows)
                        if module is bandicuss_ascii:
                            self.assertTrue(32 <= ord(frame[i]) <= 126)
                        x += 1
                        i += 1


if __name__ == "__main__":
    unittest.main()
