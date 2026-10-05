from __future__ import annotations

from io import BytesIO
import base64
import math
from typing import Any, Dict, Iterable, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

PAGE_W, PAGE_H = A4
SOLAR = colors.HexColor("#F6B80E")
SOLAR_DARK = colors.HexColor("#D79600")
GREEN = colors.HexColor("#166534")
NAVY = colors.HexColor("#0F172A")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#CBD5E1")
WHITE = colors.white


def money(value: float) -> str:
    try:
        value = float(value)
    except Exception:
        value = 0.0
    return f"INR {value:,.2f}"


def _para(text: Any, style: ParagraphStyle) -> Paragraph:
    if text is None:
        text = ""
    safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = safe.replace("\n", "<br/>")
    return Paragraph(safe, style)


def _logo_flowable(settings: Dict[str, Any], width: float = 24 * mm, height: float = 24 * mm):
    logo_b64 = settings.get("logo_b64")
    if logo_b64:
        try:
            raw = base64.b64decode(logo_b64)
            return Image(BytesIO(raw), width=width, height=height, kind="proportional")
        except Exception:
            pass
    # Text fallback: deliberately generic; user can upload the real logo in Settings.
    return Table(
        [[Paragraph("<b>SR</b>", ParagraphStyle("logo", fontName="Helvetica-Bold", fontSize=16, textColor=NAVY, alignment=TA_CENTER))]],
        colWidths=[width],
        rowHeights=[height],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOLAR),
            ("BOX", (0, 0), (-1, -1), 1, SOLAR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]),
    )


def _header_footer(canvas, doc, settings: Dict[str, Any]):
    canvas.saveState()
    # top solar band
    canvas.setFillColor(SOLAR)
    canvas.rect(0, PAGE_H - 9 * mm, PAGE_W, 9 * mm, stroke=0, fill=1)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(15 * mm, PAGE_H - 6 * mm, settings.get("company_name", "Solar Rays Energy Solutions LLP"))
    canvas.setFont("Helvetica", 7)
    phones = " / ".join([p for p in [settings.get("phone1"), settings.get("phone2")] if p])
    right_text = phones or settings.get("website", "")
    if right_text:
        canvas.drawRightString(PAGE_W - 15 * mm, PAGE_H - 6 * mm, right_text)

    # footer line and contact
    canvas.setStrokeColor(SOLAR_DARK)
    canvas.setLineWidth(1)
    canvas.line(14 * mm, 13 * mm, PAGE_W - 14 * mm, 13 * mm)
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 6.8)
    footer = " | ".join([x for x in [settings.get("website"), settings.get("email")] if x])
    canvas.drawString(15 * mm, 8.8 * mm, footer[:110])
    canvas.drawRightString(PAGE_W - 15 * mm, 8.8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=20,
            leading=24, textColor=NAVY, spaceAfter=7 * mm
        ),
        "h1": ParagraphStyle(
            "h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=13,
            leading=16, textColor=NAVY, spaceBefore=2 * mm, spaceAfter=3 * mm
        ),
        "h2": ParagraphStyle(
            "h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=10.5,
            leading=13, textColor=GREEN, spaceBefore=2 * mm, spaceAfter=2 * mm
        ),
        "body": ParagraphStyle(
            "body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.1,
            leading=13, textColor=colors.HexColor("#1E293B"), spaceAfter=2.4 * mm
        ),
        "small": ParagraphStyle(
            "small", parent=ss["BodyText"], fontName="Helvetica", fontSize=7.8,
            leading=10.2, textColor=colors.HexColor("#334155")
        ),
        "small_bold": ParagraphStyle(
            "small_bold", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=7.8,
            leading=10.2, textColor=NAVY
        ),
        "table": ParagraphStyle(
            "table", parent=ss["BodyText"], fontName="Helvetica", fontSize=7.3,
            leading=9.2, textColor=colors.HexColor("#1E293B")
        ),
        "table_bold": ParagraphStyle(
            "table_bold", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=7.3,
            leading=9.2, textColor=NAVY
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=7.3,
            leading=9.2, textColor=WHITE
        ),
        "center": ParagraphStyle(
            "center", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=9,
            leading=12, alignment=TA_CENTER, textColor=NAVY
        ),
        "right": ParagraphStyle(
            "right", parent=ss["BodyText"], fontName="Helvetica", fontSize=8.5,
            leading=11, alignment=TA_RIGHT, textColor=NAVY
        ),
        "hero": ParagraphStyle(
            "hero", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=30,
            leading=34, textColor=NAVY, alignment=TA_LEFT
        ),
        "hero_sub": ParagraphStyle(
            "hero_sub", parent=ss["BodyText"], fontName="Helvetica", fontSize=11,
            leading=16, textColor=SLATE
        ),
    }


