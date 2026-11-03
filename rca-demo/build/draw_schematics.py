"""Draw CH-DOC-DWG-0102 (three schematic sheets) as one PDF in library/supplier/.

    python3 rca-demo/build/draw_schematics.py
"""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "library", "supplier",
                   "CH-DOC-DWG-0102_CH-Francis-Canyon_Unit-Schematics_Rev2.pdf")

TEAL = colors.HexColor("#0f6e6e")
INK = colors.HexColor("#1d1d1b")
GREY = colors.HexColor("#6b6b66")
LIGHT = colors.HexColor("#e3f1f0")
WATER = colors.HexColor("#2f6db3")
OIL = colors.HexColor("#b07a18")
WET = colors.HexColor("#dfe9f5")
W, H = landscape(A4)


def frame(c, sheet, title):
    c.setStrokeColor(INK)
    c.setLineWidth(1.2)
    c.rect(8 * mm, 8 * mm, W - 16 * mm, H - 16 * mm)
    # title block
    x0, y0, bw, bh = W - 8 * mm - 120 * mm, 8 * mm, 120 * mm, 30 * mm
    c.setLineWidth(0.8)
    c.rect(x0, y0, bw, bh)
    c.line(x0, y0 + 20 * mm, x0 + bw, y0 + 20 * mm)
    c.line(x0, y0 + 10 * mm, x0 + bw, y0 + 10 * mm)
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x0 + 3 * mm, y0 + 23 * mm, "CROMLEY HYDRAULICS")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x0 + 3 * mm, y0 + 13 * mm, title)
    c.setFont("Helvetica", 7.5)
    c.drawString(x0 + 3 * mm, y0 + 3.5 * mm,
                 f"CH-DOC-DWG-0102   Sheet {sheet}/3   Rev 2   2026-08-14   FC-40/100 Copper Canyon U1-U3")
    c.setFillColor(GREY)
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(12 * mm, 11 * mm, "Schematic, not to scale. Supplier document. Fictional, for training only.")


def label(c, x, y, text, size=7.5, color=INK, bold=False, anchor="l"):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    {"l": c.drawString, "c": c.drawCentredString, "r": c.drawRightString}[anchor](x, y, text)


def box(c, x, y, w, h, text=None, fill=None, stroke=INK, size=7.5, bold=False, lw=0.8):
    c.setStrokeColor(stroke)
    c.setLineWidth(lw)
    if fill is not None:
        c.setFillColor(fill)
        c.rect(x, y, w, h, stroke=1, fill=1)
    else:
        c.rect(x, y, w, h, stroke=1, fill=0)
    if text:
        lines = text.split("\n")
        for i, t in enumerate(lines):
            label(c, x + w / 2, y + h / 2 + (len(lines) / 2 - i - 0.75) * (size + 1.5), t, size, bold=bold, anchor="c")


def arrow(c, x1, y1, x2, y2, color=INK, lw=0.9):
    import math
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(lw)
    c.line(x1, y1, x2, y2)
    a = math.atan2(y2 - y1, x2 - x1)
    s = 4
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - s * math.cos(a - 0.4), y2 - s * math.sin(a - 0.4))
    p.lineTo(x2 - s * math.cos(a + 0.4), y2 - s * math.sin(a + 0.4))
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def instrument(c, x, y, tag, r=6.5):
    c.setStrokeColor(INK)
    c.setFillColor(colors.white)
    c.setLineWidth(0.7)
    c.circle(x, y, r, stroke=1, fill=1)
    label(c, x, y - 2.3, tag, 5.6, anchor="c")


