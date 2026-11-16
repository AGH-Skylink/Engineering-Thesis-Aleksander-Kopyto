"""Run and save a CW ODMR acquisition without the GUI (simulation by default)."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import logging
from pathlib import Path
from threading import Event
import signal

from nv_lab.core.odmr import CWConfig, StationConfig
from nv_lab.experiments.cw_odmr import run_cw
from nv_lab.experiments.storage import RunJournal, save_csv, save_run
from nv_lab.hardware.simulators import SimStation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hardware", action="store_true", help="Use real instruments; default is simulation")
    parser.add_argument("--start-mhz", type=float, default=2820)
    parser.add_argument("--stop-mhz", type=float, default=2920)
    parser.add_argument("--points", type=int, default=101)
    parser.add_argument("--averages", type=int, default=3)
    parser.add_argument("--power-dbm", type=float, default=-30)
    parser.add_argument("--settling-ms", type=float, default=20)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--no-reference", action="store_true")
    parser.add_argument("--fail-after", type=int, default=0, help="Simulated scope error at this capture number")
    parser.add_argument("--output-dir", type=Path, default=Path("runs"))
    parser.add_argument("--sg", default=StationConfig.sg_address)
    parser.add_argument("--scope", default="")
    parser.add_argument("--pulse", default=StationConfig.pulse_address)
    parser.add_argument("--visa", default="@py")
    parser.add_argument("--channel", type=int, default=2)
    parser.add_argument("--wiring-verified", action="store_true")
    parser.add_argument("--direct-rf", action="store_true", help="Disable external I/Q (legacy station uses I/Q)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    config = CWConfig(args.start_mhz*1e6, args.stop_mhz*1e6, args.points, args.power_dbm,
                      args.averages, args.settling_ms/1000, args.samples, not args.no_reference)
    station_config = StationConfig(backend=args.visa, sg_address=args.sg, scope_address=args.scope,
        pulse_address=args.pulse, scope_channel=args.channel, sg_iq=not args.direct_rf,
        wiring_verified=args.wiring_verified, simulation_fail_after=args.fail_after)
    try:
        config.validate()
        station_config.validate(not args.hardware)
    except ValueError as exc:
        parser.error(str(exc))
    if args.hardware:
        from nv_lab.hardware.station import RealStation
        station = RealStation(station_config)
    else:
        station = SimStation(station_config)
    stop = Event()
    previous = signal.signal(signal.SIGINT, lambda *_: stop.set())
    journal = None
    base = None
    try:
        def started(run):
            nonlocal journal, base
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            base = args.output_dir / f"{'HW' if args.hardware else 'SIM'}_CW_{stamp}_{run.run_id[:8]}"
            journal = RunJournal(base.with_suffix(".jsonl"))
            journal.write("start", run.document())
        result = run_cw(station, config, stop, lambda p: journal.write("point", asdict(p)), on_start=started,
                        on_devices=lambda ids: journal.write("devices", ids))
        if journal:
            journal.write("end", {"state": result.state, "error": result.error,
                                   "cleanup_errors": result.cleanup_errors, "identities": result.identities})
        if base:
            save_run(result, base.with_suffix(".json"))
            save_csv(result, base.with_suffix(".csv"))
            print(f"Saved: {base}.json")
        print(f"{'SIMULATED' if result.simulated else 'HARDWARE'} | {result.state} | {len(result.points)} points")
        return 0 if result.state == "COMPLETED" else 130 if result.state == "STOPPED" else 1
    finally:
        if journal:
            journal.close()
        signal.signal(signal.SIGINT, previous)


if __name__ == "__main__":
    raise SystemExit(main())
