"""The MQTT namespace of Copper Canyon Dam: single source of truth for both topic trees.

Copied into every image. Publishers build their topics from here, subscribers read their topics
from here, and tools/inventory.py turns it into inventory/ (tested against the code).

Two trees on one broker:

  customer tree   v1.0/DRWPA/CopperCanyon/<Area>/<Module>/<Tag>          (dam simulator)
                  ... /Cmd/<Command>                                      (dam SCADA, grid operator)
  CH tree         v1.0/CH/Fleet/<CustomerId>/<SiteId>/<AssetSerial>/<Subsystem>/<Component>/<Metric>
                                                                          (one CH PLC per turbine)

Plus the hardwired signals: a handful of dual-element sensors on each turbine whose second element
is wired to the customer's unit controller (copper, not MQTT; see HARDWIRED).

Never rename a published topic without a note in the PR: external clients (edge devices, Node-RED,
MQTT Explorer bookmarks) break.
"""

VERSION = "v1.0"

# ----------------------------------------------------------------------------- customer tree
CUSTOMER_ID = "DRWPA"            # Desert River Water & Power Authority
SITE_ID = "CopperCanyon"
CUSTOMER_PREFIX = f"{VERSION}/{CUSTOMER_ID}/{SITE_ID}"
UNITS = ("Unit1", "Unit2", "Unit3")
SPILLWAY_GATES = ("Gate01", "Gate02")

UNIT_STATES = ("Stopped", "Starting", "SpeedNoLoad", "Synchronising", "Generating", "Stopping", "Tripped")
CONTROL_MODES = ("PLANT", "LOCAL")   # unit follows the plant controller, or its own MW setpoint
GATE_MODES = ("AUTO", "MAN")         # spillway gates, bottom outlet


def _t(path, unit, kind, desc, dec=2, lo=None, hi=None):
    return {"path": path, "unit": unit, "type": kind, "desc": desc, "dec": dec, "lo": lo, "hi": hi}


