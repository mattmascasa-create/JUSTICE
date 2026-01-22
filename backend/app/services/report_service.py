"""
PDF Report Generation Service for JUSTICE Platform
Generates professional court-ready and simple summary reports for evidence highlights.
"""
import io
import os
import qrcode
from datetime import datetime, timezone
from fpdf import FPDF
from PIL import Image

class JusticeReportPDF(FPDF):
    """Custom PDF class for JUSTICE reports"""
    
    def __init__(self, report_style="formal"):
        super().__init__()
        self.report_style = report_style
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        if self.report_style == "formal":
            # Formal header
            self.set_font('Helvetica', 'B', 14)
            self.cell(0, 8, 'JUSTICE PLATFORM - EVIDENCE REPORT', 0, 1, 'C')
            self.set_font('Helvetica', 'I', 10)
            self.cell(0, 5, 'Civil Rights Documentation System', 0, 1, 'C')
            self.line(10, 25, 200, 25)
            self.ln(10)
        else:
            # Simple header
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 8, 'ENCOUNTER HIGHLIGHTS SUMMARY', 0, 1, 'C')
            self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}} | Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} | JUSTICE Platform', 0, 0, 'C')


def generate_highlights_report(
    encounter_data: dict,
    highlights: list,
    report_style: str = "formal",
    include_qr: bool = True,
    share_url: str = None
) -> bytes:
    """
    Generate a PDF report for encounter highlights.
    
    Args:
        encounter_data: Encounter metadata (id, location, duration, etc.)
        highlights: List of evidence highlights
        report_style: "formal" for court-ready, "simple" for quick overview
        include_qr: Whether to include QR code linking to video
        share_url: URL to include in QR code
    
    Returns:
        PDF bytes
    """
    pdf = JusticeReportPDF(report_style=report_style)
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # ===== CASE INFORMATION =====
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'CASE INFORMATION', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', '', 10)
    encounter_id = encounter_data.get('encounter_id', 'N/A')
    started_at = encounter_data.get('started_at', 'N/A')
    if started_at and started_at != 'N/A':
        try:
            dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            started_at = dt.strftime('%B %d, %Y at %I:%M %p UTC')
        except:
            pass
    
    location = encounter_data.get('location', {})
    address = location.get('address', 'Location not recorded')
    duration = encounter_data.get('duration_seconds', 0)
    duration_str = f"{duration // 60}m {duration % 60}s" if duration else "N/A"
    encounter_type = encounter_data.get('encounter_type', 'N/A').replace('_', ' ').title()
    
    info_lines = [
        ('Encounter ID:', encounter_id),
        ('Date/Time:', started_at),
        ('Location:', address),
        ('Duration:', duration_str),
        ('Encounter Type:', encounter_type),
    ]
    
    for label, value in info_lines:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(40, 6, label, 0, 0)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, str(value), 0, 1)
    
    pdf.ln(5)
    
    # ===== EXECUTIVE SUMMARY =====
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'EXECUTIVE SUMMARY', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Count by severity
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    category_counts = {}
    for h in highlights:
        sev = h.get('severity', 'medium').lower()
        cat = h.get('category', 'other')
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f'Total Evidence Highlights Identified: {len(highlights)}', 0, 1)
    pdf.ln(2)
    
    # Severity breakdown
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'Severity Breakdown:', 0, 1)
    pdf.set_font('Helvetica', '', 10)
    
    severity_colors = {
        'critical': (220, 53, 69),
        'high': (253, 126, 20),
        'medium': (255, 193, 7),
        'low': (13, 110, 253)
    }
    
    for sev, count in severity_counts.items():
        if count > 0:
            r, g, b = severity_colors.get(sev, (128, 128, 128))
            pdf.set_fill_color(r, g, b)
            pdf.set_text_color(255 if sev in ['critical', 'high', 'low'] else 0)
            pdf.cell(20, 6, f' {sev.upper()} ', 0, 0, 'C', fill=True)
            pdf.set_text_color(0)
            pdf.cell(0, 6, f'  {count} highlight(s)', 0, 1)
    
    pdf.ln(3)
    
    # Category breakdown
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'Categories Identified:', 0, 1)
    pdf.set_font('Helvetica', '', 10)
    
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        cat_display = cat.replace('_', ' ').title()
        pdf.cell(0, 5, f'  - {cat_display}: {count}', 0, 1)
    
    pdf.ln(5)
    
    # ===== DETAILED HIGHLIGHTS =====
    if report_style == "formal":
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'DETAILED EVIDENCE HIGHLIGHTS', 0, 1, 'L', fill=True)
        pdf.ln(2)
        
        for i, h in enumerate(highlights, 1):
            # Highlight header
            sev = h.get('severity', 'medium').lower()
            r, g, b = severity_colors.get(sev, (128, 128, 128))
            
            pdf.set_fill_color(r, g, b)
            pdf.set_text_color(255 if sev in ['critical', 'high', 'low'] else 0)
            pdf.set_font('Helvetica', 'B', 10)
            
            timestamp = h.get('timestamp', 'N/A')
            title = h.get('title', 'Untitled')[:50]
            category = h.get('category', 'N/A').replace('_', ' ').title()
            
            pdf.cell(0, 7, f' #{i} | {timestamp} | {sev.upper()} | {category} ', 0, 1, 'L', fill=True)
            pdf.set_text_color(0)
            
            # Title
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, title, 0, 1)
            
            # Quote
            quote = h.get('quote', '')
            if quote:
                pdf.set_font('Helvetica', 'I', 9)
                pdf.set_text_color(80)
                pdf.multi_cell(0, 5, f'"{quote}"')
                pdf.set_text_color(0)
            
            # Description
            desc = h.get('description', '')
            if desc:
                pdf.set_font('Helvetica', '', 9)
                pdf.multi_cell(0, 5, desc)
            
            # Legal relevance
            legal = h.get('legal_relevance', '')
            if legal:
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_text_color(139, 69, 19)
                pdf.cell(0, 5, 'Legal Significance:', 0, 1)
                pdf.set_font('Helvetica', '', 9)
                pdf.multi_cell(0, 5, legal)
                pdf.set_text_color(0)
            
            # Speaker
            speaker = h.get('speaker', '')
            if speaker:
                pdf.set_font('Helvetica', 'I', 8)
                pdf.set_text_color(100)
                pdf.cell(0, 5, f'Speaker: {speaker}', 0, 1)
                pdf.set_text_color(0)
            
            pdf.ln(3)
            
            # Page break if needed
            if pdf.get_y() > 250:
                pdf.add_page()
    
    else:
        # Simple style - table format
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'HIGHLIGHTS TABLE', 0, 1, 'L', fill=True)
        pdf.ln(2)
        
        # Table header
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(20, 7, 'Time', 1, 0, 'C', fill=True)
        pdf.cell(25, 7, 'Severity', 1, 0, 'C', fill=True)
        pdf.cell(35, 7, 'Category', 1, 0, 'C', fill=True)
        pdf.cell(0, 7, 'Title', 1, 1, 'C', fill=True)
        
        # Table rows
        pdf.set_font('Helvetica', '', 8)
        for h in highlights:
            timestamp = h.get('timestamp', 'N/A')
            sev = h.get('severity', 'medium').upper()
            cat = h.get('category', 'N/A').replace('_', ' ').title()
            title = h.get('title', 'N/A')[:40]
            
            pdf.cell(20, 6, timestamp, 1, 0, 'C')
            pdf.cell(25, 6, sev, 1, 0, 'C')
            pdf.cell(35, 6, cat, 1, 0, 'C')
            pdf.cell(0, 6, title, 1, 1, 'L')
    
    # ===== QR CODE =====
    if include_qr and share_url:
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'VIDEO EVIDENCE ACCESS', 0, 1, 'L', fill=True)
        pdf.ln(5)
        
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, 'Scan the QR code below to access the video evidence:', 0, 1)
        pdf.ln(5)
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(share_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to bytes and add to PDF
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Save temporarily
        temp_path = '/tmp/qr_temp.png'
        with open(temp_path, 'wb') as f:
            f.write(img_buffer.getvalue())
        
        pdf.image(temp_path, x=60, w=80)
        
        pdf.ln(5)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.multi_cell(0, 5, f'Direct Link: {share_url}')
        
        # Clean up
        os.remove(temp_path)
    
    # ===== LEGAL DISCLAIMER =====
    if report_style == "formal":
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'LEGAL DISCLAIMER', 0, 1, 'L', fill=True)
        pdf.ln(2)
        
        pdf.set_font('Helvetica', '', 9)
        disclaimer = """This report was generated by the JUSTICE Platform, a civil rights documentation system. The evidence highlights contained herein were identified using artificial intelligence analysis of audio/video recordings and transcriptions.

IMPORTANT NOTICES:

1. AI-Generated Analysis: The highlights and legal relevance notes were generated by AI and should be reviewed by qualified legal counsel before use in legal proceedings.

2. Evidence Integrity: Original audio/video recordings are stored with blockchain-verified timestamps and IPFS hashes to ensure evidence integrity.

3. Chain of Custody: This report represents a summary of identified highlights. Complete evidence including original recordings should be obtained for legal proceedings.

4. Rights Advisory: This documentation is intended to support civil rights protection and legal accountability. All individuals depicted are presumed innocent until proven guilty.

5. Confidentiality: This report may contain sensitive information. Handle in accordance with applicable privacy laws and attorney-client privilege where applicable.

For questions regarding this evidence or to obtain certified copies, please contact the JUSTICE Platform support team."""
        
        pdf.multi_cell(0, 5, disclaimer)
    
    # Generate PDF bytes
    return pdf.output()


