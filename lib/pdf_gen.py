import os
import sys
import math
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from lib.database import get_db
from lib.logger import get_logger

if getattr(sys, "frozen", False):
    PDF_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FerdlWorks", "data", "pdfs")
else:
    PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pdfs")


def _get_sender(settings):
    parts = []
    name = " ".join(filter(None, [settings.get("sender_first_name", ""), settings.get("sender_last_name", "")]))
    if settings.get("sender_company"):
        parts.append(settings["sender_company"])
    if name:
        parts.append(name)
    parts.append(settings.get("sender_street", ""))
    zip_city = " ".join(filter(None, [settings.get("sender_zip", ""), settings.get("sender_city", "")]))
    if zip_city:
        parts.append(zip_city)
    phone = settings.get("sender_phone", "")
    email = settings.get("sender_email", "")
    if phone:
        parts.append(f"Tel: {phone}")
    if email:
        parts.append(f"E-Mail: {email}")
    tax_id = settings.get("sender_tax_id", "")
    if tax_id:
        parts.append(f"Steuer-Nr: {tax_id}")
    return parts


def _build_elements(doc_data, settings, db):
    style_normal = ParagraphStyle("Normal", parent=getSampleStyleSheet()["Normal"], fontSize=9, leading=12, spaceAfter=4)
    style_small = ParagraphStyle("Small", parent=style_normal, fontSize=9, leading=12, spaceAfter=2)
    style_title = ParagraphStyle("Title", parent=style_normal, fontSize=9, textColor=colors.HexColor("#8b0000"),
                                 fontName="Helvetica-Bold", spaceAfter=4)
    style_header = ParagraphStyle("Header", parent=style_normal, fontSize=9,
                                  textColor=colors.HexColor("#8b0000"), fontName="Helvetica-Bold", spaceAfter=4)
    style_right = ParagraphStyle("Right", parent=style_normal, alignment=TA_RIGHT)
    style_center = ParagraphStyle("Center", parent=style_normal, alignment=TA_CENTER)
    style_bold_left = ParagraphStyle("BoldLeft", parent=style_normal, alignment=TA_LEFT,
                                     fontName="Helvetica-Bold")
    style_bold_right_big = ParagraphStyle("BoldRightBig", parent=style_normal, alignment=TA_RIGHT,
                                          fontName="Helvetica-Bold")
    elements = []

    # Absender
    for line in _get_sender(settings):
        elements.append(Paragraph(line, style_small))
    elements.append(Spacer(1, 30*mm))

    # Adresse (links) + Rechnungsblock (rechts)
    customer = doc_data.get("customer", {})
    addr_lines = [customer.get("company", "")]
    name = " ".join(filter(None, [customer.get("first_name", ""), customer.get("last_name", "")]))
    if name:
        addr_lines.append(name)
    addr_lines.append(customer.get("street", ""))
    zip_city = " ".join(filter(None, [customer.get("zip", ""), customer.get("city", "")]))
    if zip_city:
        addr_lines.append(zip_city)
    addr_text = "<br/>".join(addr_lines)
    doc_type_label = "RECHNUNG" if doc_data.get("doc_type") == "RG" else "LIEFERSCHEIN"
    raw_date = doc_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    try:
        dt = datetime.strptime(raw_date, "%Y-%m-%d")
        date_formatted = dt.strftime("%d.%m.%Y")
    except ValueError:
        date_formatted = raw_date
    payment_term = int(settings.get("payment_term", "30"))
    due_formatted = ""
    try:
        due_dt = datetime.strptime(raw_date, "%Y-%m-%d") + timedelta(days=payment_term)
        due_formatted = due_dt.strftime("%d.%m.%Y")
    except ValueError:
        pass
    right_lines = [f"<b>{doc_type_label}</b>", doc_data.get('doc_number', ''),
                   f"Datum: {date_formatted}"]
    if due_formatted:
        right_lines.append(f"Zahlbar bis: {due_formatted}")
    iban = settings.get("sender_iban", "").strip()
    if iban:
        right_lines.append(f"IBAN: {iban}")
    header_table = Table([
        [Paragraph(addr_text, style_normal),
         Paragraph("<br/>".join(right_lines), style_right)]
    ], colWidths=[90*mm, 70*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 28*mm))

    # Positionen
    elements.append(Paragraph("Positionen", style_header))
    elements.append(Spacer(1, 2*mm))
    pos_data = doc_data.get("positions", [])

    merge_tools = str(doc_data.get("merge_tools", "0")) == "1"
    merge_tool_name = doc_data.get("merge_tool_name", "Werkzeug")
    round_tools = str(doc_data.get("round_tools", "0")) == "1"

    # Separate positions into groups
    table_rows = []  # material or standalone tool
    text_rows = []   # text entries (rendered as paragraphs)
    tool_rows = []   # tool entries (for merging)
    for pos in pos_data:
        if pos.get("pos_type") == "text":
            text_rows.append(pos)
        elif merge_tools and pos.get("pos_type") == "tool":
            tool_rows.append(pos)
        else:
            table_rows.append(pos)

    # Add text entries as plain paragraphs BEFORE the table
    for pos in text_rows:
        txt = pos.get("description", "")
        if txt.strip():
            elements.append(Paragraph(txt, style_normal))
            elements.append(Spacer(1, 2*mm))

    unit_labels = {"h": "Std.", "min": "Min.", "m": "m", "qm": "m\u00b2", "Stk": "Stk.", "m\u00b2": "m\u00b2"}
    table_data = [["Pos.", "Beschreibung", "Menge", "Einheit", "EP", "Gesamt"]]
    for i, pos in enumerate(table_rows, 1):
        desc = pos.get("description", "")
        qty = pos.get("quantity", 1)
        unit = pos.get("unit", "")
        unit_label = unit_labels.get(unit, unit) if unit else ""
        ppu = pos.get("price_per_unit", 0)
        orig_p = pos.get("orig_price")
        orig_u = pos.get("orig_price_unit")
        if not orig_p or not orig_u:
            ref_id = pos.get("ref_id")
            ptype = pos.get("pos_type")
            if ref_id and ptype == "tool":
                t = get_db().tool_get(ref_id)
                if t:
                    orig_p = t.get("price", 0)
                    orig_u = t.get("price_unit", "")
            elif ref_id and ptype == "material":
                m = get_db().material_get(ref_id)
                if m:
                    orig_p = m.get("price_per_m2", 0)
                    orig_u = "m\u00b2"
        if orig_p and orig_u:
            ep_str = f"{float(orig_p):.2f} \u20ac/{orig_u}"
        else:
            ep_str = f"{ppu:.2f} \u20ac"
        total = pos.get("total", 0)
        table_data.append([
            str(i),
            Paragraph(desc, style_normal),
            f"{qty:.2f}" if qty != int(qty) else str(int(qty)),
            unit_label,
            ep_str,
            f"{total:.2f} \u20ac",
        ])

    # Add merged tool row if applicable
    if tool_rows:
        tool_total = sum(p.get("total", 0) for p in tool_rows)
        if round_tools:
            tool_total = math.ceil(tool_total / 10) * 10
        i = len(table_rows) + 1
        table_data.append([
            str(i),
            Paragraph(merge_tool_name, style_normal),
            "", "", "",
            f"{tool_total:.2f} \u20ac",
        ])
        pos_data_displayed_total = sum(p.get("total", 0) for p in table_rows) + tool_total
    else:
        pos_data_displayed_total = sum(p.get("total", 0) for p in table_rows) + sum(p.get("total", 0) for p in tool_rows)
    # Apply rounding to tool portion regardless of merge state
    if round_tools:
        all_tool = sum(p.get("total", 0) for p in pos_data if p.get("pos_type") == "tool")
        all_other = sum(p.get("total", 0) for p in pos_data if p.get("pos_type") != "tool")
        pos_data_displayed_total = math.ceil(all_tool / 10) * 10 + all_other

    avail_width = (210*mm - 20*mm - 15*mm) * 0.98
    col_widths = [10*mm, avail_width-10*mm-19*mm-16*mm-24*mm-23*mm, 19*mm, 16*mm, 24*mm, 23*mm]
    pos_table = Table(table_data, colWidths=col_widths)
    pos_style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b0000")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    pos_table.setStyle(TableStyle(pos_style))
    elements.append(pos_table)
    elements.append(Spacer(1, 8*mm))

    # Summen (rechtsbündig) – use displayed positions
    total_net = pos_data_displayed_total
    total_tax = doc_data.get("total_tax", 0)
    total_gross = doc_data.get("total_gross", 0)
    discount_value = doc_data.get("discount_value", 0)
    has_discount = discount_value and float(discount_value) > 0
    tax_rate_val = float(settings.get("tax_rate", "19"))
    rabatt_abs = 0
    summary_data = []
    summary_data.append(["Nettobetrag:", f"{total_net:.2f} \u20ac"])
    if has_discount:
        dtype = doc_data.get("discount_type", "percent")
        if dtype == "percent":
            rabatt_abs = total_net * float(discount_value) / 100
            summary_data.append([f"Rabatt ({discount_value}%):", f"-{rabatt_abs:.2f} \u20ac"])
        else:
            rabatt_abs = float(discount_value)
            summary_data.append(["Rabatt:", f"-{rabatt_abs:.2f} \u20ac"])
        net_after = total_net - rabatt_abs
        summary_data.append(["Netto nach Rabatt:", f"{net_after:.2f} \u20ac"])
    total_tax = (total_net - (rabatt_abs if has_discount else 0)) * tax_rate_val / 100
    total_gross = (total_net - (rabatt_abs if has_discount else 0)) + total_tax
    summary_data.append([f"MwSt. ({tax_rate_val:.0f}%):", f"{total_tax:.2f} \u20ac"])
    sum_rows = []
    for label, value in summary_data:
        sum_rows.append([Paragraph(label, style_normal), Paragraph(value, style_right)])
    sum_rows.append([
        Paragraph("Gesamtbetrag:", style_bold_left),
        Paragraph(f"{total_gross:.2f} \u20ac", style_bold_right_big)
    ])
    sum_table = Table(sum_rows, colWidths=[48*mm, 28*mm], hAlign="RIGHT")
    sum_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, -2), (-1, -2), 0.5, colors.HexColor("#cccccc")),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.HexColor("#8b0000")),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 8*mm))
    # Notiz auf Rechnung (nur wenn print_note=1)
    if doc_data.get("print_note", "1") == "1":
        note = doc_data.get("note", "").strip()
        if note:
            elements.append(Paragraph(note, style_normal))
            elements.append(Spacer(1, 6*mm))
    elements.append(Spacer(1, 10*mm))
    return elements


def generate_pdf(doc_data, output_path=None):
    db = get_db()
    settings = db.settings_get_all()
    logger = get_logger()
    os.makedirs(PDF_DIR, exist_ok=True)
    if not output_path:
        num = doc_data.get("doc_number", "XXXX")
        date_str = doc_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        safe_date = date_str.replace("-", "")
        output_path = os.path.join(PDF_DIR, f"{num}_{safe_date}.pdf")

    # Alte PDF löschen falls vorhanden
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except Exception:
            pass

    elements = _build_elements(doc_data, settings, db)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(210*mm/2, 12*mm, "Vielen Dank f\xfcr Ihren Auftrag!")
        canvas.restoreState()

    title = doc_data.get("doc_number", "FerdlWorks")
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=20*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=20*mm,
                            onFirstPage=footer, onLaterPages=footer, title=title)
    doc.build(elements)
    logger.info(f"PDF erstellt: {output_path}")
    return output_path
