"""评测报告生成。"""

import json
from collections import Counter
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


def build_report(evaluation):
    results = evaluation.get("results", [])
    rubrics = [item.get("final_rubric") or item.get("rubric") or item.get("rule_rubric") for item in results]
    statuses = Counter(rubric["status"] for rubric in rubrics)
    scores = [rubric["overall_score"] for rubric in rubrics]
    capabilities = {}
    for rubric in rubrics:
        for name, score in rubric["dimension_scores"].items():
            capabilities.setdefault(name, []).append(score)
    capability_scores = {name: round(sum(values) / len(values)) for name, values in capabilities.items()}
    badcases = [item["badcase"] for item in results if item["badcase"]]
    distribution = dict(Counter(item["type"] for item in badcases))
    summary = {"total_cases": len(results), "pass": statuses["pass"], "warning": statuses["warning"],
               "fail": statuses["fail"], "pass_rate": round(statuses["pass"] / len(results) * 100, 1) if results else 0,
               "overall_score": round(sum(scores) / len(scores)) if scores else 0}
    return {"summary": summary, "capability_scores": capability_scores, "failed_cases": badcases,
            "badcase_distribution": distribution, "root_cause_analysis": "基于 V0.1 规则基线的首要失败维度。",
            "recommendations": ["优先修复高严重度 Badcase。", "为低分能力点补充针对性 Case。"]}


def markdown_report(report):
    summary = report["summary"]
    failed_lines = [f"- {item['case_id']}: {item['type']}" for item in report["failed_cases"]] or ["- None"]
    distribution_lines = [f"- {key}: {value}" for key, value in report["badcase_distribution"].items()] or ["- None"]
    lines = ["# EvalForge Evaluation Report", "", "## Summary", *[f"- {key}: {value}" for key, value in summary.items()],
             "", "## Capability Scores", *[f"- {key}: {value}" for key, value in report["capability_scores"].items()],
             "", "## Failed Cases", *failed_lines,
             "", "## Badcase Distribution", *distribution_lines,
             "", "## Root Cause Analysis", report["root_cause_analysis"], "", "## Recommendations",
             *[f"- {item}" for item in report["recommendations"]]]
    return "\n".join(lines) + "\n"


def _set_cell_shading(cell, fill):
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def _set_cell_margins(cell, top=90, start=120, bottom=90, end=120):
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _set_table_borders(table, color="D9D9D9"):
    properties = table._tbl.tblPr
    borders = properties.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "6")
        node.set(qn("w:space"), "0")
        node.set(qn("w:color"), color)


def _add_table(document, headers, rows, widths=None):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = False
    _set_table_borders(table)
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = str(header)
        _set_cell_shading(cell, "1F4E78")
        _set_cell_margins(cell)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragraph.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cell = cells[index]
            cell.text = str(value)
            _set_cell_margins(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if row_index % 2:
                _set_cell_shading(cell, "EAF3F8")
            if index and len(str(value)) <= 14:
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if widths:
        for row in table.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Inches(width)
    document.add_paragraph()
    return table


def docx_report(report, path):
    """将结构化评测结果写成可直接交付的 Word 报告。"""
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    for style_name in ("Title", "Heading 1", "Heading 2"):
        style = document.styles[style_name]
        style.font.name = "Arial"
        style.font.color.rgb = RGBColor(0, 0, 0)
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")

    title = document.add_paragraph(style="Title")
    title_run = title.add_run("EvalForge Evaluation Report")
    title_run.font.color.rgb = RGBColor(0, 0, 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    intro = document.add_paragraph(
        "This report summarizes the evaluation outcome, identifies quality risks, and highlights the next improvements to prioritize."
    )
    intro.alignment = WD_ALIGN_PARAGRAPH.CENTER

    document.add_heading("Evaluation Overview", level=1)
    document.add_paragraph("The report combines the rule-based evaluation results and any available AI Judge outcome into one delivery-ready summary.")

    document.add_heading("Summary", level=1)
    _add_table(document, ["Metric", "Value"], report["summary"].items(), widths=[3.9, 2.6])

    document.add_heading("Capability Scores", level=1)
    capability_rows = list(report["capability_scores"].items()) or [("No capability scores", "-")]
    _add_table(document, ["Capability", "Score"], capability_rows, widths=[4.6, 1.9])

    document.add_heading("Failed Cases", level=1)
    failed_rows = [
        (item["case_id"], item["type"], item.get("severity", "-"), item.get("reason", "-"))
        for item in report["failed_cases"]
    ] or [("None", "-", "-", "No failed or warning cases were identified.")]
    _add_table(document, ["Case ID", "Type", "Severity", "Reason"], failed_rows, widths=[1.1, 1.4, 0.9, 3.1])

    document.add_heading("Badcase Distribution", level=1)
    distribution_rows = list(report["badcase_distribution"].items()) or [("None", 0)]
    _add_table(document, ["Badcase Type", "Count"], distribution_rows, widths=[4.6, 1.9])

    document.add_heading("Root Cause Analysis", level=1)
    document.add_paragraph(report["root_cause_analysis"])

    document.add_heading("Recommendations", level=1)
    for recommendation in report["recommendations"]:
        document.add_paragraph(recommendation, style="List Bullet")

    document.add_heading("Evaluation Conclusion", level=1)
    summary = report["summary"]
    document.add_paragraph(
        f"The evaluation covered {summary['total_cases']} case(s), with an overall score of {summary['overall_score']} and a pass rate of {summary['pass_rate']}%."
    )
    document.save(path)


def write_reports(evaluation, markdown_path="eval_report.md", json_path="eval_report.json", docx_path="eval_report.docx"):
    report = build_report(evaluation)
    Path(markdown_path).write_text(markdown_report(report), encoding="utf-8")
    Path(json_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    docx_report(report, docx_path)
    return report
