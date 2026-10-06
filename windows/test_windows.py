import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import run_windows as host
import setup_windows as setup


class WindowsTests(unittest.TestCase):
    def renderer(self):
        return types.SimpleNamespace(DURATION=8, FPS=16,
                                     frame_at=Mock(return_value=(b'', 0)),
                                     ansi_frame=Mock(return_value='ART'))

    def play(self, renderer, wait=None, sizes=(120, 36)):
        output = io.StringIO()
        output.isatty = lambda: True
        stdin = Mock()
        stdin.isatty.return_value = True
        with patch.object(host.sys, 'stdin', stdin), patch.object(host.sys, 'stdout', output), \
                patch.dict(host.os.environ, {}, clear=True), \
                patch.object(host.shutil, 'get_terminal_size', return_value=sizes), \
                patch.object(host, 'wait_key', wait or Mock(return_value=True)):
            try:
                host.play_intro(renderer, .5)
            finally:
                self.output = output.getvalue()

    def test_skip_restores_screen(self):
        renderer = self.renderer()
        self.play(renderer)
        self.assertIn('ART', self.output)
        self.assertTrue(self.output.endswith(host.RESTORE))

    def test_failure_and_interrupt_restore_screen(self):
        for error in (RuntimeError('render failed'), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                renderer = self.renderer()
                renderer.ansi_frame.side_effect = error
                with self.assertRaises(type(error)):
                    self.play(renderer)
                self.assertTrue(self.output.endswith(host.RESTORE))

    def test_small_terminal_skips(self):
        renderer = self.renderer()
        self.play(renderer, sizes=(78, 23))
        renderer.frame_at.assert_not_called()
        self.assertEqual(self.output, '')

    def test_no_color_and_noninteractive_skip(self):
        for key in ('NO_COLOR', 'BANDICUSS_NO_ANIMATION'):
            with patch.dict(host.os.environ, {key: '1'}):
                renderer = self.renderer()
                host.play_intro(renderer)
                renderer.frame_at.assert_not_called()

    def test_resize_stops_cleanly(self):
        renderer = self.renderer()
        def shrink(_):
            host.shutil.get_terminal_size.return_value = (70, 20)
            return False
        self.play(renderer, wait=Mock(side_effect=shrink))
        self.assertEqual(renderer.ansi_frame.call_count, 1)
        self.assertTrue(self.output.endswith(host.RESTORE))

    def test_arrow_skip_consumes_pair(self):
        crt = Mock()
        crt.kbhit.side_effect = [True, False]
        crt.getwch.side_effect = ['\xe0', 'H']
        with patch.dict(sys.modules, {'msvcrt': crt}):
            self.assertTrue(host.wait_key(.05))
        self.assertEqual(crt.getwch.call_count, 2)

    def test_key_poll_timeout(self):
        crt = Mock()
        crt.kbhit.return_value = False
        with patch.dict(sys.modules, {'msvcrt': crt}):
            self.assertFalse(host.wait_key(0))
        crt.getwch.assert_not_called()

    def test_browser_uses_default_and_reports_failure(self):
        weather = types.SimpleNamespace(clear=Mock(), title=Mock())
        for result in (True, False):
            stream = io.StringIO()
            with patch.object(host.webbrowser, 'open', return_value=result) as launch, \
                    patch.object(host.sys, 'stdout', stream):
                host.open_product(weather, 'https://radar.weather.gov/', 'Radar')
            launch.assert_called_once_with('https://radar.weather.gov/', new=2)
            self.assertIn('Opened' if result else 'Could not', stream.getvalue())

    def test_existing_destination_refused_before_download(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(setup, 'upstream_payload') as download:
            with self.assertRaisesRegex(ValueError, 'already exists'):
                setup.install(Path(temp), 'KMEM')
            download.assert_not_called()

    def test_upstream_hash_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            pin = json.loads((setup.HERE / 'upstream.json').read_text())
            for name in pin['files']:
                (Path(temp) / name).write_text('changed')
            with self.assertRaisesRegex(ValueError, 'verification failed'):
                setup.upstream_payload(Path(temp))

    def test_receipt_detects_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app.py').write_text('initial')
            receipt = {'files': {'app.py': setup.sha(root / 'app.py')}}
            (root / 'windows-receipt.json').write_text(json.dumps(receipt))
            host.verify(root)
            (root / 'app.py').write_text('user edits')
            with self.assertRaisesRegex(ValueError, 'changed'):
                host.verify(root)
            self.assertEqual((root / 'app.py').read_text(), 'user edits')


if __name__ == '__main__':
    unittest.main()