def _kv_table(rows: Iterable, styles: Dict[str, ParagraphStyle], widths=None):
    data = []
    for key, val in rows:
        data.append([_para(key, styles["small_bold"]), _para(val, styles["small"])])
    if widths is None:
        widths = [38 * mm, 120 * mm]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _boq_table(boq: List[Dict[str, Any]], styles):
    data = [[
        _para("S.No.", styles["table_header"]),
        _para("Description", styles["table_header"]),
        _para("Make", styles["table_header"]),
        _para("Unit", styles["table_header"]),
        _para("Qty", styles["table_header"]),
    ]]
    for i, row in enumerate(boq, start=1):
        data.append([
            _para(row.get("S.No.", i), styles["table"]),
            _para(row.get("Description", ""), styles["table"]),
            _para(row.get("Make", ""), styles["table"]),
            _para(row.get("Unit", ""), styles["table"]),
            _para(row.get("Qty", ""), styles["table"]),
        ])
    t = Table(data, colWidths=[10 * mm, 89 * mm, 36 * mm, 20 * mm, 20 * mm], repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _material_table(materials: List[Dict[str, Any]], styles):
    data = [[
        _para("S.No.", styles["table_header"]),
        _para("Component", styles["table_header"]),
        _para("Description", styles["table_header"]),
        _para("Quantity", styles["table_header"]),
        _para("Make", styles["table_header"]),
    ]]
    for i, row in enumerate(materials, start=1):
        data.append([
            _para(row.get("S.No.", i), styles["table"]),
            _para(row.get("Component", ""), styles["table"]),
            _para(row.get("Description", ""), styles["table"]),
            _para(row.get("Quantity", ""), styles["table"]),
            _para(row.get("Make", ""), styles["table"]),
        ])
    t = Table(data, colWidths=[9 * mm, 36 * mm, 76 * mm, 25 * mm, 29 * mm], repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def generate_quote_pdf(data: Dict[str, Any]) -> bytes:
    """Generate the 3-page quotation PDF used by the Streamlit app."""
    settings = data.get("settings", {})
    customer = data.get("customer", {})
    project = data.get("project", {})
    commercial = data.get("commercial", {})
    boq = data.get("boq", [])
    materials = data.get("materials", [])
    terms = data.get("terms", {})
    styles = _styles()

    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Quotation {data.get('quote_ref', '')}",
        author=settings.get("company_name", "Solar Rays Energy Solutions LLP"),
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(
        id="quotation",
        frames=[frame],
        onPage=lambda canvas, d: _header_footer(canvas, d, settings),
    )
    doc.addPageTemplates([template])

    story = []

    # PAGE 1 - proposal / company introduction
    logo = _logo_flowable(settings, 24 * mm, 24 * mm)
    brand = Table([
        [logo, Paragraph(
            f"<b>{settings.get('company_name', 'Solar Rays Energy Solutions LLP')}</b><br/>"
            f"<font size='9' color='#475569'>{settings.get('tagline', 'Clean solar. Smarter savings.')}</font>",
            ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=15, leading=20, textColor=NAVY)
        )]
    ], colWidths=[30 * mm, 140 * mm], hAlign="LEFT")
    brand.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [Spacer(1, 6 * mm), brand, Spacer(1, 11 * mm)]

    story.append(_para("Solar Power Proposal", styles["hero"]))
    subtitle = f"{project.get('capacity_kw', '')} kW {project.get('system_type', '')} Solar Power Project"
    story.append(_para(subtitle, styles["hero_sub"]))
    story.append(Spacer(1, 8 * mm))

    quote_meta = [
        [
            _para("PREPARED FOR", styles["small_bold"]),
            _para("QUOTATION", styles["small_bold"]),
            _para("DATE", styles["small_bold"]),
        ],
        [
            _para(customer.get("name", ""), styles["body"]),
            _para(data.get("quote_ref", ""), styles["body"]),
            _para(data.get("quote_date", ""), styles["body"]),
        ],
    ]
    meta = Table(quote_meta, colWidths=[80 * mm, 50 * mm, 40 * mm], hAlign="LEFT")
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [meta, Spacer(1, 8 * mm)]

    story.append(_para("Dear Customer,", styles["body"]))
    intro = settings.get(
        "intro_text",
        "Solar Rays Energy Solutions LLP designs, deploys and maintains high-performance rooftop solar systems focused on long-term savings, reliable engineering and energy independence."
    )
    story.append(_para(intro, styles["body"]))
    story.append(_para(
        "We are pleased to submit our proposal based on the project requirements shared with us. The proposed solution includes engineering, supply, installation, testing and commissioning of the solar power system, subject to the final site survey and agreed commercial terms.",
        styles["body"]
    ))

    story.append(_para("Project Snapshot", styles["h1"]))
    snapshot_rows = [
        ("System Type", project.get("system_type", "")),
        ("Plant Capacity", f"{project.get('capacity_kw', '')} kW"),
        ("Phase", project.get("phase", "")),
        ("Solar Module", f"{project.get('panel_brand', '')} - {project.get('panel_wattage', '')} Wp"),
        ("No. of Modules", str(project.get("panel_count", ""))),
        ("Inverter", f"{project.get('inverter_brand', '')} - {project.get('inverter_capacity_kw', '')} kW"),
    ]
    story.append(_kv_table(snapshot_rows, styles))

    story.append(Spacer(1, 5 * mm))
    story.append(_para("Our Scope", styles["h1"]))
    scope_items = [
        "System sizing and engineering based on the agreed capacity and site conditions.",
        "Supply of solar modules, inverter, mounting structure, protection systems, cables and standard accessories as listed in the BOQ.",
        "Installation, testing and commissioning of the solar power plant.",
        "Support for net-metering / documentation where included in the commercial scope.",
        "After-sales support as per applicable product warranties and the final order terms.",
    ]
    for item in scope_items:
        story.append(Paragraph(f"&#8226; {item}", styles["body"]))

    story.append(PageBreak())

    # PAGE 2 - commercial quotation
    story.append(_para("Commercial Quotation", styles["title"]))
    project_title = f"{project.get('capacity_kw', '')} kW {project.get('system_type', '')} Solar Power Project"
    story.append(_para(project_title, styles["center"]))
    story.append(Spacer(1, 4 * mm))

    contact_rows = [
        ("Quotation Ref.", data.get("quote_ref", "")),
        ("Quotation Date", data.get("quote_date", "")),
        ("Customer", customer.get("name", "")),
        ("Mobile", customer.get("phone", "")),
        ("Address", customer.get("address", "")),
    ]
    story.append(_kv_table(contact_rows, styles))
    story.append(Spacer(1, 5 * mm))

    story.append(_para("Bill of Quantities (BOQ)", styles["h1"]))
    story.append(_boq_table(boq, styles))
    story.append(Spacer(1, 4 * mm))

    taxable = float(commercial.get("taxable_value", 0) or 0)
    gst_amt = float(commercial.get("gst_amount", 0) or 0)
    grand = float(commercial.get("grand_total", 0) or 0)
    subsidy = float(commercial.get("total_subsidy", 0) or 0)
    effective = float(commercial.get("effective_price", grand - subsidy) or 0)
    summary_rows = [
        [_para("Commercial Summary", styles["small_bold"]), ""],
        [_para("Basic Amount", styles["small"]), _para(money(commercial.get("basic_amount", 0)), styles["right"])],
        [_para("Discount", styles["small"]), _para(money(commercial.get("discount", 0)), styles["right"])],
        [_para("Taxable Value", styles["small"]), _para(money(taxable), styles["right"])],
        [_para(f"GST @ {commercial.get('gst_rate', 0)}%", styles["small"]), _para(money(gst_amt), styles["right"])],
        [_para("Other Charges", styles["small"]), _para(money(commercial.get("other_charges", 0)), styles["right"])],
        [_para("Grand Total", styles["small_bold"]), _para(money(grand), styles["right"])],
    ]
    if subsidy > 0:
        summary_rows.extend([
            [_para("Central Subsidy", styles["small"]), _para(money(commercial.get("central_subsidy", 0)), styles["right"])],
            [_para("State Subsidy", styles["small"]), _para(money(commercial.get("state_subsidy", 0)), styles["right"])],
            [_para("Total Indicative Subsidy", styles["small_bold"]), _para(money(subsidy), styles["right"])],
            [_para("Effective Customer Cost", styles["small_bold"]), _para(money(effective), styles["right"])],
        ])
    summary = Table(summary_rows, colWidths=[105 * mm, 65 * mm], hAlign="RIGHT")
    summary.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), SOLAR),
        ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#FEF3C7")),
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary)

    if subsidy > 0:
        story.append(Spacer(1, 2.5 * mm))
        subsidy_note = commercial.get("subsidy_note") or (
            "Subsidy shown above is indicative and subject to scheme eligibility, prevailing government rules, portal approval and successful completion of the required process."
        )
        story.append(_para(subsidy_note, styles["small"]))

    story.append(Spacer(1, 3 * mm))
    story.append(_para("Terms & Conditions", styles["h2"]))
    term_lines = [
        f"Quotation validity: {terms.get('validity_days', 10)} days from date of issue.",
        f"Payment terms: {terms.get('payment_terms', 'As mutually agreed / as per purchase order.')} ",
        f"Delivery, installation & commissioning: {terms.get('delivery_timeline', 'Within 1-2 weeks from confirmed order and advance, subject to site readiness.')} ",
        f"Net-metering: {terms.get('net_metering', 'As per selected scope and applicable DISCOM process.')} ",
        f"Warranty: {terms.get('warranty', 'As per OEM warranty and final order terms.')} ",
    ]
    for line in term_lines:
        story.append(Paragraph(f"&#8226; {line}", styles["small"]))

    bank_bits = [settings.get("bank_name"), settings.get("bank_account"), settings.get("ifsc"), settings.get("bank_branch")]
    if any(bank_bits):
        story.append(Spacer(1, 2 * mm))
        story.append(_para("Payment Details", styles["h2"]))
        bank_rows = [
            ("Account Name", settings.get("bank_account_name", settings.get("company_name", ""))),
            ("Bank", settings.get("bank_name", "")),
            ("Account No.", settings.get("bank_account", "")),
            ("IFSC", settings.get("ifsc", "")),
            ("Branch", settings.get("bank_branch", "")),
        ]
        story.append(_kv_table(bank_rows, styles, widths=[35 * mm, 90 * mm]))

    story.append(PageBreak())

    # PAGE 3 - detailed material
    story.append(_para("Detailed Material Specification", styles["title"]))
    story.append(_material_table(materials, styles))
    story.append(Spacer(1, 5 * mm))
    material_note = terms.get(
        "material_note",
        "Final makes, models and quantities are subject to approved design, site survey, availability and the mutually accepted purchase order. Any deviation requested by the customer may affect price and delivery."
    )
    story.append(Paragraph(f"<b>Note:</b> {str(material_note).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}", styles["small"]))
    story.append(Spacer(1, 7 * mm))

    registered = settings.get("registered_address") or settings.get("office_address") or ""
    company_rows = [
        ("Company", settings.get("company_name", "Solar Rays Energy Solutions LLP")),
        ("GSTIN", settings.get("gstin", "")),
        ("Website", settings.get("website", "")),
        ("Email", settings.get("email", "")),
        ("Phone", " / ".join([p for p in [settings.get("phone1"), settings.get("phone2")] if p])),
        ("Address", registered),
    ]
    story.append(_para("Company Details", styles["h1"]))
    story.append(_kv_table(company_rows, styles))
    story.append(Spacer(1, 8 * mm))
    story.append(_para("Thank you for the opportunity to submit this proposal.", styles["body"]))
    story.append(_para(f"For {settings.get('company_name', 'Solar Rays Energy Solutions LLP')}", styles["small_bold"]))
    story.append(Spacer(1, 8 * mm))
    story.append(_para("Authorized Signatory", styles["small_bold"]))

    doc.build(story)
    return buffer.getvalue()


