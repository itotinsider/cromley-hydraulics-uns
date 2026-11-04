"""Generate DRWPA's maintenance and operations records for the RCA demo (library/drwpa/records/).

Deterministic (fixed seed): rerunning gives the same files. The planted clues for the demo
scenarios are written explicitly below (search for "PLANTED"); everything else is routine
background generated from the PM plan with some realistic noise (missing failure codes, free text).

    python3 rca-demo/build/generate_records.py
"""

import csv
import datetime as dt
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "library", "drwpa", "records")
rng = random.Random(1987)

UNITS = {"Unit1": "CH-FR-1987-0042", "Unit2": "CH-FR-1987-0043", "Unit3": "CH-FR-1989-0051"}
UNO = {"Unit1": "U1", "Unit2": "U2", "Unit3": "U3"}
TODAY = dt.date(2026, 11, 3)

PEOPLE = {
    "mgr": "Elena Marsh", "sup": "Ray Okafor", "rel": "Priya Nandakumar", "mech": "Tom Halvorsen",
    "plan": "Gina Alvarez", "ic": "Dale Whitaker", "ic2": "Nora Fenwick", "tech1": "Luis Ortega",
    "tech2": "Ben Carver", "ssA": "Marcus Bell", "ssB": "Sofia Reyes", "ssC": "Jake Lindqvist",
    "sysops": "Karen Doyle", "ch": "Lars Bergström (Cromley Hydraulics)",
}


def write(name, header, rows):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(h, "") for h in header])
    print(f"wrote records/{name}: {len(rows)} rows")


# ===================================================================================== asset register
def asset_register():
    rows = [
        dict(functional_location="CCD", description="Copper Canyon Dam hydropower plant (3 x 40 MW)", level="Plant",
             parent="", equipment_class="Hydropower plant", manufacturer="", model="", serial="", criticality="A",
             in_service="1987", notes="Operator: Desert River Water & Power Authority (DRWPA)"),
    ]
    plant = [
        ("CCD-INT", "Intake with emergency gate, trash rack and raker", "Intake", "B", ""),
        ("CCD-INT-RAK", "Trash rack raker", "Raker", "C", "Runs automatically at rack DP >= 0.35 m"),
        ("CCD-PEN", "Steel penstock DN 5500, branches to Units 1-3", "Penstock", "A", ""),
        ("CCD-SPW-G01", "Spillway radial gate 01 with hydraulic hoist", "Gate", "A", "CH-Gate supply 1987"),
        ("CCD-SPW-G02", "Spillway radial gate 02 with hydraulic hoist", "Gate", "A", "CH-Gate supply 1987"),
        ("CCD-BOT", "Bottom outlet fixed-cone valve", "Valve", "B", "Keeps minimum river flow (10 m3/s)"),
        ("CCD-SWY", "150 kV switchyard", "Switchyard", "A", "Not CH supply"),
        ("CCD-CTL", "Plant control system: unit controllers, plant controller, SCADA", "Control system", "A",
         "Not CH supply. Unit protection on bearing element A, governor oil pressure, overspeed"),
    ]
    for fl, d, cls, crit, note in plant:
        rows.append(dict(functional_location=fl, description=d, level="Equipment unit", parent="CCD",
                         equipment_class=cls, criticality=crit, in_service="1987", notes=note))
    for unit, serial in UNITS.items():
        u = UNO[unit]
        year = "1989" if unit == "Unit3" else "1987"
        base = f"CCD-{u}"
        notes = {"Unit1": "Major overhaul 2019", "Unit2": "Major overhaul 2014", "Unit3": "Major overhaul 2017"}[unit]
        rows.append(dict(functional_location=base, description=f"{unit} generating unit, 40 MW", level="Equipment unit",
                         parent="CCD", equipment_class="Hydro generating unit", manufacturer="Cromley Hydraulics",
                         model="CH-Francis Canyon FC-40/100", serial=serial, criticality="A", in_service=year,
                         notes=notes))
        sub = [
            ("TUR", "Turbine (runner, wicket gates, spiral case, draft tube)", "Subunit", "A", ""),
            ("TUR-RUN", "Runner, 13 blades", "Maintainable item", "A", "Unit2: cavitation repair 2025 (RCA-2025-007)" if unit == "Unit2" else ""),
            ("TUR-WG", "Wicket gates (20) with shear pins and regulating ring", "Maintainable item", "A", ""),
            ("TUR-DT", "Draft tube cone", "Maintainable item", "B", "Unit2: cone stiffener cracks weld-repaired 2025 (RCA-2025-007)" if unit == "Unit2" else ""),
            ("TUR-SEAL", "Shaft seal (carbon segments)", "Maintainable item", "B", ""),
            ("BRG-THR", "Thrust bearing, 6 tilting pads", "Maintainable item", "A", ""),
            ("BRG-UGB", "Upper guide bearing", "Maintainable item", "A", ""),
            ("BRG-LGB", "Lower guide bearing", "Maintainable item", "A", ""),
            ("BRG-TGB", "Turbine guide bearing, oil bath", "Maintainable item", "A", {
                "Unit1": "Pads re-babbitted 2019 by Desert Bearing Services. Pad 3 radial clearance measured 0.24 mm "
                         "(design 0.30 +/- 0.05, tight), accepted on CH concession CH-CON-2019-017: trend pad 3 temperature.",
                "Unit2": "Pads re-scraped after wipe 2023 (RCA-2023-004), clearances in tolerance.",
                "Unit3": ""}[unit]),
            ("LUB", "Bearing lubrication (4 oil pots, ISO VG 68)", "Subunit", "A", ""),
            ("CW", "Cooling water system", "Subunit", "A", ""),
            ("CW-STR", "Unit cooling water strainer (duplex)", "Maintainable item", "A", ""),
            ("CW-TB", "Cooling circuit TB (TGB oil cooler)", "Maintainable item", "B", ""),
            ("CW-GB", "Cooling circuit GB (thrust, UGB, LGB coolers)", "Maintainable item", "B", ""),
            ("CW-AC", "Generator air coolers (6)", "Maintainable item", "B", ""),
            ("GOV-HPU", "Governor hydraulic power unit (2 pumps, accumulator)", "Subunit", "A", ""),
            ("GOV-SRV", "Wicket gate servomotors A and B", "Maintainable item", "A", ""),
            ("INV", "Butterfly inlet valve DN 3200", "Subunit", "A", ""),
            ("GEN", "Generator (rotor, stator, air coolers)", "Subunit", "A", "Not CH supply"),
            ("MON-PLC", "CH monitoring PLC (retrofit 2026)", "Subunit", "B", "Commissioned Sep 2026, publishes the CH tree"),
            ("MON-JB04", f"Junction box JB-{u}-04, headcover pit (TGB RTDs to CH PLC)", "Maintainable item", "C",
             "Wet area"),
        ]
        for code, d, lvl, crit, note in sub:
            rows.append(dict(functional_location=f"{base}-{code}", description=d, level=lvl, parent=base,
                             equipment_class=d.split(",")[0].split(" (")[0], criticality=crit,
                             manufacturer="" if code in ("GEN",) else "Cromley Hydraulics",
                             in_service="2026" if code.startswith("MON") else year, notes=note))
    write("asset-register.csv", ["functional_location", "description", "level", "parent", "equipment_class",
                                 "manufacturer", "model", "serial", "criticality", "in_service", "notes"], rows)


