"""Run with python3 -m unittest -v test_intros.py; no weather/network required."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