# ---------------------------------------------------------------- sheet 1: unit cross-section
def sheet1(c):
    frame(c, 1, "Unit arrangement: bearings and monitoring sensors")
    label(c, 14 * mm, H - 18 * mm, "Sheet 1. Unit arrangement: shaft line, bearings and CH monitoring sensors", 11, TEAL, True)
    cx = 75 * mm
    c.setFillColor(colors.HexColor("#d9d7cf"))
    c.setStrokeColor(INK)
    c.rect(cx - 5, 78 * mm, 10, 100 * mm, stroke=1, fill=1)
    rows = [
        (166, 12, 80, LIGHT, "Upper bracket: THRUST BEARING (6 tilting pads) + UPPER GUIDE BEARING (UGB)",
         "TE thrust pads 1-6, UGB pads 1-4 (pad 1 dual A/B); oil bath TE and LT; HP lift PT; UGB proximity probes X/Y; keyphasor"),
        (136, 22, 110, None, "GENERATOR: rotor (10 pole pairs) and stator",
         "TE stator RTDs 01-06; capacitive air gap sensor (minimum air gap)"),
        (118, 10, 70, LIGHT, "Lower bracket: LOWER GUIDE BEARING (LGB)",
         "TE LGB pads 1-4 (pad 1 dual A/B); oil TE and LT; LGB proximity probes X/Y"),
        (96, 12, 90, LIGHT, "Headcover: TURBINE GUIDE BEARING (TGB), oil bath, own cooling circuit TB",
         "TE TGB pads 1-4 (pad 1 dual A/B); oil TE and LT; TGB proximity probes X/Y; headcover accelerometer; headcover PT"),
        (78, 13, 120, None, "RUNNER (13 blades) in 20 WICKET GATES, SPIRAL CASE around",
         "Spiral case PT; shaft seal water FT; shear pin status (20 pins) and breakaway switch"),
    ]
    short = ["THRUST + UGB", "GENERATOR", "LGB", "TGB (headcover)", "RUNNER / WICKET GATES"]
    for (y, h, w, fill, name, sens), sh in zip(rows, short):
        box(c, cx - w / 2 * mm, y * mm, w * mm, h * mm, fill=fill)
        label(c, cx + 8 * mm, (y + h / 2 - 1) * mm, sh, 7.5, INK, True)
        instrument(c, 140 * mm, (y + h / 2) * mm, "TE" if "TE" in sens[:3] else "PT")
        label(c, 145 * mm, (y + h / 2 + 1) * mm, name, 7.5, INK, True)
        label(c, 145 * mm, (y + h / 2 - 3.2) * mm, sens, 6.6, GREY)
    p = c.beginPath()
    p.moveTo(cx - 25 * mm, 78 * mm)
    p.lineTo(cx - 38 * mm, 56 * mm)
    p.lineTo(cx + 38 * mm, 56 * mm)
    p.lineTo(cx + 25 * mm, 78 * mm)
    c.setStrokeColor(INK)
    c.drawPath(p, stroke=1, fill=0)
    instrument(c, 140 * mm, 67 * mm, "PT")
    label(c, 145 * mm, 68 * mm, "DRAFT TUBE CONE -> tailrace (vortex rope at part load)", 7.5, INK, True)
    label(c, 145 * mm, 63.8 * mm, "Draft tube cone PT (100 S/s waveform)", 6.6, GREY)
    lx, ly = 14 * mm, 48 * mm
    label(c, lx, ly, "Pad numbering and RTDs", 8, TEAL, True)
    for i, t in enumerate([
        "Pads are numbered clockwise seen from above, pad 1 at the +X probe.",
        "Pad 1 of each bearing: dual-element Pt100. Element A -> owner's unit controller (protection).",
        "Element B -> CH monitoring PLC. Pads 2..n: single element -> CH monitoring PLC only.",
        "TGB design radial clearance 0.30 mm +/- 0.05 mm (see CH-DOC-OM-0101 section 4.2).",
    ]):
        label(c, lx, ly - 11 - i * 10, t, 7.2)


