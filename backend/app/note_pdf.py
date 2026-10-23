from __future__ import annotations

import html
import io
import re
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import LectureNote, NoteImage


IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(/api/notes/[^/]+/images/([0-9a-f-]{36})\)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MARKUP_RE = re.compile(r"(\*\*|__|`|\$)")
FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]


def _register_font() -> str:
    name = "HamdarsPersian"
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    path = next((candidate for candidate in FONT_CANDIDATES if candidate.is_file()), None)
    if not path:
        raise RuntimeError("No Persian-capable font was found for PDF generation")
    pdfmetrics.registerFont(TTFont(name, str(path)))
    return name


def _plain(text: str) -> str:
    return MARKUP_RE.sub("", LINK_RE.sub(r"\1", text)).strip()


def _rtl(text: str) -> str:
    return get_display(arabic_reshaper.reshape(_plain(text)), base_dir="R") if text else ""


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(_rtl(text)), style)


def _image_flowable(image: NoteImage, max_width: float) -> Image:
    stream = io.BytesIO(image.data)
    with PillowImage.open(stream) as decoded:
        width, height = decoded.size
    stream.seek(0)
    scale = min(max_width / width, (150 * mm) / height, 1)
    return Image(stream, width=width * scale, height=height * scale)


def _styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = dict(fontName=font_name, alignment=TA_RIGHT, wordWrap="RTL", leading=20, textColor=colors.HexColor("#172033"))
    without_leading_color = {key: value for key, value in base.items() if key not in {"leading", "textColor"}}
    return {
        "body": ParagraphStyle("body", fontSize=10.5, spaceAfter=7, **base),
        "h1": ParagraphStyle("h1", fontSize=20, leading=30, textColor=colors.HexColor("#0f3d3a"), spaceBefore=10, spaceAfter=10, **without_leading_color),
        "h2": ParagraphStyle("h2", fontSize=15, leading=24, textColor=colors.HexColor("#0f766e"), spaceBefore=14, spaceAfter=7, **without_leading_color),
        "h3": ParagraphStyle("h3", fontSize=12.5, leading=21, textColor=colors.HexColor("#115e59"), spaceBefore=10, spaceAfter=5, **without_leading_color),
        "meta": ParagraphStyle("meta", fontSize=9, leading=15, textColor=colors.HexColor("#64748b"), **without_leading_color),
        "list": ParagraphStyle("list", fontSize=10.5, rightIndent=12, bulletIndent=0, spaceAfter=4, **base),
        "code": ParagraphStyle("code", fontName=font_name, fontSize=8.5, leading=14, alignment=TA_LEFT, backColor=colors.HexColor("#f1f5f9"), borderPadding=7, spaceAfter=8),
    }


def _page_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, str(document.page))
    canvas.restoreState()


def _story(note: LectureNote, course_title: str, images: list[NoteImage], font_name: str) -> list:
    styles = _styles(font_name)
    story: list = [
        _paragraph("هم‌درس · جزوهٔ آموزشی", styles["meta"]),
        _paragraph(note.title, styles["h1"]),
        _paragraph(course_title, styles["meta"]),
        Spacer(1, 5 * mm),
    ]
    image_map = {image.id: image for image in images}
    lines = note.markdown_content.splitlines()
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False
    first_h1_skipped = False

    def flush_paragraph() -> None:
        if paragraph_lines:
            story.append(_paragraph(" ".join(paragraph_lines), styles["body"]))
            paragraph_lines.clear()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(Paragraph(html.escape("\n".join(code_lines)).replace("\n", "<br/>"), styles["code"]))
                code_lines.clear()
            in_code = not in_code
            index += 1
            continue
        if in_code:
            code_lines.append(lines[index])
            index += 1
            continue
        if not line:
            flush_paragraph()
            index += 1
            continue
        image_match = IMAGE_RE.match(line)
        if image_match:
            flush_paragraph()
            image = image_map.get(image_match.group(2))
            if image:
                figure = [_image_flowable(image, 165 * mm)]
                if image_match.group(1):
                    figure.extend([Spacer(1, 2 * mm), _paragraph(image_match.group(1), styles["meta"])])
                story.extend([KeepTogether(figure), Spacer(1, 4 * mm)])
            index += 1
            continue
        if line.startswith("# "):
            flush_paragraph()
            heading = line[2:].strip()
            if not first_h1_skipped and _plain(heading) == _plain(note.title):
                first_h1_skipped = True
            else:
                story.append(_paragraph(heading, styles["h1"]))
            index += 1
            continue
        if line.startswith("## ") or line.startswith("### "):
            flush_paragraph()
            style = styles["h3"] if line.startswith("### ") else styles["h2"]
            story.append(_paragraph(line.lstrip("# "), style))
            index += 1
            continue
        if line.startswith(("- ", "* ")) or re.match(r"\d+[.)]\s", line):
            flush_paragraph()
            item = re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line)
            story.append(_paragraph(f"• {item}", styles["list"]))
            index += 1
            continue
        if "|" in line and index + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[index + 1]):
            flush_paragraph()
            table_rows = [[cell.strip() for cell in line.strip("|").split("|")]]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                table_rows.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
                index += 1
            cells = [[_paragraph(cell, styles["meta"]) for cell in row] for row in table_rows]
            table = Table(cells, repeatRows=1, hAlign="RIGHT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ccfbf1")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([table, Spacer(1, 4 * mm)])
            continue
        if line in {"---", "***"}:
            flush_paragraph()
            story.append(Spacer(1, 3 * mm))
            index += 1
            continue
        paragraph_lines.append(line.lstrip("> "))
        index += 1
    flush_paragraph()
    return story


def render_note_pdf(note: LectureNote, course_title: str, images: list[NoteImage]) -> bytes:
    font_name = _register_font()
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=note.title,
        author="هم‌درس",
    )
    document.build(_story(note, course_title, images, font_name), onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output.getvalue()