# ===================================================================================== FMECA
def fmeca():
    P = "v1.0/CH/Fleet/DRWPA/CopperCanyon/<serial>/"
    C = "v1.0/DRWPA/CopperCanyon/Powerhouse/<unit>/"
    rows = []

    def add(**k):
        k["rpn"] = int(k["S"]) * int(k["O"]) * int(k["D"])
        rows.append(k)

    add(id="FM-01", item="Turbine guide bearing (TGB)", function="Carry radial load at the runner, keep shaft centred",
        functional_failure="Bearing cannot carry load without overheating", failure_mode="OHE: pad overheating, babbitt wiping",
        mechanism="2.4 Wear; 2.7 Overheating", causes="Oil oxidation/degradation; clearance out of tolerance; contamination; overload at transients",
        local_effect="Pad temperature rises, oil film breaks down", unit_effect="Trip at 90 C on pad 1, forced outage, possible shaft/journal damage",
        detection="Oil sampling (Sn, TAN, MPC); pad temperatures (CH PLC, all pads); customer RTD pad 1 only",
        signals=f"{P}Bearings/TGB/PadTemp01..04; {P}Bearings/TGB/OilTemp; {C}TurbineGuideBearingTemp",
        S=8, O=3, D=3, task="Oil sampling quarterly (CH CH-DOC-OM-0101 ch. 10); oil change on condition, max 36 months",
        note="2026-10-12 PN: D=3 assumes quarterly sampling. PM plan is semi-annual since MOC-2025-004: review requested.",
        owner="Priya Nandakumar", status="Review open")
    add(id="FM-02", item="Cooling water supply (unit strainer)", function="Deliver 80 L/s cooling water to all coolers",
        functional_failure="Cooling flow below 70 %", failure_mode="PLU: strainer plugged", mechanism="5.1 Blockage/plugged",
        causes="Silt and debris (spring runoff); missed cleaning", local_effect="All circuit flows fall together",
        unit_effect="All bearings and generator warm up; trip on bearing temperature",
        detection="Strainer DP gauge (local rounds); owner total flow alarm < 56 L/s; CH circuit flows",
        signals=f"{C}CoolingWaterFlow; {P}Cooling/WaterFlow_TB; {P}Cooling/WaterFlow_GB; {P}Cooling/WaterFlow_AirCoolers",
        S=7, O=3, D=2, task="Strainer cleaning at DP > 0.3 bar; monthly Mar-Jun (MOC-2023-006)",
        note="After RCA-2023-004", owner="Tom Halvorsen", status="Current")
    add(id="FM-03", item="Bearing oil coolers", function="Remove bearing heat", functional_failure="Oil temperature high",
        failure_mode="OHE: oil overheating", mechanism="5.2 Contamination (fouling)", causes="Cooler fouling (scale, biofilm)",
        local_effect="Oil bath temperature rises slowly at constant load and inlet temperature", unit_effect="Reduced bearing margin",
        detection="Oil bath temperatures, cooler outlet temperature", signals=f"{P}Bearings/*/OilTemp; {P}Cooling/OilCoolerOutletTemp",
        S=5, O=3, D=3, task="Cooler inspection/cleaning 2 years", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-04", item="Bearing oil (all pots)", function="Lubricate and cool bearings", functional_failure="Oil unfit for service",
        failure_mode="PDE: oil contamination (water ingress)", mechanism="5.2 Contamination", causes="Cooler tube leak; seal water ingress",
        local_effect="Oil level rises, water in oil", unit_effect="Film strength loss, bearing damage",
        detection="Oil level; oil sampling (water ppm)", signals=f"{P}Bearings/*/OilLevel", S=7, O=2, D=3,
        task="Oil sampling (see FM-01)", note="", owner="Priya Nandakumar", status="Current")
    add(id="FM-05", item="Thrust bearing", function="Carry rotating weight and hydraulic thrust",
        functional_failure="Bearing cannot carry thrust load", failure_mode="OHE: pad overheating",
        mechanism="2.7 Overheating", causes="Oil degradation; HP lift failure at start; overload",
        local_effect="Pad temperatures rise", unit_effect="Trip, major outage",
        detection="Pad temperatures (CH all pads, owner pad 1); HP lift pressure; oil sampling",
        signals=f"{P}Bearings/Thrust/PadTemp01..06; {P}Bearings/Thrust/HPLiftPressure; {C}ThrustBearingTemp",
        S=9, O=2, D=3, task="Oil sampling; HP lift function test at each start", note="", owner="Priya Nandakumar", status="Current")
    add(id="FM-06", item="Bearing temperature measurement", function="Indicate true pad temperature",
        functional_failure="False high (or low) temperature", failure_mode="AIR: abnormal instrument reading",
        mechanism="3.3 Faulty signal/indication", causes="Loose or corroded terminal; moisture in connector; damaged cable",
        local_effect="One channel deviates from neighbours and oil bath", unit_effect="Spurious shutdown (lost production) or masked real problem",
        detection="Cross-check with neighbouring pads, oil bath and element A/B (OP-07)",
        signals=f"{P}Bearings/*/PadTemp*; {C}*BearingTemp", S=5, O=3, D=4,
        task="OP-07 alarm validation; JB connector/gland check 6 months (CH-SB-2026-03)",
        note="Added after RCA-2024-011. Interval for gland check added 2026-10-12, PM not yet created.",
        owner="Dale Whitaker", status="Review open")
    add(id="FM-07", item="Turbine (runner, draft tube)", function="Convert hydraulic energy smoothly",
        functional_failure="Excessive pressure pulsation and vibration", failure_mode="VIB: draft-tube vortex rope (part load)",
        mechanism="1.2 Vibration; 2.6 Fatigue", causes="Sustained operation in the rough zone (35-70 % gate)",
        local_effect="Draft tube pulsation ~1.4 Hz, TGB vibration, MW swings", unit_effect="Cone cracks, runner cavitation, bearing load",
        detection="Draft tube pressure waveform; TGB shaft vibration; gate vs rough-zone table",
        signals=f"{P}Vibration/DraftTube/Pressure/Waveform; {P}Vibration/TGB/ShaftX/Overall_um_pp; {C}GatePosition",
        S=7, O=3, D=4, task="Plant controller rough-zone table; OP-03 rev C (bypass needs reliability sign-off); inspect after > 50 h/year",
        note="After RCA-2025-007. Rough-zone hours KPI not yet implemented (action RCA-2025-007-A4 open).",
        owner="Priya Nandakumar", status="Action open")
    add(id="FM-08", item="Runner", function="Convert energy without material loss", functional_failure="Material loss on band/blades",
        failure_mode="STD: cavitation erosion", mechanism="2.1 Cavitation", causes="High load, low head, low tailwater, part load",
        local_effect="High-frequency headcover energy", unit_effect="Efficiency loss, repair outage",
        detection="Annual inspection; headcover accelerometer", signals=f"{P}Vibration/Headcover/Accel/Waveform; {P}Vibration/Headcover/Vel_mm_s_rms",
        S=5, O=3, D=4, task="Annual runner inspection", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-09", item="Runner", function="Structural integrity", functional_failure="Blade crack", failure_mode="BRD: runner blade crack",
        mechanism="2.6 Fatigue", causes="Rotor-stator interaction, rough-zone operation, weld defects",
        local_effect="Blade-pass sidebands, 2X on headcover", unit_effect="Blade loss, major damage",
        detection="Annual inspection (NDT); headcover accelerometer", signals=f"{P}Vibration/Headcover/Accel/Waveform",
        S=10, O=1, D=5, task="Annual inspection, NDT every 4 years", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-10", item="Shaft line", function="Run with low vibration", functional_failure="Shaft vibration above alert",
        failure_mode="VIB: mechanical unbalance", mechanism="1.2 Vibration", causes="Rotor pole/rim shift; after maintenance",
        local_effect="1X up, stable phase, rises with speed", unit_effect="Bearing load, fatigue",
        detection="Shaft proximity probes (overall, 1X vector)", signals=f"{P}Vibration/UGB/ShaftX/Waveform; {P}Vibration/*/Shaft*/Overall_um_pp",
        S=6, O=2, D=2, task="Balance check after rotor work", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-11", item="Shaft line", function="Run aligned", functional_failure="Shaft vibration above alert",
        failure_mode="VIB: misalignment / bearing clearance", mechanism="1.3 Clearance/alignment failure",
        causes="Foundation movement; bearing wear; assembly", local_effect="1X + 2X, elliptical orbit",
        unit_effect="Bearing overload", detection="Shaft proximity probes (orbit, 2X)", signals=f"{P}Vibration/*/Shaft*/Waveform",
        S=6, O=2, D=3, task="Alignment check at major overhaul", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-12", item="Wicket gates", function="Regulate flow", functional_failure="Gate not following ring",
        failure_mode="BRD: shear pin broken", mechanism="2.5 Breakage", causes="Debris jammed between gates; overload",
        local_effect="One gate out of position; vibration step", unit_effect="Unit must stop",
        detection="Shear pin switches; breakaway alarm; vibration step", signals=f"{P}Turbine/ShearPinStatus; {P}Turbine/WicketGateBreakawayAlarm",
        S=7, O=2, D=1, task="Annual inspection", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-13", item="Governor HPU", function="Supply 58-63 bar oil to servomotors", functional_failure="Pressure below 52 bar",
        failure_mode="INL: internal leakage / pump wear", mechanism="2.4 Wear", causes="Pump wear; valve leakage",
        local_effect="Pump starts per hour rise; faster pressure decay", unit_effect="Low-pressure trip (48 bar), loss of gate control",
        detection="Pump starts per hour; accumulator pressure", signals=f"{P}Governor/HPU/PumpStartsPerHour; {P}Governor/HPU/AccumulatorPressure; {C}GovernorOilPressure",
        S=8, O=2, D=2, task="HPU oil sample 6 months; filter 12 months", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-14", item="Servomotors", function="Hold gate position", functional_failure="Gate drifts, oil loss",
        failure_mode="ELU: external leakage (servomotor seal)", mechanism="1.1 Leakage", causes="Seal wear",
        local_effect="Sump level falls; servo position error", unit_effect="Oil spill to tailrace (environmental)",
        detection="Sump level; servo A/B position", signals=f"{P}Governor/HPU/SumpLevel; {P}Governor/HPU/ServoPositionA; {P}Governor/HPU/ServoPositionB",
        S=6, O=2, D=2, task="Annual inspection", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-15", item="Shaft seal", function="Limit leakage into headcover pit", functional_failure="Leakage high",
        failure_mode="ELP: external leakage (seal wear)", mechanism="2.4 Wear", causes="Carbon segment wear; abrasive water",
        local_effect="Seal water flow and headcover sump pump starts rise", unit_effect="Humid pit, flooding risk",
        detection="Seal water flow; sump pump starts", signals=f"{P}Turbine/ShaftSealWaterFlow; {P}Turbine/HeadcoverSumpPumpStarts",
        S=4, O=3, D=2, task="Annual inspection; trend", note="", owner="Tom Halvorsen", status="Current")
    add(id="FM-16", item="Generator", function="Keep air gap", functional_failure="Air gap below limit",
        failure_mode="STD: rotor/stator deformation", mechanism="1.4 Deformation", causes="Loose rim, thermal cycling, pole shift",
        local_effect="Minimum air gap falls", unit_effect="Rub risk, major damage", detection="Air gap sensor",
        signals=f"{P}Generator/AirGapMin_mm", S=9, O=1, D=3, task="Air gap check at major overhaul", note="Not CH supply; sensor via CH PLC",
        owner="Tom Halvorsen", status="Current")
    add(id="FM-17", item="Intake trash rack", function="Pass water, keep debris out", functional_failure="Head loss high",
        failure_mode="PLU: rack clogged", mechanism="5.1 Blockage", causes="Storm debris; raker failure",
        local_effect="Rack DP rises", unit_effect="Lower net head, output loss", detection="Rack DP; raker status",
        signals="v1.0/DRWPA/CopperCanyon/Intake/TrashRackDP; v1.0/DRWPA/CopperCanyon/Intake/RakerRunning",
        S=4, O=4, D=1, task="Raker inspection 3 months", note="", owner="Tom Halvorsen", status="Current")
    write("fmeca_ch-francis-unit.csv",
          ["id", "item", "function", "functional_failure", "failure_mode", "mechanism", "causes", "local_effect",
           "unit_effect", "detection", "signals", "S", "O", "D", "rpn", "task", "note", "owner", "status"], rows)