# ---------------------------------------------------------------- sheet 2: cooling water
def sheet2(c):
    frame(c, 2, "Cooling water system, one unit (x = 1, 2, 3)")
    label(c, 14 * mm, H - 18 * mm, "Sheet 2. Cooling water system (one per unit, x = unit number)", 11, TEAL, True)
    y = H - 75 * mm
    box(c, 14 * mm, y - 9 * mm, 30 * mm, 18 * mm, "PENSTOCK\nbranch tap")
    arrow(c, 44 * mm, y, 58 * mm, y, WATER, 1.6)
    box(c, 58 * mm, y - 9 * mm, 34 * mm, 18 * mm, "UNIT STRAINER\nduplex basket", fill=LIGHT)
    instrument(c, 75 * mm, y + 16 * mm, "PDI")
    label(c, 75 * mm, y + 25 * mm, "PDI-x01 local gauge (clean > 0.3 bar)", 6.6, GREY, anchor="c")
    arrow(c, 92 * mm, y, 108 * mm, y, WATER, 1.6)
    instrument(c, 100 * mm, y - 15 * mm, "FT")
    label(c, 100 * mm, y - 25 * mm, "FT-x01 owner total flow (80 L/s)", 6.6, GREY, anchor="c")
    label(c, 100 * mm, y - 31 * mm, "-> control room CoolingWaterFlow", 6.6, GREY, anchor="c")
    instrument(c, 115 * mm, y + 16 * mm, "TE")
    label(c, 115 * mm, y + 25 * mm, "TE inlet (CH PLC)", 6.6, GREY, anchor="c")
    # header
    c.setStrokeColor(WATER)
    c.setLineWidth(1.6)
    c.line(108 * mm, y, 125 * mm, y)
    c.line(125 * mm, y + 55 * mm, 125 * mm, y - 75 * mm)
    branches = [
        (y + 55 * mm, "TB circuit, 8 L/s", "TGB OIL COOLER", "FT-TB (CH PLC, alarm < 5.6 L/s)"),
        (y + 20 * mm, "GB circuit, 12 L/s", "THRUST + UGB + LGB\nOIL COOLERS", "FT-GB (CH PLC, alarm < 8.4 L/s)"),
        (y - 15 * mm, "Air coolers, 60 L/s", "GENERATOR\nAIR COOLERS (x6)", "FT-AC (CH PLC, alarm < 42 L/s)"),
        (y - 50 * mm, "Shaft seal water, 35-45 L/min", "SHAFT SEAL\n(carbon segments)", "FT seal water (CH PLC)"),
    ]
    for by, name, cooler, ft in branches:
        arrow(c, 125 * mm, by, 165 * mm, by, WATER, 1.3)
        label(c, 128 * mm, by + 4, name, 7.2, WATER, True)
        instrument(c, 140 * mm, by - 12, "FT")
        label(c, 128 * mm, by - 10 * mm, ft, 6.4, GREY)
        box(c, 165 * mm, by - 9 * mm, 42 * mm, 18 * mm, cooler, fill=LIGHT, size=7)
        arrow(c, 207 * mm, by, 228 * mm, by, WATER, 1.3)
    c.setStrokeColor(WATER)
    c.line(228 * mm, y + 55 * mm, 228 * mm, y - 75 * mm)
    arrow(c, 228 * mm, y - 75 * mm, 250 * mm, y - 75 * mm, WATER, 1.6)
    label(c, 252 * mm, y - 77 * mm, "TAILRACE", 8, INK, True)
    instrument(c, 238 * mm, y + 30 * mm, "TE")
    label(c, 238 * mm, y + 39 * mm, "TE cooler outlet", 6.6, GREY, anchor="c")
    label(c, 14 * mm, 52 * mm, "Notes", 8, TEAL, True)
    for i, t in enumerate([
        "1. The TGB has its own circuit (TB). Thrust, UGB and LGB share the GB circuit.",
        "2. A blocked unit strainer reduces ALL circuits together: every bearing and the generator warm up at once.",
        "3. The owner measures total flow only (FT-x01). Circuit flows are measured by the CH monitoring PLC (retrofit 2026).",
        "4. Strainer cleaning: at PDI > 0.3 bar, and at least monthly during the high-silt season (spring runoff).",
    ]):
        label(c, 14 * mm, 52 * mm - 11 - i * 10, t, 7.2)