def generate_simple_summary(encounter_data: dict, highlights: list) -> str:
    """Generate a plain text summary for quick reference"""
    lines = []
    lines.append("=" * 50)
    lines.append("ENCOUNTER HIGHLIGHTS SUMMARY")
    lines.append("=" * 50)
    lines.append(f"Encounter ID: {encounter_data.get('encounter_id', 'N/A')}")
    lines.append(f"Date: {encounter_data.get('started_at', 'N/A')}")
    lines.append(f"Location: {encounter_data.get('location', {}).get('address', 'N/A')}")
    lines.append(f"Total Highlights: {len(highlights)}")
    lines.append("")
    
    for i, h in enumerate(highlights, 1):
        lines.append(f"--- Highlight #{i} ---")
        lines.append(f"Time: {h.get('timestamp', 'N/A')}")
        lines.append(f"Severity: {h.get('severity', 'N/A').upper()}")
        lines.append(f"Category: {h.get('category', 'N/A').replace('_', ' ').title()}")
        lines.append(f"Title: {h.get('title', 'N/A')}")
        if h.get('quote'):
            lines.append(f"Quote: \"{h.get('quote')}\"")
        if h.get('legal_relevance'):
            lines.append(f"Legal Note: {h.get('legal_relevance')}")
        lines.append("")
    
    return "\n".join(lines)
