from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt


def set_rtl(paragraph, right_to_left=True):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_pr = paragraph._p.get_or_add_pPr()
    bidi = p_pr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}bidi")
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        p_pr.append(bidi)


def set_run_rtl(run):
    r_pr = run._r.get_or_add_rPr()
    rtl = r_pr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rtl")
    if rtl is None:
        rtl = OxmlElement("w:rtl")
        r_pr.append(rtl)


def create_worklog_docx(output_path: str, title: str, tasks: list[str]) -> str:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    title_paragraph = document.add_paragraph()
    set_rtl(title_paragraph)
    title_paragraph.paragraph_format.space_after = Pt(12)
    title_run = title_paragraph.add_run(title)
    title_run.bold = True
    title_run.font.name = "Tahoma"
    title_run.font.size = Pt(14)
    set_run_rtl(title_run)

    for task in tasks:
        if not task.strip():
            continue
        paragraph = document.add_paragraph(style="List Bullet")
        set_rtl(paragraph)
        paragraph.paragraph_format.left_indent = Inches(0.25)
        paragraph.paragraph_format.right_indent = Inches(0)
        paragraph.paragraph_format.first_line_indent = Inches(0)
        paragraph.paragraph_format.space_after = Pt(6)
        run = paragraph.add_run(task.strip())
        run.font.name = "Tahoma"
        run.font.size = Pt(11)
        set_run_rtl(run)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)
    return str(path)