# ===================================================================================== PM plan
PM = [
    # id, fl suffix, task, interval_days, type, source, notes, last done offset handled in work orders
    ("PM-OIL-BRG", "LUB", "Bearing oil sampling, all 4 pots (Thrust, UGB, LGB, TGB)", 182, "CBM",
     "MOC-2025-004 (was 91 days per CH-DOC-OM-0101)", "Interval extended Feb 2025"),
    ("PM-OIL-CHG", "LUB", "Bearing oil change (per pot)", 1461, "TBM",
     "MOC-2025-004 (was 730 days; CH recommends on condition, max 36 months)", "Interval extended Feb 2025"),
    ("PM-STR", "CW-STR", "Clean unit cooling water strainer, record DP before/after", 91, "TBM",
     "CH-DOC-OM-0101 ch. 6", "Monthly Mar-Jun (MOC-2023-006)"),
    ("PM-CLR", "CW", "Inspect/clean bearing oil coolers", 730, "TBM", "CH-DOC-OM-0101 ch. 10", ""),
    ("PM-HPU-OIL", "GOV-HPU", "HPU oil sample", 182, "CBM", "CH-DOC-OM-0101 ch. 10", ""),
    ("PM-HPU-FLT", "GOV-HPU", "Change HPU pressure filter element", 365, "TBM", "CH-DOC-OM-0101 ch. 10", ""),
    ("PM-ACC", "GOV-HPU", "Accumulator pre-charge check", 365, "TBM", "CH-DOC-OM-0101 ch. 10", ""),
    ("PM-ANN", "TUR", "Annual unit inspection: runner, draft tube cone, wicket gates, shear pins, shaft seal", 365,
     "Inspection", "CH-DOC-OM-0101 ch. 10", "Draft tube cone NDT after > 50 h/year in rough zone"),
    ("PM-JB", "MON-JB04", "Inspect CH PLC RTD connectors and cable glands in wet areas", 182, "Inspection",
     "CH-SB-2026-03", "PROPOSED 2026-10-12 (FMECA FM-06), not yet scheduled"),
    ("PM-RAK", "INT-RAK", "Trash rack raker inspection", 91, "Inspection", "DRWPA", "Plant level"),
]


def pm_plan():
    rows = []
    for pid, fl, task, days, typ, src, note in PM:
        scope = "CCD-INT-RAK" if fl == "INT-RAK" else "CCD-U1/U2/U3-" + fl
        status = "Proposed" if pid == "PM-JB" else "Active"
        rows.append(dict(task_id=pid, functional_location=scope, task=task, interval_days=days, type=typ,
                         basis=src, status=status, notes=note))
    write("pm-plan.csv", ["task_id", "functional_location", "task", "interval_days", "type", "basis", "status", "notes"], rows)


# ===================================================================================== oil analysis
OIL_LAB = "Mesa Lubricant Labs"