# ---------------------------------------------------------------- sheet 3: RTD wiring
def sheet3(c):
    frame(c, 3, "Bearing RTD wiring: element A (owner) and element B (CH PLC)")
    label(c, 14 * mm, H - 18 * mm, "Sheet 3. Bearing RTD wiring: owner protection (element A) and CH monitoring PLC (element B)", 11, TEAL, True)
    top = H - 38 * mm
    bearings = [("THRUST", "pads 1-6", "JB-x-01", "Upper bracket", False),
                ("UGB", "pads 1-4", "JB-x-01", "Upper bracket", False),
                ("LGB", "pads 1-4", "JB-x-02", "Lower bracket", False),
                ("TGB", "pads 1-4", "JB-x-04", "Headcover pit (WET AREA)", True)]
    rowh = 30 * mm
    for i, (b, pads, jb, loc, wet) in enumerate(bearings):
        y = top - i * rowh - 18 * mm
        box(c, 14 * mm, y, 34 * mm, 18 * mm, f"{b}\n{pads}", fill=LIGHT, bold=True)
        # element A from pad 1
        # element B and pads 2..n to JB
        if wet:
            c.setFillColor(WET)
            c.setStrokeColor(WATER)
            c.rect(78 * mm, y - 4 * mm, 50 * mm, 22 * mm, stroke=1, fill=1)
            label(c, 103 * mm, y - 2.5 * mm, loc, 6.5, WATER, True, anchor="c")
        arrow(c, 48 * mm, y + 13 * mm, 230 * mm, y + 13 * mm, OIL, 0.9)
        label(c, 52 * mm, y + 15 * mm, "pad 1, element A (direct, 4-wire)", 6.5, OIL)
        box(c, 85 * mm, y + 2 * mm, 36 * mm, 9 * mm, jb, size=7.5, bold=True)
        if not wet:
            label(c, 103 * mm, y - 2.5 * mm, loc, 6.5, GREY, anchor="c")
        arrow(c, 48 * mm, y + 6 * mm, 85 * mm, y + 6 * mm, TEAL, 0.9)
        label(c, 50 * mm, y + 1.5 * mm, "pad 1 elem. B + pads 2..n", 6.3, TEAL)
        c.setFillColor(INK)
        c.circle(121 * mm, y + 6.5 * mm, 1.6, stroke=0, fill=1)
        label(c, 123 * mm, y + 8.5 * mm, "M12", 6.2, INK)
        arrow(c, 121 * mm, y + 6.5 * mm, 160 * mm, y + 6.5 * mm, TEAL, 0.9)
    # receivers
    yy = top - 4 * rowh + 2 * mm
    box(c, 160 * mm, yy, 40 * mm, 4 * rowh - 6 * mm, "CH MONITORING\nPLC CABINET\n(element B,\nall pads)\n\nMQTT -> site broker\nv1.0/CH/Fleet/...", fill=LIGHT, size=7.5, bold=False)
    box(c, 230 * mm, yy, 45 * mm, 4 * rowh - 6 * mm, "OWNER UNIT\nCONTROLLER\n(element A, pad 1\nonly)\n\nalarm 80 C\ntrip 90 C (5 s)\n-> control room", size=7.5)
    label(c, 14 * mm, 50 * mm, "Notes", 8, TEAL, True)
    for i, t in enumerate([
        "1. The owner's control room sees one pad per bearing (element A). All other pads are visible only in the CH PLC data.",
        "2. M12 connectors are IP67 only when fully mated and with the cable gland fully tightened. See CH-SB-2026-03.",
        "3. JB-x-04 sits in the headcover pit, a wet area: inspect connectors and glands every 6 months.",
        "4. Element B and pads 2..n: 3-wire Pt100 to the PLC analog input cards.",
    ]):
        label(c, 14 * mm, 50 * mm - 11 - i * 10, t, 7.2)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    c = canvas.Canvas(OUT, pagesize=landscape(A4))
    c.setTitle("CH-DOC-DWG-0102 CH-Francis Canyon unit schematics Rev 2")
    c.setAuthor("Cromley Hydraulics")
    c.setCreator("Cromley Hydraulics Product Engineering")
    for s in (sheet1, sheet2, sheet3):
        s(c)
        c.showPage()
    c.save()
    import importlib.util, sys as _s
    spec = importlib.util.spec_from_file_location("render_pdf", os.path.join(HERE, "render_pdf.py"))
    rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)
    rp.stamp(OUT, "2026-08-14", "Cromley Hydraulics Product Engineering")
    print("drew", os.path.relpath(OUT, os.path.dirname(HERE)))


if __name__ == "__main__":
    main()
