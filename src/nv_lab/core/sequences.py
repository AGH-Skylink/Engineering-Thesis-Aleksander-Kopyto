"""OFFLINE educational T1 sequence compiler. No hardware I/O.

Generated with AI assistance; timing semantics require laboratory approval.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple

Pattern = List[Tuple[int, int]]


@dataclass(frozen=True)
class T1Settings:
    initialization_ns: int = 2_000_000
    pi_pulse_ns: int = 100
    tau_ns: int = 100_000
    readout_ns: int = 2_000_000
    trigger_ns: int = 300
    readout_delay_ns: int = 500
    laser_active_high: bool = False  # legacy runtime uses laser_on=0, verify in lab

    def validate(self) -> None:
        for key, value in vars(self).items():
            if key == 'laser_active_high':
                continue
            if not isinstance(value, int) or value < 0:
                raise ValueError(f'{key} must be an integer >= 0')
        if self.initialization_ns == 0 or self.readout_ns == 0 or self.trigger_ns == 0:
            raise ValueError('initialization, readout, trigger must be >0')
        if self.pi_pulse_ns > self.tau_ns:
            raise ValueError('π pulse must fit before the defined free-relaxation interval')


@dataclass(frozen=True)
class CompiledSequence:
    duration_ns: int
    channels: Dict[str, Pattern]
    metadata: Dict[str, object]


def _pattern_from_intervals(duration: int, intervals: List[Tuple[int, int]], idle: int, active: int) -> Pattern:
    """Build zero-gap normalized patterns from non-overlapping [start, stop) intervals."""
    pattern: Pattern = []
    cursor = 0
    for start, stop in sorted(intervals):
        if not (0 <= cursor <= start <= stop <= duration):
            raise ValueError('overlapping/out-of-range intervals')
        if start > cursor:
            pattern.append((start - cursor, idle))
        if stop > start:
            pattern.append((stop - start, active))
        cursor = stop
    if cursor < duration:
        pattern.append((duration - cursor, idle))
    return pattern


def compile_t1(config: T1Settings, with_pi: bool) -> CompiledSequence:
    """Proposed experiment: initialization; optional π; wait τ; laser readout.

    The no-π reference reserves an equal-length π slot so both cycles have
    equal length. τ always starts *after* this slot; in π mode that means after π.
    """
    config.validate()
    pi_start = config.initialization_ns
    pi_end = pi_start + config.pi_pulse_ns
    readout_start = pi_end + config.tau_ns + config.readout_delay_ns
    duration = readout_start + config.readout_ns
    laser_on = int(config.laser_active_high)
    laser_off = 1 - laser_on
    laser = _pattern_from_intervals(duration, [(0, config.initialization_ns),
                                               (readout_start, duration)], laser_off, laser_on)
    mw = _pattern_from_intervals(duration, [(pi_start, pi_end)] if with_pi else [], 0, 1)
    trigger = _pattern_from_intervals(duration,
                                      [(readout_start, readout_start + config.trigger_ns)], 0, 1)
    return CompiledSequence(duration, {'laser':laser, 'mw_gate':mw, 'scope_trigger':trigger},
                            {'tau_ns':config.tau_ns,'with_pi':with_pi,
                             'readout_start_ns':readout_start, 'note':'proposed/offline only'})