def oil_status(v):
    action = v["tan"] > 0.40 or v["water"] > 500 or v["sn"] > 15 or v["mpc"] > 30 or v["fe"] > 25
    caution = v["tan"] >= 0.25 or v["water"] >= 200 or v["sn"] >= 5 or v["mpc"] >= 20 or v["fe"] >= 10
    return "Action" if action else ("Caution" if caution else "Normal")


def sample_dates():
    d = []
    for y in range(2021, 2025):
        for m in (2, 5, 8, 11):
            d.append(dt.date(y, m, 9))
    for y in (2025, 2026):
        for m in (2, 8):
            d.append(dt.date(y, m, 9))
    return d


def oil_analysis(wo_log):
    rows = []
    n = 0
    # oil change dates per (unit, pot): oil age drives TAN, MPC and tin
    changes = {}
    for i, u in enumerate(UNITS):
        for p in ("Thrust", "UGB", "LGB"):
            changes[(u, p)] = [dt.date(2020, 6 + i, 10), dt.date(2022, 6 + i, 10), dt.date(2024, 6 + i, 10)]
    changes[("Unit1", "TGB")] = [dt.date(2021, 1, 20), dt.date(2023, 1, 18)]   # PLANTED: Jan 2025 change cancelled (MOC-2025-004)
    changes[("Unit2", "TGB")] = [dt.date(2021, 3, 10), dt.date(2023, 3, 22)]   # 2023 change after the wipe
    changes[("Unit3", "TGB")] = [dt.date(2021, 5, 12), dt.date(2023, 5, 16)]
    for d in sample_dates():
        for u in UNITS:
            for p in ("Thrust", "UGB", "LGB", "TGB"):
                last = max([c for c in changes[(u, p)] if c <= d], default=dt.date(2019, 6, 1))
                age = (d - last).days / 365.0
                v = dict(visc=round(68 + rng.gauss(0, 0.8) + 0.6 * age, 1),
                         tan=round(0.10 + 0.035 * age + abs(rng.gauss(0, 0.01)), 2),
                         water=int(80 + rng.gauss(0, 25) + (30 if p == "TGB" else 0)),
                         sn=round(max(0.5, 1.2 + 0.5 * age + rng.gauss(0, 0.4)), 1),
                         fe=round(max(0.5, 2 + 0.6 * age + rng.gauss(0, 0.6)), 1),
                         cu=round(max(0.2, 1 + rng.gauss(0, 0.3)), 1),
                         mpc=int(8 + 2.5 * age + rng.gauss(0, 1.5)), iso="16/14/11")
                comment = ""
                # PLANTED: Unit 1 TGB oxidation and babbitt trend
                if (u, p) == ("Unit1", "TGB") and d >= dt.date(2024, 5, 1):
                    trend = {dt.date(2024, 5, 1): (0.19, 3.6, 14), dt.date(2024, 8, 1): (0.21, 4.2, 15),
                             dt.date(2024, 11, 1): (0.22, 4.6, 16), dt.date(2025, 2, 1): (0.24, 5.4, 18),
                             dt.date(2025, 8, 1): (0.30, 8.1, 22), dt.date(2026, 2, 1): (0.34, 10.9, 25),
                             dt.date(2026, 8, 1): (0.38, 14.2, 28)}
                    key = max(k for k in trend if k <= d)
                    v["tan"], v["sn"], v["mpc"] = trend[key]
                    v["iso"] = "17/15/12" if d.year == 2026 else v["iso"]
                st = oil_status(v)
                if st == "Caution":
                    comment = {"Unit1": "Oxidation (TAN, MPC) and tin trending up together: early babbitt distress "
                                        "possible. Resample within 30 days; consider oil change and flush."}.get(u, "Monitor.")
                    if (u, p) != ("Unit1", "TGB"):
                        comment = "Single parameter at caution level. Monitor at next routine sample."
                if (u, p) == ("Unit1", "TGB") and d >= dt.date(2026, 8, 1):
                    comment = ("CAUTION. Tin 14.2 ppm (was 10.9), TAN 0.38, MPC 28: oxidation and babbitt wear "
                               "accelerating. Resample within 30 days. Plan oil change and flush; inspect TGB if "
                               "tin exceeds 15 ppm.")
                n += 1
                rows.append(dict(sample_id=f"MLL-{d.year}-{n:05d}", sample_date=d.isoformat(), unit=u,
                                 serial=UNITS[u], compartment=p, lab=OIL_LAB, viscosity_40C_cSt=v["visc"],
                                 tan_mgKOH_g=v["tan"], water_ppm=max(20, v["water"]), tin_Sn_ppm=v["sn"],
                                 iron_Fe_ppm=v["fe"], copper_Cu_ppm=v["cu"], iso4406=v["iso"], mpc_dE=v["mpc"],
                                 status=st, lab_comment=comment))
    # PLANTED: the 2023-03 post-event sample on Unit 2 TGB (before the oil change)
    rows.append(dict(sample_id="MLL-2023-00412", sample_date="2023-03-15", unit="Unit2", serial=UNITS["Unit2"],
                     compartment="TGB", lab=OIL_LAB, viscosity_40C_cSt=67.4, tan_mgKOH_g=0.16, water_ppm=110,
                     tin_Sn_ppm=31.5, iron_Fe_ppm=6.2, copper_Cu_ppm=1.4, iso4406="20/18/15", mpc_dE=13,
                     status="Action", lab_comment="Post-event sample. Babbitt particles present (tin 31.5 ppm). "
                                                  "Change oil, flush, inspect bearing."))
    rows.append(dict(sample_id="MLL-2025-00703", sample_date="2025-09-04", unit="Unit1", serial=UNITS["Unit1"],
                     compartment="TGB", lab=OIL_LAB, viscosity_40C_cSt=70.1, tan_mgKOH_g=0.31, water_ppm=104,
                     tin_Sn_ppm=8.3, iron_Fe_ppm=3.9, copper_Cu_ppm=1.1, iso4406="16/14/12", mpc_dE=22,
                     status="Caution", lab_comment="Resample. Results confirm August: oxidation and tin trend. "
                                                   "Monitor at next routine sample; consider oil change."))
    rows.sort(key=lambda r: (r["sample_date"], r["unit"], r["compartment"]))
    write("oil-analysis_2021-2026.csv",
          ["sample_id", "sample_date", "unit", "serial", "compartment", "lab", "viscosity_40C_cSt", "tan_mgKOH_g",
           "water_ppm", "tin_Sn_ppm", "iron_Fe_ppm", "copper_Cu_ppm", "iso4406", "mpc_dE", "status", "lab_comment"], rows)


# ===================================================================================== work orders
WO_HEADER = ["wo_number", "created", "completed", "status", "type", "priority", "functional_location", "unit",
             "short_text", "long_text", "failure_mode", "failure_mechanism", "failure_cause", "detection_method",
             "downtime_h", "labour_h", "reported_by", "assigned_to", "linked_docs"]
counters = {}


def wo_no(year):
    counters[year] = counters.get(year, 0) + rng.randint(1, 4)
    return f"WO-{year}-{counters[year]:04d}"


