"""Qt worker around shared simulation/hardware acquisition engines."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot, Qt
from PySide6.QtWidgets import QFileDialog
import pyqtgraph as pg

from nv_lab.core.odmr import CWConfig, StationConfig
from nv_lab.core.pulsed import PulsedConfig, PulsedPoint, compile_pulsed
from nv_lab.experiments.pulsed import run_pulsed
from nv_lab.ui.pulse_settings import PulseSettingsDialog
from nv_lab.experiments.cw_odmr import run_cw
from nv_lab.experiments.storage import RunJournal, save_csv, save_run
from nv_lab.hardware.simulators import SimStation
from nv_lab.ui.settings import SettingsDialog

logger = logging.getLogger(__name__)


class AcquisitionWorker(QThread):
    point = Signal(object)
    status = Signal(str)
    result = Signal(object)
    devices = Signal(object)
    failed = Signal(str)

    def __init__(self, config, station_config, simulated, output_dir, parent=None):
        super().__init__(parent)
        self.config, self.station_config = config, station_config
        self.simulated, self.output_dir = simulated, Path(output_dir)
        self.stop_requested = Event()

    def run(self):
        journal = None
        base = None
        try:
            if self.simulated:
                station = SimStation(self.station_config)
            else:
                from nv_lab.hardware.station import RealStation
                station = RealStation(self.station_config)

            def started(run):
                nonlocal journal, base
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                mode = getattr(self.config, 'mode', 'CW')
                base = self.output_dir / f"{'SIM' if self.simulated else 'HW'}_{mode}_{stamp}_{run.run_id[:8]}"
                journal = RunJournal(base.with_suffix(".jsonl"))
                journal.write("start", run.document())

            def point(data):
                journal.write("point", asdict(data))
                self.point.emit(data)

            runner = run_pulsed if isinstance(self.config, PulsedConfig) else run_cw
            def devices(ids):
                journal.write('devices',ids)
                self.devices.emit(ids)
            result = runner(station, self.config, self.stop_requested, point, self.status.emit, started,
                            on_devices=devices)
            if journal:
                try:
                    journal.write("end", {"state": result.state, "error": result.error,
                                           "cleanup_errors": result.cleanup_errors,
                                           "identities": result.identities})
                    journal.close()
                    journal = None
                except Exception as exc:
                    result.storage_errors.append(f"journal: {exc}")
            if base:
                # Independent attempts: a failed CSV must not prevent the raw JSON.
                for kind, writer in (("csv", save_csv), ("json", save_run)):
                    try:
                        writer(result, base.with_suffix(f".{kind}"))
                        logger.info("Zapisano %s: %s.%s", kind, base, kind)
                    except Exception as exc:
                        result.storage_errors.append(f"{kind}: {exc}")
            if result.storage_errors:
                self.failed.emit("Autozapis niepełny: " + "; ".join(result.storage_errors))
            self.result.emit(result)
        except Exception as exc:
            logger.exception("Nie udało się uruchomić pomiaru")
            self.failed.emit(str(exc))
        finally:
            if journal:
                try:
                    journal.close()
                except Exception as exc:
                    logger.error("Nie zamknięto dziennika: %s", exc)


class CWController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.station_config = StationConfig()
        self.output_dir = Path.cwd() / "runs"
        self.worker = None
        self.last_run = None
        self.points = []
        self.closing = False
        self.curve = None
        self.pulse_template = PulsedConfig()
        self._environment_index = 0
        self._load_settings()
        window.environment.currentIndexChanged.connect(self.environment_changed)
        window.start_button.clicked.connect(self.start)
        window.stop_button.clicked.connect(self.stop)
        window.save_button.clicked.connect(self.save)
        window.settings_button.clicked.connect(self.settings)
        window.pulse_settings_button.clicked.connect(self.pulse_settings)
        window.reference.setChecked(True)
        window.reference.setEnabled(False)
        for field in (window.pi_duration,window.pulsed_pi,window.initialization,window.readout,
                      window.trigger,window.delay,window.tau_start,window.tau_stop,
                      window.echo_pi,window.echo_pi2,window.echo_start,window.echo_stop):
            field.valueChanged.connect(self.invalidate_calibration)
        window.power.valueChanged.connect(self.invalidate_calibration)
        window.frequency.valueChanged.connect(self.invalidate_calibration)
        window.active_high.toggled.connect(self.invalidate_calibration)
        window.settings_button.setToolTip("Połączenia, kanały, I/Q, katalog danych i symulowane awarie.")
        self.environment_changed()

    def invalidate_calibration(self,*_args):
        self.pulse_template=replace(self.pulse_template,timings_verified=False)

    @property
    def simulated(self):
        return bool(self.window.environment.currentData())

    def _load_settings(self):
        path = Path.cwd() / "local_config.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Verification is never reused across application sessions.
            candidate = replace(StationConfig(**data["station"]), wiring_verified=False)
            candidate.validate()
            directory = Path(data["output_dir"]).expanduser().resolve()
            self.station_config, self.output_dir = candidate, directory
        except Exception as exc:
            logger.warning("Nie wczytano local_config.json: %s", exc)

    def settings(self):
        if self.worker is not None or self.window.console.busy:
            return
        dialog = SettingsDialog(self.station_config, self.output_dir, self.window)
        if dialog.exec():
            self.station_config, self.output_dir = dialog.config, dialog.output_dir
            self.invalidate_calibration()
            try:
                Path("local_config.json").write_text(json.dumps({"station": asdict(self.station_config),
                    "output_dir": str(self.output_dir)}, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError as exc:
                logger.warning("Ustawienia przyjęto w pamięci, zapis nieudany: %s", exc)
            self.environment_changed()

    def environment_changed(self, *_args):
        w = self.window
        if w.console.busy or self.worker is not None:
            w.environment.blockSignals(True)
            w.environment.setCurrentIndex(self._environment_index)
            w.environment.blockSignals(False)
            logger.warning("Zakończ bieżącą operację przed zmianą środowiska.")
            return
        self._environment_index = w.environment.currentIndex()
        w.setWindowTitle(f"NV Lab — {'SYMULATOR' if self.simulated else 'STANOWISKO / SPRZĘT'}")
        w.console.demo_mode = self.simulated
        w.active_high.setChecked(self.station_config.laser_active_high)
        w.console.scope_channel=self.station_config.scope_channel
        w.help_panel.set_station_config(self.station_config,self.simulated)
        w.console.simulation_provider = self.simulation_diagnostic if self.simulated else None
        if self.simulated:
            w.console.sg_address.setText("SIM::SG386")
            w.console.scope_address.setText("SIM::DSOX3034A")
            w.notice.setText("SYMULATOR URZĄDZEŃ · Dane syntetyczne · CW / Pulsed ODMR / T1 / T2 · Czasy wymagają kalibracji.")
            w.notice.setStyleSheet("background:#fff2cc; color:#725012; padding:9px; font-weight:600;")
        else:
            w.console.sg_address.setText(self.station_config.sg_address)
            w.console.scope_address.setText(self.station_config.scope_address)
            w.console.backend.setCurrentIndex(0 if self.station_config.backend else 1)
            w.notice.setText("SPRZĘT · Sprawdź mapowanie, skale i czasy przed START. Pomiary impulsowe: trigger z Pulse Streamera.")
            w.notice.setStyleSheet("background:#e7f1ff; color:#183b6b; padding:9px;")
        w.console._set_busy(False)
        self.mode_changed()

    def simulation_diagnostic(self, task):
        if task=="scope-scale":
            return "SYMULACJA: porównanie WORD/ASCII wymaga rzeczywistego oscyloskopu; nie wykonano testu sprzętu."
        station = SimStation(self.station_config)
        try:
            station.open()
            if task == "list":
                return " | ".join(f"{key}: {value}" for key, value in station.identities.items())
            return str(station.identities["sg386" if task == "sg386" else "scope"])
        finally:
            station.shutdown()

    def mode_changed(self):
        if self.worker is not None:
            return
        self.invalidate_calibration()
        w = self.window
        enabled = w.mode_fields.currentIndex() == 0
        w.start_button.setEnabled(True)
        w.frequency.setEnabled(w.mode_fields.currentIndex() >= 2)
        w.stop_button.setEnabled(False)
        w.save_button.setEnabled(self.last_run is not None)
        w.measurement_plot.clear()
        w.measurement_plot.setTitle(f"{w.MODES[w.mode_fields.currentIndex()]} — wybierz START")
        w.start_button.setToolTip("Rozpocznij pomiar w wybranym środowisku; czasy impulsowe wymagają kalibracji.")
        w.status.setText(f"{'SYMULATOR' if self.simulated else 'SPRZĘT'} · GOTOWY DO KONFIGURACJI | "
                        f"laser D{self.station_config.laser_channel} ON="
                        f"{'HIGH' if self.station_config.laser_active_high else 'LOW'} | stan wyjść: nieodczytany")

    def _lock(self, locked):
        w = self.window
        for item in (w.mode_fields, w.power, w.frequency, w.environment, w.settings_button,
                     *w.mode_buttons, w.console.sg_button, w.console.scope_button,
                     w.console.discover_button, w.console.backend, w.console.sg_address, w.console.scope_address,
                     w.pulse_settings_button,w.console.scale_button):
            item.setEnabled(not locked)
        if self.simulated:
            for item in (w.console.sg_address, w.console.scope_address, w.console.backend):
                item.setEnabled(False)
        w.start_button.setEnabled(not locked)
        w.frequency.setEnabled(not locked and w.mode_fields.currentIndex() >= 2)
        w.stop_button.setEnabled(locked)
        w.preview_button.setEnabled(not locked and w.mode_fields.currentIndex() >= 1)
        w.save_button.setEnabled(not locked and self.last_run is not None)

    def config(self):
        w = self.window
        mode = w.mode_fields.currentIndex()
        if mode:
            low, high = w.odmr_ranges[1]
            if mode==3:
                config=replace(self.pulse_template,mode="T2",start=round(w.echo_start.value()*1000),
                    stop=round(w.echo_stop.value()*1000),points=w.echo_points.value(),
                    average_count=w.echo_averages.value(),pi_ns=round(w.echo_pi.value()),pi2_ns=round(w.echo_pi2.value()),
                    frequency_hz=w.frequency.value()*1e6,power_dbm=w.power.value(),
                    initialization_ns=round(w.initialization.value()*1000),readout_ns=round(w.readout.value()*1000),
                    guard_ns=round(w.delay.value()),trigger_ns=round(w.trigger.value()))
                config.validate()
                return config
            config = replace(self.pulse_template, mode="T1" if mode == 2 else "PULSED_ODMR",
                start=round(w.tau_start.value()*1000) if mode==2 else low.value()*1e6,
                stop=round(w.tau_stop.value()*1000) if mode==2 else high.value()*1e6,
                points=w.points.value() if mode==2 else w.pulsed_points.value(),
                average_count=w.averages.value() if mode==2 else w.pulsed_averages.value(),
                pi_ns=round(w.pi_duration.value() if mode==2 else w.pulsed_pi.value()),
                frequency_hz=w.frequency.value()*1e6, power_dbm=w.power.value(),
                initialization_ns=round(w.initialization.value()*1000),
                readout_ns=round(w.readout.value()*1000),guard_ns=round(w.delay.value()),
                trigger_ns=round(w.trigger.value()))
            config.validate()
            return config
        low, high = w.odmr_ranges[0]
        config = CWConfig(low.value() * 1e6, high.value() * 1e6, w.cw_points.value(),
                          w.power.value(), w.cw_averages.value(), w.cw_settling.value() / 1000,
                          w.cw_samples.value(), w.cw_reference.isChecked())
        config.validate()
        return config

    def start(self):
        w = self.window
        if self.worker is not None:
            return
        if w.console.busy:
            logger.warning("Najpierw zakończ test diagnostyczny.")
            return
        try:
            config = self.config()
            if isinstance(config,PulsedConfig):
                same_polarity=self.station_config.laser_active_high==w.active_high.isChecked()
                self.station_config=replace(self.station_config,laser_active_high=w.active_high.isChecked(),
                    wiring_verified=self.station_config.wiring_verified and same_polarity)
                if not self.simulated and not config.timings_verified:
                    raise ValueError("Czasy niezweryfikowane: otwórz CZASY / OKNA i sprawdź kalibrację na stanowisku.")
            if not self.simulated:
                self.station_config = replace(self.station_config,
                    sg_address=w.console.sg_address.text().strip(),
                    scope_address=w.console.scope_address.text().strip(), backend=w.console.backend.currentData())
            self.station_config.validate(self.simulated)
        except ValueError as exc:
            w.feedback.setText(str(exc))
            logger.warning("Nie uruchomiono pomiaru: %s", exc)
            return
        self.last_run, self.points = None, []
        plot = w.measurement_plot
        plot.clear()
        label = "SYMULACJA" if self.simulated else "SPRZĘT"
        pulsed=isinstance(config,PulsedConfig)
        mode=getattr(config,"mode","CW ODMR")
        plot.setTitle(f"{mode} · {label}", color="#24395b")
        plot.setLabel("bottom", "Częstotliwość", units="Hz")
        plot.getAxis("bottom").enableAutoSIPrefix(True)
        if pulsed:
            plot.setLabel("bottom","Czas t = 2τ" if mode=="T2" else "Czas τ" if mode=="T1" else "Częstotliwość",
                units="Hz" if mode=="PULSED_ODMR" else "s")
            plot.setLabel("left","Różnica faz 180° − 0°" if mode=="T2" else "Różnica znormalizowana: bez π − z π",units="")
        else:
            plot.setLabel("left", "Kontrast (OFF−ON)/OFF" if config.reference else "Sygnał RF ON",
                          units="%" if config.reference else "V")
        plot.enableAutoRange(axis="y", enable=True)
        if pulsed:
            factor=1 if mode=="PULSED_ODMR" else 1e-9
            plot.setXRange(config.start*factor,config.stop*factor,padding=0.02)
        else:
            plot.setXRange(config.start_hz, config.stop_hz, padding=0.02)
        self.curve = plot.plot([], [], pen=pg.mkPen("#2468d9", width=2), symbol="o",
                               symbolSize=4, symbolBrush="#2468d9", symbolPen=None)
        w.tabs.setCurrentIndex(0)
        w.progress.setRange(0, config.points)
        w.progress.setValue(0)
        w.metrics.setText("Oczekiwanie na pierwszy odczyt…")
        self._lock(True)
        self.worker = AcquisitionWorker(config, self.station_config, self.simulated, self.output_dir, self)
        self.worker.point.connect(self._point)
        self.worker.status.connect(self._status)
        self.worker.result.connect(self._result)
        self.worker.devices.connect(self._devices)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def _status(self, text):
        self.window.status.setText(f"{'SYMULATOR' if self.simulated else 'SPRZĘT'} · {text}")

    @Slot(object)
    def _devices(self,identities):
        self.window.help_panel.identities(identities,self.simulated)

    def _point(self, point):
        self.points.append(point)
        w = self.window
        if isinstance(point,PulsedPoint):
            factor=1 if self.worker.config.mode=="PULSED_ODMR" else 1e-9
            self.curve.setData([p.x*factor for p in self.points],[p.difference for p in self.points])
            w.progress.setValue(len(self.points))
            ref_label,signal_label=("180°","0°") if self.worker.config.mode=="T2" else ("bez π","z π")
            w.metrics.setText(f"{ref_label}: {point.reference_ratio:.5f} | {signal_label}: {point.signal_ratio:.5f} | Δ: {point.difference:.5f}")
            w.waveform_plot.clear()
            for name,t,color in ((ref_label,point.reference_trace,"#22a078"),(signal_label,point.signal_trace,"#2468d9")):
                w.waveform_plot.plot([t.t0_s+i*t.dt_s for i in range(len(t.samples_v))],t.samples_v,
                    name=name,pen=pg.mkPen(color,width=1))
            cfg=self.worker.config
            for a,b,color in ((cfg.baseline_start_ns,cfg.baseline_stop_ns,(150,150,150,40)),
                (cfg.trigger_lead_ns+cfg.signal_start_ns,cfg.trigger_lead_ns+cfg.signal_stop_ns,(30,90,220,45)),
                (cfg.trigger_lead_ns+cfg.reference_start_ns,cfg.trigger_lead_ns+cfg.reference_stop_ns,(30,190,90,45))):
                w.waveform_plot.addItem(pg.LinearRegionItem([a*1e-9,b*1e-9],movable=False,brush=color))
            w.feedback.setText(f"{len(self.points)}/{w.progress.maximum()} · tło / sygnał / referencja zaznaczone na przebiegu.")
            return
        self.curve.setData([p.frequency_hz for p in self.points],
                           [100 * p.contrast if p.contrast is not None else p.signal_v for p in self.points])
        w.progress.setValue(len(self.points))
        w.metrics.setText(f"{point.frequency_hz/1e6:.3f} MHz  |  RF ON {point.signal_v*1000:.3f} mV  |  "
                         + (f"RF OFF {point.reference_v*1000:.3f} mV  |  kontrast {point.contrast*100:.3f}%"
                            if point.reference_v is not None else "bez referencji"))
        w.waveform_plot.clear()
        for name, traces, color in (("RF ON", point.rf_on, "#2468d9"), ("RF OFF", point.rf_off, "#22a078")):
            if traces:
                t = traces[-1]
                w.waveform_plot.plot([t.t0_s + i*t.dt_s for i in range(len(t.samples_v))], t.samples_v,
                                     name=name, pen=pg.mkPen(color, width=1))
        w.feedback.setText(f"{len(self.points)}/{w.progress.maximum()} punktów. Surowe odczyty zapisywane w tle.")

    def _result(self, result):
        self.last_run = result
        self.window.help_panel.run_result(result)
        if result.storage_errors:
            self.window.feedback.setText("AUTOZAPIS NIEPEŁNY: " + "; ".join(result.storage_errors)
                                         + ". Dane w pamięci — użyj SAVE.")
        elif result.error:
            self.window.feedback.setText(f"BŁĄD: {result.error}. Zachowano {len(result.points)} punktów.")
        else:
            self.window.feedback.setText(f"{result.state}: {len(result.points)} punktów. "
                                         + ("Dane syntetyczne." if result.simulated else "Odczyty ze sprzętu."))

    def _failed(self, message):
        self.window.feedback.setText(f"BŁĄD: {message}")
        logger.error(message)

    def _finished(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self._lock(False)
        if self.closing:
            QTimer.singleShot(0, self.window.close)

    def stop(self):
        if self.worker is not None:
            self.worker.stop_requested.set()
            self.window.stop_button.setEnabled(False)
            self._status("STOP: oczekiwanie na zakończenie bieżącej operacji i wyłączenie wyjść…")

    def pulse_settings(self):
        if self.worker is not None:
            return
        try:
            config=self.config()
        except ValueError as exc:
            self.window.feedback.setText(str(exc))
            return
        dialog=PulseSettingsDialog(config,self.window)
        if dialog.exec():
            w=self.window
            w.initialization.setValue(dialog.config.initialization_ns/1000)
            w.readout.setValue(dialog.config.readout_ns/1000)
            w.trigger.setValue(dialog.config.trigger_ns)
            w.delay.setValue(dialog.config.guard_ns)
            self.pulse_template=dialog.config
            self.preview_pulsed()

    def preview_pulsed(self):
        w=self.window
        w.invalidate_preview()
        try:
            cfg=self.config()
            x=cfg.stop if cfg.mode=="T1" and w.preview_tau.currentIndex() else cfg.start
            sequences=tuple(compile_pulsed(cfg,x,pi,w.active_high.isChecked()) for pi in (True,False))
        except ValueError as exc:
            w.feedback.setText(f"Błąd parametrów: {exc}")
            return
        w.last_sequences=sequences
        w.sequence_autoscale_button.setEnabled(True)
        tracks=(("Laser TTL","laser","#27935a"),("MW π","mw_gate","#297bc1"),
                ("Trigger","scope_trigger","#be7630"),("I [0…0,5 V]","iq_i","#8b66b1"))
        ticks=[]
        for index,(name,key,color) in enumerate(tracks):
            offset=(len(tracks)-index-1)*2
            xs=[];ys=[];cursor=0
            for duration,level in sequences[0].channels[key]:
                xs.extend((cursor/1000,(cursor+duration)/1000));ys.extend((offset+level,offset+level))
                cursor+=duration
            w.sequence_plot.plot(xs,ys,pen=pg.mkPen(color,width=2))
            ticks.append((offset+.5,name))
        if cfg.mode=="T2":
            xs=[];ys=[];cursor=0
            for duration,level in sequences[1].channels['iq_i']:
                xs.extend((cursor/1000,(cursor+duration)/1000));ys.extend((level,level));cursor+=duration
            w.sequence_plot.plot(xs,ys,pen=pg.mkPen("#e47830",width=2,style=Qt.PenStyle.DashLine))
        w.sequence_plot.getAxis("left").setTicks([ticks])
        w.sequence_plot.autoRange();w.tabs.setCurrentIndex(1)
        meaning="Echo Hahna; oś 2τ. Pomarańczowy I: referencja 180°. " if cfg.mode=="T2" else "Referencja bez π. τ: koniec π → laser ON. "
        w.feedback.setText(f"Cykl {sequences[0].duration_ns/1000:g} µs; laser ON={int(w.active_high.isChecked())}. "
            + meaning
            + ("Czasy potwierdzone przez operatora." if cfg.timings_verified else "Czasy robocze, wymagają kalibracji!"))

    def request_close(self):
        if self.worker is not None:
            self.closing = True
            self.stop()
            return False
        return True

    def save(self):
        if self.last_run is None or self.worker is not None:
            return
        prefix = "SIM" if self.last_run.simulated else "HW"
        mode=self.last_run.config.get('mode','CW_ODMR')
        path, _ = QFileDialog.getSaveFileName(self.window, "Zapis pomiaru — pełne surowe dane",
            f"{prefix}_{mode}.json", "Pełne dane JSON (*.json);;Podsumowanie CSV (*.csv)")
        if path:
            try:
                (save_csv if path.lower().endswith(".csv") else save_run)(self.last_run, path)
                logger.info("Zapisano: %s", path)
            except OSError as exc:
                self._failed(str(exc))
