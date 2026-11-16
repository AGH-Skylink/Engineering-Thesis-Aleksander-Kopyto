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
        # These legacy preview/diagnostic checks explicitly select hardware diagnostics
        # and the unverified T1 page; no test contacts real equipment.
        self.window.environment.setCurrentIndex(1)
        self.window.set_mode(2)
        self.window.console.scope_address.clear()
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
        self.assertTrue(self.window.start_button.isEnabled())
        with patch("nv_lab.hardware.station.RealStation.open") as hardware_open:
            self.window.start_button.click()
            hardware_open.assert_not_called()
        self.assertIn("Czasy niezweryfikowane",self.window.feedback.text())
        for button in (self.window.stop_button, self.window.save_button):
            self.assertFalse(button.isEnabled())
        self.assertEqual(self.window.measurement_plot.listDataItems(), [])

    def test_numeric_values_have_visible_edit_area_at_minimum_window_size(self):
        from PySide6.QtWidgets import QAbstractSpinBox
        self.window.resize(1000,700);self.window.show()
        self.app.processEvents()
        for mode in range(4):
            self.window.set_mode(mode);self.app.processEvents()
            for spin in self.window.findChildren(QAbstractSpinBox):
                if spin.isVisible():
                    self.assertGreater(spin.lineEdit().width(),50,spin.lineEdit().text())

    def test_sequence_autoscale_restores_full_timing_after_zoom(self):
        self.window.show();self.app.processEvents()
        self.window.show_preview()
        self.assertTrue(self.window.sequence_autoscale_button.isEnabled())
        self.window.sequence_plot.setXRange(2000,2010,padding=0)
        self.window.sequence_autoscale_button.click();self.app.processEvents()
        low,high=self.window.sequence_plot.viewRange()[0]
        self.assertLessEqual(low,0)
        self.assertGreaterEqual(high,self.window.last_sequences[0].duration_ns/1000)

    def test_help_indicators_distinguish_failed_confirmed_and_unmonitored_devices(self):
        panel=self.window.help_panel
        self.assertEqual(len(panel.nodes),9)
        self.window._update_test_status('scope','test nieudany')
        self.assertEqual(panel.nodes['scope'][0].brush().color().name(),'#c13e49')
        self.window._update_test_status('scope','test OK (sesja zamknięta)')
        self.assertEqual(panel.nodes['scope'][0].brush().color().name(),'#158451')
        self.assertEqual(panel.nodes['laser'][0].brush().color().name(),'#8b98ac')
        self.window.environment.setCurrentIndex(0)
        panel.identities({'sg386':'SIM SG386','laser':'SIM laser'},True)
        self.assertIn('SIM',panel.nodes['sg386'][1].text())

    def test_large_help_dialog_closes_and_shared_diagram_remains_usable(self):
        from PySide6.QtCore import QTimer
        self.window.show();self.window.tabs.setCurrentIndex(3);self.app.processEvents()
        QTimer.singleShot(30,lambda:self.app.activeModalWidget().accept())
        self.window.help_panel.expand_diagram()
        self.app.processEvents()
        self.window.environment.setCurrentIndex(0)
        self.assertIs(self.window.help_panel.view.scene(),self.window.help_panel.scene)
        self.assertEqual(len(self.window.help_panel.nodes),9)

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

    def setup_cw(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.window.environment.setCurrentIndex(0)
        self.window.set_mode(0)
        self.window.acquisition.output_dir = Path(folder.name)
        self.window.cw_points.setValue(9)
        self.window.cw_averages.setValue(1)
        self.window.cw_samples.setValue(100)
        self.window.cw_settling.setValue(0)
        return self.window.acquisition

    def test_cw_gui_uses_engine_autosaves_and_populates_waveforms(self):
        controller = self.setup_cw()
        with patch("nv_lab.hardware.station.RealStation.open") as hardware_open:
            self.window.start_button.click()
            self.assertIsNotNone(controller.worker)
            self.assertFalse(self.window.settings_button.isEnabled())
            self.wait_until(lambda: controller.worker is None)
            hardware_open.assert_not_called()
        self.assertEqual(controller.last_run.state, "COMPLETED")
        self.assertEqual(len(controller.last_run.points), 9)
        self.assertEqual(self.window.progress.value(), 9)
        self.assertEqual(len(self.window.waveform_plot.listDataItems()), 2)
        files = list(controller.output_dir.glob("SIM_*.json"))
        self.assertEqual(len(files), 1)
        doc = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertTrue(doc["simulated"])
        self.assertEqual(len(doc["points"]), 9)
        journal=list(controller.output_dir.glob("*.jsonl"))[0]
        events=[json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(events[1]["event"], "devices")
        self.assertIn("sg386",events[1]["data"])
        self.assertTrue(self.window.save_button.isEnabled())

    def test_t1_and_pulsed_gui_acquire_raw_export_and_reset_calibration(self):
        from dataclasses import replace
        controller=self.setup_cw()
        for mode in (1,2,3):
            self.window.set_mode(mode)
            self.window.pulsed_points.setValue(5)
            self.window.points.setValue(5)
            self.window.echo_points.setValue(5)
            self.window.show_preview()
            self.assertEqual(len(self.window.last_sequences),2)
            with patch('nv_lab.hardware.station.RealStation.open') as hardware_open:
                self.window.start_button.click()
                self.assertIsNotNone(controller.worker)
                self.wait_until(lambda: controller.worker is None)
                hardware_open.assert_not_called()
            self.assertEqual(controller.last_run.state,'COMPLETED',controller.last_run.error)
            self.assertEqual(len(controller.last_run.points),5)
            self.assertEqual(len(self.window.waveform_plot.listDataItems()),2)
            files=list(controller.output_dir.glob('SIM_*.json'))
            self.assertEqual(len(files),mode)
            self.assertTrue(controller.last_run.document()['simulated'])
        controller.pulse_template=replace(controller.pulse_template,timings_verified=True)
        self.window.pi_duration.setValue(200)
        self.assertFalse(controller.pulse_template.timings_verified)
        from nv_lab.ui.pulse_settings import PulseSettingsDialog
        dialog=PulseSettingsDialog(replace(controller.config(),timings_verified=True),self.window)
        self.assertTrue(dialog.verified.isChecked())
        dialog.fields['signal_start_ns'].setValue(.3)
        self.assertFalse(dialog.verified.isChecked())
        dialog.close()

    def test_cw_gui_fault_injection_and_restart(self):
        from dataclasses import replace
        controller = self.setup_cw()
        controller.station_config = replace(controller.station_config, simulation_fail_after=4)
        self.window.start_button.click()
        self.wait_until(lambda: controller.worker is None)
        self.assertEqual(controller.last_run.state, "ERROR")
        self.assertEqual(len(controller.last_run.points), 1)
        self.assertIn("TimeoutError", self.window.feedback.text())
        controller.station_config = replace(controller.station_config, simulation_fail_after=0)
        self.window.start_button.click()
        self.wait_until(lambda: controller.worker is None)
        self.assertEqual(controller.last_run.state, "COMPLETED")
        self.assertEqual(len(list(controller.output_dir.glob("SIM_*.json"))), 2)

    def test_csv_write_failure_does_not_lose_raw_json_or_hide_error(self):
        controller = self.setup_cw()
        with patch("nv_lab.ui.acquisition.save_csv", side_effect=OSError("test disk error")):
            self.window.start_button.click()
            self.wait_until(lambda: controller.worker is None)
        self.assertEqual(controller.last_run.state, "COMPLETED")
        self.assertTrue(controller.last_run.storage_errors)
        self.assertIn("AUTOZAPIS NIEPEŁNY", self.window.feedback.text())
        files=list(controller.output_dir.glob("*.json"))
        self.assertEqual(len(files),1)
        self.assertTrue(json.loads(files[0].read_text(encoding="utf-8"))["storage_errors"])

    def test_cw_gui_stop_and_close_wait_for_cleanup(self):
        controller = self.setup_cw()
        self.window.cw_points.setValue(101)
        self.window.cw_settling.setValue(30)
        self.window.start_button.click()
        self.wait_until(lambda: bool(controller.points))
        self.window.stop_button.click()
        self.wait_until(lambda: controller.worker is None)
        self.assertEqual(controller.last_run.state, "STOPPED")
        self.assertLess(len(controller.last_run.points), 101)
        self.window.start_button.click()
        self.window.close()
        self.wait_until(lambda: controller.worker is None)
        self.assertEqual(controller.last_run.state, "STOPPED")
        self.assertFalse(controller.last_run.cleanup_errors)

    def test_hardware_start_requires_mapping_and_does_not_fall_back_to_simulation(self):
        self.window.set_mode(0)
        with patch("nv_lab.hardware.station.RealStation.open") as open_hardware:
            self.window.start_button.click()
            self.assertIsNone(self.window.acquisition.worker)
            open_hardware.assert_not_called()
        self.assertIn("Uzupełnij adresy", self.window.feedback.text())

    def test_environment_cannot_change_during_diagnostic(self):
        self.window.environment.setCurrentIndex(0)
        self.window.console.discover_button.click()
        self.window.environment.setCurrentIndex(1)
        self.assertEqual(self.window.environment.currentIndex(), 0)
        self.wait_until(lambda: not self.window.console.busy)

    def test_bad_saved_settings_do_not_replace_valid_defaults(self):
        from dataclasses import asdict
        from nv_lab.core.odmr import StationConfig
        controller = self.window.acquisition
        before = controller.station_config
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            data = asdict(StationConfig())
            data["laser_channel"] = 99
            (path/"local_config.json").write_text(json.dumps({"station":data,"output_dir":folder}))
            with patch("nv_lab.ui.acquisition.Path.cwd", return_value=path):
                controller._load_settings()
            self.assertEqual(controller.station_config, before)
            data = asdict(StationConfig(wiring_verified=True))
            (path/"local_config.json").write_text(json.dumps({"station":data,"output_dir":folder}))
            with patch("nv_lab.ui.acquisition.Path.cwd", return_value=path):
                controller._load_settings()
            self.assertFalse(controller.station_config.wiring_verified)

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
            self.assertEqual(demo.rows[0]["x"], self.window.odmr_ranges[mode][0].value())
            self.assertEqual(demo.rows[-1]["x"], self.window.odmr_ranges[mode][1].value())
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