def work_orders():
    rows = []

    def add(created, short, fl, unit="", typ="PM", status="CLOSED", completed=None, long="", fm="", mech="",
            cause="", det="", down=0, lab=None, prio="3", rep=None, ass=None, links="", number=None):
        created = created if isinstance(created, dt.date) else dt.date.fromisoformat(created)
        if completed is None and status == "CLOSED":
            same_day = typ == "MOD" or short.startswith(("Bearing oil sampling", "HPU oil sample"))
            completed = created + dt.timedelta(days=0 if same_day else rng.randint(0, 6))
        rows.append(dict(wo_number=number or wo_no(created.year), created=created.isoformat(),
                         completed=completed.isoformat() if isinstance(completed, dt.date) else (completed or ""),
                         status=status, type=typ, priority=prio, functional_location=fl, unit=unit, short_text=short,
                         long_text=long, failure_mode=fm, failure_mechanism=mech, failure_cause=cause,
                         detection_method=det, downtime_h=down, labour_h=lab if lab is not None else rng.choice([2, 3, 4, 6, 8]),
                         reported_by=rep or PEOPLE["plan"], assigned_to=ass or rng.choice([PEOPLE["tech1"], PEOPLE["tech2"]]),
                         linked_docs=links))

    # ---- routine PM work orders
    for unit in UNITS:
        u = UNO[unit]
        for y in range(2021, 2027):
            for m in range(1, 13):
                d = dt.date(y, m, 5 + rng.randint(0, 15))
                if d > TODAY:
                    continue
                if m in (1, 4, 7, 10) or (m in (3, 4, 5, 6) and y >= 2023):
                    dp = round(rng.uniform(0.12, 0.28), 2)
                    if m in (4, 5) and rng.random() < 0.3:
                        dp = round(rng.uniform(0.3, 0.42), 2)
                    add(d, "Clean cooling water strainer", f"CCD-{u}-CW-STR", unit, long=f"DP before {dp} bar, after 0.05 bar. Basket changed over.",
                        ass=PEOPLE["tech1"], lab=2)
                if m in (3, 9):
                    add(d, "HPU oil sample", f"CCD-{u}-GOV-HPU", unit, long="Sample sent to Mesa Lubricant Labs. Result normal.", lab=1)
                if m == 6:
                    add(d, "Change HPU pressure filter element", f"CCD-{u}-GOV-HPU", unit, long=f"Filter DP before change {round(rng.uniform(0.6, 1.4), 1)} bar.", lab=2)
                    add(d, "Accumulator pre-charge check", f"CCD-{u}-GOV-HPU", unit, long="Pre-charge in tolerance.", lab=2)
            # annual inspection
            ann = dt.date(y, {"Unit1": 10, "Unit2": 10, "Unit3": 3}[unit], {"Unit1": 4, "Unit2": 18, "Unit3": 2}[unit])
            if ann <= TODAY and not (unit == "Unit2" and y == 2025):
                add(ann, "Annual unit inspection", f"CCD-{u}-TUR", unit, typ="INS", completed=ann + dt.timedelta(days=4),
                    long="Runner, draft tube cone, wicket gates, shear pins and shaft seal inspected. No findings requiring action."
                         + (" Minor cavitation pitting on runner band, depth < 1 mm, recorded." if rng.random() < 0.4 else ""),
                    down=96, lab=60, ass=PEOPLE["mech"])
        # bearing oil sampling work orders (match the lab samples: quarterly to 2024, semi-annual from 2025)
        for y in range(2021, 2027):
            for m in ((2, 5, 8, 11) if y <= 2024 else (2, 8)):
                d = dt.date(y, m, 9)
                if d <= TODAY:
                    add(d, "Bearing oil sampling, 4 pots", f"CCD-{u}-LUB", unit, long="Samples Thrust, UGB, LGB, TGB to Mesa Lubricant Labs.", lab=2)

    # bearing oil changes (old 24-month cycle until MOC-2025-004)
    for i, unit in enumerate(UNITS):
        u = UNO[unit]
        for d in (dt.date(2022, 6 + i, 10), dt.date(2024, 6 + i, 10)):
            add(d, "Bearing oil change Thrust, UGB, LGB", f"CCD-{u}-LUB", unit, long="Oil changed, pots flushed, ISO VG 68.",
                down=24, lab=24, ass=PEOPLE["tech1"])
    add("2021-01-20", "TGB oil change", "CCD-U1-LUB", "Unit1", long="TGB pot drained, flushed, refilled ISO VG 68.", down=12, lab=10)
    add("2023-01-18", "TGB oil change", "CCD-U1-LUB", "Unit1", long="TGB pot drained, flushed, refilled ISO VG 68.", down=12, lab=10)
    add("2021-03-10", "TGB oil change", "CCD-U2-LUB", "Unit2", long="TGB pot drained, flushed, refilled.", down=12, lab=10)
    add("2021-05-12", "TGB oil change", "CCD-U3-LUB", "Unit3", long="TGB pot drained, flushed, refilled.", down=12, lab=10)
    add("2023-05-16", "TGB oil change", "CCD-U3-LUB", "Unit3", long="TGB pot drained, flushed, refilled.", down=12, lab=10)
    # PLANTED: the U1 TGB oil change due Jan 2025 never happened
    add("2025-01-08", "U1 TGB oil change (24-month PM)", "CCD-U1-LUB", "Unit1", typ="PM", status="CANCELLED", completed="",
        long="Postponed 2025-01-14 pending MOC-2025-004. Cancelled 2025-02-24: new interval 48 months, next due 2027-01.",
        links="MOC-2025-004", lab=0, number="WO-2025-0011")
    add("2025-03-12", "U2 TGB oil change (24-month PM)", "CCD-U2-LUB", "Unit2", typ="PM", status="CANCELLED", completed="",
        long="Cancelled: new interval 48 months per MOC-2025-004.", links="MOC-2025-004", lab=0)

    # raker and plant routine
    for y in range(2021, 2027):
        for m in (1, 4, 7, 10):
            d = dt.date(y, m, 20)
            if d <= TODAY:
                add(d, "Trash rack raker inspection", "CCD-INT-RAK", long="Chain, rake teeth and limit switches checked.", lab=3)

    # ---- background corrective work (with realistic gaps in coding)
    background = [
        ("Raker chain broken, replaced 2 links", "CCD-INT-RAK", "", "BRD", "2.5 Breakage", "3.4 Expected wear and tear", "7 Casual observation"),
        ("HPU oil top-up, sump at 58 %", "GOV-HPU", "u", "", "", "", ""),
        ("Shaft seal leaking more than usual, adjusted", "TUR-SEAL", "u", "ELP", "2.4 Wear", "3.4 Expected wear and tear", "3 Inspection"),
        ("Headcover sump pump not starting, contactor replaced", "TUR", "u", "FTS", "4.0 Electrical failure", "", "7 Casual observation"),
        ("Inlet valve seal water leak", "INV", "u", "ELU", "1.1 Leakage", "3.4 Expected wear and tear", "3 Inspection"),
        ("Generator air cooler tube leak, plugged", "CW-AC", "u", "ELU", "2.2 Corrosion", "3.4 Expected wear and tear", "3 Inspection"),
        ("Bearing oil level gauge glass dirty, cleaned", "LUB", "u", "", "", "", ""),
        ("Noise at wicket gate linkage", "TUR-WG", "u", "NOI", "", "", "7 Casual observation"),
        ("Spillway gate 01 hoist oil leak at fitting", "CCD-SPW-G01", "", "ELU", "1.1 Leakage", "3.3 Maintenance error", "3 Inspection"),
        ("Bottom outlet valve exercise, stiff, lubricated", "CCD-BOT", "", "SER", "1.6 Sticking", "3.4 Expected wear and tear", "2 Functional testing"),
        ("strainer DP gauge broken", "CW-STR", "u", "", "", "", ""),
        ("Governor oil temp high in summer, fan cleaned", "GOV-HPU", "u", "OHE", "5.2 Contamination", "3.4 Expected wear and tear", "4 Periodic condition monitoring"),
        ("unit tripped on grid disturbance, restarted", "", "u", "UST", "5.3 Miscellaneous external influences", "5.4 Other unit/cascading", "6 Production interference"),
        ("Brake pad wear check, ok", "GEN", "u", "", "", "", ""),
        ("LGB oil level slightly high, checked", "LUB", "u", "", "", "", ""),
    ]
    for y in range(2021, 2027):
        for _ in range(9 if y < 2026 else 7):
            short, fl, scope, fm, mech, cause, det = rng.choice(background)
            unit = rng.choice(list(UNITS)) if scope == "u" else ""
            full_fl = fl if fl.startswith("CCD") else (f"CCD-{UNO[unit]}-{fl}" if unit else "CCD")
            d = dt.date(y, rng.randint(1, 12), rng.randint(1, 28))
            if d > TODAY - dt.timedelta(days=10):
                continue
            if rng.random() < 0.15:   # noise: some technicians skip the codes
                fm = mech = cause = det = ""
            add(d, short, full_fl, unit, typ="CM", long=short + "." if rng.random() < 0.6 else "",
                fm=fm, mech=mech, cause=cause, det=det, down=rng.choice([0, 0, 0, 2, 4]), prio=rng.choice(["2", "3", "3", "4"]))

    # ---- PLANTED: key events
    # Unit 2 TGB wipe 2023 (RCA-2023-004)
    add("2023-03-14", "U2 TRIP bearing temp TGB", "CCD-U2-BRG-TGB", "Unit2", typ="EM", prio="1",
        completed=dt.date(2023, 3, 24),
        long="Unit 2 tripped 04:12 on TGB temperature (pad 1 element, 90 C). Cooling water total flow found at 48 L/s, "
             "strainer DP 0.62 bar, basket full of silt (spring runoff). TGB inspected: pads 1-4 lightly wiped, re-scraped "
             "by CH field service. Oil changed and pot flushed. Strainer cleaned. See RCA-2023-004.",
        fm="OHE", mech="2.7 Overheating", cause="3.3 Maintenance error", det="6 Production interference",
        down=238, lab=180, rep=PEOPLE["ssC"], ass=PEOPLE["mech"], links="RCA-2023-004", number="WO-2023-0204")
    add("2023-04-03", "Add monthly strainer cleaning Mar-Jun (MOC-2023-006)", "CCD-U1/U2/U3-CW-STR", typ="MOD",
        long="PM plan updated: monthly strainer cleaning March to June on all units.", links="RCA-2023-004; MOC-2023-006",
        rep=PEOPLE["mech"], ass=PEOPLE["plan"], lab=2)

    # Unit 3 spurious thrust temperature 2024 (RCA-2024-011)
    add("2024-08-19", "U3 thrust brg temp high - unit stopped", "CCD-U3-BRG-THR", "Unit3", typ="EM", prio="1",
        completed=dt.date(2024, 8, 20),
        long="Thrust bearing temperature (control room, pad 1) jumped from 66 to 84 C and back several times. "
             "Shift supervisor stopped the unit at 21:40 as a precaution. Oil bath temp unchanged at 52 C. "
             "Inspection: bearing fine. I&C found loose, corroded terminal in JB-U3-01 for the pad 1 RTD, re-terminated. "
             "Unit back 11:50 next day. See RCA-2024-011.",
        fm="AIR", mech="3.3 Faulty signal/indication", cause="2.2 Installation error", det="5 Continuous condition monitoring",
        down=14.2, lab=16, rep=PEOPLE["ssB"], ass=PEOPLE["ic"], links="RCA-2024-011", number="WO-2024-0649")
    add("2024-10-02", "Issue OP-07 bearing temperature alarm response", "CCD-CTL", typ="MOD",
        long="New operating procedure OP-07: validate bearing temperature alarms before stopping, unless trip level.",
        links="RCA-2024-011; MOC-2024-015", rep=PEOPLE["rel"], ass=PEOPLE["rel"], lab=6)

    # MOC-2025-004 PM optimisation
    add("2025-02-24", "Update PM intervals per MOC-2025-004", "CCD-U1/U2/U3-LUB", typ="MOD",
        long="Bearing oil sampling 91 -> 182 days, bearing oil change 730 -> 1461 days, all units, all pots. "
             "Budget saving approx. USD 38k/year.", links="MOC-2025-004", rep=PEOPLE["sup"], ass=PEOPLE["plan"], lab=2)
    add("2025-09-04", "U1 TGB oil resample (lab caution Aug 2025)", "CCD-U1-LUB", "Unit1", typ="CBM",
        long="Resample taken. Result similar to August (TAN 0.31, Sn 8.3). Lab: monitor at next routine sample.",
        links="MLL Aug 2025", ass=PEOPLE["tech2"], lab=1)

    # Summer 2025 rough-zone bypass and Unit 2 damage (RCA-2025-007)
    add("2025-06-02", "Enable rough-zone bypass, plant controller (MOC-2025-012)", "CCD-CTL", typ="MOD",
        long="Plant controller rough-zone table bypassed to allow regulation reserve band 15-35 MW per unit as requested by System Ops.",
        links="MOC-2025-012", rep=PEOPLE["sysops"], ass=PEOPLE["ic"], lab=4)
    add("2025-10-20", "U2 annual inspection: draft tube cone cracks, runner cavitation", "CCD-U2-TUR", "Unit2", typ="INS",
        prio="2", completed=dt.date(2025, 10, 24),
        long="Draft tube cone: 3 cracks at stiffener welds (lengths 80, 140, 210 mm). Runner band: cavitation erosion "
             "over 0.4 m2, max depth 4 mm. Not seen at 2024 inspection. See RCA-2025-007.",
        fm="STD", mech="2.6 Fatigue; 2.1 Cavitation", cause="3.1 Off-design service", det="3 Inspection",
        down=96, lab=70, ass=PEOPLE["mech"], links="RCA-2025-007", number="WO-2025-0821")
    add("2025-10-25", "U2 weld repair draft tube cone, runner cavitation repair", "CCD-U2-TUR-DT", "Unit2", typ="CM", prio="2",
        completed=dt.date(2025, 11, 3), long="Cracks ground out and welded, NDT ok. Runner band built up and ground. CH field service attended.",
        fm="STD", mech="2.6 Fatigue", cause="3.1 Off-design service", det="3 Inspection", down=216, lab=240,
        ass=PEOPLE["mech"], links="RCA-2025-007", number="WO-2025-0834")
    add("2025-12-08", "Restore plant controller rough-zone table", "CCD-CTL", typ="MOD",
        long="Bypass removed, table restored. MOC-2025-012 closed.", links="RCA-2025-007; MOC-2025-012",
        ass=PEOPLE["ic"], lab=3)
    add("2026-01-15", "Issue OP-03 rev C (reliability sign-off for rough-zone bypass)", "CCD-CTL", typ="MOD",
        long="OP-03 revised: any bypass of the rough-zone table requires a reliability engineer sign-off on the MOC.",
        links="RCA-2025-007; MOC-2025-019", rep=PEOPLE["rel"], ass=PEOPLE["rel"], lab=4)
    add("2026-02-10", "Implement rough-zone hours KPI per unit", "CCD-CTL", typ="MOD", status="OPEN",
        completed="", long="Action RCA-2025-007-A4. Waiting for CH monitoring PLC data (retrofit Sep 2026).",
        links="RCA-2025-007", rep=PEOPLE["rel"], ass=PEOPLE["ic"], lab=0)

    # CH monitoring PLC retrofit Sep 2026
    for unit, start in (("Unit1", "2026-09-08"), ("Unit2", "2026-09-15"), ("Unit3", "2026-09-22")):
        u = UNO[unit]
        s = dt.date.fromisoformat(start)
        add(s, f"{u} CH monitoring PLC retrofit (MOC-2026-007)", f"CCD-{u}-MON-PLC", unit, typ="MOD",
            completed=s + dt.timedelta(days=4), long="Dual-element RTDs on pad 1 of each bearing, element B and pads 2..n to CH PLC, "
            "proximity probes, accelerometer, draft tube PT, circuit flowmeters. Commissioned with CH field service.",
            down=104, lab=120, ass=PEOPLE["ic"], links="MOC-2026-007; CH-DOC-OM-0101 Rev 4")
    # PLANTED: deferred resample (A)
    add("2026-08-28", "U1 TGB oil resample - lab CAUTION", "CCD-U1-LUB", "Unit1", typ="CBM", status="DEFERRED", prio="3",
        completed="", long="Lab result Aug 2026 Caution (Sn 14.2, TAN 0.38, MPC 28): resample within 30 days. "
        "Deferred 2026-09-02: technicians on CH retrofit outages. New date not set.",
        rep=PEOPLE["plan"], ass=PEOPLE["tech2"], lab=0, links="MLL Aug 2026", number="WO-2026-0672")
    # punch list
    add("2026-09-12", "Punch: U1 TGB pad 4 reads 1-3 K above the other pads", "CCD-U1-MON-PLC", "Unit1", typ="CM",
        long="Checked loop resistance and calibration: ok. Fixed pad offset, consistent with CH manual 4.3. Accepted.",
        ass=PEOPLE["ic2"], rep=PEOPLE["ch"], lab=2, number="WO-2026-0912")
    add("2026-09-19", "Punch: U2 keyphasor gap adjust", "CCD-U2-MON-PLC", "Unit2", typ="CM", long="Gap set to 1.5 mm.",
        ass=PEOPLE["ic2"], rep=PEOPLE["ch"], lab=1, number="WO-2026-0921")
    # PLANTED: open gland (G)
    add("2026-09-26", "Punch: U3 JB-U3-04 cable gland TGB RTD cable not fully tightened", "CCD-U3-MON-JB04", "Unit3",
        typ="CM", status="OPEN", prio="4", completed="",
        long="CH commissioning punch item. Gland for the TGB RTD cable to the CH PLC (pad 1 element B and pads 2-4) in JB-U3-04 (headcover pit) not fully tightened, "
             "seal insert missing from site stock. Temporary tape. Schedule with next U3 outage.",
        ass=PEOPLE["ic2"], rep=PEOPLE["ch"], lab=0, number="WO-2026-0753")
    add("2026-07-08", "U3 headcover sump pump replaced", "CCD-U3-TUR", "Unit3", typ="CM",
        long="Pump running continuously, impeller worn. Replaced. Pit was flooded to 20 cm for ~2 h.",
        fm="LOO", mech="2.4 Wear", cause="3.4 Expected wear and tear", det="7 Casual observation", lab=6)
    add("2026-10-21", "U3 strainer DP 0.35 bar after rain, cleaned", "CCD-U3-CW-STR", "Unit3", typ="CM",
        long="DP before 0.35 bar, after 0.05.", fm="PLU", mech="5.1 Blockage/plugged", cause="3.4 Expected wear and tear",
        det="3 Inspection", lab=2)
    # PLANTED: bypass enabled again (C)
    add("2026-11-02", "Enable rough-zone bypass U2 for regulation reserve trial (MOC-2026-019)", "CCD-CTL", "Unit2",
        typ="MOD", completed=dt.date(2026, 11, 2),
        long="Per MOC-2026-019 (temporary, 2026-11-03 to 2026-11-17): plant controller rough-zone table bypassed for Unit 2 only. "
             "Unit 2 to carry regulation reserve at part load.", links="MOC-2026-019", rep=PEOPLE["sysops"],
        ass=PEOPLE["ic"], lab=2, number="WO-2026-0856")

    # number work orders in date order, as a CMMS would (gaps = work orders for other assets)
    rows.sort(key=lambda r: (r["created"], r["short_text"]))
    last = {}
    for r in rows:
        d = dt.date.fromisoformat(r["created"])
        n = max(int(d.timetuple().tm_yday * 2.8), last.get(d.year, 0) + 1)
        last[d.year] = n
        r["wo_number"] = f"WO-{d.year}-{n:04d}"
    for r in rows:
        if r["linked_docs"] or r["status"] != "CLOSED" or r["type"] == "EM":
            print("   key WO:", r["wo_number"], r["created"], r["status"], r["short_text"])
    write("work-orders_2021-2026.csv", WO_HEADER, rows)