def customer_tags():
    """Every measured topic of the customer tree (relative to CUSTOMER_PREFIX), in publish order."""
    tags = [
        _t("Reservoir/Level", "m a.s.l.", "float", "Reservoir water level", 3, 380, 426),
        _t("Reservoir/Inflow", "m³/s", "float", "River inflow into the reservoir (estimated)", 1, 0, 3000),
        _t("Reservoir/Volume", "hm³", "float", "Stored volume above the dead storage at 380 m a.s.l.", 2, 0, 500),
        _t("River/TailwaterLevel", "m a.s.l.", "float", "Tailwater level below the powerhouse", 3, 300, 315),
        _t("River/Flow", "m³/s", "float", "Total release to the river (units + spillway + bottom outlet)", 1, 0, 3000),
        _t("Plant/GrossHead", "m", "float", "Reservoir level - tailwater level", 2, 60, 125),
        _t("Plant/TotalMW", "MW", "float", "Sum of the unit outputs", 2, -5, 130),
        _t("Plant/MWSetpoint", "MW", "float", "Plant MW setpoint from the grid operator (incl. AGC)", 1, 0, 130),
        _t("Plant/MWSetpointReachable", "", "bool", "False when the online units can't make the setpoint", 0),
        _t("Plant/AGCEnabled", "", "bool", "The grid operator's AGC adds small setpoint changes", 0),
        _t("Plant/GridFrequency", "Hz", "float", "Grid frequency at the 150 kV busbar", 3, 49, 51),
        _t("Intake/GatePosition", "%", "float", "Intake (emergency) gate position, 100 = open", 1, 0, 100),
        _t("Intake/TrashRackDP", "m", "float", "Head loss across the trash rack (clogging)", 3, 0, 2),
        _t("Intake/RakerRunning", "", "bool", "Trash rack raker cleaning cycle active", 0),
        _t("Penstock/Pressure", "bar", "float", "Penstock pressure at the powerhouse manifold", 2, 0, 16),
        _t("Penstock/Flow", "m³/s", "float", "Total penstock flow (all three units)", 1, 0, 160),
    ]
    for g in SPILLWAY_GATES:
        tags += [
            _t(f"Spillway/{g}/Position", "%", "float", f"Spillway radial gate {g[-2:]} position", 1, 0, 100),
            _t(f"Spillway/{g}/Flow", "m³/s", "float", f"Flow over spillway gate {g[-2:]}", 1, 0, 1200),
            _t(f"Spillway/{g}/Mode", "", "string", "AUTO (opens near 420 m a.s.l.) or MAN", 0),
        ]
    tags += [
        _t("BottomOutlet/ValvePosition", "%", "float", "Fixed-cone valve position", 1, 0, 100),
        _t("BottomOutlet/Flow", "m³/s", "float", "Bottom outlet flow", 1, 0, 70),
        _t("BottomOutlet/Mode", "", "string", "AUTO (keeps the minimum river flow) or MAN", 0),
    ]
    for u in UNITS:
        p = f"Powerhouse/{u}"
        tags += [
            _t(f"{p}/State", "", "string", "Unit state: " + ", ".join(UNIT_STATES), 0),
            _t(f"{p}/BreakerClosed", "", "bool", "Generator breaker closed", 0),
            _t(f"{p}/ControlMode", "", "string", "PLANT (plant controller) or LOCAL (own MW setpoint)", 0),
            _t(f"{p}/MWSetpoint", "MW", "float", "Unit MW setpoint (from the plant controller or local)", 2, 0, 45),
            _t(f"{p}/MW", "MW", "float", "Active power", 2, -5, 45),
            _t(f"{p}/MVAr", "MVAr", "float", "Reactive power", 2, -20, 25),
            _t(f"{p}/GatePosition", "%", "float", "Wicket gate position", 1, 0, 100),
            _t(f"{p}/GateSetpoint", "%", "float", "Governor gate setpoint", 1, 0, 100),
            _t(f"{p}/Speed", "rpm", "float", "Shaft speed", 1, 0, 600),
            _t(f"{p}/Flow", "m³/s", "float", "Turbine flow", 2, 0, 60),
            _t(f"{p}/NetHead", "m", "float", "Net head at the unit (gross head - penstock losses)", 2, 60, 125),
            _t(f"{p}/InletValveOpen", "", "bool", "Butterfly inlet valve fully open", 0),
            _t(f"{p}/ActiveAlarms", "", "json", "Unit controller alarms and trip causes (list of codes)", 0),
            # The customer's own (hardwired) sensors on the CH turbine: one element of each
            # dual-element sensor, see HARDWIRED.
            _t(f"{p}/ThrustBearingTemp", "°C", "float", "Thrust bearing pad 1 temperature (customer RTD element)", 1, 0, 150),
            _t(f"{p}/UpperGuideBearingTemp", "°C", "float", "Upper guide bearing pad 1 temperature (customer RTD element)", 1, 0, 150),
            _t(f"{p}/LowerGuideBearingTemp", "°C", "float", "Lower guide bearing pad 1 temperature (customer RTD element)", 1, 0, 150),
            _t(f"{p}/TurbineGuideBearingTemp", "°C", "float", "Turbine guide bearing pad 1 temperature (customer RTD element)", 1, 0, 150),
            _t(f"{p}/CoolingWaterFlow", "L/s", "float", "Total unit cooling water flow", 1, 0, 120),
            _t(f"{p}/GovernorOilPressure", "bar", "float", "Governor HPU accumulator pressure", 1, 0, 80),
        ]
    return tags


