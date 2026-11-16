"""Paired RF OFF/ON CW ODMR, identical orchestration for real and simulated devices."""
from dataclasses import asdict
from datetime import datetime, timezone
import logging
from statistics import fmean, stdev
from threading import Event
from uuid import uuid4

from nv_lab.core.odmr import CWConfig, ODMRPoint, ODMRRun
from nv_lab.core.ports import CWStation

logger = logging.getLogger(__name__)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Cancelled(Exception):
    pass


def _mean_and_sem(values):
    return fmean(values), stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0


def run_cw(station: CWStation, config: CWConfig, stop: Event | None = None,
           on_point=None, on_status=None, on_start=None, on_devices=None) -> ODMRRun:
    """Always attempts all output-off/close actions, including partial-open failures."""
    config.validate()
    station.config.validate(station.simulated)
    stop = stop or Event()
    result = ODMRRun(str(uuid4()), station.simulated, asdict(config), asdict(station.config), utc_now())
    label = "SIM" if station.simulated else "HW"
    opened = False

    def checkpoint(delay=0):
        if stop.wait(delay):
            raise Cancelled()

    def status(message):
        logger.info("%s | %s", label, message)
        if on_status:
            on_status(message)

    try:
        if on_start:
            on_start(result)
        checkpoint()
        status("Łączenie z urządzeniami…")
        station.open()
        opened = True
        result.identities = dict(station.identities)
        if on_devices:
            on_devices(result.identities)
        station.rf.disable_output()
        station.pulse.constant(False, False)
        station.scope.configure(config.waveform_points)
        station.rf.configure(config.start_hz, config.power_dbm)
        checkpoint()
        status("CW ODMR: laser ciągły, parowane odczyty RF OFF/ON.")
        station.pulse.constant(True, False)
        for index, frequency in enumerate(config.frequencies()):
            checkpoint()
            station.rf.disable_output()
            station.rf.configure(frequency, config.power_dbm)
            off, on = [], []
            for repetition in range(config.averages):
                if config.reference:
                    station.rf.disable_output()
                    station.pulse.constant(True, False)
                    checkpoint(config.settling_s)
                    trace = station.scope.capture()
                    trace.validate()
                    if trace.metadata.get("clipped"):
                        raise ValueError("Przebieg RF OFF jest obcięty. Popraw skalę oscyloskopu.")
                    off.append(trace)
                checkpoint()
                station.pulse.constant(True, True)
                station.rf.set_output(True)
                checkpoint(config.settling_s)
                trace = station.scope.capture()
                trace.validate()
                if trace.metadata.get("clipped"):
                    raise ValueError("Przebieg RF ON jest obcięty. Popraw skalę oscyloskopu.")
                on.append(trace)
            station.rf.disable_output()
            signal, signal_sem = _mean_and_sem([fmean(t.samples_v) for t in on])
            reference, reference_sem, contrast = None, None, None
            if off:
                reference, reference_sem = _mean_and_sem([fmean(t.samples_v) for t in off])
                if abs(reference) < 1e-9:
                    raise ValueError("Sygnał referencyjny bliski zeru; nie można obliczyć kontrastu.")
                contrast = (reference - signal) / reference
            point = ODMRPoint(index, frequency, signal, reference, contrast,
                              signal_sem, reference_sem, on, off)
            result.points.append(point)
            logger.info("%s | %d/%d %.6f MHz: ON=%.6g V OFF=%s V", label,
                        index + 1, config.points, frequency / 1e6, signal,
                        f"{reference:.6g}" if reference is not None else "—")
            if on_point:
                on_point(point)
        checkpoint()
        result.state = "COMPLETED"
    except Cancelled:
        result.state = "STOPPED"
        status("Przerwano na żądanie. Zachowano ukończone punkty.")
    except Exception as exc:
        result.state, result.error = "ERROR", f"{type(exc).__name__}: {exc}"
        logger.exception("%s | Błąd CW ODMR", label)
    finally:
        result.identities = dict(station.identities)
        try:
            result.cleanup_errors = station.shutdown()
        except Exception as exc:
            result.cleanup_errors = [str(exc)]
        if result.cleanup_errors:
            result.state = "ERROR"
            logger.error("%s | Nie potwierdzono wyłączenia wyjść: %s", label, result.cleanup_errors)
        result.ended_utc = utc_now()
        status(f"{result.state}: {len(result.points)}/{config.points} punktów; "
               + (("procedura OFF zakończona; sesje zamknięte." if opened else
                   "bez rozpoczętej akwizycji; zakończono dostępne sesje.") if not result.cleanup_errors
                  else "BŁĄD wyłączenia wyjść — sprawdź stanowisko."))
    return result
