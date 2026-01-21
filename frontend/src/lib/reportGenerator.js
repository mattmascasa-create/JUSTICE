import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { format } from 'date-fns';

export async function generateCaseReport(reportData) {
  const { case: caseData, evidence, timeline, user, generated_at, report_id } = reportData;
  
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 20;
  let yPos = 20;

  // Helper function to add text with word wrap
  const addText = (text, x, y, maxWidth, fontSize = 10) => {
    doc.setFontSize(fontSize);
    const lines = doc.splitTextToSize(text, maxWidth);
    doc.text(lines, x, y);
    return y + (lines.length * fontSize * 0.4);
  };

  // Header
  doc.setFillColor(15, 23, 42); // Dark blue
  doc.rect(0, 0, pageWidth, 40, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(24);
  doc.setFont('helvetica', 'bold');
  doc.text('JUSTICE', margin, 25);
  
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text('Constitutional Rights Protection Platform', margin, 33);
  
  doc.setFontSize(8);
  doc.text(`Report ID: ${report_id}`, pageWidth - margin - 50, 25);
  doc.text(`Generated: ${format(new Date(generated_at), 'MMM dd, yyyy HH:mm')}`, pageWidth - margin - 50, 33);

  yPos = 55;
  doc.setTextColor(0, 0, 0);

  // Case Title Section
  doc.setFillColor(248, 250, 252);
  doc.rect(margin, yPos - 5, pageWidth - 2 * margin, 25, 'F');
  
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('CASE REPORT', margin + 5, yPos + 5);
  
  doc.setFontSize(12);
  doc.setFont('helvetica', 'normal');
  yPos = addText(caseData.title, margin + 5, yPos + 15, pageWidth - 2 * margin - 10, 12);
  
  yPos += 15;

  // Case Details
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text('Case Details', margin, yPos);
  yPos += 8;

  const caseDetails = [
    ['Case ID', caseData.case_id],
    ['Status', caseData.status.toUpperCase()],
    ['Severity', caseData.severity.toUpperCase()],
    ['Violation Type', caseData.violation_type],
    ['Incident Date', format(new Date(caseData.incident_date), 'MMMM dd, yyyy')],
    ['Location', caseData.location],
    ['Department', caseData.department || 'Not specified'],
    ['Officer Name', caseData.officer_name || 'Not specified'],
    ['Officer Badge', caseData.officer_badge || 'Not specified'],
    ['Created', format(new Date(caseData.created_at), 'MMM dd, yyyy HH:mm')],
    ['Last Updated', format(new Date(caseData.updated_at), 'MMM dd, yyyy HH:mm')],
  ];

  autoTable(doc, {
    startY: yPos,
    head: [],
    body: caseDetails,
    theme: 'plain',
    styles: { fontSize: 9, cellPadding: 3 },
    columnStyles: {
      0: { fontStyle: 'bold', cellWidth: 40 },
      1: { cellWidth: 100 }
    },
    margin: { left: margin, right: margin }
  });

  yPos = doc.lastAutoTable.finalY + 15;

  // Description
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text('Incident Description', margin, yPos);
  yPos += 8;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  yPos = addText(caseData.description, margin, yPos, pageWidth - 2 * margin, 9);
  yPos += 10;

  // Check if we need a new page
  if (yPos > 250) {
    doc.addPage();
    yPos = 20;
  }

  // Evidence Section
  if (evidence && evidence.length > 0) {
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(`Evidence (${evidence.length} files)`, margin, yPos);
    yPos += 8;

    const evidenceData = evidence.map((ev, index) => [
      index + 1,
      ev.file_name,
      ev.file_type,
      `${(ev.file_size / 1024).toFixed(1)} KB`,
      format(new Date(ev.uploaded_at), 'MMM dd, yyyy'),
      ev.blockchain_hash ? '✓ Verified' : 'Pending'
    ]);

    autoTable(doc, {
      startY: yPos,
      head: [['#', 'File Name', 'Type', 'Size', 'Uploaded', 'Blockchain']],
      body: evidenceData,
      theme: 'striped',
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [59, 130, 246], textColor: 255 },
      margin: { left: margin, right: margin }
    });

    yPos = doc.lastAutoTable.finalY + 15;
  }

  // Check if we need a new page
  if (yPos > 250) {
    doc.addPage();
    yPos = 20;
  }

  // Timeline Section
  if (timeline && timeline.length > 0) {
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('Case Timeline', margin, yPos);
    yPos += 8;

    const timelineData = timeline.map(event => [
      format(new Date(event.created_at), 'MMM dd, yyyy HH:mm'),
      event.event_type.replace('_', ' ').toUpperCase(),
      event.description
    ]);

    autoTable(doc, {
      startY: yPos,
      head: [['Date/Time', 'Event', 'Description']],
      body: timelineData,
      theme: 'striped',
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [59, 130, 246], textColor: 255 },
      columnStyles: {
        0: { cellWidth: 35 },
        1: { cellWidth: 30 },
        2: { cellWidth: 85 }
      },
      margin: { left: margin, right: margin }
    });

    yPos = doc.lastAutoTable.finalY + 15;
  }

  // Footer on last page
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(128, 128, 128);
    doc.text(
      `Page ${i} of ${pageCount} | JUSTICE Platform | Confidential Case Report`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 10,
      { align: 'center' }
    );
  }

  // Disclaimer
  doc.setPage(pageCount);
  yPos = doc.internal.pageSize.getHeight() - 30;
  doc.setFillColor(254, 243, 199);
  doc.rect(margin, yPos - 5, pageWidth - 2 * margin, 15, 'F');
  doc.setTextColor(146, 64, 14);
  doc.setFontSize(7);
  doc.text(
    'DISCLAIMER: This report is generated for informational purposes. It does not constitute legal advice. Consult a licensed attorney for legal matters.',
    margin + 5,
    yPos + 3
  );

  return doc;
}

export function downloadCaseReport(doc, caseId) {
  doc.save(`JUSTICE_Case_Report_${caseId}.pdf`);
}

export function openCaseReportInNewTab(doc) {
  const pdfBlob = doc.output('blob');
  const pdfUrl = URL.createObjectURL(pdfBlob);
  window.open(pdfUrl, '_blank');
}
