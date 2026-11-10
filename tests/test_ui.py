"""GUI checks run headlessly; skipped when optional GUI dependencies are absent."""

import importlib.util
from contextlib import contextmanager
import logging
import json
import os
import socketserver
import threading
import time
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
GUI_AVAILABLE = all(importlib.util.find_spec(name) for name in ("PySide6", "pyqtgraph"))
HARDWARE_AVAILABLE = all(importlib.util.find_spec(name) for name in ("qcodes", "pyvisa", "pyvisa_py"))


@contextmanager
def instrument_server(replies):
    """Local TCP test instrument; no actual lab equipment is contacted."""
    commands = []

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(10)
            try:
                for line in self.rfile:
                    command = line.strip()
                    commands.append(command)
                    reply = replies.get(command)
                    if reply is not None:
                        self.wfile.write(reply + b"\n")
            except (OSError, TimeoutError):
                pass

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True

    with Server(("127.0.0.1", 0), Handler) as server:
        worker = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        worker.start()
        try:
            yield f"TCPIP0::127.0.0.1::{server.server_address[1]}::SOCKET", commands
        finally:
            server.shutdown()
            worker.join(2)


@unittest.skipUnless(GUI_AVAILABLE, "Install the optional [gui] dependencies")
class OfflineWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from nv_lab.ui.main_window import MainWindow
        self.window = MainWindow()
        self.addCleanup(self.dispose_window)

    def dispose_window(self):
        from shiboken6 import delete
        self.window.close()
        delete(self.window)

    @classmethod
    def tearDownClass(cls):
        from shiboken6 import delete
        delete(cls.app)
        cls.app = None

    def test_offline_actions_and_empty_measurement_plot(self):
        for button in (self.window.start_button, self.window.stop_button, self.window.save_button):
            self.assertFalse(button.isEnabled())
        self.assertEqual(self.window.measurement_plot.listDataItems(), [])

    def test_preview_uses_compiler_and_preserves_reference_timing(self):
        self.window.show_preview()
        signal, reference = self.window.last_sequences
        self.assertEqual(signal.duration_ns, reference.duration_ns)
        self.assertEqual(signal.channels["laser"], reference.channels["laser"])
        self.assertEqual(signal.channels["scope_trigger"], reference.channels["scope_trigger"])
        self.assertNotEqual(signal.channels["mw_gate"], reference.channels["mw_gate"])
        self.window.tau_stop.setValue(250)
        self.assertEqual(self.window.last_sequences, ())
        self.assertEqual(self.window.sequence_plot.listDataItems(), [])
        self.window.preview_tau.setCurrentIndex(1)
        self.window.show_preview()
        self.assertEqual(self.window.last_sequences[0].metadata["tau_ns"], 250000)

    def test_invalid_sweep_and_trigger_leave_no_stale_preview(self):
        self.window.show_preview()
        self.window.tau_start.setValue(2000)
        self.window.show_preview()
        self.assertEqual(self.window.last_sequences, ())
        self.assertIn("Start", self.window.feedback.text())
        self.window.tau_start.setValue(100)
        self.window.trigger.setValue(3000000)
        self.window.show_preview()
        self.assertEqual(self.window.last_sequences, ())
        self.assertIn("Trigger", self.window.feedback.text())

    def test_mode_switch_preserves_fields_and_disables_t1_preview(self):
        self.window.tau_start.setValue(250)
        self.window.mode_buttons[0].click()
        self.assertEqual(self.window.mode_fields.currentIndex(), 0)
        self.assertFalse(self.window.preview_button.isEnabled())
        self.assertFalse(self.window.tabs.isTabEnabled(1))
        self.window.mode_buttons[2].click()
        self.assertEqual(self.window.tau_start.value(), 250)
        self.assertTrue(self.window.preview_button.isEnabled())

    def wait_until(self, condition, timeout=12):
        from PySide6.QtTest import QTest
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(condition(), "Asynchronous diagnostic did not finish in time")

    def make_demo(self):
        self.dispose_window()
        from nv_lab.ui.main_window import MainWindow
        self.window = MainWindow(demo_mode=True)
        self.window.points.setValue(5)
        return self.window.demo

    def test_demo_sweep_export_is_labelled_and_never_launches_visa(self):
        demo = self.make_demo()
        with patch("nv_lab.ui.console.QProcess.start") as start_process:
            self.window.start_button.click()
            self.assertTrue(demo.running)
            self.assertFalse(self.window.mode_fields.isEnabled())
            for _ in range(5):
                demo.tick()
            self.assertFalse(demo.running)
            self.assertEqual(len(demo.rows), 5)
            self.assertTrue(demo.metadata["completed"])
            self.assertTrue(self.window.save_button.isEnabled())
            self.assertIn("DEMO", self.window.status.text())
            self.assertEqual(demo.rows[0]["x"], 100)
            self.assertEqual(demo.rows[-1]["x"], 1000)
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "DEMO.json"
                demo.export(path)
                document = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(document["metadata"]["simulated"])
                self.assertIn("NOT AN EXPERIMENT", document["metadata"]["label"])
                self.assertEqual(len(document["samples"]), 5)
            for button in (self.window.console.sg_button, self.window.console.scope_button,
                           self.window.console.discover_button):
                button.click()
                self.wait_until(lambda: not self.window.console.busy)
            start_process.assert_not_called()

    def test_demo_stop_restart_mode_switch_and_close(self):
        demo = self.make_demo()
        self.window.start_button.click()
        demo.tick()
        self.window.stop_button.click()
        self.assertFalse(demo.running)
        self.assertFalse(demo.metadata["completed"])
        self.assertEqual(len(demo.rows), 1)
        self.assertTrue(self.window.start_button.isEnabled())
        for mode in (0, 1):
            self.window.mode_buttons[mode].click()
            self.assertEqual(demo.rows, [])
            self.window.start_button.click()
            for _ in range(5):
                demo.tick()
            self.assertTrue(demo.metadata["completed"])
            self.assertEqual(demo.metadata["mode"], self.window.MODES[mode])
            self.assertEqual(demo.rows[0]["x"], 2800)
            self.assertEqual(demo.rows[-1]["x"], 2940)
        self.window.start_button.click()
        self.window.close()
        self.assertFalse(demo.timer.isActive())
        self.assertFalse(demo.running)

    def test_demo_rejects_invalid_t1_range_before_generating_samples(self):
        demo = self.make_demo()
        self.window.tau_start.setValue(2000)
        self.window.start_button.click()
        self.assertFalse(demo.running)
        self.assertEqual(demo.rows, [])
        self.assertIn("Błąd parametrów", self.window.feedback.text())

    def test_console_shows_program_logs_and_validates_missing_address(self):
        console = self.window.console
        logging.getLogger("nv_lab.test").warning("sample program message")
        self.assertIn("sample program message", console.output.toPlainText())
        console.scope_button.click()
        self.assertFalse(console.busy)
        self.assertIn("Wpisz adres VISA", console.output.toPlainText())

    def test_failed_process_start_restores_controls(self):
        console = self.window.console
        with patch("nv_lab.ui.console.sys.executable", "nv_lab_nonexistent_python_executable"):
            console.discover_button.click()
            self.wait_until(lambda: not console.busy)
        self.assertTrue(console.discover_button.isEnabled())
        self.assertIn("Nie można uruchomić testu", console.output.toPlainText())

    @unittest.skipUnless(HARDWARE_AVAILABLE, "Install [hardware] for subprocess integration checks")
    def test_scope_identification_runs_asynchronously_and_rejects_wrong_model(self):
        console = self.window.console
        with instrument_server({b"*IDN?": b"KEYSIGHT TECHNOLOGIES,DSO-X 2014A,SNTEST,1.0"}) as (address, commands):
            console.scope_address.setText(address)
            console.scope_button.click()
            self.assertTrue(console.busy)
            # Other UI controls continue processing events during the check.
            self.window.mode_buttons[0].click()
            self.assertEqual(self.window.mode_fields.currentIndex(), 0)
            self.wait_until(lambda: not console.busy)
            self.assertEqual(commands, [b"*IDN?"])
            self.assertIn("test OK (sesja zamknięta)", self.window.status.text())
        with instrument_server({b"*IDN?": b"SRS,SG386,SNTEST,1.0"}) as (address, commands):
            console.scope_address.setText(address)
            console.scope_button.click()
            self.wait_until(lambda: not console.busy)
            self.assertEqual(commands, [b"*IDN?"])
            self.assertIn("test nieudany", self.window.status.text())
            self.assertIn("nie identyfikuje", console.output.toPlainText())

    @unittest.skipUnless(HARDWARE_AVAILABLE, "Install [hardware] for subprocess integration checks")
    def test_sg386_uses_driver_queries_without_changing_settings(self):
        console = self.window.console
        replies = {b"*IDN?": b"Stanford Research Systems,SG386,SNTEST,1.0",
                   b"FREQ?": b"2870000000", b"AMPR?": b"-30"}
        with instrument_server(replies) as (address, commands):
            console.sg_address.setText(address)
            console.sg_button.click()
            self.wait_until(lambda: not console.busy)
            self.assertEqual(commands, [b"*IDN?", b"FREQ?", b"AMPR?"])
            self.assertIn("SG386: test OK (sesja zamknięta)", self.window.status.text())
            self.assertIn("2870000000", console.output.toPlainText())

    @unittest.skipUnless(HARDWARE_AVAILABLE, "Install [hardware] for subprocess integration checks")
    def test_timeout_and_cancel_release_worker_and_restore_buttons(self):
        console = self.window.console
        with instrument_server({}) as (address, commands):
            console.scope_address.setText(address)
            console.scope_button.click()
            self.wait_until(lambda: bool(commands))
            # Exercise the watchdog without making the test wait 30 seconds.
            console.deadline.setInterval(50)
            self.wait_until(lambda: not console.busy)
            self.assertIn("Przekroczono limit", console.output.toPlainText())
            self.assertIn("test nieudany", self.window.status.text())
            self.assertTrue(console.scope_button.isEnabled())
            self.assertFalse(console.cancel_button.isEnabled())
            console.deadline.setInterval(30000)
            console.scope_button.click()
            self.wait_until(lambda: len(commands) == 2)
            console.cancel_button.click()
            self.wait_until(lambda: not console.busy)
            self.assertIn("przerwano", console.output.toPlainText())
            console.scope_button.click()
            self.wait_until(lambda: len(commands) == 3)
            self.window.close()
            self.assertFalse(console.busy)
            self.assertNotIn(console.handler, logging.getLogger("nv_lab").handlers)
