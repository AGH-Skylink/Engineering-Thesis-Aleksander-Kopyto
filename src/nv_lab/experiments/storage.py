"""Recoverable acquisition journal and explicit raw-data exports."""
import csv
import json
from pathlib import Path


def save_run(run, path):
    """Write JSON through a neighbouring temporary file; retain the full raw traces."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(run.document(), ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)
    return path


def save_csv(run, path):
    with Path(path).open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        if run.config.get("mode") in ("T1","T2","PULSED_ODMR"):
            writer.writerow(["run_id","simulated","state","time_ns" if run.config["mode"]!="PULSED_ODMR" else "sweep_frequency_hz",
                             "frequency_hz","reference_ratio","signal_ratio","difference"])
            for p in run.points:
                writer.writerow([run.run_id,run.simulated,run.state,p.x,p.frequency_hz,p.reference_ratio,p.signal_ratio,p.difference])
            return
        writer.writerow(["run_id", "simulated", "state", "frequency_hz", "signal_v", "reference_v",
                         "contrast_fraction", "signal_sem_v", "reference_sem_v"])
        for point in run.points:
            writer.writerow([run.run_id, run.simulated, run.state, point.frequency_hz, point.signal_v,
                             point.reference_v, point.contrast, point.signal_sem_v, point.reference_sem_v])


class RunJournal:
    """Append/flush each completed point so a crash leaves readable partial data."""
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = path.open("x", encoding="utf-8")

    def write(self, event, data):
        self.stream.write(json.dumps({"event": event, "data": data}, ensure_ascii=False, allow_nan=False) + "\n")
        self.stream.flush()

    def close(self):
        self.stream.close()
