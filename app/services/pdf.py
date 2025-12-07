"""PDF generation for Norwood certifications."""

import os
from datetime import datetime
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# Colors
GOLD = HexColor("#C9A227")
NAVY = HexColor("#1a365d")
DARK_GRAY = HexColor("#2d3748")
CREAM = HexColor("#f7f3e8")

# Asset paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SEAL_PATH = os.path.join(ASSETS_DIR, "seal.png")
SIGNATURE_PATH = os.path.join(ASSETS_DIR, "signature.png")


def generate_certification_pdf(
    user_name: str,
    norwood_stage: int,
    norwood_variant: str | None,
    confidence: float,
    clinical_assessment: str,
    certified_at: datetime,
) -> bytes:
    """
    Generate university-style certification PDF.

    Args:
        user_name: Name to appear on certificate
        norwood_stage: Norwood stage (1-7)
        norwood_variant: Variant if applicable ('A' or 'V')
        confidence: Confidence score (0.0-1.0)
        clinical_assessment: Clinical assessment text
        certified_at: Certification date

    Returns:
        PDF file as bytes
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Draw ornate border
    _draw_border(c, width, height)

    # Header
    c.setFont("Times-Bold", 22)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 1.3 * inch, "CERTIFICATE OF NORWOOD CLASSIFICATION")

    # Subtitle
    c.setFont("Times-Italic", 14)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 2 * inch, "Official Hair Loss Assessment")

    # Decorative line
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(1.5 * inch, height - 2.3 * inch, width - 1.5 * inch, height - 2.3 * inch)

    # "This certifies that"
    c.setFont("Times-Roman", 12)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 3 * inch, "This is to certify that")

    # Name
    c.setFont("Times-Bold", 24)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 3.5 * inch, user_name)

    # Decorative line under name
    name_width = c.stringWidth(user_name, "Times-Bold", 24)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(
        (width - name_width) / 2 - 20,
        height - 3.6 * inch,
        (width + name_width) / 2 + 20,
        height - 3.6 * inch,
    )

    # "has been officially classified as"
    c.setFont("Times-Roman", 12)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 4.1 * inch, "has been officially classified as")

    # Norwood Stage (big)
    stage_text = f"NORWOOD STAGE {norwood_stage}"
    if norwood_variant:
        stage_text += norwood_variant
    c.setFont("Times-Bold", 36)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 4.8 * inch, stage_text)

    # Confidence
    confidence_pct = int(confidence * 100)
    c.setFont("Times-Italic", 11)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(
        width / 2, height - 5.2 * inch, f"Classification Confidence: {confidence_pct}%"
    )

    # Clinical assessment box
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.5)
    c.rect(1 * inch, height - 7.5 * inch, width - 2 * inch, 1.8 * inch)

    c.setFont("Times-Bold", 10)
    c.setFillColor(NAVY)
    c.drawString(1.2 * inch, height - 5.9 * inch, "CLINICAL ASSESSMENT")

    # Wrap and draw clinical assessment text
    c.setFont("Times-Roman", 9)
    c.setFillColor(DARK_GRAY)
    _draw_wrapped_text(
        c,
        clinical_assessment,
        1.2 * inch,
        height - 6.2 * inch,
        width - 2.4 * inch,
        12,
    )

    # Date
    date_str = certified_at.strftime("%B %d, %Y")
    c.setFont("Times-Roman", 11)
    c.drawCentredString(width / 2, height - 8 * inch, f"Certified on {date_str}")

    # Signature section
    sig_y = height - 9.2 * inch

    # Signature line
    c.setStrokeColor(DARK_GRAY)
    c.setLineWidth(0.5)
    c.line(1.5 * inch, sig_y, 3.5 * inch, sig_y)

    # Signature image (if exists)
    if os.path.exists(SIGNATURE_PATH):
        try:
            sig_img = ImageReader(SIGNATURE_PATH)
            c.drawImage(
                sig_img,
                1.8 * inch,
                sig_y + 0.1 * inch,
                width=1.5 * inch,
                height=0.5 * inch,
                mask="auto",
            )
        except Exception:
            pass  # Skip if image can't be loaded

    c.setFont("Times-Roman", 9)
    c.drawString(1.5 * inch, sig_y - 0.25 * inch, "President & Founder")
    c.drawString(1.5 * inch, sig_y - 0.45 * inch, "Norwood AI")

    # Seal
    seal_x = width - 2.5 * inch
    if os.path.exists(SEAL_PATH):
        try:
            seal_img = ImageReader(SEAL_PATH)
            c.drawImage(
                seal_img,
                seal_x,
                sig_y - 0.5 * inch,
                width=1.2 * inch,
                height=1.2 * inch,
                mask="auto",
            )
        except Exception:
            _draw_placeholder_seal(c, seal_x + 0.6 * inch, sig_y + 0.1 * inch)
    else:
        _draw_placeholder_seal(c, seal_x + 0.6 * inch, sig_y + 0.1 * inch)

    # Footer
    c.setFont("Times-Italic", 8)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(
        width / 2,
        0.5 * inch,
        "This certificate is for educational and entertainment purposes only. Not a medical diagnosis.",
    )

    c.save()
    buffer.seek(0)
    return buffer.read()


def _draw_border(c: canvas.Canvas, width: float, height: float) -> None:
    """Draw ornate double border with corner flourishes."""
    margin = 0.5 * inch

    # Outer border
    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Inner border
    c.setLineWidth(1)
    inner_margin = 0.7 * inch
    c.rect(inner_margin, inner_margin, width - 2 * inner_margin, height - 2 * inner_margin)

    # Corner flourishes (simple L shapes)
    flourish_size = 0.3 * inch
    c.setLineWidth(2)

    # Top-left
    c.line(
        margin + 0.1 * inch,
        height - margin - 0.1 * inch,
        margin + 0.1 * inch + flourish_size,
        height - margin - 0.1 * inch,
    )
    c.line(
        margin + 0.1 * inch,
        height - margin - 0.1 * inch,
        margin + 0.1 * inch,
        height - margin - 0.1 * inch - flourish_size,
    )

    # Top-right
    c.line(
        width - margin - 0.1 * inch,
        height - margin - 0.1 * inch,
        width - margin - 0.1 * inch - flourish_size,
        height - margin - 0.1 * inch,
    )
    c.line(
        width - margin - 0.1 * inch,
        height - margin - 0.1 * inch,
        width - margin - 0.1 * inch,
        height - margin - 0.1 * inch - flourish_size,
    )

    # Bottom-left
    c.line(
        margin + 0.1 * inch,
        margin + 0.1 * inch,
        margin + 0.1 * inch + flourish_size,
        margin + 0.1 * inch,
    )
    c.line(
        margin + 0.1 * inch,
        margin + 0.1 * inch,
        margin + 0.1 * inch,
        margin + 0.1 * inch + flourish_size,
    )

    # Bottom-right
    c.line(
        width - margin - 0.1 * inch,
        margin + 0.1 * inch,
        width - margin - 0.1 * inch - flourish_size,
        margin + 0.1 * inch,
    )
    c.line(
        width - margin - 0.1 * inch,
        margin + 0.1 * inch,
        width - margin - 0.1 * inch,
        margin + 0.1 * inch + flourish_size,
    )


def _draw_placeholder_seal(c: canvas.Canvas, x: float, y: float) -> None:
    """Draw a placeholder seal circle."""
    c.setStrokeColor(GOLD)
    c.setFillColor(CREAM)
    c.setLineWidth(2)
    c.circle(x, y, 0.5 * inch, fill=1)

    # Inner circle
    c.setLineWidth(1)
    c.circle(x, y, 0.4 * inch, fill=0)

    c.setFillColor(NAVY)
    c.setFont("Times-Bold", 10)
    c.drawCentredString(x, y + 0.08 * inch, "NORWOOD")
    c.setFont("Times-Bold", 8)
    c.drawCentredString(x, y - 0.12 * inch, "AI")


def _draw_wrapped_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    line_height: float,
) -> None:
    """Draw text wrapped to max_width."""
    words = text.split()
    lines = []
    current_line: list[str] = []

    for word in words:
        test_line = " ".join(current_line + [word])
        if c.stringWidth(test_line, "Times-Roman", 9) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    for i, line in enumerate(lines[:8]):  # Max 8 lines
        c.drawString(x, y - (i * line_height), line)


def generate_cock_certification_pdf(
    user_name: str,
    length_inches: float,
    girth_inches: float,
    size_category: str,
    pleasure_zone: str,
    pleasure_zone_label: str,
    description: str,
    confidence: float,
    certified_at: datetime,
) -> bytes:
    """
    Generate cock certification PDF.

    Args:
        user_name: Name to appear on certificate
        length_inches: Measured length
        girth_inches: Measured girth
        size_category: Size category (micro, below_average, etc.)
        pleasure_zone: Pleasure zone (A-E)
        pleasure_zone_label: Human readable pleasure zone label
        description: Clinical description
        confidence: Confidence score (0.0-1.0)
        certified_at: Certification date

    Returns:
        PDF file as bytes
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Draw ornate border
    _draw_border(c, width, height)

    # Header
    c.setFont("Times-Bold", 22)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 1.3 * inch, "CERTIFICATE OF COCK CLASSIFICATION")

    # Subtitle
    c.setFont("Times-Italic", 14)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 2 * inch, "Official Pleasure Zone Assessment")

    # Decorative line
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(1.5 * inch, height - 2.3 * inch, width - 1.5 * inch, height - 2.3 * inch)

    # "This certifies that"
    c.setFont("Times-Roman", 12)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 3 * inch, "This is to certify that")

    # Name
    c.setFont("Times-Bold", 24)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 3.5 * inch, user_name)

    # Decorative line under name
    name_width = c.stringWidth(user_name, "Times-Bold", 24)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(
        (width - name_width) / 2 - 20,
        height - 3.6 * inch,
        (width + name_width) / 2 + 20,
        height - 3.6 * inch,
    )

    # "has been officially classified as"
    c.setFont("Times-Roman", 12)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 4.1 * inch, "has been officially measured and classified in")

    # Pleasure Zone (big)
    c.setFont("Times-Bold", 36)
    c.setFillColor(NAVY)
    c.drawCentredString(width / 2, height - 4.7 * inch, f"ZONE {pleasure_zone.upper()}")

    # Pleasure zone label
    c.setFont("Times-Italic", 16)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 5.1 * inch, f'"{pleasure_zone_label}"')

    # Measurements box
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.5)
    c.rect(1.3 * inch, height - 6.3 * inch, width - 2.6 * inch, 0.9 * inch)

    c.setFont("Times-Bold", 11)
    c.setFillColor(NAVY)
    measurements_y = height - 5.7 * inch
    c.drawCentredString(
        width / 2,
        measurements_y,
        f"Length: {length_inches:.1f}\"  |  Girth: {girth_inches:.1f}\"  |  Category: {size_category.replace('_', ' ').title()}",
    )

    # Confidence
    confidence_pct = int(confidence * 100)
    c.setFont("Times-Italic", 10)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(width / 2, height - 6.1 * inch, f"Measurement Confidence: {confidence_pct}%")

    # Description box
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.5)
    c.rect(1 * inch, height - 8.3 * inch, width - 2 * inch, 1.7 * inch)

    c.setFont("Times-Bold", 10)
    c.setFillColor(NAVY)
    c.drawString(1.2 * inch, height - 6.8 * inch, "CLINICAL ASSESSMENT")

    # Wrap and draw description text
    c.setFont("Times-Roman", 9)
    c.setFillColor(DARK_GRAY)
    _draw_wrapped_text(
        c,
        description,
        1.2 * inch,
        height - 7.1 * inch,
        width - 2.4 * inch,
        12,
    )

    # Date
    date_str = certified_at.strftime("%B %d, %Y")
    c.setFont("Times-Roman", 11)
    c.drawCentredString(width / 2, height - 8.7 * inch, f"Certified on {date_str}")

    # Signature section
    sig_y = height - 9.7 * inch

    # Signature line
    c.setStrokeColor(DARK_GRAY)
    c.setLineWidth(0.5)
    c.line(1.5 * inch, sig_y, 3.5 * inch, sig_y)

    # Signature image (if exists)
    if os.path.exists(SIGNATURE_PATH):
        try:
            sig_img = ImageReader(SIGNATURE_PATH)
            c.drawImage(
                sig_img,
                1.8 * inch,
                sig_y + 0.1 * inch,
                width=1.5 * inch,
                height=0.5 * inch,
                mask="auto",
            )
        except Exception:
            pass

    c.setFont("Times-Roman", 9)
    c.drawString(1.5 * inch, sig_y - 0.25 * inch, "Chief Measurement Officer")
    c.drawString(1.5 * inch, sig_y - 0.45 * inch, "Norwood AI")

    # Seal
    seal_x = width - 2.5 * inch
    if os.path.exists(SEAL_PATH):
        try:
            seal_img = ImageReader(SEAL_PATH)
            c.drawImage(
                seal_img,
                seal_x,
                sig_y - 0.5 * inch,
                width=1.2 * inch,
                height=1.2 * inch,
                mask="auto",
            )
        except Exception:
            _draw_placeholder_seal(c, seal_x + 0.6 * inch, sig_y + 0.1 * inch)
    else:
        _draw_placeholder_seal(c, seal_x + 0.6 * inch, sig_y + 0.1 * inch)

    # Footer
    c.setFont("Times-Italic", 8)
    c.setFillColor(DARK_GRAY)
    c.drawCentredString(
        width / 2,
        0.5 * inch,
        "This certificate is for educational and entertainment purposes only. Not a medical assessment.",
    )

    c.save()
    buffer.seek(0)
    return buffer.read()
