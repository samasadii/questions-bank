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
from reportlab.platypus import HRFlowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import LectureNote, NoteImage


IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(/api/notes/[^/]+/images/([0-9a-f-]{36})\)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MARKUP_RE = re.compile(r"(\*\*|__|`|\$)")
LATEX_TEXT_RE = re.compile(r"\\text\{([^{}]*)\}")
FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"


def _register_fonts() -> tuple[str, str]:
    regular_name = "Vazirmatn"
    bold_name = "Vazirmatn-Bold"
    if regular_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_name, str(FONT_DIR / "Vazirmatn-Regular.ttf")))
    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, str(FONT_DIR / "Vazirmatn-Bold.ttf")))
    return regular_name, bold_name


def _plain(text: str) -> str:
    text = LINK_RE.sub(r"\1", text)
    text = LATEX_TEXT_RE.sub(r"\1", text)
    replacements = {
        r"\supset": " شامل ",
        r"\rightarrow": " سپس ",
        r"\leftarrow": " پس از ",
        r"\times": "×",
        r"\approx": "≈",
        r"\le": "≤",
        r"\ge": "≥",
        r"\mathrm": "",
    }
    for command, symbol in replacements.items():
        text = text.replace(command, symbol)
    text = re.sub(r"\\[A-Za-z]+", "", text)
    text = re.sub(r"[_^]\{([^{}]+)\}", r"\1", text)
    text = text.replace("{", "").replace("}", "")
    return MARKUP_RE.sub("", text).strip()


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


def _styles(font_name: str, bold_name: str) -> dict[str, ParagraphStyle]:
    base = dict(fontName=font_name, alignment=TA_RIGHT, wordWrap="RTL", leading=20, textColor=colors.HexColor("#183247"))
    without_leading_color = {key: value for key, value in base.items() if key not in {"leading", "textColor"}}
    return {
        "body": ParagraphStyle("body", fontSize=10.5, spaceAfter=7, **base),
        "h1": ParagraphStyle("h1", fontName=bold_name, fontSize=21, leading=32, textColor=colors.HexColor("#183247"), spaceBefore=10, spaceAfter=10, **{k: v for k, v in without_leading_color.items() if k != "fontName"}),
        "h2": ParagraphStyle("h2", fontName=bold_name, fontSize=15, leading=24, textColor=colors.HexColor("#315b7c"), spaceBefore=14, spaceAfter=7, **{k: v for k, v in without_leading_color.items() if k != "fontName"}),
        "h3": ParagraphStyle("h3", fontName=bold_name, fontSize=12.5, leading=21, textColor=colors.HexColor("#274e6b"), spaceBefore=10, spaceAfter=5, **{k: v for k, v in without_leading_color.items() if k != "fontName"}),
        "meta": ParagraphStyle("meta", fontSize=9, leading=15, textColor=colors.HexColor("#64748b"), **without_leading_color),
        "list": ParagraphStyle("list", fontSize=10.5, rightIndent=12, bulletIndent=0, spaceAfter=4, **base),
        "code": ParagraphStyle("code", fontName=font_name, fontSize=8.5, leading=14, alignment=TA_LEFT, backColor=colors.HexColor("#f1f5f9"), borderPadding=7, spaceAfter=8),
        "math": ParagraphStyle("math", fontName=bold_name, fontSize=11, leading=22, alignment=TA_RIGHT, wordWrap="RTL", textColor=colors.HexColor("#274e6b"), backColor=colors.HexColor("#f3f6f8"), borderColor=colors.HexColor("#d5dee5"), borderWidth=0.5, borderPadding=10, spaceBefore=7, spaceAfter=10),
        "cover": ParagraphStyle("cover", fontName=bold_name, fontSize=28, leading=42, alignment=TA_RIGHT, wordWrap="RTL", textColor=colors.HexColor("#183247"), spaceAfter=12),
    }


def _page_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, str(document.page))
    canvas.restoreState()


def _story(
    note: LectureNote,
    course_title: str,
    images: list[NoteImage],
    font_name: str,
    bold_name: str,
) -> list:
    styles = _styles(font_name, bold_name)
    story: list = [
        _paragraph("هم‌درس  |  جزوهٔ آموزشی", styles["meta"]),
        _paragraph(note.title, styles["h1"]),
        _paragraph(course_title, styles["meta"]),
        Spacer(1, 2 * mm),
        HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#315b7c"), spaceAfter=5 * mm),
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
        if line == "$$":
            flush_paragraph()
            math_lines: list[str] = []
            index += 1
            while index < len(lines) and lines[index].strip() != "$$":
                math_lines.append(lines[index].strip())
                index += 1
            story.append(_paragraph(" ".join(math_lines), styles["math"]))
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
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0f4")),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#b8c5cf")),
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
    font_name, bold_name = _register_fonts()
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
    document.build(_story(note, course_title, images, font_name, bold_name), onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output.getvalue()


def render_course_pdf(
    course_title: str,
    notes_with_images: list[tuple[LectureNote, list[NoteImage]]],
) -> bytes:
    font_name, bold_name = _register_fonts()
    styles = _styles(font_name, bold_name)
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{course_title} - همهٔ فصل‌ها",
        author="هم‌درس",
    )
    story: list = [
        Spacer(1, 25 * mm),
        _paragraph("هم‌درس", styles["meta"]),
        _paragraph(course_title, styles["cover"]),
        _paragraph("مجموعهٔ کامل جزوه‌های دوره", styles["h2"]),
        Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#315b7c")),
        Spacer(1, 12 * mm),
        _paragraph(f"شامل {len(notes_with_images)} فصل", styles["meta"]),
        PageBreak(),
        _paragraph("فهرست فصل‌ها", styles["h1"]),
    ]
    for index, (note, _) in enumerate(notes_with_images, start=1):
        story.append(_paragraph(f"{index}. {note.title}", styles["body"]))
    for note, images in notes_with_images:
        story.append(PageBreak())
        story.extend(_story(note, course_title, images, font_name, bold_name))
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output.getvalue()