def customer_commands():
    """Command topics (relative to CUSTOMER_PREFIX). The dam simulator subscribes to `.../Cmd/#`.

    Payload: a bare value or JSON {"value": ...} (optionally "source"). Never retained: a retained
    Start would replay on every simulator restart.
    """
    cmds = [
        {"path": "Plant/Cmd/MWSetpoint", "type": "float", "lo": 0, "hi": 130, "unit": "MW",
         "desc": "Grid operator: plant MW setpoint, split over the units in PLANT mode"},
        {"path": "Plant/Cmd/AGC", "type": "bool", "desc": "Grid operator: AGC on/off (small automatic setpoint changes)"},
        {"path": "Intake/Cmd/GatePosition", "type": "float", "lo": 0, "hi": 100, "unit": "%",
         "desc": "Intake gate position; closing is refused while a unit is not stopped"},
        {"path": "BottomOutlet/Cmd/Mode", "type": "enum", "values": list(GATE_MODES), "desc": "AUTO or MAN"},
        {"path": "BottomOutlet/Cmd/Position", "type": "float", "lo": 0, "hi": 100, "unit": "%",
         "desc": "Valve position (switches the outlet to MAN)"},
    ]
    for g in SPILLWAY_GATES:
        cmds += [
            {"path": f"Spillway/{g}/Cmd/Mode", "type": "enum", "values": list(GATE_MODES), "desc": "AUTO or MAN"},
            {"path": f"Spillway/{g}/Cmd/Position", "type": "float", "lo": 0, "hi": 100, "unit": "%",
             "desc": "Gate position (switches the gate to MAN)"},
        ]
    for u in UNITS:
        p = f"Powerhouse/{u}/Cmd"
        cmds += [
            {"path": f"{p}/Start", "type": "trigger", "desc": "Start sequence to Generating (permissives checked)"},
            {"path": f"{p}/Stop", "type": "trigger", "desc": "Normal shutdown: unload, open breaker, close gates, brakes"},
            {"path": f"{p}/EmergencyStop", "type": "trigger", "desc": "Emergency stop (latched, needs Reset at standstill)"},
            {"path": f"{p}/Reset", "type": "trigger", "desc": "Reset a trip once the unit is at standstill and no cause is active"},
            {"path": f"{p}/ControlMode", "type": "enum", "values": list(CONTROL_MODES), "desc": "PLANT or LOCAL"},
            {"path": f"{p}/MWSetpoint", "type": "float", "lo": 0, "hi": 42, "unit": "MW",
             "desc": "Local MW setpoint (switches the unit to LOCAL)"},
        ]
    return cmds


EVENTS_TOPIC = "Plant/Events"   # non-retained JSON events: commands accepted/refused, trips, sequence steps

# ----------------------------------------------------------------------------- CH tree
CH_PREFIX = f"{VERSION}/CH/Fleet"

# The serial is the asset's identity for CH: it stays when the customer renames "Unit 1" or the
# unit is refurbished. The customer's name only lives in _meta/Nameplate.
ASSETS = (
    {"serial": "CH-FR-1987-0042", "unit": "Unit1", "commissioned": 1987, "seed": 42},
    {"serial": "CH-FR-1987-0043", "unit": "Unit2", "commissioned": 1987, "seed": 43},
    {"serial": "CH-FR-1989-0051", "unit": "Unit3", "commissioned": 1989, "seed": 51},
)
SERIAL_BY_UNIT = {a["unit"]: a["serial"] for a in ASSETS}
UNIT_BY_SERIAL = {a["serial"]: a["unit"] for a in ASSETS}


def ch_asset_prefix(serial):
    return f"{CH_PREFIX}/{CUSTOMER_ID}/{SITE_ID}/{serial}"


GUIDE_BEARINGS = ("UGB", "LGB", "TGB")   # upper/lower generator guide, turbine guide
QUALITIES = ("GOOD", "UNCERTAIN", "BAD")


