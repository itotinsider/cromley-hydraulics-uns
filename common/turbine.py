"""CH-Francis "Canyon" design data, shared by the dam simulator and the CH PLC simulator.

Both simulators import this file, so the dam's view of a unit (flow, power, rough zone, MW swings)
and the CH PLC's view (draft-tube pulsation, cavitation, bearing load) can never disagree about the
operating point. All figures are demo assumptions (design basis: "Copper Canyon Dam"), not OEM data.

Pure functions, standard library only, no I/O.
"""

import math

RHO = 1000.0            # kg/m³
G = 9.81                # m/s²

RATED_MW = 40.0         # generator rating
RATED_HEAD_M = 100.0    # net head at rating
RATED_RPM = 300.0       # 50 Hz, 20 pole pairs: 1X = 5 Hz
RATED_FREQ_HZ = 50.0
Q_MAX_M3S = 50.0        # flow at 100 % gate and rated head
RUNNER_BLADES = 13      # blade-pass = 13 × 5 Hz = 65 Hz
WICKET_GATES = 20
POLE_PAIRS = 10         # 300 rpm × 10 / 60 = 50 Hz

ETA_PEAK = 0.93         # best efficiency, at BEP_GATE
BEP_GATE = 0.87         # gate fraction of best efficiency (~45 m³/s at rated head)
ETA_CURV = 1.2          # efficiency falls with (g - BEP_GATE)²: ~0.77 at half gate
ETA_HEAD_CURV = 1.5e-5  # and with (H - rated)²: -0.6 points at 80 m
MECH_LOSS_MW = 0.6      # bearing/windage losses at rated speed

# Draft-tube vortex rope (part load): ~40-80 % of BEP flow, worst near 55 % gate.
ROUGH_GATE_LO = 0.35
ROUGH_GATE_HI = 0.70
ROUGH_GATE_PEAK = 0.55
ROPE_FREQ_RATIO = 0.28  # x runner frequency (Rheingans: 0.2-0.4)

# The plant controller's rough-zone table, in MW at rated head (see rough_zone_mw()).
P_MIN_MW = 3.0          # minimum stable load


def efficiency(gate, head_m):
    """Hill-chart-like hydraulic efficiency: peak ETA_PEAK at BEP_GATE and rated head."""
    g = max(0.0, min(1.0, gate))
    eta = ETA_PEAK - ETA_CURV * (g - BEP_GATE) ** 2 - ETA_HEAD_CURV * (head_m - RATED_HEAD_M) ** 2
    return max(0.0, eta)


def flow(gate, head_m):
    """Turbine flow in m³/s: proportional to gate opening and √head."""
    return Q_MAX_M3S * max(0.0, min(1.0, gate)) * math.sqrt(max(head_m, 0.0) / RATED_HEAD_M)


def hydraulic_mw(gate, head_m):
    """Shaft power at rated speed before mechanical losses: ρ·g·Q·H·η."""
    return RHO * G * flow(gate, head_m) * head_m * efficiency(gate, head_m) / 1e6


def shaft_mw(gate, head_m):
    return hydraulic_mw(gate, head_m) - MECH_LOSS_MW


def gate_for_mw(mw, head_m):
    """Inverse of shaft_mw() by bisection (the plant controller's feed-forward and rough-zone table)."""
    lo, hi = 0.0, 1.0
    if shaft_mw(hi, head_m) <= mw:
        return 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if shaft_mw(mid, head_m) < mw:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def max_mw(head_m):
    return min(RATED_MW * 1.05, shaft_mw(1.0, head_m))


def rough_zone_mw(head_m):
    """(lo, hi) MW band the plant controller avoids at this head."""
    return shaft_mw(ROUGH_GATE_LO, head_m), shaft_mw(ROUGH_GATE_HI, head_m)


def rope_intensity(gate, speed_frac=1.0):
    """0..1 strength of the draft-tube vortex rope: zero outside the rough zone, 1 at its peak."""
    if speed_frac < 0.9 or not (ROUGH_GATE_LO < gate < ROUGH_GATE_HI):
        return 0.0
    if gate <= ROUGH_GATE_PEAK:
        x = (gate - ROUGH_GATE_LO) / (ROUGH_GATE_PEAK - ROUGH_GATE_LO)
    else:
        x = (ROUGH_GATE_HI - gate) / (ROUGH_GATE_HI - ROUGH_GATE_PEAK)
    return math.sin(math.pi / 2 * max(0.0, min(1.0, x))) ** 1.5


def in_rough_zone(gate, speed_frac=1.0):
    return rope_intensity(gate, speed_frac) > 0.05


def cavitation_index(gate, head_m, tailwater_m):
    """0..~1.5 relative cavitation intensity (demo): high load, off-design head and low tailwater.

    A real one follows from Thoma's σ against the runner's critical σ; here three terms that move
    the right way: above ~80 % gate, at heads away from rated, and with the tailwater (the runner's
    submergence) below its normal ~304.5 m a.s.l.
    """
    load = max(0.0, gate - 0.80) * 2.5
    off_head = abs(head_m - RATED_HEAD_M) / 20.0 * max(0.0, gate - 0.5)
    submergence = max(0.0, 304.5 - tailwater_m) * 0.6 * gate
    return load + off_head + submergence