def default_boq(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    cap = float(project.get("capacity_kw", 5) or 5)
    watt = int(project.get("panel_wattage", 580) or 580)
    panel_count = int(math.ceil(cap * 1000 / watt))
    return [
        {"S.No.": 1, "Description": f"Solar PV array - {cap:g} kW system using {watt} Wp modules", "Make": project.get("panel_brand", "As selected"), "Unit": "Wp", "Qty": panel_count},
        {"S.No.": 2, "Description": f"{project.get('system_type', 'On-Grid')} solar inverter", "Make": project.get("inverter_brand", "As selected"), "Unit": "kW", "Qty": project.get("inverter_capacity_kw", cap)},
        {"S.No.": 3, "Description": "Module mounting structure with required fasteners for rooftop installation", "Make": project.get("structure_make", "GI / HDG"), "Unit": "Set", "Qty": 1},
        {"S.No.": 4, "Description": "ACDB / DCDB, surge protection and required electrical protection", "Make": "As per approved design", "Unit": "Set", "Qty": 1},
        {"S.No.": 5, "Description": "AC/DC cables, conduit, junctions, connectors and standard accessories", "Make": "As per approved design", "Unit": "Lot", "Qty": 1},
        {"S.No.": 6, "Description": "Earthing system and lightning protection", "Make": "As per approved design", "Unit": "Set", "Qty": 1},
        {"S.No.": 7, "Description": "Installation, testing and commissioning", "Make": "Solar Rays", "Unit": "Job", "Qty": 1},
    ]


def default_materials(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    cap = float(project.get("capacity_kw", 5) or 5)
    watt = int(project.get("panel_wattage", 580) or 580)
    panel_count = int(math.ceil(cap * 1000 / watt))
    return [
        {"S.No.": 1, "Component": "Solar PV Modules", "Description": f"Bifacial Mono PERC / TOPCon modules, approx. {watt} Wp each", "Quantity": f"{panel_count} Nos.", "Make": project.get("panel_brand", "As selected")},
        {"S.No.": 2, "Component": "Inverter / PCU", "Description": f"{project.get('system_type', 'On-Grid')} inverter, {project.get('phase', '')}", "Quantity": f"{project.get('inverter_capacity_kw', cap)} kW / 1 No.", "Make": project.get("inverter_brand", "As selected")},
        {"S.No.": 3, "Component": "DC Distribution Box", "Description": "IP65 enclosure with DC protection / SPD / fuses as required", "Quantity": "1 Set", "Make": "As per approved design"},
        {"S.No.": 4, "Component": "AC Distribution Box", "Description": "IP65 enclosure with MCB/MCCB, SPD and protection as required", "Quantity": "1 Set", "Make": "As per approved design"},
        {"S.No.": 5, "Component": "AC Cable", "Description": "Copper / aluminium cable sized as per approved electrical design", "Quantity": "As per system", "Make": "Standard approved make"},
        {"S.No.": 6, "Component": "Interconnecting DC Cable", "Description": "Solar DC cable, UV resistant and suitably rated", "Quantity": "As per system", "Make": "Standard approved make"},
        {"S.No.": 7, "Component": "Module Mounting Structure", "Description": "GI / HDG structure designed for site conditions and module layout", "Quantity": "As per module layout", "Make": project.get("structure_make", "GI / HDG")},
        {"S.No.": 8, "Component": "Earthing Cable", "Description": "Copper / GI earthing conductor sized as per design", "Quantity": "As per system", "Make": "Standard approved make"},
        {"S.No.": 9, "Component": "Earthing", "Description": "Earth electrodes / rods with required accessories", "Quantity": "3 Sets (typical)", "Make": "Standard approved make"},
        {"S.No.": 10, "Component": "Lightning Arrestor", "Description": "Conventional lightning protection with supporting arrangement", "Quantity": "1 Set", "Make": "Standard approved make"},
    ]