def ch_tags():
    """Every 1 s process topic of one CH asset (relative to ch_asset_prefix(serial))."""
    tags = [
        _t("Context/MW", "MW", "float", "Active power (copied from the customer tree)", 2, -5, 45),
        _t("Context/MVAr", "MVAr", "float", "Reactive power (copied from the customer tree)", 2, -20, 25),
        _t("Context/GatePosition_pct", "%", "float", "Wicket gate position (copied)", 1, 0, 100),
        _t("Context/NetHead_m", "m", "float", "Net head (copied)", 2, 60, 125),
        _t("Context/Speed_rpm", "rpm", "float", "Shaft speed (copied)", 1, 0, 600),
        _t("Context/UnitState", "", "string", "Customer unit state (copied)", 0),
        _t("Context/TailwaterLevel_m", "m a.s.l.", "float", "Tailwater level (copied)", 3, 300, 315),
    ]
    tags += [_t(f"Bearings/Thrust/PadTemp{i:02d}", "°C", "float", f"Thrust bearing pad {i} temperature", 2, 0, 150)
             for i in range(1, 7)]
    tags += [
        _t("Bearings/Thrust/OilBathTemp", "°C", "float", "Thrust bearing oil bath temperature", 2, 0, 120),
        _t("Bearings/Thrust/OilLevel", "%", "float", "Thrust bearing oil level", 1, 0, 100),
        _t("Bearings/Thrust/HPLiftPressure", "bar", "float", "High-pressure oil lift (jacking) pressure", 1, 0, 200),
    ]
    for b in GUIDE_BEARINGS:
        tags += [_t(f"Bearings/{b}/PadTemp{i:02d}", "°C", "float", f"{b} pad {i} temperature", 2, 0, 150)
                 for i in range(1, 5)]
        tags += [
            _t(f"Bearings/{b}/OilTemp", "°C", "float", f"{b} oil temperature", 2, 0, 120),
            _t(f"Bearings/{b}/OilLevel", "%", "float", f"{b} oil level", 1, 0, 100),
        ]
    tags += [
        _t("Cooling/WaterInletTemp", "°C", "float", "Cooling water inlet temperature (seasonal)", 2, 0, 40),
        _t("Cooling/WaterFlow_TB", "L/s", "float", "Cooling water flow, turbine bearing circuit", 2, 0, 30),
        _t("Cooling/WaterFlow_GB", "L/s", "float", "Cooling water flow, generator bearing circuit", 2, 0, 40),
        _t("Cooling/WaterFlow_AirCoolers", "L/s", "float", "Cooling water flow, generator air coolers", 2, 0, 100),
        _t("Cooling/OilCoolerOutletTemp", "°C", "float", "Cooling water outlet temperature, oil coolers", 2, 0, 60),
        _t("Governor/HPU/AccumulatorPressure", "bar", "float", "Accumulator pressure", 2, 0, 80),
        _t("Governor/HPU/SumpLevel", "%", "float", "HPU sump oil level", 2, 0, 100),
        _t("Governor/HPU/OilTemp", "°C", "float", "HPU oil temperature", 2, 0, 80),
        _t("Governor/HPU/Pump1Running", "", "bool", "Pump 1 (lead) running", 0),
        _t("Governor/HPU/Pump2Running", "", "bool", "Pump 2 (lag) running", 0),
        _t("Governor/HPU/PumpStartsPerHour", "1/h", "float", "Pump starts in the last hour (both pumps)", 0, 0, 200),
        _t("Governor/HPU/FilterDP", "bar", "float", "Pressure filter differential pressure", 2, 0, 6),
        _t("Governor/HPU/ServoPositionA", "%", "float", "Servomotor A position", 2, 0, 100),
        _t("Governor/HPU/ServoPositionB", "%", "float", "Servomotor B position", 2, 0, 100),
        _t("Governor/HPU/GateSetpoint", "%", "float", "Governor gate setpoint (from the customer's governor)", 2, 0, 100),
        _t("Turbine/SpiralCasePressure", "bar", "float", "Spiral case pressure", 2, 0, 16),
        _t("Turbine/HeadcoverPressure", "bar", "float", "Headcover pressure (behind the runner crown)", 2, 0, 8),
        _t("Turbine/DraftTubePressure", "bar", "float", "Draft tube cone pressure, 1 s mean (gauge)", 3, -1, 3),
        _t("Turbine/ShaftSealWaterFlow", "L/min", "float", "Shaft seal water flow", 1, 0, 200),
        _t("Turbine/HeadcoverSumpPumpStarts", "", "int", "Headcover sump pump starts (counter)", 0, 0, None),
        _t("Turbine/ShearPinStatus", "", "string", "Wicket gate shear pins: OK or BROKEN", 0),
        _t("Turbine/WicketGateBreakawayAlarm", "", "bool", "A wicket gate lags its servo ring (breakaway link)", 0),
    ]
    for b in GUIDE_BEARINGS:
        for ax in ("X", "Y"):
            tags.append(_t(f"Vibration/{b}/Shaft{ax}/Overall_um_pp", "µm", "float",
                           f"{b} shaft displacement {ax}, overall peak-to-peak", 1, 0, 1000))
    tags += [
        _t("Vibration/Headcover/Vel_mm_s_rms", "mm/s", "float", "Headcover vibration velocity, RMS 2-1000 Hz", 2, 0, 50),
        _t("Generator/AirGapMin_mm", "mm", "float", "Minimum air gap (rotor to stator)", 2, 0, 20),
    ]
    tags += [_t(f"Generator/StatorTemp{i:02d}", "°C", "float", f"Stator winding RTD {i}", 1, 0, 180)
             for i in range(1, 7)]
    tags += [
        _t("Counters/Starts", "", "int", "Unit starts since commissioning", 0, 0, None),
        _t("Counters/RunHours", "h", "float", "Generating hours since commissioning", 1, 0, None),
        _t("Counters/EmergencyStops", "", "int", "Emergency stops (trips) since commissioning", 0, 0, None),
        _t("Counters/LoadRejections", "", "int", "Breaker openings under load", 0, 0, None),
    ]
    return tags


