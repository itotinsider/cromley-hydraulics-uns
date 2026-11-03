"""Render the Markdown sources in build/src/ to the PDFs in library/.

A small Markdown subset (front matter, #/##/### headings, paragraphs, - and 1. lists, pipe tables,
**bold**, *italic*, `code`, > notes) is turned into a styled A4 PDF with ReportLab. Two house
styles: Cromley Hydraulics (supplier documents) and DRWPA (Copper Canyon Dam's own documents).

    python3 rca-demo/build/render_pdf.py            # all sources
    python3 rca-demo/build/render_pdf.py RCA-2023-004.md
"""

import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
LIB = os.path.join(os.path.dirname(HERE), "library")

HOUSE = {
    "CH": {"brand": "CROMLEY HYDRAULICS", "tag": "75 years of dam hydraulics",
           "accent": colors.HexColor("#0f6e6e"), "light": colors.HexColor("#e3f1f0")},
    "DRWPA": {"brand": "DESERT RIVER WATER & POWER AUTHORITY", "tag": "Copper Canyon Dam",
              "accent": colors.HexColor("#7a4a12"), "light": colors.HexColor("#f6ece0")},
}
INK = colors.HexColor("#1d1d1b")
GREY = colors.HexColor("#6b6b66")
RULE = colors.HexColor("#c9c7c0")


def styles(h):
    a = h["accent"]
    base = dict(fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=a,
                                spaceAfter=6),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11.5, leading=15, textColor=GREY,
                                   spaceAfter=10),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13.5, leading=17, textColor=a,
                             spaceBefore=12, spaceAfter=5),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK,
                             spaceBefore=9, spaceAfter=4),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=9.8, leading=13, textColor=GREY,
                             spaceBefore=6, spaceAfter=2),
        "p": ParagraphStyle("p", spaceAfter=5, **base),
        "li": ParagraphStyle("li", spaceAfter=1.5, **base),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.3, leading=10.5, textColor=INK),
        "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8.3, leading=10.5,
                                textColor=colors.white),
        "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=9, leading=12.5, textColor=INK,
                               leftIndent=8, borderPadding=6, backColor=h["light"], spaceBefore=4,
                               spaceAfter=8),
        "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK),
    }


def inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("³", "<super>3</super>").replace("²", "<super>2</super>")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier" size="8">\1</font>', text)
    return text


def parse_front_matter(lines):
    meta = {}
    if lines and lines[0].strip() == "---":
        end = lines.index("---", 1) if "---" in lines[1:] else None
        for ln in lines[1:end]:
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip()] = v.strip()
        lines = lines[end + 1:]
    return meta, lines


