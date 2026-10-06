import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock

import start

PACKAGE = Path(__file__).resolve().parents[2]
WEATHER = b'''def startup_animation():
    """Play the optional Pixel intro before station selection."""
    pass

def build_v4_controls():
    controls.append("[Q]", style="bold bright_cyan")

def weather_menu(station):
    while True:
        if choice == "1":
            pass
        elif choice == "q":
            return
'''


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'Weather & Friends'
        self.root.mkdir()
        support = self.root / 'support'
        support.mkdir()
        for name, source in {'intro_install.py': 'install.py', 'bandicuss_ascii.py': 'bandicuss_ascii.py',
                             'bandicuss_intro_settings.py': 'bandicuss_intro_settings.py'}.items():
            shutil.copyfile(PACKAGE / source, support / name)
        self.pin = {'repository': 'example/weather', 'commit': 'abc',
                    'files': {'weather.py': start.sha(WEATHER)}}
        (support / 'upstream.json').write_text(json.dumps(self.pin))
        self.fetch = Mock(return_value=WEATHER)

    def test_first_run_then_no_network_and_settings_preserved(self):
        installation, created = start.prepare_installation(self.root, self.fetch)
        self.assertTrue(created)
        self.assertEqual((installation / 'original/weather.py').read_bytes(), WEATHER)
        self.assertIn(b'BANDICUSS-INTROS', (installation / 'app/weather.py').read_bytes())
        settings = installation / 'config/bandicuss-weather/intros.json'
        settings.write_text('{"style":"ascii"}')
        denied = Mock(side_effect=AssertionError('Offline opening attempted network'))
        self.assertFalse(start.prepare_installation(self.root, denied)[1])
        denied.assert_not_called()
        self.assertEqual(json.loads(settings.read_text())['style'], 'ascii')

    def test_move_retains_relative_receipt(self):
        start.prepare_installation(self.root, self.fetch)
        moved = self.root.parent / 'Moved Café & Weather'
        self.root.rename(moved)
        self.assertFalse(start.prepare_installation(moved, Mock(side_effect=AssertionError()))[1])

    def test_network_failure_leaves_no_partial_app_and_can_retry(self):
        with self.assertRaises(OSError):
            start.prepare_installation(self.root, Mock(side_effect=OSError('Offline')))
        self.assertFalse((self.root / 'data/installation').exists())
        self.assertTrue(start.prepare_installation(self.root, self.fetch)[1])

    def test_bad_download_is_not_executed_or_installed(self):
        with self.assertRaisesRegex(ValueError, 'reviewed version'):
            start.prepare_installation(self.root, Mock(return_value=b'bad'))
        self.assertFalse((self.root / 'data/installation').exists())

    def test_drift_is_preserved_without_download(self):
        app, _ = start.prepare_installation(self.root, self.fetch)
        path = app / 'app/weather.py'
        path.write_text('local edits')
        denied = Mock(side_effect=AssertionError())
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            start.prepare_installation(self.root, denied)
        self.assertEqual(path.read_text(), 'local edits')
        denied.assert_not_called()

    def test_unknown_existing_folder_is_preserved(self):
        app = self.root / 'data/installation'
        app.mkdir(parents=True)
        (app / 'notes.txt').write_text('keep me')
        with self.assertRaisesRegex(ValueError, 'no receipt'):
            start.prepare_installation(self.root, self.fetch)
        self.assertEqual((app / 'notes.txt').read_text(), 'keep me')
        self.fetch.assert_not_called()

    def test_bundle_drift_and_path_escape_refused(self):
        for name in ('../outside', '/absolute', 'C:/absolute', 'bad\\name'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                start.verify_files(self.root, {name: '0' * 64})
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            start.verify_files(self.root, {'missing.py': '0' * 64})

    def test_second_instance_refused_then_lock_released(self):
        with start.launch_lock(self.root / 'data'):
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                with start.launch_lock(self.root / 'data'):
                    self.fail('Second lock acquired')
        with start.launch_lock(self.root / 'data'):
            pass

    def test_terminal_arguments_preserve_spaces_and_ampersands(self):
        command = start.terminal_command(self.root, 'wt.exe', 'KMEM')
        self.assertIn(str(self.root / 'runtime/python.exe'), command)
        self.assertIn(str(self.root / 'support/start.py'), command)
        self.assertIn('--here', command)
        self.assertEqual(command[-1], 'KMEM')


if __name__ == '__main__':
    unittest.main()