# Raw waveform blocks: the PLC does no spectral analysis. Interval and length are settable
# (docker-compose.yml) so the load can be raised for streaming demos; these are the defaults.
def ch_waveforms():
    w = []
    for b in GUIDE_BEARINGS:
        for ax in ("X", "Y"):
            w.append({"path": f"Vibration/{b}/Shaft{ax}/Waveform", "unit": "µm", "group": "shaft",
                      "rate": 1000, "seconds": 4.0, "every_s": 30, "desc": f"{b} shaft displacement {ax}"})
    w.append({"path": "Vibration/DraftTube/Pressure/Waveform", "unit": "bar", "group": "drafttube",
              "rate": 100, "seconds": 10.0, "every_s": 30, "desc": "Draft tube cone pressure (gauge)"})
    w.append({"path": "Vibration/Headcover/Accel/Waveform", "unit": "m/s²", "group": "accel",
              "rate": 10000, "seconds": 0.5, "every_s": 300, "desc": "Headcover accelerometer (cavitation)"})
    return w


META_NAMEPLATE = "_meta/Nameplate"   # retained JSON
META_STATUS = "_meta/Status"         # retained "ONLINE" / "OFFLINE" (MQTT last will)
EVENTS_ALARM = "Events/Alarm"        # non-retained JSON alarm events

# ----------------------------------------------------------------------------- hardwired
# Dual-element sensors on each turbine: element A is wired to the customer's unit controller
# (unit protection, published in the customer tree), element B to the CH PLC. In the simulation
# the turbine physics lives in the CH PLC simulator, which serves element A on an internal HTTP
# endpoint (GET /api/hardwired) that stands for the copper; the dam simulator polls it. A CH-side
# sensor fault (scenario G) only affects element B.
HARDWIRED = (
    {"key": "ThrustBearingTemp", "ch": "Bearings/Thrust/PadTemp01", "unit": "°C"},
    {"key": "UpperGuideBearingTemp", "ch": "Bearings/UGB/PadTemp01", "unit": "°C"},
    {"key": "LowerGuideBearingTemp", "ch": "Bearings/LGB/PadTemp01", "unit": "°C"},
    {"key": "TurbineGuideBearingTemp", "ch": "Bearings/TGB/PadTemp01", "unit": "°C"},
    {"key": "CoolingWaterFlow", "ch": None, "unit": "L/s"},   # sum of the three circuits (one flowmeter)
    {"key": "GovernorOilPressure", "ch": "Governor/HPU/AccumulatorPressure", "unit": "bar"},
)

# Context the CH PLC copies from the customer tree (subscribe only, never writes there).
CH_CONTEXT = {
    "Context/MW": "Powerhouse/{unit}/MW",
    "Context/MVAr": "Powerhouse/{unit}/MVAr",
    "Context/GatePosition_pct": "Powerhouse/{unit}/GatePosition",
    "Context/NetHead_m": "Powerhouse/{unit}/NetHead",
    "Context/Speed_rpm": "Powerhouse/{unit}/Speed",
    "Context/UnitState": "Powerhouse/{unit}/State",
    "Context/TailwaterLevel_m": "River/TailwaterLevel",
}
CH_CONTEXT_EXTRA = {"Governor/HPU/GateSetpoint": "Powerhouse/{unit}/GateSetpoint"}


def customer_topic(path):
    return f"{CUSTOMER_PREFIX}/{path}"


def ch_topic(serial, path):
    return f"{ch_asset_prefix(serial)}/{path}"