# ===================================================================================== MOC register
def moc_register():
    rows = [
        dict(moc_id="MOC-2023-006", raised="2023-03-30", title="Monthly strainer cleaning in high-silt season",
             description="Clean unit strainers monthly March-June in addition to the quarterly PM.", type="Permanent",
             originator=PEOPLE["mech"], reliability_signoff="T. Halvorsen 2023-03-30", approved_by=PEOPLE["sup"],
             approved="2023-04-02", status="Implemented", expiry="", links="RCA-2023-004"),
        dict(moc_id="MOC-2024-015", raised="2024-09-12", title="OP-07 Bearing temperature alarm response",
             description="Validate a bearing temperature alarm (neighbouring pads, oil bath, second element) before stopping, unless at trip level.",
             type="Permanent", originator=PEOPLE["rel"], reliability_signoff="P. Nandakumar 2024-09-12",
             approved_by=PEOPLE["mgr"], approved="2024-09-30", status="Implemented", expiry="", links="RCA-2024-011"),
        dict(moc_id="MOC-2025-004", raised="2025-02-03", title="PM optimisation: bearing oil intervals",
             description="Extend bearing oil sampling from quarterly to semi-annual and bearing oil change from 24 to 48 months, all units and pots. "
                         "Rationale: oil results mostly normal 2021-2024; budget target 2025.",
             type="Permanent", originator=PEOPLE["sup"],
             reliability_signoff="P. Nandakumar 2025-02-11: CONDITIONAL. Agree for Thrust/UGB/LGB. TGB results vary more and Unit 1 TGB "
                                 "TAN/tin trend upward: keep TGB sampling quarterly and change U1 TGB oil as planned (due Jan 2025).",
             approved_by=PEOPLE["sup"], approved="2025-02-20",
             status="Implemented as proposed (condition not incorporated)", expiry="", links="PM plan; oil analysis"),
        dict(moc_id="MOC-2025-012", raised="2025-05-26", title="Rough-zone bypass for regulation reserve (summer 2025)",
             description="Bypass plant controller rough-zone table so units can hold 15-35 MW for the regulation reserve contract.",
             type="Temporary", originator=PEOPLE["sysops"], reliability_signoff="Not requested",
             approved_by=PEOPLE["mgr"], approved="2025-05-30", status="Closed 2025-12-08 (reverted)", expiry="2025-09-30",
             links="RCA-2025-007"),
        dict(moc_id="MOC-2025-019", raised="2025-12-15", title="OP-03 rev C: reliability sign-off for rough-zone bypass",
             description="Any bypass of the rough-zone table requires a documented reliability engineer sign-off and a limit on hours.",
             type="Permanent", originator=PEOPLE["rel"], reliability_signoff="P. Nandakumar 2025-12-15",
             approved_by=PEOPLE["mgr"], approved="2026-01-12", status="Implemented", expiry="", links="RCA-2025-007"),
        dict(moc_id="MOC-2026-007", raised="2026-04-14", title="CH monitoring PLC retrofit, Units 1-3",
             description="Install CH monitoring PLCs with dual-element RTDs, vibration, cooling and HPU monitoring; MQTT to site broker.",
             type="Permanent", originator=PEOPLE["rel"], reliability_signoff="P. Nandakumar 2026-04-14",
             approved_by=PEOPLE["mgr"], approved="2026-05-04", status="Implemented (punch items open)", expiry="",
             links="CH-DOC-OM-0101 Rev 4"),
        dict(moc_id="MOC-2026-019", raised="2026-10-27", title="Temporary rough-zone bypass Unit 2: regulation reserve trial",
             description="Two-week trial of the new regulation reserve product: Unit 2 holds part load inside the rough zone while Units 1 and 3 "
                         "carry the rest. Revenue estimate USD 46k for the trial.",
             type="Temporary", originator=PEOPLE["sysops"],
             reliability_signoff="PENDING (requested 2026-10-28, P. Nandakumar on leave until 2026-11-04)",
             approved_by=PEOPLE["mgr"], approved="2026-10-30", status="Active", expiry="2026-11-17",
             links="OP-03 rev C; RCA-2025-007"),
    ]
    write("moc-register.csv", ["moc_id", "raised", "title", "description", "type", "originator",
                               "reliability_signoff", "approved_by", "approved", "status", "expiry", "links"], rows)


