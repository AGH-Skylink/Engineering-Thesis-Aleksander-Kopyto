"""Paired π/no-π T1 and pulsed ODMR using an externally triggered scope."""
from dataclasses import asdict
import logging
import time
from threading import Event
from uuid import uuid4
from nv_lab.core.pulsed import compile_pulsed, window_means, PulsedPoint, PulsedRun
from nv_lab.experiments.cw_odmr import Cancelled, utc_now

logger=logging.getLogger(__name__)


def run_pulsed(station,config,stop=None,on_point=None,on_status=None,on_start=None,on_devices=None):
    config.validate()
    station.config.validate(station.simulated)
    if config.mode=="T2" and not station.config.sg_iq:
        raise ValueError("T2 z cyklem fazy wymaga zewnętrznego I/Q.")
    if not station.simulated and not config.timings_verified:
        raise ValueError("Najpierw potwierdź kalibrację π, opóźnień i okien pomiarowych na stanowisku.")
    max_sequence=compile_pulsed(config,config.stop,True,station.config.laser_active_high)
    if (config.average_count+2)*max_sequence.duration_ns*1e-9>station.config.timeout_s:
        raise ValueError("Seria impulsów przekracza timeout. Zmniejsz uśrednienia/τ lub zwiększ timeout.")
    stop=stop or Event()
    result=PulsedRun(str(uuid4()),station.simulated,asdict(config),asdict(station.config),utc_now())
    def check(delay=0):
        if stop.wait(delay):raise Cancelled()
    def status(message):
        logger.info("%s | %s", "SIM" if station.simulated else "HW",message)
        if on_status:on_status(message)
    try:
        if on_start:on_start(result)
        check();station.open()
        result.identities=dict(station.identities)
        if on_devices:on_devices(result.identities)
        station.rf.disable_output();station.pulse.constant(False,False)
        station.scope.configure_pulsed(config,station.config)
        pair="fazy końcowego π/2: 180° / 0°" if config.mode=="T2" else "pary bez π / z π"
        status(f"{config.mode}: zewnętrzny trigger, {pair}, WORD/LSBF.")
        for index,x in enumerate(config.axis()):
            check()
            frequency=x if config.mode=="PULSED_ODMR" else config.frequency_hz
            station.rf.disable_output();station.rf.configure(frequency,config.power_dbm)
            check(config.settling_s)
            traces=[];windows=[];sequences={}
            for with_pi in (False,True):
                check()
                sequence=compile_pulsed(config,x,with_pi,station.config.laser_active_high)
                station.pulse.constant(False,False)
                station.scope.arm_pulsed(stop,station.config.timeout_s)
                station.rf.set_output(True)
                station.pulse.stream_pulsed(sequence,config.average_count+2)
                deadline=time.monotonic()+station.config.timeout_s
                while not station.pulse.has_finished():
                    check(0.005)
                    if time.monotonic()>deadline:raise TimeoutError("Pulse Streamer nie zakończył sekwencji.")
                check()
                trace=station.scope.read_pulsed()
                traces.append(trace);windows.append(window_means(trace,config))
                key=("phase_0" if with_pi else "phase_180") if config.mode=="T2" else ("pi" if with_pi else "reference")
                sequences[key]=asdict(sequence)
                station.rf.disable_output();station.pulse.constant(False,False)
            point=PulsedPoint(index,x,frequency,windows[0]["ratio"],windows[1]["ratio"],
                windows[0]["ratio"]-windows[1]["ratio"],windows[0],windows[1],traces[0],traces[1],sequences)
            result.points.append(point)
            status(f"{index+1}/{config.points}: x={x:g}, różnica={point.difference:.6g}")
            if on_point:on_point(point)
        check();result.state="COMPLETED"
    except Cancelled:result.state="STOPPED"
    except Exception as exc:
        result.state="ERROR";result.error=f"{type(exc).__name__}: {exc}"
        logger.exception("Błąd pomiaru impulsowego")
    finally:
        result.identities=dict(station.identities)
        try:result.cleanup_errors=station.shutdown()
        except Exception as exc:result.cleanup_errors=[str(exc)]
        if result.cleanup_errors:result.state="ERROR"
        result.ended_utc=utc_now()
        status(f"{result.state}: {len(result.points)}/{config.points}, procedura OFF i zamknięcie sesji.")
    return result