def table_flowable(rows, st, h, width):
    header, body = rows[0], rows[1:]
    ncol = len(header)
    data = [[Paragraph(inline(c), st["cellh"]) for c in header]]
    for r in body:
        r = (r + [""] * ncol)[:ncol]
        data.append([Paragraph(inline(c), st["cell"]) for c in r])
    # column widths from text length, clamped
    lens = [max(len(str(r[i])) if i < len(r) else 0 for r in rows) for i in range(ncol)]
    lens = [min(max(l, 6), 60) for l in lens]
    tot = sum(lens)
    widths = [width * l / tot for l in lens]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), h["accent"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f6f2")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def build_story(lines, st, h, width):
    story, para, lst, lst_kind, tbl = [], [], [], None, []

    def flush_para():
        if para:
            story.append(Paragraph(inline(" ".join(para)), st["p"]))
            para.clear()

    def flush_list():
        nonlocal lst_kind
        if lst:
            items = [ListItem(Paragraph(inline(x), st["li"]), leftIndent=12) for x in lst]
            kw = {"bulletType": "1"} if lst_kind == "ol" else {"bulletType": "bullet", "start": "•"}
            story.append(ListFlowable(items, leftIndent=12, bulletFontSize=8.5, spaceAfter=5, **kw))
            lst.clear()
        lst_kind = None

    def flush_table():
        if tbl:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl
                    if not re.match(r"^\s*\|?\s*:?-{2,}", r)]
            story.append(table_flowable(rows, st, h, width))
            story.append(Spacer(1, 7))
            tbl.clear()

    for raw in lines:
        line = raw.rstrip("\n")
        s = line.strip()
        if s.startswith("|"):
            flush_para(); flush_list(); tbl.append(s); continue
        flush_table()
        if not s:
            flush_para(); flush_list(); continue
        if s == "\\pagebreak":
            flush_para(); flush_list(); story.append(PageBreak()); continue
        m = re.match(r"^(#{1,3})\s+(.*)", s)
        if m:
            flush_para(); flush_list()
            lvl = len(m.group(1))
            story.append(Paragraph(inline(m.group(2)), st[f"h{lvl}"]))
            continue
        m = re.match(r"^[-*]\s+(.*)", s)
        if m:
            flush_para()
            if lst_kind not in (None, "ul"):
                flush_list()
            lst_kind = "ul"; lst.append(m.group(1)); continue
        m = re.match(r"^\d+\.\s+(.*)", s)
        if m:
            flush_para()
            if lst_kind not in (None, "ol"):
                flush_list()
            lst_kind = "ol"; lst.append(m.group(1)); continue
        if s.startswith(">"):
            flush_para(); flush_list()
            story.append(Paragraph(inline(s.lstrip("> ")), st["note"]))
            continue
        if lst and raw.startswith("  "):
            lst[-1] += " " + s
            continue
        flush_list()
        para.append(s)
    flush_para(); flush_list(); flush_table()
    return story


def render(src_path):
    with open(src_path, encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]
    meta, lines = parse_front_matter(lines)
    h = HOUSE[meta.get("house", "DRWPA")]
    st = styles(h)
    out = os.path.join(LIB, meta["out"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    W, H = A4
    margin = 18 * mm
    width = W - 2 * margin

    def decorate(c, doc):
        c.saveState()
        c.setFillColor(h["accent"])
        c.rect(0, H - 14 * mm, W, 14 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, H - 9 * mm, h["brand"])
        c.setFont("Helvetica", 8)
        c.drawRightString(W - margin, H - 9 * mm, h["tag"])
        c.setStrokeColor(RULE)
        c.line(margin, 13 * mm, W - margin, 13 * mm)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 7.5)
        c.drawString(margin, 9 * mm, f"{meta.get('doc', '')}   Rev {meta.get('rev', '')}   {meta.get('date', '')}")
        c.drawCentredString(W / 2, 9 * mm, meta.get("class", ""))
        c.drawRightString(W - margin, 9 * mm, f"Page {doc.page}")
        c.restoreState()

    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=margin, rightMargin=margin,
                            topMargin=22 * mm, bottomMargin=20 * mm, title=meta.get("title", ""),
                            author=meta.get("author", h["brand"]), subject=meta.get("doc", ""))
    story = [Paragraph(inline(meta.get("title", "")), st["title"])]
    if meta.get("subtitle"):
        story.append(Paragraph(inline(meta["subtitle"]), st["subtitle"]))
    rows = [(k, meta[k]) for k in ("doc", "rev", "date", "applies", "owner", "approved", "status") if meta.get(k)]
    if rows:
        labels = {"doc": "Document", "rev": "Revision", "date": "Date", "applies": "Applies to",
                  "owner": "Owner", "approved": "Approved", "status": "Status"}
        t = Table([[Paragraph(f"<b>{labels[k]}</b>", st["meta"]), Paragraph(inline(v), st["meta"])] for k, v in rows],
                  colWidths=[30 * mm, width - 30 * mm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), h["light"]),
                               ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
        story += [t, Spacer(1, 10)]
    story += build_story(lines, st, h, width)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return out


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(n for n in os.listdir(SRC) if n.endswith(".md"))
    for n in names:
        print("rendered", os.path.relpath(render(os.path.join(SRC, n)), os.path.dirname(HERE)))