# ===================================================================================== shift log
def shift_log():
    rows = []
    sup = {"A": PEOPLE["ssA"], "B": PEOPLE["ssB"], "C": PEOPLE["ssC"]}
    routine = [
        "Plant on AGC, setpoint 110 MW. All units generating. No alarms.",
        "Rounds complete. Strainer DPs normal. Nothing to report.",
        "Grid frequency stable. Reservoir level steady.",
        "Raker ran twice, rack DP normal.",
        "Quiet shift. All units in PLANT mode.",
    ]
    outage = [("Unit1", dt.date(2026, 9, 8), dt.date(2026, 9, 12)), ("Unit2", dt.date(2026, 9, 15), dt.date(2026, 9, 19)),
              ("Unit3", dt.date(2026, 9, 22), dt.date(2026, 9, 26)), ("Unit1", dt.date(2026, 10, 4), dt.date(2026, 10, 8)),
              ("Unit2", dt.date(2026, 10, 18), dt.date(2026, 10, 22))]
    d = dt.date(2026, 9, 1)
    while d <= TODAY:
        out = [u for u, a, b in outage if a <= d <= b]
        for shift, hour in (("A", 6), ("B", 14), ("C", 22)):
            if rng.random() < 0.55:
                t = dt.datetime(d.year, d.month, d.day, hour) + dt.timedelta(minutes=rng.randint(30, 7 * 60))
                if out:
                    text = rng.choice([f"{out[0]} out of service (planned). Other units on AGC, no alarms.",
                                       "Rounds complete. Strainer DPs normal. Nothing to report.",
                                       "Grid frequency stable. Reservoir level steady."])
                else:
                    text = rng.choice(routine)
                if t.date() <= TODAY and t < dt.datetime(2026, 11, 3, 13, 30):
                    rows.append(dict(timestamp=t.strftime("%Y-%m-%dT%H:%M"), shift=shift, supervisor=sup[shift],
                                     unit="", entry=text))
        d += dt.timedelta(days=1)

    def e(ts, shift, unit, text):
        rows.append(dict(timestamp=ts, shift=shift, supervisor=sup[shift], unit=unit, entry=text))

    for unit, s in (("Unit1", 8), ("Unit2", 15), ("Unit3", 22)):
        e(f"2026-09-{s:02d}T06:30", "A", unit, f"{unit} stopped and isolated for CH monitoring PLC retrofit. Plant setpoint reduced to 80 MW.")
        e(f"2026-09-{s + 4:02d}T15:10", "B", unit, f"{unit} returned to service after CH PLC retrofit. CH viewer shows all channels.")
    e("2026-10-04T06:20", "A", "Unit1", "Unit1 stopped for annual inspection.")
    e("2026-10-08T14:50", "B", "Unit1", "Unit1 back in service after annual inspection.")
    e("2026-10-18T06:25", "A", "Unit2", "Unit2 stopped for annual inspection.")
    e("2026-10-22T15:30", "B", "Unit2", "Unit2 back in service after annual inspection. Draft tube cone checked, no new cracks.")
    e("2026-09-30T23:40", "C", "Unit3", "Heavy rain. U3 headcover sump pump running often, pit humid.")
    e("2026-10-08T09:15", "A", "", "System Ops (K. Doyle) asked whether units can hold part load for the new regulation reserve product. Referred to plant manager.")
    e("2026-10-14T16:20", "B", "Unit3", "U3 headcover pit humid again after rain, condensation on JB covers.")
    e("2026-10-20T07:45", "A", "Unit1", "U1 TGB temperature (control room) 66 C at 38 MW, about 1 C above usual for this load. Within limits.")
    e("2026-10-21T10:30", "A", "Unit3", "U3 strainer DP 0.35 bar after rain, cleaned by L. Ortega.")
    e("2026-10-27T13:05", "A", "", "MOC-2026-019 raised by System Ops: Unit 2 regulation reserve trial from 3 Nov.")
    e("2026-10-29T22:50", "C", "Unit3", "U3 headcover sump pump starts higher than usual tonight. Pit humid.")
    e("2026-11-02T15:40", "B", "Unit2", "D. Whitaker enabled rough-zone bypass for Unit 2 per MOC-2026-019 (active from tomorrow 06:00). "
                                         "Reliability sign-off still pending, plant manager approved.")
    e("2026-11-03T06:05", "A", "Unit2", "Regulation reserve trial started. U2 on part load per plant controller. U1 and U3 near 42 MW.")
    # scenario A: how the shift learned of the CH alarm (CH viewer on a second screen, no horn, no
    # acknowledge) and the OP-07 response; values from history/scenario-A at these times
    e("2026-11-03T09:03", "A", "Unit1", "Checking U2 vibration for the trial in the CH viewer (second screen): red HH badge on Unit1, "
                                         "TGB pad 3 85 C. Viewer also lists TGB pad 3 H since 23:54 yesterday. Control room U1 TGB 70 C, "
                                         "no SCADA alarm. Started OP-07 checks.")
    e("2026-11-03T09:14", "A", "Unit1", "OP-07 checks with N. Fenwick (I&C on call) by phone: TGB pads 2 and 4 72-73 C, warmer than pad 1 "
                                         "and creeping up with pad 3 over the last 30 min (viewer trend); TGB oil 58 C; pad 1 element A 70.2, "
                                         "element B 70.0; TB cooling flow 8.0 L/s, inlet 14.7 C; gate 84 %, out of the rough zone; TGB "
                                         "vibration 56 um pp, unchanged. Bearing problem per OP-07 §4. U1 to 34 MW (LOCAL). P. Nandakumar on "
                                         "leave until 4 Nov; oil sample requested from T. Halvorsen.")
    e("2026-11-03T09:48", "A", "Unit1", "U1 TGB pad 3 still 81.5 C after 30 min at 34 MW. HH was reached: controlled stop per OP-07 §4, "
                                         "agreed with E. Marsh by phone.")
    e("2026-11-03T09:55", "A", "Unit1", "U1 stopped 09:51. Not to be restarted before TGB inspection. Level 1 RCA required (PRO-REL-01).")
    rows.sort(key=lambda r: r["timestamp"])
    write("shift-log_2026-09_2026-11.csv", ["timestamp", "shift", "supervisor", "unit", "entry"], rows)


if __name__ == "__main__":
    asset_register()
    fmeca()
    pm_plan()
    oil_analysis(None)
    work_orders()
    moc_register()
    shift_log()
