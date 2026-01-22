"""
PDF Report Generation Service for JUSTICE Platform
Generates professional court-ready and simple summary reports for evidence highlights.
"""
import io
import os
import qrcode
from datetime import datetime, timezone
from fpdf import FPDF

class JusticeReportPDF(FPDF):
    """Custom PDF class for JUSTICE reports"""
    
    def __init__(self, report_style="formal"):
        super().__init__()
        self.report_style = report_style
        self.set_auto_page_break(auto=True, margin=20)
        
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 8, 'JUSTICE PLATFORM - EVIDENCE REPORT', 0, 1, 'C')
        if self.report_style == "formal":
            self.set_font('Helvetica', 'I', 10)
            self.cell(0, 5, 'Civil Rights Documentation System', 0, 1, 'C')
        self.line(10, 25, 200, 25)
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()} | Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}', 0, 0, 'C')
        self.set_text_color(0)


def generate_highlights_report(
    encounter_data: dict,
    highlights: list,
    report_style: str = "formal",
    include_qr: bool = True,
    share_url: str = None
) -> bytes:
    """
    Generate a PDF report for encounter highlights.
    """
    pdf = JusticeReportPDF(report_style=report_style)
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
    address = location.get('address', 'Location not recorded') if isinstance(location, dict) else str(location)
    duration = encounter_data.get('duration_seconds', 0)
    duration_str = f"{duration // 60}m {duration % 60}s" if duration else "N/A"
    encounter_type = str(encounter_data.get('encounter_type', 'N/A')).replace('_', ' ').title()
    
    info_lines = [
        ('Encounter ID:', str(encounter_id)),
        ('Date/Time:', str(started_at)),
        ('Location:', str(address) if address else 'N/A'),
        ('Duration:', str(duration_str)),
        ('Encounter Type:', str(encounter_type)),
    ]
    
    for label, value in info_lines:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(40, 6, label, 0, 0)
        pdf.set_font('Helvetica', '', 10)
        # Truncate long values
        value = value[:80] if len(value) > 80 else value
        pdf.cell(0, 6, value, 0, 1)
    
    pdf.ln(5)
    
    # ===== EXECUTIVE SUMMARY =====
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'EXECUTIVE SUMMARY', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Count by severity
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    category_counts = {}
    for h in highlights:
        sev = str(h.get('severity', 'medium')).lower()
        cat = str(h.get('category', 'other'))
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f'Total Evidence Highlights: {len(highlights)}', 0, 1)
    pdf.ln(2)
    
    # Severity breakdown
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'By Severity:', 0, 1)
    pdf.set_font('Helvetica', '', 10)
    
    for sev, count in severity_counts.items():
        if count > 0:
            pdf.cell(0, 5, f'  {sev.upper()}: {count}', 0, 1)
    
    pdf.ln(3)
    
    # Category breakdown
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'By Category:', 0, 1)
    pdf.set_font('Helvetica', '', 10)
    
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        cat_display = cat.replace('_', ' ').title()
        pdf.cell(0, 5, f'  {cat_display}: {count}', 0, 1)
    
    pdf.ln(5)
    
    # ===== DETAILED HIGHLIGHTS =====
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'DETAILED HIGHLIGHTS', 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    for i, h in enumerate(highlights, 1):
        # Check for page break
        if pdf.get_y() > 240:
            pdf.add_page()
        
        sev = str(h.get('severity', 'medium')).upper()
        timestamp = str(h.get('timestamp', 'N/A'))
        title = str(h.get('title', 'Untitled'))[:60]
        category = str(h.get('category', 'N/A')).replace('_', ' ').title()
        
        # Highlight header
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(0, 7, f'#{i} | {timestamp} | {sev} | {category}', 0, 1, 'L', fill=True)
        
        # Title
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, title, 0, 1)
        
        # Quote
        quote = str(h.get('quote', ''))
        if quote:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(80)
            quote = quote[:150] if len(quote) > 150 else quote
            quote = quote.replace('\n', ' ')
            pdf.cell(0, 5, f'"{quote}"', 0, 1)
            pdf.set_text_color(0)
        
        # Description
        desc = str(h.get('description', ''))
        if desc:
            pdf.set_font('Helvetica', '', 9)
            desc = desc[:200] if len(desc) > 200 else desc
            desc = desc.replace('\n', ' ')
            pdf.cell(0, 5, desc, 0, 1)
        
        # Legal relevance
        legal = str(h.get('legal_relevance', ''))
        if legal:
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(0, 5, 'Legal Note:', 0, 1)
            pdf.set_font('Helvetica', '', 9)
            legal = legal[:200] if len(legal) > 200 else legal
            legal = legal.replace('\n', ' ')
            pdf.cell(0, 5, legal, 0, 1)
        
        pdf.ln(3)
    
    # ===== QR CODE =====
    if include_qr and share_url:
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'VIDEO EVIDENCE ACCESS', 0, 1, 'L', fill=True)
        pdf.ln(5)
        
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, 'Access video evidence at:', 0, 1)
        pdf.ln(2)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.cell(0, 5, share_url[:100], 0, 1)
    
    # ===== DISCLAIMER =====
    if report_style == "formal":
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'LEGAL DISCLAIMER', 0, 1, 'L', fill=True)
        pdf.ln(2)
        
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(0, 5, 'This report was generated by the JUSTICE Platform.', 0, 1)
        pdf.cell(0, 5, 'Evidence highlights were identified using AI analysis.', 0, 1)
        pdf.cell(0, 5, 'Please review with qualified legal counsel.', 0, 1)
        pdf.ln(2)
        pdf.cell(0, 5, 'Original recordings have blockchain-verified timestamps.', 0, 1)
        pdf.cell(0, 5, 'All individuals are presumed innocent until proven guilty.', 0, 1)
    
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
