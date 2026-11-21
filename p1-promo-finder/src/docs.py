"""Compiles markdown documentation into PDF format using ReportLab."""

import re
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_LAST_PAGE_COUNT = 0


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        global _LAST_PAGE_COUNT
        num_pages = len(self._saved_page_states)
        _LAST_PAGE_COUNT = num_pages
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#666666"))
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 36, 18, text)
        self.restoreState()


def _md_to_flowables(md_text: str, is_compact: bool = False) -> List[Flowable]:
    styles = getSampleStyleSheet()
    base_font_size = 8.0 if is_compact else 9.5
    base_leading = 10.0 if is_compact else 12.5

    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=base_font_size,
        leading=base_leading,
        textColor=colors.HexColor("#222222"),
        spaceAfter=2.5 if is_compact else 5,
    )
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=12.5 if is_compact else 16,
        leading=14.5 if is_compact else 19,
        textColor=colors.HexColor("#111111"),
        alignment=0,
        spaceAfter=3 if is_compact else 8,
    )
    h1_style = ParagraphStyle(
        "DocH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=9.5 if is_compact else 13,
        leading=11.5 if is_compact else 15,
        textColor=colors.HexColor("#0f2d59"),
        spaceBefore=3.5 if is_compact else 8,
        spaceAfter=1.5 if is_compact else 4,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=8.5 if is_compact else 11,
        leading=10.5 if is_compact else 13,
        textColor=colors.HexColor("#1b4984"),
        spaceBefore=2.5 if is_compact else 6,
        spaceAfter=1.5 if is_compact else 3,
        keepWithNext=True,
    )
    code_style = ParagraphStyle(
        "DocCode",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7.0 if is_compact else 8.5,
        leading=8.5 if is_compact else 10.5,
        textColor=colors.HexColor("#222222"),
        spaceAfter=2.5,
    )

    flowables: List[Flowable] = []
    lines = md_text.splitlines()
    in_code_block = False
    code_buffer: List[str] = []
    table_buffer: List[str] = []

    def flush_table():
        nonlocal table_buffer
        if not table_buffer:
            return
        table_rows = []
        for trow in table_buffer:
            cleaned = trow.strip().strip("|")
            cols = [c.strip() for c in cleaned.split("|")]
            table_rows.append(cols)
        table_buffer = []
        if len(table_rows) < 2:
            return
        header = [Paragraph(f"<b>{c}</b>", body_style) for c in table_rows[0]]
        data_rows = []
        for r in table_rows[2:]:
            data_rows.append([Paragraph(c, body_style) for c in r])
        full_table = [header] + data_rows
        t = Table(full_table, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f8")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 if is_compact else 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.5 if is_compact else 3),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ]
            )
        )
        flowables.append(t)
        flowables.append(Spacer(1, 2 if is_compact else 6))

    for line in lines:
        sline = line.strip()

        if sline.startswith("```"):
            if in_code_block:
                code_text = "<br/>".join(code_buffer)
                flowables.append(Paragraph(code_text, code_style))
                code_buffer = []
                in_code_block = False
            else:
                flush_table()
                in_code_block = True
            continue

        if in_code_block:
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
            code_buffer.append(safe)
            continue

        if sline.startswith("|") and sline.endswith("|"):
            table_buffer.append(sline)
            continue
        elif table_buffer:
            flush_table()

        if not sline:
            continue

        if sline.startswith("# "):
            flowables.append(Paragraph(sline[2:], title_style))
            flowables.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1b4984"), spaceAfter=3))
        elif sline.startswith("## "):
            flowables.append(Paragraph(sline[3:], h1_style))
        elif sline.startswith("### "):
            flowables.append(Paragraph(sline[4:], h2_style))
        elif sline.startswith("- ") or sline.startswith("* "):
            safe = sline[2:].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe)
            safe = re.sub(r"\*(.*?)\*", r"<i>\1</i>", safe)
            flowables.append(Paragraph(f"• {safe}", body_style))
        else:
            safe = sline.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe)
            safe = re.sub(r"\*(.*?)\*", r"<i>\1</i>", safe)
            flowables.append(Paragraph(safe, body_style))

    if table_buffer:
        flush_table()
    return flowables


def build_pdf(md_path: Path | str, out_path: Path | str, is_compact: bool = False) -> int:
    global _LAST_PAGE_COUNT
    in_p = Path(md_path)
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    with open(in_p, "r", encoding="utf-8") as f:
        md_text = f.read()

    margin = 24 if is_compact else 36
    doc = SimpleDocTemplate(
        str(out_p),
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    flowables = _md_to_flowables(md_text, is_compact=is_compact)
    doc.build(flowables, canvasmaker=NumberedCanvas)
    return _LAST_PAGE_COUNT


def compile_all_docs() -> None:
    sol_md = Path("docs/solution.md")
    sol_pdf = Path("docs/solution.pdf")
    if sol_md.exists():
        pages = build_pdf(sol_md, sol_pdf, is_compact=True)
        print(f"Compiled {sol_pdf} ({pages} page(s)).")

    walk_md = Path("docs/walkthrough.md")
    walk_pdf = Path("docs/walkthrough.pdf")
    if walk_md.exists():
        pages = build_pdf(walk_md, walk_pdf, is_compact=False)
        print(f"Compiled {walk_pdf} ({pages} page(s)).")


if __name__ == "__main__":
    compile_all_docs()
