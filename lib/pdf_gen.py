import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from lib.database import get_db
from lib.logger import get_logger

PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pdfs")

UNIT_NAMES = {"h": "Std.", "min": "Min.", "m": "m", "qm": "m\xb2"}


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


def generate_pdf(doc_data, output_path=None):
    db = get_db()
    settings = db.settings_get_all()
    logger = get_logger()
    os.makedirs(PDF_DIR, exist_ok=True)
    if not output_path:
        doc_type = doc_data.get("doc_type", "RG")
        num = doc_data.get("doc_number", "XXXX")
        date_str = doc_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        safe_date = date_str.replace("-", "")
        output_path = os.path.join(PDF_DIR, f"{doc_type}_{num}_{safe_date}.pdf")
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=20*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle("Normal", parent=styles["Normal"], fontSize=9, leading=12, spaceAfter=4)
    style_small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=10, spaceAfter=2)
    style_title = ParagraphStyle("Title", parent=styles["Normal"], fontSize=16, leading=20,
                                 textColor=colors.HexColor("#8b0000"), spaceAfter=6)
    style_header = ParagraphStyle("Header", parent=styles["Normal"], fontSize=10, leading=14,
                                  textColor=colors.HexColor("#8b0000"), spaceAfter=4)
    style_right = ParagraphStyle("Right", parent=style_normal, alignment=TA_RIGHT)
    style_center = ParagraphStyle("Center", parent=style_normal, alignment=TA_CENTER)
    elements = []
    # Kopfbereich
    sender_lines = _get_sender(settings)
    for line in sender_lines:
        elements.append(Paragraph(line, style_small))
    elements.append(Spacer(1, 5*mm))
    # Absender + Empfänger (Tabelle)
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
    header_right = f"<b>{doc_type_label}</b><br/>Nr: {doc_data.get('doc_number', '')}<br/>Datum: {doc_data.get('date', '')}"
    addr_data = [[Paragraph(addr_text, style_normal), Paragraph(header_right, style_right)]]
    addr_table = Table(addr_data, colWidths=[90*mm, 70*mm])
    addr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(addr_table)
    elements.append(Spacer(1, 8*mm))
    # Notiz
    note = doc_data.get("note", "")
    if note:
        elements.append(Paragraph(note, style_normal))
        elements.append(Spacer(1, 4*mm))
    # Positionen
    elements.append(Paragraph("Positionen", style_header))
    elements.append(Spacer(1, 2*mm))
    pos_data = doc_data.get("positions", [])
    table_data = [["Pos.", "Beschreibung", "Menge", "Einheit", "EP", "Gesamt"]]
    unit_labels = {"h": "Std.", "min": "Min.", "m": "m", "qm": "m\u00b2", "Stk": "Stk.", "m\u00b2": "m\u00b2"}
    for i, pos in enumerate(pos_data, 1):
        desc = pos.get("description", "")
        qty = pos.get("quantity", 1)
        unit = pos.get("unit", "")
        unit_label = unit_labels.get(unit, unit) if unit else ""
        ppu = pos.get("price_per_unit", 0)
        total = pos.get("total", 0)
        table_data.append([
            str(i),
            Paragraph(desc, style_normal),
            f"{qty:.2f}" if qty != int(qty) else str(int(qty)),
            unit_label,
            f"{ppu:.2f} \u20ac",
            f"{total:.2f} \u20ac",
        ])
    col_widths = [10*mm, 75*mm, 18*mm, 15*mm, 22*mm, 22*mm]
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
    elements.append(Spacer(1, 5*mm))
    # Summen
    total_net = doc_data.get("total_net", 0)
    total_tax = doc_data.get("total_tax", 0)
    total_gross = doc_data.get("total_gross", 0)
    discount_value = doc_data.get("discount_value", 0)
    has_discount = discount_value and float(discount_value) > 0
    tax_rate = float(settings.get("tax_rate", "19"))
    summary_data = []
    summary_data.append(["Nettobetrag:", f"{total_net:.2f} \u20ac"])
    if has_discount:
        if doc_data.get("discount_type") == "percent":
            summary_data.append([f"Rabatt ({discount_value}%):", f"-{total_net * float(discount_value) / 100:.2f} \u20ac"])
        else:
            summary_data.append([f"Rabatt:", f"-{float(discount_value):.2f} \u20ac"])
        # Netto nach Rabatt
        if doc_data.get("discount_type") == "percent":
            net_after = total_net * (1 - float(discount_value) / 100)
        else:
            net_after = total_net - float(discount_value)
        summary_data.append(["Netto nach Rabatt:", f"{net_after:.2f} \u20ac"])
    summary_data.append([f"MwSt. ({tax_rate:.0f}%):", f"{total_tax:.2f} \u20ac"])
    summary_data.append(["<b>Gesamtbetrag:</b>", f"<b>{total_gross:.2f} \u20ac</b>"])
    sum_table = Table(summary_data, colWidths=[60*mm, 35*mm])
    sum_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, -2), (-1, -2), 0.5, colors.HexColor("#cccccc")),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.HexColor("#8b0000")),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 10*mm))
    # Footer
    elements.append(Paragraph("Vielen Dank f\xfcr Ihren Auftrag!", style_center))
    elements.append(Paragraph("Zahlbar innerhalb von 14 Tagen ohne Abzug.", style_small))
    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph("---", style_center))
    elements.append(Paragraph(f"Erstellt mit {doc_data.get('app_name', 'FerdlWorks')} am {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              style_small))
    doc.build(elements)
    logger.info(f"PDF erstellt: {output_path}")
    return output_path
